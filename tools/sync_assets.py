"""Download the shared JavaScript assets from a controlcharts git ref."""

import argparse
import urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/AUS-DOH-Safety-and-Quality/controlcharts"
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
    parser.add_argument("ref")
    ref: str = parser.parse_args().ref
    destination = Path(__file__).resolve().parents[1] / "src/controlchartspy/_vendor"
    for name, path in ASSETS.items():
        with urllib.request.urlopen(f"{URL}/{ref}/{path}") as response:
            (destination / name).write_bytes(response.read())


if __name__ == "__main__":
    main()
