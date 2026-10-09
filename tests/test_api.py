"""Public API, input alignment, export, and engine isolation tests."""

import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date
from pathlib import Path
from xml.etree import ElementTree

from pycontrolcharts import funnel, funnel_default_settings, spc, spc_default_settings


def sample_data():
    return {
        "month": [date(2024, month, 1) for month in (3, 1, 2, 4)],
        "value": [12, 10, 8, 11],
        "population": [120, 100, 80, 110],
        "label": ["third", "first", "second", "fourth"],
    }


class APITests(unittest.TestCase):
    def test_columns_and_sequences_keep_original_row_alignment(self):
        data = sample_data()
        expected = spc(data, "month", "value", labels="label")
        actual = spc(data, data["month"], data["value"], labels=data["label"])
        self.assertEqual(actual.limits, expected.limits)
        self.assertEqual(actual.static_plot.svg, expected.static_plot.svg)
        self.assertEqual([row["value"] for row in actual.limits], [10, 8, 12, 11])

    def test_records_are_accepted(self):
        data = sample_data()
        records = [dict(zip(data, values)) for values in zip(*data.values())]
        actual = funnel(records, "label", "value", "population", return_objs="limits")
        expected = funnel(data, "label", "value", "population", return_objs="limits")
        self.assertEqual(actual.limits, expected.limits)

    def test_inputs_and_settings_are_not_mutated(self):
        data = sample_data()
        settings = {"colour": ["#333333", "#111111", "#222222", "#444444"]}
        before = deepcopy((data, settings))
        chart = spc(data, "month", "value", scatter_settings=settings)
        self.assertEqual((data, settings), before)
        objects = chart.static_plot.data_views[0]["categorical"]["categories"][0][
            "objects"
        ]
        self.assertEqual(
            [value["scatter"]["colour"] for value in objects],
            ["#111111", "#222222", "#333333", "#444444"],
        )

    def test_settings_are_independent_copies(self):
        original = spc_default_settings("canvas")
        changed = spc_default_settings("canvas")
        changed["left_padding"] = 999
        self.assertEqual(spc_default_settings("canvas"), original)
        with self.assertRaisesRegex(ValueError, "valid settings group"):
            funnel_default_settings("missing")

    def test_limits_only_omits_the_plot(self):
        chart = spc(sample_data(), "month", "value", return_objs="limits")
        self.assertEqual(len(chart.limits), 4)
        self.assertIsNone(chart.static_plot)
        with self.assertRaisesRegex(ValueError, "no static plot"):
            chart.save_plot("unused.svg")

    def test_limit_lines_only(self):
        chart = funnel(
            sample_data(), "label", "value", "population", return_objs="limit_lines"
        )
        self.assertIsNone(chart.limits)
        self.assertIsNone(chart.static_plot)
        self.assertGreater(len(chart.limit_lines), 4)
        self.assertIn("denominator", chart.limit_lines[0])

    def test_svg_export_and_resize(self):
        data = sample_data()
        chart = spc(data, "month", "value", title="A < B & C")
        original = chart.static_plot.svg
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plot.svg"
            chart.save_plot(path)
            self.assertEqual(
                path.read_text(encoding="utf-8").rstrip("\n"),
                chart.static_plot.to_svg(),
            )
            chart.save_plot(path, width=800, height=500)
            root = ElementTree.parse(path).getroot()
            self.assertEqual(root.attrib["viewBox"], "0 0 800 500")
            self.assertIn("A < B & C", "".join(root.itertext()))
            expected = spc(
                data, "month", "value", title="A < B & C", width=800, height=500
            )
            self.assertEqual(
                path.read_text(encoding="utf-8").rstrip("\n"),
                expected.static_plot.to_svg(),
            )
        self.assertEqual(chart.static_plot.svg, original)
        self.assertEqual(chart._repr_svg_(), chart.static_plot.to_svg())
        with self.assertRaisesRegex(ValueError, "Only SVG"):
            chart.save_plot("unused.png")

    def test_grouped_limits_and_svg_rejection(self):
        data = sample_data()
        data["region"] = ["North", "North", "South", "South"]
        data["site"] = ["A", "A", "B", "B"]
        indicators = {"Region": "region", "Site": "site"}
        chart = spc(data, "month", "value", indicators=indicators, return_objs="limits")
        self.assertEqual(chart.indicator_names, ["Region", "Site"])
        self.assertEqual(set(chart.limits), {"North", "South"})
        self.assertEqual([row["value"] for row in chart.limits["North"]["A"]], [10, 12])
        with self.assertRaisesRegex(
            ValueError, "Grouped SPC charts support limits only"
        ):
            spc(data, "month", "value", indicators=indicators)

    def test_single_indicator_group_can_render(self):
        data = sample_data()
        data["site"] = ["A"] * 4
        chart = spc(data, "month", "value", indicators="site")
        self.assertIn("A", chart.limits)
        self.assertIn("<path", chart.static_plot.svg)

    def test_failure_does_not_return_stale_results(self):
        data = sample_data()
        expected = funnel(data, "label", "value", "population", return_objs="limits")
        with self.assertRaisesRegex(ValueError, "All numerators are negative"):
            funnel(data, "label", [-1] * 4, "population", return_objs="limits")
        self.assertEqual(
            funnel(data, "label", "value", "population", return_objs="limits").limits,
            expected.limits,
        )
        spc(data, "month", "value", "population", spc_settings={"chart_type": "p"})
        with self.assertRaisesRegex(ValueError, "requires denominators"):
            spc(
                data,
                "month",
                "value",
                spc_settings={"chart_type": "p"},
                return_objs="limits",
            )

    def test_missing_numerators_are_accepted(self):
        data = sample_data()
        results = []
        for missing in (None, float("nan")):
            data["value"][1] = missing
            results.append(spc(data, "month", "value", return_objs="limits").limits)
        self.assertEqual(len(results[0]), 4)
        self.assertEqual(results[0], results[1])

    def test_invalid_inputs_are_rejected(self):
        data = sample_data()
        with self.assertRaisesRegex(ValueError, "No data"):
            spc({"month": [], "value": []}, "month", "value")
        with self.assertRaisesRegex(ValueError, "one value per observation"):
            spc(data, "month", [1])
        with self.assertRaisesRegex(ValueError, "Invalid setting"):
            spc(data, "month", "value", spc_settings={"unknown": 1})
        with self.assertRaisesRegex(ValueError, "one or 4 values"):
            spc(data, "month", "value", scatter_settings={"colour": ["red", "blue"]})
        with self.assertRaisesRegex(ValueError, "valid aggregation"):
            spc(data, "month", "value", aggregations={"numerators": "unknown"})
        with self.assertRaisesRegex(ValueError, "Invalid return_objs"):
            spc(data, "month", "value", return_objs="html_plot")
        with self.assertRaisesRegex(ValueError, "Infinite values"):
            spc(data, "month", [float("inf")] * 4)
        with self.assertRaisesRegex(TypeError, "SPC keys"):
            spc(data, [3, 1, 2, 4], "value")
        funnel(data, [3, 1, 2, 4], "value", "population", return_objs="limits")
        for width in (-1, 0, float("nan")):
            with (
                self.subTest(width=width),
                self.assertRaisesRegex(ValueError, "dimensions"),
            ):
                spc(data, "month", "value", width=width)
        for width in (True, "640px"):
            with (
                self.subTest(width=width),
                self.assertRaisesRegex(TypeError, "dimensions"),
            ):
                spc(data, "month", "value", width=width)

    def test_threaded_calls_do_not_share_visual_state(self):
        def calculate(offset):
            data = sample_data()
            data["value"] = [value + offset for value in data["value"]]
            return spc(data, "month", "value", return_objs="limits").limits

        expected = [calculate(offset) for offset in range(8)]
        with ThreadPoolExecutor(max_workers=2) as executor:
            actual = list(executor.map(calculate, range(8)))
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
