"""Copy the shared JavaScript assets from an R controlcharts checkout."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ASSETS = {
    "minidom.js": "inst/js/minidom.js",
    "ccCore.js": "inst/htmlwidgets/lib/UTILS/ccCore.js",
    "PBISPC.js": "inst/htmlwidgets/lib/PBISPC/PBISPC.js",
    "PBIFUN.js": "inst/htmlwidgets/lib/PBIFUN/PBIFUN.js",
    "commonUtils.js": "inst/htmlwidgets/lib/UTILS/commonUtils.js",
    "headlessUtils.js": "inst/htmlwidgets/lib/UTILS/headlessUtils.js",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("controlcharts", type=Path)
    args = parser.parse_args()
    controlcharts: Path = args.controlcharts
    root = Path(__file__).resolve().parents[1]
    destination = root / "src/controlchartspy/_vendor"
    destination.mkdir(parents=True, exist_ok=True)
    for path in destination.glob("*.js"):
        if path.name not in ASSETS:
            path.unlink()
    git = ["git", "-C", str(controlcharts)]
    revision = subprocess.check_output(git + ["rev-parse", "HEAD"], text=True).strip()
    repository = subprocess.check_output(
        git + ["remote", "get-url", "origin"], text=True
    ).strip()
    assets: dict[str, dict[str, str]] = {}
    manifest = {"repository": repository, "revision": revision, "assets": assets}
    for name, relative in ASSETS.items():
        source = subprocess.check_output(git + ["show", f"{revision}:{relative}"])
        (destination / name).write_bytes(source)
        assets[name] = {
            "source": relative,
            "sha256": hashlib.sha256(source).hexdigest(),
        }
    license_text = subprocess.check_output(git + ["show", f"{revision}:LICENSE.md"])
    licenses = root / "licenses"
    licenses.mkdir(exist_ok=True)
    (licenses / "controlcharts-LICENSE.txt").write_bytes(license_text)
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
