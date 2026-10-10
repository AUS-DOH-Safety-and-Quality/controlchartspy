"""Verify the runtime resources and their upstream provenance."""

import hashlib
import json
import unittest
from importlib.resources import files
from pathlib import Path


class ResourceTests(unittest.TestCase):
    def test_vendored_assets_match_the_recorded_hashes(self):
        package = files("pycontrolcharts")
        self.assertTrue(package.joinpath("py.typed").is_file())
        vendor = package.joinpath("_vendor")
        manifest = json.loads(vendor.joinpath("manifest.json").read_text())
        for name, metadata in manifest["assets"].items():
            with self.subTest(asset=name):
                actual = hashlib.sha256(vendor.joinpath(name).read_bytes()).hexdigest()
                self.assertEqual(actual, metadata["sha256"])

    def test_reference_cases_use_the_same_upstream_assets(self):
        vendor = files("pycontrolcharts").joinpath("_vendor", "manifest.json")
        actual = json.loads(vendor.read_text())
        path = Path(__file__).parent / "reference_manifest.json"
        expected = json.loads(path.read_text())
        self.assertEqual(actual["repository"], expected["repository"])
        self.assertEqual(actual["revision"], expected["revision"])
        self.assertEqual(actual["assets"], expected["assets"])


if __name__ == "__main__":
    unittest.main()
