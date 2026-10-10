"""Copy the shared JavaScript assets from an R controlcharts checkout."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ASSETS = {
    "minidom.js": "inst/js/minidom.js",
    "ccD3.js": "inst/htmlwidgets/lib/UTILS/ccD3.js",
    "PBISPC.js": "inst/htmlwidgets/lib/PBISPC/PBISPC.js",
    "PBIFUN.js": "inst/htmlwidgets/lib/PBIFUN/PBIFUN.js",
    "MISC.js": "inst/htmlwidgets/lib/MISC/MISC.js",
    "commonUtils.js": "inst/htmlwidgets/lib/UTILS/commonUtils.js",
    "headlessUtils.js": "inst/htmlwidgets/lib/UTILS/headlessUtils.js",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("controlcharts", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    destination = root / "src/controlchartspy/_vendor"
    destination.mkdir(parents=True, exist_ok=True)
    git = ["git", "-C", str(args.controlcharts)]
    revision = subprocess.check_output(git + ["rev-parse", "HEAD"], text=True).strip()
    repository = subprocess.check_output(
        git + ["remote", "get-url", "origin"], text=True
    ).strip()
    manifest = {"repository": repository, "revision": revision, "assets": {}}
    for name, relative in ASSETS.items():
        source = subprocess.check_output(git + ["show", f"{revision}:{relative}"])
        (destination / name).write_bytes(source)
        manifest["assets"][name] = {
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
