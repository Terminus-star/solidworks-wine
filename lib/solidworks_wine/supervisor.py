"""Bound installer time, CPU concurrency, and output; clean up only its prefix."""
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def prefix_processes(prefix):
    matches = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdecimal():
            continue
        try:
            env = (proc / 'environ').read_bytes().split(b'\0')
            value = next((x[11:] for x in env if x.startswith(b'WINEPREFIX=')), None)
            if value and Path(os.fsdecode(value)).resolve() == prefix.resolve():
                command = (proc / 'comm').read_text().strip()
                matches.append((int(proc.name), command))
        except (OSError, ValueError):
            pass
    return matches


def ensure_idle(prefix):
    busy = [(pid, name) for pid, name in prefix_processes(prefix)
            if any(x in name.lower() for x in ('sldim', 'msiexec', 'msi-tool', 'sldworks', 'setup.exe'))]
    if busy:
        raise ValueError(f"Prefix already has an installer/application running: {busy}")


def lock_prefix(prefix):
    handle = (prefix / '.solidworks-install.lock').open('a')
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        raise ValueError("Another installation controller holds this prefix lock.") from None
    return handle


def supervise(command, serial, directory, prefix, timeout=1800, idle_timeout=240, max_bytes=256*1024*1024):
    console = directory / 'console.private.log'
    msi_log = directory / 'msi.private.log'
    state = directory / 'state.json'
    start = time.monotonic()
    last_change = start
    last_size = 0
    last_io = None
    last_report = 0
    reason = None
    cpus = sorted(os.sched_getaffinity(0))[:4]
    bounded = ['nice', '-n', '10', 'taskset', '-c', ','.join(map(str, cpus)), *command]
    with console.open('wb') as output:
        process = subprocess.Popen(bounded, stdin=subprocess.PIPE, stdout=output,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            process.stdin.write((serial + '\n').encode('ascii'))
            process.stdin.close()
            while process.poll() is None:
                now = time.monotonic()
                size = sum(p.stat().st_size for p in (console, msi_log) if p.exists())
                try:
                    counters = dict(line.split(': ', 1) for line in
                                    Path(f'/proc/{process.pid}/io').read_text().splitlines())
                    io = (int(counters['read_bytes']), int(counters['write_bytes']))
                except (OSError, KeyError, ValueError):
                    io = last_io
                if size != last_size or io != last_io:
                    last_change = now
                    last_size = size
                    last_io = io
                if size > max_bytes:
                    reason = 'log-limit'
                elif now - start > timeout:
                    reason = 'wall-timeout'
                elif now - last_change > idle_timeout:
                    reason = 'no-install-progress'
                snapshot = {'pid': process.pid, 'elapsed_seconds': round(now-start),
                            'output_bytes': size, 'status': 'stopping' if reason else 'running',
                            'reason': reason, 'io_bytes': io}
                state.write_text(json.dumps(snapshot, indent=2) + '\n')
                if now - last_report >= 30:
                    print(f"Installer: {snapshot['elapsed_seconds']}s elapsed, {size//1024} KiB output; PID {process.pid}", flush=True)
                    last_report = now
                if reason:
                    break
                time.sleep(2)
        except BaseException:
            reason = 'controller-interrupted'
            raise
        finally:
            if reason:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                subprocess.run([os.environ['WINESERVER'], '-k'], timeout=15, check=False,
                               env=dict(os.environ, WINEPREFIX=str(prefix.resolve())),
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            rc = process.wait(timeout=15)
            state.write_text(json.dumps({'pid': process.pid, 'status': 'stopped' if reason else 'exited',
                                         'reason': reason, 'exit_code': rc,
                                         'elapsed_seconds': round(time.monotonic()-start)}, indent=2)+'\n')
    if reason:
        raise RuntimeError(f"Installer stopped by watchdog: {reason}. Evidence: {directory}")
    return rc
