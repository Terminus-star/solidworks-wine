"""Audit vendor media before allowing the core MSI to change the prefix."""
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile


def missing_toolbox_files(media: Path):
    catalog = media / 'sldim/sldim.xml'
    if not catalog.is_file():
        raise ValueError(f'Media catalog is missing: {catalog}')
    root = ET.parse(catalog).getroot()
    names = {node.findtext('FileName') for node in root.findall('.//SourceFile')
             if node.findtext('SourcePath', '').lower() == 'toolbox'}
    if not names:
        raise ValueError('The media catalog contains no Toolbox source files.')
    return [str(media / 'toolbox' / name) for name in sorted(names)
            if not (media / 'toolbox' / name).is_file()]


def spatial_payload_issues(archive: Path, target: Path):
    issues = []
    with zipfile.ZipFile(archive) as package:
        for info in package.infolist():
            if info.is_dir():
                continue
            relative = Path(info.filename.replace('\\', '/'))
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('Spatial archive contains an unsafe member path.')
            path = target / relative
            if not path.is_file() or path.stat().st_size != info.file_size:
                issues.append(str(relative))
    return issues
