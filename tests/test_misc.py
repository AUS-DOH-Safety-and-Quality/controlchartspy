"""Sigma chart input alignment, validation, and SVG export."""

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from typing import TypedDict
from xml.etree import ElementTree

from controlchartspy import funnel, funnel_default_settings, misc, misc_default_settings
from controlchartspy._api import ReturnObjs, Title
from controlchartspy._data import Column, Columns
from controlchartspy._engine import engine


class _Comparison(TypedDict):
    organisation: list[str | int]
    indicator: list[str]
    numerator: list[float]
    denominator: list[float]
    direction: list[str]
    grouping: list[str]


class Comparison(_Comparison, total=False):
    note: list[str]


class _Arguments(TypedDict):
    data: Comparison | list[dict[str, object]]
    keys: Column
    numerators: Column
    denominators: Column
    indicators: Columns
    outlier_settings: dict[str, object]


class FunnelArguments(_Arguments, total=False):
    tooltips: Columns
    aggregations: dict[str, str]
    title: Title
    funnel_settings: dict[str, object]
    misc_settings: dict[str, object]
    return_objs: ReturnObjs
    width: float
    height: float


class MiscArguments(FunnelArguments):
    target: object


class Overrides(TypedDict, total=False):
    target: object
    indicators: Columns
    outlier_settings: dict[str, object]
    funnel_settings: dict[str, object]
    misc_settings: dict[str, object]
    return_objs: ReturnObjs


class Tooltip(TypedDict):
    displayName: str
    value: str


class Point(TypedDict):
    tooltip: list[Tooltip]


def comparison_data() -> Comparison:
    return {
        "organisation": list("ABCDABCD"),
        "indicator": ["Higher is better"] * 4 + ["Lower is better"] * 4,
        "numerator": [80, 20, 24, 30, 4, 20, 24, 30],
        "denominator": [100] * 8,
        "direction": ["increase"] * 4 + ["decrease"] * 4,
        "grouping": ["Effectiveness"] * 4 + ["Safety"] * 4,
    }


def funnel_arguments(data: Comparison) -> FunnelArguments:
    return {
        "data": data,
        "keys": "organisation",
        "numerators": "numerator",
        "denominators": "denominator",
        "indicators": "indicator",
        "outlier_settings": {"improvement_direction": data["direction"]},
    }


def chart_arguments(data: Comparison) -> MiscArguments:
    return {**funnel_arguments(data), "target": "A"}


