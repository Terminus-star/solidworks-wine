"""Keep the licensed serial out of command arguments and shareable output."""
import re
from pathlib import Path


def read_log(path: Path) -> str:
    data = path.read_bytes()
    encoding = 'utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
    return data.decode(encoding, errors='replace')


def redact_run(directory: Path, serial: str):
    for name in ('console', 'msi'):
        raw = directory / f'{name}.private.log'
        if raw.exists():
            destination = directory / f'{name}.log'
            destination.write_text(redact(read_log(raw), serial))
            destination.chmod(0o600)


def read_serial(path: Path) -> str:
    serial = re.sub(r"\s+", "", path.read_text()).upper()
    if not re.fullmatch(r"[0-9]{16}[A-Z0-9]{8}", serial):
        raise ValueError("Serial file must contain 16 digits followed by 8 letters/digits.")
    path.chmod(0o600)
    return serial


def redact(text: str, serial: str = "") -> str:
    text = re.sub(r"(?i)((?:serial_number|[?&]sn|explungulation)=)[^&\s\"<>]+", r"\1[REDACTED]", text)
    if serial:
        text = re.sub(r"[\s-]*".join(map(re.escape, serial)), "[SERIAL REDACTED]", text, flags=re.I)
        # The MSI also publishes SOLIDWORKSSERIALNUMBER16 separately.
        text = re.sub(r"[\s-]*".join(map(re.escape, serial[:16])), "[SERIAL REDACTED]", text, flags=re.I)
    text = re.sub(r"(?im)^([^\n]*(?:SERIALNUMBER|Serial Number)[^=\n]*=)[^\n]*", r"\1 [SERIAL REDACTED]", text)
    return re.sub(r"(?<![A-Za-z0-9])(?:[0-9]{4}[ -]?){4}(?:[A-Za-z0-9]{4}[ -]?){2}(?![A-Za-z0-9])",
                  "[SERIAL REDACTED]", text)
