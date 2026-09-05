"""Read the vendor's MSI tables and select the complete core feature tree."""
import os
import subprocess
import tempfile
from pathlib import Path

ROOTS = {"SolidWorks", "FeatureWorks", "SolidWorksUtilities", "CoreSolidWorksTaskScheduler",
         "ExampleFiles", "Manuals", "HelpFiles", "i386_Treehouse"}
REQUIRED = ("SolidWorks", "ProgramFiles", "i386_ProgramFiles", "i386_SWFiles", "English",
            "FlexLmFiles", "CoreSolidWorksTaskScheduler")


def validate_product(product, target):
    if (product.get('ProductCode', '').upper() != target['core_product_code'].upper()
            or product.get('ProductVersion') != target['msi_version']):
        raise ValueError('Unsupported MSI product/version; this recipe targets only SOLIDWORKS 2026 SP03.2')


def helper_output(command, timeout=45, check=False):
    # Wine services can inherit a helper's stdout. Waiting for pipe EOF then
    # outlives the helper itself; regular temporary files avoid that deadlock.
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        result = subprocess.run(command, stdout=output, stderr=errors, timeout=timeout, check=check)
        output.seek(0)
        errors.seek(0)
        return subprocess.CompletedProcess(command, result.returncode,
                                           output.read().decode('utf-8', errors='replace'),
                                           errors.read().decode('utf-8', errors='replace'))


class MSI:
    def __init__(self, root: Path, media: Path):
        self.wine = os.environ["WINE"]
        self.helper = root / "build/msi-tool.exe"
        self.package = media / "swwi/data/solidworks.msi"
        self.transform = media / "swwi/data/1033.mst"
        for path in (self.helper, self.package, self.transform):
            if not path.is_file():
                raise ValueError(f"Required file is missing: {path}")

    def command(self, *args):
        return [self.wine, str(self.helper), *map(str, args)]

    def query(self, sql):
        result = helper_output(self.command("query", self.package, sql), timeout=40, check=True)
        return [line.split("\t") for line in result.stdout.splitlines() if "\t" in line]

    def plan(self):
        rows = self.query("SELECT `Feature`, `Feature_Parent`, `Level`, `Attributes` FROM `Feature`")
        selected = select_features(rows)
        properties = dict(self.query("SELECT `Property`, `Value` FROM `Property` WHERE `Property` = 'ProductCode' OR `Property` = 'ProductVersion' OR `Property` = 'ProductName'"))
        return {"product": properties, "features": selected, "package": str(self.package)}


def select_features(rows):
    features = {row[0]: (row[1], int(row[2])) for row in rows}
    missing = ROOTS - features.keys()
    if missing:
        raise ValueError(f"Required feature roots missing from this MSI: {sorted(missing)}")
    selected = set(ROOTS)
    while True:
        extra = {name for name, (parent, level) in features.items()
                 if parent in selected and 0 < level <= 100}
        if extra <= selected:
            break
        selected |= extra
    if not set(REQUIRED) <= selected:
        raise ValueError("MSI feature selection does not include the complete core application.")
    return sorted(selected)
