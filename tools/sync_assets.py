"""Copy the shared JavaScript assets from an R controlcharts checkout."""

import argparse
import hashlib
import json
import shutil
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
    destination = Path(__file__).resolve().parents[1] / "src/pycontrolcharts/_vendor"
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, relative in ASSETS.items():
        source = args.controlcharts / relative
        shutil.copyfile(source, destination / name)
        manifest[name] = {
            "source": relative,
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
