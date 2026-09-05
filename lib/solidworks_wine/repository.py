"""Fail-closed source-export checks. Never include matched secrets in output."""
import hashlib
from pathlib import PurePosixPath
import re

ROOT_FILES = {'.gitignore', '.gitattributes', 'AGENTS.md', 'README.md', 'LICENSE.md',
              'CONTRIBUTING.md', 'config.example.sh', 'reproducibility.json'}
SOURCE_DIRS = {'bin', 'lib', 'native', 'tests', 'patches', 'docs', 'licenses', '.github'}
SOURCE_SUFFIXES = {'.sh', '.py', '.c', '.cpp', '.h', '.vbs', '.patch', '.md', '.txt', '.json', '.yml', '.yaml'}
FONT_NAMES = {'selawk.ttf', 'selawkb.ttf', 'selawkl.ttf', 'selawksb.ttf', 'selawksl.ttf'}
SERIAL = re.compile(r'(?<![A-Za-z0-9])(?:[0-9][ -]?){16}(?:[A-Z0-9][ -]?){8}(?![A-Za-z0-9])', re.I)
TOKENS = re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[A-Z0-9]{16}|sk-[A-Za-z0-9_-]{32,})\b')
PRIVATE_KEY = re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----')
AUTH_URL = re.compile(r'https?://[^\s/]+:[^\s/]+@', re.I)


def allowed_path(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts:
        return False
    if name in ROOT_FILES:
        return True
    if path.parts[:2] == ('assets', 'fonts') and len(path.parts) == 3:
        return path.name in FONT_NAMES | {'README.md', 'LICENSE.txt', 'SHA256SUMS'}
    if name == 'assets/README.md':
        return True
    return (len(path.parts) > 1 and path.parts[0] in SOURCE_DIRS
            and path.suffix in SOURCE_SUFFIXES and not path.name.endswith('.private.log')
            and '__pycache__' not in path.parts)


def audit_blob(name, mode, data, known_serial='', font_hashes=None):
    issues = []
    if mode not in ('100644', '100755'):
        issues.append('symlink, submodule, or unsupported Git mode')
    if not allowed_path(name):
        issues.append('path is not in the source-publication allowlist')
    if data.startswith((b'MZ', b'\x7fELF', b'PK\x03\x04', b'\xd0\xcf\x11\xe0')):
        issues.append('compiled binary, installer, or archive signature')
    if name.startswith('assets/fonts/') and name.endswith('.ttf'):
        expected = (font_hashes or {}).get(PurePosixPath(name).name)
        if not expected or hashlib.sha256(data).hexdigest() != expected:
            issues.append('font is missing a matching checksum')
    else:
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError:
            text = ''
            issues.append('unexpected binary/non-UTF-8 source')
        if '\0' in text:
            issues.append('unexpected NUL in source')
        if SERIAL.search(text):
            issues.append('possible serial-shaped credential')
        if TOKENS.search(text) or PRIVATE_KEY.search(text) or AUTH_URL.search(text):
            issues.append('possible authentication credential')
    if known_serial:
        compact = re.sub(r'[\s-]', '', known_serial).upper()
        if len(compact) == 24:
            for fragment in (compact, compact[:16]):
                variants = {fragment, ' '.join(fragment[i:i+4] for i in range(0, len(fragment), 4)),
                            '-'.join(fragment[i:i+4] for i in range(0, len(fragment), 4))}
                if any(value.lower().encode(encoding) in data.lower()
                       for value in variants for encoding in ('utf-8', 'utf-16-le', 'utf-16-be')):
                    issues.append('contains local license material')
                    break
    return sorted(set(issues))
