"""Sigma chart input alignment, validation, and SVG export."""

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree

from controlchartspy import misc


def comparison_data():
    return {
        "organisation": list("ABCDABCD"),
        "indicator": ["Higher is better"] * 4 + ["Lower is better"] * 4,
        "numerator": [80, 20, 24, 30, 4, 20, 24, 30],
        "denominator": [100] * 8,
        "direction": ["increase"] * 4 + ["decrease"] * 4,
        "grouping": ["Effectiveness"] * 4 + ["Safety"] * 4,
    }


def chart_arguments(data):
    return {
        "data": data,
        "keys": "organisation",
        "numerators": "numerator",
        "denominators": "denominator",
        "indicators": "indicator",
        "target": "A",
        "groupings": "grouping",
        "outlier_settings": {"improvement_direction": data["direction"]},
    }


class MiscTests(unittest.TestCase):
    def test_column_sequences_and_records_match(self):
        data = comparison_data()
        expected = misc(**chart_arguments(data))
        sequences = chart_arguments(data)
        for name in ("keys", "numerators", "denominators", "indicators", "groupings"):
            sequences[name] = data[sequences[name]]
        self.assertEqual(misc(**sequences).limits, expected.limits)
        records = [dict(zip(data, values)) for values in zip(*data.values())]
        actual = misc(**chart_arguments(data), return_objs="limits")
        record_arguments = chart_arguments(data)
        record_arguments["data"] = records
        self.assertEqual(misc(**record_arguments).limits, actual.limits)

    def test_settings_and_tooltips_follow_their_respective_rows(self):
        data = comparison_data()
        repeated = {name: [] for name in data}
        for i in range(len(data["organisation"]) - 1, -1, -1):
            for _ in range(2):
                for name, values in data.items():
                    value = values[i]
                    if name in ("numerator", "denominator"):
                        value /= 2
                    repeated[name].append(value)
        repeated["note"] = [f"row-{i}" for i in range(16)]
        arguments = chart_arguments(repeated)
        arguments["tooltips"] = {"Note": "note"}
        arguments["aggregations"] = {"tooltips": "last"}
        arguments["bar_settings"] = {"colour_improvement": ["#112233", "#445566"]}
        arguments["outlier_settings"]["three_sigma"] = False
        before = deepcopy(arguments)
        chart = misc(**arguments)
        self.assertEqual(arguments, before)
        self.assertEqual(
            [row["indicator"] for row in chart.limits],
            ["Lower is better", "Higher is better"],
        )
        self.assertEqual([row["outlier"] for row in chart.limits], ["improvement"] * 2)
        view = chart.static_plot.data_views[0]["categorical"]
        objects = view["categories"][0]["objects"]
        self.assertEqual(
            [settings["bars"]["colour_improvement"] for settings in objects],
            ["#112233", "#445566"],
        )
        for column in view["values"]:
            if column["source"]["roles"].get("tooltips"):
                self.assertEqual(column["values"], ["row-7", "row-15"])

    def test_svg_export_and_resize(self):
        arguments = chart_arguments(comparison_data())
        arguments["title"] = {"text": "MISC <chart> & scores", "subtitle": "Comparison"}
        chart = misc(**arguments)
        self.assertEqual(chart.target, "A")
        self.assertEqual(chart.static_plot.type, "misc")
        self.assertIn("misc-bar", chart.static_plot.svg)
        original = chart.static_plot.svg
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "misc.svg"
            chart.save_plot(path, width=720, height=480)
            root = ElementTree.parse(path).getroot()
            self.assertEqual(root.attrib["viewBox"], "0 0 720 480")
            self.assertIn("MISC <chart> & scores", "".join(root.itertext()))
            expected = misc(**arguments, width=720, height=480)
            self.assertEqual(path.read_text().rstrip("\n"), expected.static_plot.to_svg())
        self.assertEqual(chart.static_plot.svg, original)

    def test_requested_outputs(self):
        arguments = chart_arguments(comparison_data())
        chart = misc(**arguments, return_objs="limits")
        self.assertIsNone(chart.static_plot)
        self.assertEqual(len(chart.limits), 2)
        self.assertIsNone(chart.limit_lines)
        chart = misc(**arguments, return_objs=(name for name in ["static_plot"]))
        self.assertIsNotNone(chart.static_plot)
        self.assertIsNone(chart.limits)
        chart = misc(**arguments, return_objs=())
        self.assertIsNone(chart.static_plot)
        self.assertIsNone(chart.limits)

    def test_repeated_renders_are_independent(self):
        arguments = chart_arguments(comparison_data())
        arguments["title"] = {"text": "First chart", "subtitle": "First subtitle"}
        first = misc(**arguments)
        misc(**(arguments | {"target": "B", "title": "Second chart"}))
        repeated = misc(**arguments)
        self.assertEqual(repeated.static_plot.svg, first.static_plot.svg)
        root = ElementTree.fromstring(repeated.static_plot.to_svg())
        roots = []
        bars = []
        for element in root.iter():
            if element.attrib.get("class") == "misc-root":
                roots.append(element)
            if element.attrib.get("class") == "misc-bar":
                bars.append(element)
        self.assertEqual(len(roots), 1)
        self.assertEqual(len(bars), 2)

    def test_invalid_inputs(self):
        arguments = chart_arguments(comparison_data())
        cases = [
            ({"target": None}, "single non-missing"),
            ({"target": float("nan")}, "single non-missing"),
            ({"target": ["A", "B"]}, "single non-missing"),
            ({"target": "missing"}, "not present"),
            ({"indicators": ["Only one"]}, "one value per observation"),
            ({"outlier_settings": {"improvement_direction": "invalid"}}, "one improvement_direction"),
            ({"outlier_settings": {"improvement_direction": ["decrease"] + ["increase"] * 7}}, "one improvement_direction"),
            ({"funnel_settings": {"multiplier": [1, 100]}}, "one or 8 values"),
            ({"funnel_settings": {"unknown": 1}}, "Invalid setting"),
            ({"bar_settings": {"unknown": 1}}, "Invalid setting"),
            ({"return_objs": "limit_lines"}, "Invalid return_objs"),
        ]
        for overrides, message in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaisesRegex(ValueError, message):
                    misc(**(arguments | overrides))


if __name__ == "__main__":
    unittest.main()
