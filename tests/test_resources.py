"""Verify the runtime resources."""

import unittest
from importlib.resources import files

from controlchartspy._engine import SCRIPTS


class ResourceTests(unittest.TestCase):
    def test_vendored_assets_are_packaged(self) -> None:
        package = files("controlchartspy")
        self.assertTrue(package.joinpath("py.typed").is_file())
        vendor = package.joinpath("_vendor")
        self.assertSetEqual(
            {path.name for path in vendor.iterdir() if path.name.endswith(".js")},
            set(SCRIPTS),
        )


if __name__ == "__main__":
    unittest.main()