class MiscTests(unittest.TestCase):
    def test_column_sequences_and_records_match(self) -> None:
        data = comparison_data()
        expected = misc(**chart_arguments(data))
        sequences = chart_arguments(data)
        sequences["keys"] = data["organisation"]
        sequences["numerators"] = data["numerator"]
        sequences["denominators"] = data["denominator"]
        sequences["indicators"] = data["indicator"]
        self.assertEqual(misc(**sequences).limits, expected.limits)
        records: list[dict[str, object]] = [
            {
                "organisation": data["organisation"][index],
                "indicator": data["indicator"][index],
                "numerator": data["numerator"][index],
                "denominator": data["denominator"][index],
                "direction": data["direction"][index],
                "grouping": data["grouping"][index],
            }
            for index in range(len(data["organisation"]))
        ]
        limits_arguments = chart_arguments(data)
        limits_arguments["return_objs"] = "limits"
        actual = misc(**limits_arguments)
        record_arguments = chart_arguments(data)
        record_arguments["data"] = records
        self.assertEqual(misc(**record_arguments).limits, actual.limits)

    def test_settings_and_tooltips_follow_their_respective_rows(self) -> None:
        data = comparison_data()
        indices = [
            i for i in range(len(data["organisation"]) - 1, -1, -1) for _ in range(2)
        ]
        repeated: Comparison = {
            "organisation": [data["organisation"][i] for i in indices],
            "indicator": [data["indicator"][i] for i in indices],
            "numerator": [data["numerator"][i] / 2 for i in indices],
            "denominator": [data["denominator"][i] / 2 for i in indices],
            "direction": [data["direction"][i] for i in indices],
            "grouping": [data["grouping"][i] for i in indices],
            "note": [f"row-{i}" for i in range(16)],
        }
        arguments = chart_arguments(repeated)
        arguments["tooltips"] = {"Note": "note"}
        arguments["aggregations"] = {"tooltips": "last"}
        arguments["outlier_settings"]["three_sigma_colour_improvement"] = [
            "#112233" if indicator == "Higher is better" else "#445566"
            for indicator in repeated["indicator"]
        ]
        arguments["outlier_settings"]["three_sigma"] = False
        before = deepcopy(arguments)
        chart = misc(**arguments)
        self.assertEqual(arguments, before)
        assert isinstance(chart.limits, list)
        assert chart.static_plot is not None
        indicators = [row["indicator"] for row in chart.limits]
        expected_indicators = ["Higher is better", "Lower is better"]
        self.assertEqual(indicators, expected_indicators)
        classifications = [row["three_sigma"] for row in chart.limits]
        expected_classifications = ["improvement"] * 2
        self.assertEqual(classifications, expected_classifications)
        root = ElementTree.fromstring(chart.static_plot.to_svg())
        bars = [
            element
            for element in root.iter()
            if element.attrib.get("class") == "misc-bar"
        ]
        colours = [bar.attrib["fill"] for bar in bars]
        expected_colours = ["#112233", "#445566"]
        self.assertEqual(colours, expected_colours)
        payload = engine().context.eval(
            "JSON.stringify(ccHeadless.visuals.funnel.viewModel.miscPoints)"
        )
        assert isinstance(payload, str)
        points: list[Point] = json.loads(payload)
        notes = [
            item["value"]
            for point in points
            for item in point["tooltip"]
            if item["displayName"] == "Note"
        ]
        expected_notes = ["row-15", "row-7"]
        self.assertEqual(notes, expected_notes)

    def test_svg_export_and_resize(self) -> None:
        arguments = chart_arguments(comparison_data())
        arguments["title"] = {"text": "MISC <chart> & scores", "subtitle": "Comparison"}
        chart = misc(**arguments)
        assert chart.static_plot is not None
        self.assertEqual(chart.static_plot.type, "funnel")
        self.assertIn("misc-bar", chart.static_plot.svg)
        original = chart.static_plot.svg
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "misc.svg"
            chart.save_plot(path, width=720, height=480)
            root = ElementTree.parse(path).getroot()
            self.assertEqual(root.attrib["viewBox"], "0 0 720 480")
            self.assertIn("MISC <chart> & scores", "".join(root.itertext()))
            resized: MiscArguments = {**arguments, "width": 720, "height": 480}
            expected = misc(**resized)
            assert expected.static_plot is not None
            self.assertEqual(
                path.read_text().rstrip("\n"), expected.static_plot.to_svg()
            )
        self.assertEqual(chart.static_plot.svg, original)

    def test_requested_outputs(self) -> None:
        arguments = chart_arguments(comparison_data())
        arguments["return_objs"] = "limits"
        chart = misc(**arguments)
        self.assertIsNone(chart.static_plot)
        assert isinstance(chart.limits, list)
        self.assertEqual(len(chart.limits), 2)
        self.assertIsNone(chart.limit_lines)
        arguments["return_objs"] = (name for name in ["static_plot"])
        chart = misc(**arguments)
        self.assertIsNotNone(chart.static_plot)
        self.assertIsNone(chart.limits)
        arguments["return_objs"] = ()
        chart = misc(**arguments)
        self.assertIsNone(chart.static_plot)
        self.assertIsNone(chart.limits)

    def test_repeated_renders_are_independent(self) -> None:
        arguments = chart_arguments(comparison_data())
        arguments["title"] = {"text": "First chart", "subtitle": "First subtitle"}
        first = misc(**arguments)
        other_arguments = arguments.copy()
        other_arguments["target"] = "B"
        other_arguments["title"] = "Second chart"
        misc(**other_arguments)
        repeated = misc(**arguments)
        assert first.static_plot is not None
        assert repeated.static_plot is not None
        self.assertEqual(repeated.static_plot.svg, first.static_plot.svg)
        root = ElementTree.fromstring(repeated.static_plot.to_svg())
        roots: list[ElementTree.Element] = []
        bars: list[ElementTree.Element] = []
        for element in root.iter():
            if element.attrib.get("class") == "misc-root":
                roots.append(element)
            if element.attrib.get("class") == "misc-bar":
                bars.append(element)
        self.assertEqual(len(roots), 1)
        self.assertEqual(len(bars), 2)

    def test_invalid_inputs(self) -> None:
        arguments = chart_arguments(comparison_data())
        cases: list[tuple[Overrides, str]] = [
            ({"target": None}, "single non-missing"),
            ({"target": float("nan")}, "single non-missing"),
            ({"target": ["A", "B"]}, "single non-missing"),
            ({"target": "missing"}, "Select a MISC group present"),
            ({"indicators": ["Only one"]}, "one value per observation"),
            (
                {"outlier_settings": {"improvement_direction": "neutral"}},
                "one improvement direction",
            ),
            (
                {
                    "outlier_settings": {
                        "improvement_direction": ["decrease"] + ["increase"] * 7
                    }
                },
                "one improvement direction",
            ),
            ({"funnel_settings": {"multiplier": [1, 100]}}, "one value or 8 values"),
            ({"funnel_settings": {"unknown": 1}}, "Invalid setting"),
            ({"misc_settings": {"unknown": 1}}, "Invalid setting"),
            ({"misc_settings": {"lower": 0}}, "not a valid value for lower"),
            ({"return_objs": "limit_lines"}, "Invalid return_objs"),
        ]
        for overrides, message in cases:
            merged: MiscArguments = {**arguments, **overrides}
            with (
                self.subTest(overrides=overrides),
                self.assertRaisesRegex(ValueError, message),
            ):
                misc(**merged)

    def test_funnel_delegation_with_multiple_indicators_and_numeric_target(
        self,
    ) -> None:
        data = comparison_data()
        data["organisation"] = [1, 2, 3, 4] * 2
        arguments = funnel_arguments(data)
        arguments["indicators"] = {"Domain": "grouping", "Measure": "indicator"}
        arguments["misc_settings"] = {"group": "1", "lower": -6, "upper": 6}
        before = deepcopy(arguments)
        wrapped = misc(**arguments, target=2)
        self.assertEqual(arguments, before)
        arguments["misc_settings"]["group"] = "2"
        direct = funnel(**arguments)
        self.assertEqual(wrapped.limits, direct.limits)
        assert wrapped.static_plot is not None
        assert direct.static_plot is not None
        self.assertEqual(wrapped.static_plot.svg, direct.static_plot.svg)
        assert isinstance(wrapped.limits, list)
        groups = [row["group"] for row in wrapped.limits]
        expected_groups = ["2", "2"]
        self.assertEqual(groups, expected_groups)
        indicators = [row["indicator"] for row in wrapped.limits]
        expected_indicators = [
            "Effectiveness / Higher is better",
            "Safety / Lower is better",
        ]
        self.assertEqual(indicators, expected_indicators)
        self.assertEqual(misc_default_settings(), funnel_default_settings())

    def test_funnel_uses_first_group_when_none_is_selected(self) -> None:
        arguments = funnel_arguments(comparison_data())
        selected = misc(**arguments, target="A")
        automatic = funnel(**arguments)
        self.assertEqual(automatic.limits, selected.limits)
        assert automatic.static_plot is not None
        assert selected.static_plot is not None
        self.assertEqual(automatic.static_plot.svg, selected.static_plot.svg)


if __name__ == "__main__":
    unittest.main()
