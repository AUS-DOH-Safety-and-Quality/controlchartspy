"""Public API, input alignment, export, and engine isolation tests."""

import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import TypedDict
from xml.etree import ElementTree

from controlchartspy import funnel, funnel_default_settings, spc, spc_default_settings
from controlchartspy._data import Record
from controlchartspy._result import dimension


class _Sample(TypedDict):
    month: list[date | str]
    value: list[float]
    population: list[int]
    label: list[str]


class Sample(_Sample, total=False):
    region: list[str]
    site: list[str]


def sample_data() -> Sample:
    return {
        "month": [date(2024, month, 1) for month in (3, 1, 2, 4)],
        "value": [12, 10, 8, 11],
        "population": [120, 100, 80, 110],
        "label": ["third", "first", "second", "fourth"],
    }


class APITests(unittest.TestCase):
    def test_mixed_dates_and_iso_strings_keep_row_alignment(self) -> None:
        data = sample_data()
        expected = spc(data, "month", "value", labels="label")
        for index in (1, 3):
            month = data["month"][index]
            assert isinstance(month, date)
            data["month"][index] = month.isoformat()
        actual = spc(data, "month", "value", labels="label")
        self.assertEqual(actual.limits, expected.limits)
        assert actual.static_plot is not None
        assert expected.static_plot is not None
        self.assertEqual(actual.static_plot.svg, expected.static_plot.svg)

    def test_columns_and_sequences_keep_original_row_alignment(self) -> None:
        data = sample_data()
        expected = spc(data, "month", "value", labels="label")
        actual = spc(data, data["month"], data["value"], labels=data["label"])
        self.assertEqual(actual.limits, expected.limits)
        assert actual.static_plot is not None
        assert expected.static_plot is not None
        self.assertEqual(actual.static_plot.svg, expected.static_plot.svg)
        assert isinstance(actual.limits, list)
        values = [row["value"] for row in actual.limits]
        expected_values = [10, 8, 12, 11]
        self.assertEqual(values, expected_values)

    def test_records_are_accepted(self) -> None:
        data = sample_data()
        records = [
            {
                "month": data["month"][index],
                "value": data["value"][index],
                "population": data["population"][index],
                "label": data["label"][index],
            }
            for index in range(len(data["month"]))
        ]
        actual = funnel(records, "label", "value", "population", return_objs="limits")
        expected = funnel(data, "label", "value", "population", return_objs="limits")
        self.assertEqual(actual.limits, expected.limits)

    def test_inputs_and_settings_are_not_mutated(self) -> None:
        data = sample_data()
        settings = {"colour": ["#333333", "#111111", "#222222", "#444444"]}
        before = deepcopy((data, settings))
        chart = spc(data, "month", "value", scatter_settings=settings)
        self.assertEqual((data, settings), before)
        assert chart.static_plot is not None
        objects = chart.static_plot.data_views[0]["categorical"]["categories"][0][
            "objects"
        ]
        colours = [value["scatter"]["colour"] for value in objects]
        expected_colours = ["#111111", "#222222", "#333333", "#444444"]
        self.assertEqual(colours, expected_colours)

    def test_settings_are_independent_copies(self) -> None:
        original = spc_default_settings("canvas")
        changed = spc_default_settings("canvas")
        changed["left_padding"] = 999
        self.assertEqual(spc_default_settings("canvas"), original)
        with self.assertRaisesRegex(ValueError, "valid settings group"):
            funnel_default_settings("missing")

    def test_limits_only_omits_the_plot(self) -> None:
        chart = spc(sample_data(), "month", "value", return_objs="limits")
        assert isinstance(chart.limits, list)
        self.assertEqual(len(chart.limits), 4)
        self.assertIsNone(chart.static_plot)
        with self.assertRaisesRegex(ValueError, "no static plot"):
            chart.save_plot("unused.svg")

    def test_limit_lines_only(self) -> None:
        chart = funnel(
            sample_data(), "label", "value", "population", return_objs="limit_lines"
        )
        self.assertIsNone(chart.limits)
        self.assertIsNone(chart.static_plot)
        assert chart.limit_lines is not None
        self.assertGreater(len(chart.limit_lines), 4)
        self.assertIn("denominator", chart.limit_lines[0])

    def test_svg_export_and_resize(self) -> None:
        data = sample_data()
        chart = spc(data, "month", "value", title="A < B & C")
        assert chart.static_plot is not None
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
            assert expected.static_plot is not None
            self.assertEqual(
                path.read_text(encoding="utf-8").rstrip("\n"),
                expected.static_plot.to_svg(),
            )
        self.assertEqual(chart.static_plot.svg, original)
        self.assertEqual(chart._repr_svg_(), chart.static_plot.to_svg())
        with self.assertRaisesRegex(ValueError, "Only SVG"):
            chart.save_plot("unused.png")

    def test_grouped_limits_and_svg_rejection(self) -> None:
        data = sample_data()
        data["region"] = ["North", "North", "South", "South"]
        data["site"] = ["A", "A", "B", "B"]
        indicators = {"Region": "region", "Site": "site"}
        chart = spc(data, "month", "value", indicators=indicators, return_objs="limits")
        indicator_names = ["Region", "Site"]
        self.assertEqual(chart.indicator_names, indicator_names)
        assert isinstance(chart.limits, dict)
        self.assertSetEqual(set(chart.limits), {"North", "South"})
        north = chart.limits["North"]
        assert isinstance(north, dict)
        rows = north["A"]
        assert isinstance(rows, list)
        values = [row["value"] for row in rows]
        expected_values = [10, 12]
        self.assertEqual(values, expected_values)
        with self.assertRaisesRegex(
            ValueError, "Grouped SPC charts support limits only"
        ):
            spc(data, "month", "value", indicators=indicators)

    def test_single_indicator_group_can_render(self) -> None:
        data = sample_data()
        data["site"] = ["A"] * 4
        chart = spc(data, "month", "value", indicators="site")
        assert isinstance(chart.limits, dict)
        assert chart.static_plot is not None
        self.assertIn("A", chart.limits)
        self.assertIn("<path", chart.static_plot.svg)

    def test_failure_does_not_return_stale_results(self) -> None:
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

    def test_missing_numerators_are_accepted(self) -> None:
        data = sample_data()
        results: list[list[Record]] = []
        for missing in (None, float("nan")):
            values: list[float | None] = list(data["value"])
            values[1] = missing
            limits = spc(
                {**data, "value": values}, "month", "value", return_objs="limits"
            ).limits
            assert isinstance(limits, list)
            results.append(limits)
        actual_values = [row["value"] for row in results[0]]
        expected_values = [8, 12, 11]
        self.assertEqual(actual_values, expected_values)
        self.assertEqual(results[0], results[1])

    def test_invalid_inputs_are_rejected(self) -> None:
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
        for value in (True, "640px"):
            with (
                self.subTest(width=value),
                self.assertRaisesRegex(TypeError, "dimensions"),
            ):
                dimension(value, 640)

    def test_threaded_calls_do_not_share_visual_state(self) -> None:
        def calculate(offset: int) -> list[Record]:
            data = sample_data()
            data["value"] = [value + offset for value in data["value"]]
            limits = spc(data, "month", "value", return_objs="limits").limits
            assert isinstance(limits, list)
            return limits

        expected = [calculate(offset) for offset in range(8)]
        with ThreadPoolExecutor(max_workers=2) as executor:
            actual = list(executor.map(calculate, range(8)))
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
