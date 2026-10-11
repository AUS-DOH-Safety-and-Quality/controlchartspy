"""Check release archives and run the tests against isolated installations."""

import argparse
import email.parser
import subprocess
import tarfile
import zipfile
from pathlib import Path


def check_files(names: set[str], prefix: str, root: Path) -> None:
    required = {prefix + "controlchartspy/py.typed"}
    vendor = root / "src/controlchartspy/_vendor"
    for path in vendor.iterdir():
        required.add(prefix + "controlchartspy/_vendor/" + path.name)
    missing = required - names
    if missing:
        raise ValueError(f"Missing package files: {sorted(missing)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist", type=Path)
    args = parser.parse_args()
    dist: Path = args.dist
    root = Path(__file__).resolve().parents[1]
    wheels = list(dist.glob("*.whl"))
    sources = list(dist.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sources) != 1:
        raise ValueError("Expected one wheel and one source distribution.")
    licenses = {"LICENSE", "NOTICE"}
    for path in (root / "licenses").iterdir():
        licenses.add("licenses/" + path.name)
    with zipfile.ZipFile(wheels[0]) as archive:
        names = set(archive.namelist())
        check_files(names, "", root)
        metadata_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
        prefix = metadata_name.removesuffix("METADATA") + "licenses/"
        for name in licenses:
            if prefix + name not in names:
                raise ValueError(f"Missing wheel license: {name}")
        metadata = email.parser.BytesParser().parsebytes(archive.read(metadata_name))
        if metadata["License-Expression"] != "GPL-3.0-only":
            raise ValueError("Unexpected wheel license expression.")
    with tarfile.open(sources[0]) as archive:
        names = set(archive.getnames())
        prefix = next(name for name in names if name.endswith("/PKG-INFO")).removesuffix("PKG-INFO")
        check_files(names, prefix + "src/", root)
        required = licenses | {"tests/reference_manifest.json", "CHANGELOG.md"}
        for name in required:
            if prefix + name not in names:
                raise ValueError(f"Missing source file: {name}")
    for path in wheels + sources:
        print(f"Testing {path.name}", flush=True)
        subprocess.run(
            ["uv", "run", "--no-project", "--with", str(path.resolve()),
             "python", "-m", "unittest",
             "discover", "-s", str(root / "tests")],
            cwd=root,
            check=True,
        )


if __name__ == "__main__":
    main()
