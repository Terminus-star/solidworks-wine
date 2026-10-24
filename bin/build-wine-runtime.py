#!/usr/bin/env python3
"""Prepare pinned Wine source and optionally build a new private runtime."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import signal
import subprocess
import tarfile
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def safe_members(archive, top):
    members = archive.getmembers()
    for member in members:
        path = PurePosixPath(member.name)
        if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0] != top:
            raise ValueError('Unsafe source archive member path')
        if member.isdev() or member.isfifo():
            raise ValueError('Unexpected special file in source archive')
        if member.issym() or member.islnk():
            link = PurePosixPath(member.linkname)
            if link.is_absolute():
                raise ValueError('Absolute source archive link')
            target = path.parent / link if member.issym() else link
            stack = []
            for part in target.parts:
                if part == '..':
                    if not stack:
                        raise ValueError('Source archive link escapes its root')
                    stack.pop()
                elif part != '.':
                    stack.append(part)
            if not stack or stack[0] != top:
                raise ValueError('Source archive link escapes its root')
    return members


def fetch_source(url, destination, expected):
    if destination.exists():
        if sha256(destination) != expected:
            raise ValueError(f'Existing archive checksum differs; preserved: {destination}')
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with tempfile.NamedTemporaryFile(dir=destination.parent, suffix='.part', delete=False) as output:
        partial = Path(output.name)
        with urllib.request.urlopen(url, timeout=30) as response:
            if not response.url.startswith('https://'):
                raise ValueError('Refusing an insecure source redirect')
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > 128 * 1024 * 1024 or time.monotonic() - started > 300:
                    raise ValueError(f'Source download exceeded its bounds; partial retained: {partial}')
                output.write(chunk)
    if sha256(partial) != expected:
        raise ValueError(f'Source checksum mismatch; partial retained: {partial}')
    partial.replace(destination)


def prepare(manifest, work, supplied_archive=None):
    wine = manifest['wine']
    work.mkdir(parents=True, exist_ok=True)
    archive = supplied_archive or ROOT / 'downloads' / (wine['source_directory'] + '.tar.xz')
    if supplied_archive:
        if sha256(archive) != wine['source_sha256']:
            raise ValueError('Supplied Wine archive checksum mismatch')
    else:
        fetch_source(wine['source_url'], archive, wine['source_sha256'])
    expected = {'source_sha256': wine['source_sha256'],
                'patches': {name: sha256(ROOT / name) for name in wine['patches']}}
    source = work / wine['source_directory']
    stamp = work / 'source-manifest.json'
    if source.exists():
        if not stamp.exists() or json.loads(stamp.read_text()) != expected:
            raise ValueError('Existing source tree has a different or incomplete recipe; use a new --work-dir')
        for name in wine['patches']:
            with (ROOT / name).open('rb') as patch:
                subprocess.run(['patch', '--dry-run', '--reverse', '--batch', '--fuzz=0', '-p1'],
                               cwd=source, stdin=patch, check=True, timeout=30)
        return source
    with tarfile.open(archive, 'r:xz') as package:
        package.extractall(work, members=safe_members(package, wine['source_directory']))
    for name in wine['patches']:
        with (ROOT / name).open('rb') as patch:
            subprocess.run(['patch', '--forward', '--batch', '--fuzz=0', '-p1'],
                           cwd=source, stdin=patch, check=True, timeout=30)
    stamp.write_text(json.dumps(expected, indent=2) + '\n')
    return source


def build_commands(source, work, runtime, jobs):
    build64, build32 = work / 'build64', work / 'build32'
    # GCC 15+ defaults to C23, where `bool` is a keyword; Wine 9.22 still uses
    # it as an identifier. Pin C17 for the host compiler (CFLAGS) and the
    # MinGW compiler that builds the PE DLLs (CROSSCFLAGS). configure accepts
    # VAR=value arguments and exports them, like it did for CC= before.
    c17 = '-g -O2 -std=gnu17'
    options = ['--prefix=' + str(runtime), '--without-wayland', '--with-x',
               '--with-freetype', '--with-opengl', '--with-gnutls',
               'CFLAGS=' + c17, 'CROSSCFLAGS=' + c17]
    return [
        (build64, [str(source / 'configure'), '--enable-win64', *options]),
        (build64, ['make', '-j' + str(jobs)]),
        # No CC='gcc -m32' here: configure adds -m32 itself on x86_64 hosts
        # and also sets TARGETFLAGS=-m32 (so the shared widl emits 32-bit
        # proxies) and the 32-bit pkg-config path. Overriding CC makes it
        # detect an i686 host and skip all three.
        (build32, [str(source / 'configure'), '--with-wine64=' + str(build64),
                   '--without-mingw', *options]),
        (build32, ['make', '-j' + str(jobs)]),
        (build32, ['make', 'install']),
        (build64, ['make', 'install']),
    ]


def run_build_step(command, cwd, output, timeout):
    """Terminate the whole compiler process group on timeout/interruption."""
    process = subprocess.Popen(['nice', '-n', '10', *command], cwd=cwd,
                               stdout=output, stderr=subprocess.STDOUT,
                               start_new_session=True)
    try:
        rc = process.wait(timeout=timeout)
        if rc:
            raise subprocess.CalledProcessError(rc, command)
    except BaseException:
        for signum in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(process.pid, signum)
            except ProcessLookupError:
                break
            if signum == signal.SIGTERM:
                # The parent can exit before its children; still send SIGKILL
                # to any surviving members of this private process group.
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
        process.wait(timeout=5)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare-only', action='store_true', help='Verify archive, apply patches, print build recipe; do not compile')
    mode.add_argument('--build', action='store_true', help='Compile/install only into a new empty private runtime directory')
    parser.add_argument('--source-archive', type=Path, help='Use a locally supplied, hash-verified Wine 9.22 source archive')
    parser.add_argument('--work-dir', type=Path, default=ROOT / 'build/repro-wine')
    parser.add_argument('--runtime-dir', type=Path, default=ROOT / 'wine-runtime')
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--step-timeout', type=int, default=7200)
    args = parser.parse_args()
    if not 1 <= args.jobs <= 32 or args.step_timeout < 60:
        parser.error('Use 1–32 jobs and a step timeout of at least 60 seconds')
    os.umask(0o077)
    work, runtime = args.work_dir.resolve(), args.runtime_dir.resolve()
    if runtime in (Path('/'), Path.home(), ROOT, work) or runtime in work.parents:
        parser.error('Unsafe runtime destination')
    if args.build and runtime.exists() and any(runtime.iterdir()):
        parser.error('Runtime already exists and is not empty; it will not be overwritten')
    manifest = json.loads((ROOT / 'reproducibility.json').read_text())
    source = prepare(manifest, work, args.source_archive.resolve() if args.source_archive else None)
    commands = build_commands(source, work, runtime, args.jobs)
    print(json.dumps({'source': str(source), 'runtime': str(runtime),
                      'commands': [{'cwd': str(cwd), 'argv': command} for cwd, command in commands]}, indent=2), flush=True)
    if not args.build:
        return 0
    for tool in ('gcc', 'make', 'flex', 'bison', 'pkg-config', 'x86_64-w64-mingw32-gcc'):
        if not shutil.which(tool):
            raise ValueError('Missing build dependency: ' + tool)
    for index, (cwd, command) in enumerate(commands, 1):
        cwd.mkdir(parents=True, exist_ok=True)
        log = work / f'step-{index}.log'
        print(f'Build step {index}/{len(commands)}; log: {log}', flush=True)
        with log.open('wb') as output:
            run_build_step(command, cwd, output, args.step_timeout)
    subprocess.run([str(runtime / 'bin/wine'), '--version'], check=True, timeout=15)
    shutil.copy2(work / 'source-manifest.json', runtime / 'source-manifest.json')
    print('Private runtime built. Next build helpers, then initialize a NEW prefix.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(f'Wine runtime preparation failed: {error}')
