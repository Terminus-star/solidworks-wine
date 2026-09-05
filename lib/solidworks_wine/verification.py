"""Verify real MSI feature state and payload presence, independent of exit code."""
import re
from .msi import REQUIRED, helper_output


def is_registry_source_marker(attributes, path):
    """Wine 9.22 confuses encoded registry roots with disk-source prefixes."""
    return bool(attributes & 4 and re.match(r'^0[0-3]:\\', path))


def audit_source_states(msi, product, states):
    source_features = {name for name, state in states.items() if name != 'product' and state == '4'}
    if not source_features:
        return {}
    links = msi.query('SELECT `Feature_`, `Component_` FROM `FeatureComponents`')
    components = {row[0]: (row[1], int(row[2])) for row in msi.query(
        'SELECT `Component`, `ComponentId`, `Attributes` FROM `Component`')}
    names = sorted({component for feature, component in links if feature in source_features
                    and components[component][0]})
    paths = {}
    for start in range(0, len(names), 100):
        result = helper_output(msi.command('components', product,
                               *[components[name][0] for name in names[start:start+100]]), check=True)
        for line in result.stdout.splitlines():
            row = line.split('\t', 2)
            if len(row) == 3:
                paths[row[0]] = (row[1], row[2])
    audit = {}
    for feature in sorted(source_features):
        markers = []
        issues = []
        local_files = 0
        for owner, name in links:
            if owner != feature:
                continue
            guid, attributes = components[name]
            if not guid:
                continue
            if guid not in paths:
                issues.append(name)
                continue
            state, path = paths[guid]
            if re.match(r'^\d\d.', path):
                if is_registry_source_marker(attributes, path):
                    markers.append(name)
                else:
                    issues.append(name)
            elif path and not path.startswith('<\\'):
                # Empty paths are conditionally excluded components. <\ is a
                # registered managed-assembly identity, not a source marker.
                if state != '3' or not path.upper().startswith('C:\\'):
                    issues.append(name)
                else:
                    local_files += 1
        audit[feature] = {'registry_markers': markers, 'local_keypaths': local_files,
                          'unexpected_keypaths': issues, 'explained': bool(markers) and not issues}
    return audit


def verify(msi, prefix, plan):
    product = plan['product']['ProductCode']
    result = helper_output(msi.command('verify', product, *plan['features']))
    states = dict(line.split('\t', 1) for line in result.stdout.splitlines() if '\t' in line)
    base = prefix / 'drive_c/Program Files/SOLIDWORKS Corp/SOLIDWORKS'
    # File and Component tables place the UI resource in lang/english; this
    # release has no sldworks.dll. Check actual package files, not guessed names.
    paths = [base / name for name in ('SLDWORKS.exe', 'sldappu.dll', 'lang/english/sldresu.dll')]
    files = {str(p.relative_to(prefix)): p.is_file() and p.stat().st_size > 0 for p in paths}
    source_audit = audit_source_states(msi, product, states)
    valid = result.returncode in (0, 1) and states.get('product') == '5' and all(files.values())
    valid = valid and all(states.get(name) == '3' or
                          (states.get(name) == '4' and source_audit.get(name, {}).get('explained'))
                          for name in (*REQUIRED, *plan['features']))
    return {'verified': valid, 'product': product, 'feature_states': states, 'files': files,
            'source_state_audit': source_audit,
            'scope': 'MSI registration, selected features, and core payload; runtime/activation checked separately'}
