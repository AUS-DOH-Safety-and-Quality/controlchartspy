"""Public API, input alignment, export, and engine isolation tests."""

import tempfile
import unittest
import warnings
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import TypedDict
from xml.etree import ElementTree

from controlchartspy import (
    funnel,
    funnel_default_settings,
    misc,
    spc,
    spc_default_settings,
)
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
        ordered = spc(
            {"month": sorted(data["month"]), "value": [10, 8, 12, 11]},
            "month",
            "value",
            scatter_settings={"colour": ["#111111", "#222222", "#333333", "#444444"]},
        )
        assert chart.static_plot is not None
        assert ordered.static_plot is not None
        self.assertEqual(chart.static_plot.svg, ordered.static_plot.svg)

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

    def test_groupings_and_xbar_sds_are_forwarded(self) -> None:
        data = {
            "day": [f"2024-01-0{day}" for day in range(1, 9)],
            "value": [1, 2, 1, 2, 10, 11, 10, 11],
            "phase": ["a"] * 4 + ["b"] * 4,
            "size": [5] * 8,
        }
        phases = spc(data, "day", "value", groupings="phase", return_objs="limits")
        assert isinstance(phases.limits, list)
        targets = [row["target"] for row in phases.limits]
        self.assertEqual(targets, [1.5] * 4 + [10.5] * 4)
        widths: list[float] = []
        for sd in (1.0, 2.0):
            xbar = spc(
                data,
                "day",
                "value",
                denominators="size",
                xbar_sds=[sd] * 8,
                spc_settings={"chart_type": "xbar"},
                return_objs="limits",
            )
            assert isinstance(xbar.limits, list)
            row = xbar.limits[0]
            assert isinstance(row["ul99"], float)
            assert isinstance(row["ll99"], float)
            widths.append(row["ul99"] - row["ll99"])
        self.assertAlmostEqual(widths[1], 2 * widths[0])

    def test_xbar_and_s_limits_include_group_sizes(self) -> None:
        data = {
            "day": [f"2024-01-0{day}" for day in range(1, 9)],
            "mean": [5, 7, 6, 8, 5, 6, 7, 9],
            "sd": [1, 1.2, 0.9, 1.1, 1, 1.3, 0.8, 1],
            "size": [4, 5] * 4,
        }
        xbar = spc(
            data,
            "day",
            "mean",
            denominators="size",
            xbar_sds="sd",
            spc_settings={"chart_type": "xbar"},
            return_objs="limits",
        )
        s = spc(
            data,
            "day",
            "sd",
            denominators="size",
            spc_settings={"chart_type": "s"},
            return_objs="limits",
        )
        assert isinstance(xbar.limits, list)
        assert isinstance(s.limits, list)
        self.assertEqual([row["denominator"] for row in xbar.limits], data["size"])
        self.assertEqual([row["denominator"] for row in s.limits], data["size"])

    def test_indicator_without_denominators_plots_its_numerators(self) -> None:
        days = [f"2024-01-0{day}" for day in range(1, 9)]
        ratio = [5, 7, 6, 8, 5, 6, 7, 9]
        count = [3, 4, 3, 5, 4, 3, 4, 5]
        data = {
            "day": days * 2,
            "indicator": ["Ratio"] * 8 + ["Count"] * 8,
            "numerator": ratio + count,
            "denominator": [10] * 8 + [None] * 8,
        }
        grouped = spc(
            data, "day", "numerator", denominators="denominator", indicators="indicator"
        )
        alone_ratio = spc(
            {"day": days, "n": ratio, "d": [10] * 8},
            "day",
            "n",
            denominators="d",
            return_objs="limits",
        )
        alone_count = spc({"day": days, "n": count}, "day", "n", return_objs="limits")
        assert isinstance(grouped.limits, list)
        assert isinstance(alone_ratio.limits, list)
        assert isinstance(alone_count.limits, list)
        expected = [row["value"] for row in alone_count.limits + alone_ratio.limits]
        self.assertEqual([row["value"] for row in grouped.limits], expected)
        self.assertEqual(
            [row["value"] for row in alone_ratio.limits], [n / 10 for n in ratio]
        )
        for name in ("target", "ll99", "ul99", "trend_line"):
            grouped_values = [row[name] for row in grouped.limits]
            self.assertEqual(
                grouped_values,
                [row[name] for row in alone_count.limits + alone_ratio.limits],
            )

    def test_summary_tables_have_no_static_plot(self) -> None:
        data = sample_data()
        table = {"show_table": True}
        chart = spc(data, "month", "value", summary_table_settings=table)
        self.assertIsNone(chart.static_plot)
        self.assertEqual(
            chart.limits, spc(data, "month", "value", return_objs="limits").limits
        )
        with self.assertRaisesRegex(
            ValueError, "Static plots are not available for summary tables."
        ):
            spc(
                data,
                "month",
                "value",
                summary_table_settings=table,
                return_objs="static_plot",
            )
        sites = {
            "site": list("ABCD"),
            "n": [5, 6, 7, 8],
            "d": [50, 60, 40, 80],
            "ind": list("XXYY"),
        }
        self.assertIsNone(
            funnel(sites, "site", "n", "d", summary_table_settings=table).static_plot
        )
        with self.assertRaisesRegex(
            ValueError, "Static plots are not available for summary tables."
        ):
            funnel(
                sites,
                "site",
                "n",
                "d",
                summary_table_settings=table,
                return_objs="static_plot",
            )
        # Indicators show the MISC chart instead of the table
        sigma = funnel(
            sites, "site", "n", "d", indicators="ind", summary_table_settings=table
        )
        assert sigma.static_plot is not None
        self.assertIn("misc-root", sigma.static_plot.svg)
        targeted = misc(
            sites, "site", "n", "d", "ind", "A", summary_table_settings=table
        )
        self.assertIsNotNone(targeted.static_plot)
        self.assertIsNotNone(
            spc(
                data, "month", "value", summary_table_settings={"show_table": False}
            ).static_plot
        )
        with self.assertRaisesRegex(
            ValueError, "Invalid setting 'not_a_setting' in group 'summary_table'"
        ):
            spc(data, "month", "value", summary_table_settings={"not_a_setting": 1})

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
        assert chart.limits is not None
        self.assertSetEqual({row["Region"] for row in chart.limits}, {"North", "South"})
        values = [
            row["value"]
            for row in chart.limits
            if row["Region"] == "North" and row["Site"] == "A"
        ]
        expected_values = [10, 12]
        self.assertEqual(values, expected_values)
        default = spc(data, "month", "value", indicators=indicators)
        self.assertIsNone(default.static_plot)
        self.assertEqual(default.limits, chart.limits)
        with self.assertRaisesRegex(
            ValueError, "Static plots are not available for summary tables."
        ):
            spc(
                data, "month", "value", indicators=indicators, return_objs="static_plot"
            )

    def test_single_indicator_group_can_render(self) -> None:
        data = sample_data()
        data["site"] = ["A"] * 4
        chart = spc(
            data,
            "month",
            "value",
            indicators="site",
            return_objs=("static_plot", "limits"),
        )
        assert chart.limits is not None
        assert chart.static_plot is not None
        self.assertSetEqual({row["site"] for row in chart.limits}, {"A"})
        self.assertIn("<path", chart.static_plot.svg)

    def test_indicators_named_like_limit_columns_are_renamed(self) -> None:
        data = sample_data()
        data["region"] = ["North"] * 4
        data["site"] = ["A"] * 4
        with self.assertWarnsRegex(
            UserWarning, "value to value_, target to target_[.]"
        ):
            chart = spc(
                data,
                "month",
                "value",
                indicators={"value": "region", "target": "site"},
                return_objs="limits",
            )
        assert chart.limits is not None
        self.assertEqual([row["value_"] for row in chart.limits], ["North"] * 4)
        self.assertEqual([row["value"] for row in chart.limits], [10, 8, 12, 11])
        self.assertEqual({row["target_"] for row in chart.limits}, {"A"})
        with self.assertWarnsRegex(UserWarning, "group to group_[.]"):
            misc = funnel(
                data,
                "label",
                "value",
                "population",
                indicators={"group": "region"},
                return_objs="limits",
            )
        assert misc.limits is not None
        self.assertEqual({row["group_"] for row in misc.limits}, {"North"})
        self.assertEqual({row["group"] for row in misc.limits}, set(data["label"]))
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            spc(
                data,
                "month",
                "value",
                indicators={"Region": "region"},
                return_objs="limits",
            )

    def test_chart_warnings_are_raised_once_whatever_is_returned(self) -> None:
        data = sample_data()
        data["value"] = [12, 10, -8, 11]
        for outputs in ("limits", "static_plot", ("static_plot", "limits")):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                funnel(data, "label", "value", "population", return_objs=outputs)
            messages = [str(warning.message) for warning in caught]
            self.assertEqual(
                messages, ["label second removed due to: Numerator negative."], outputs
            )

    def test_misc_reads_the_default_empty_group_as_the_first(self) -> None:
        data = sample_data()
        data["indicator"] = ["Higher", "Higher", "Lower", "Lower"]
        data["site"] = ["A", "B", "A", "B"]
        args = (data, "site", "value", "population")
        defaults = funnel(
            *args,
            indicators={"indicator": "indicator"},
            misc_settings=funnel_default_settings("misc"),
            return_objs="limits",
        )
        first = misc(*args, {"indicator": "indicator"}, "A", return_objs="limits")
        self.assertEqual(defaults.limits, first.limits)

    def test_misc_leaves_out_rc_indicators_without_counts(self) -> None:
        data = sample_data()
        data["value"] = [3, 5, 0, 0]
        data["indicator"] = ["Higher", "Higher", "Lower", "Lower"]
        data["site"] = ["A", "B", "A", "B"]
        with self.assertWarnsRegex(UserWarning, "Lower: All numerators are zero"):
            chart = funnel(
                data,
                "site",
                "value",
                "population",
                indicators={"indicator": "indicator"},
                funnel_settings={"chart_type": "RC"},
                return_objs="limits",
            )
        assert chart.limits is not None
        self.assertEqual({row["indicator"] for row in chart.limits}, {"Higher"})

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
            with self.assertWarnsRegex(
                UserWarning, r"^month 01/01/2024 removed due to: Numerator missing\.$"
            ):
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
        with self.assertRaisesRegex(ValueError, "one value or 4 values"):
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

    def test_tooltips_return_in_limits_with_their_types(self) -> None:
        data: dict[str, list[object]] = {
            "key": ["2024-02-09", "2024-01-31", "2024-01-16"] * 2,
            "n": [6, 2, 1, 3, 4, 4],
            "start": [date(2024, 2, day) for day in (8, 2, 4, 7, 1, 3)],
            "eligible": [True, False, False, False, False, True],
            "score": [None, 2, None, 5, 1, float("nan")],
        }
        tooltips = {"Start": "start", "Eligible": "eligible"}
        chart = spc(data, "key", "n", tooltips=tooltips, return_objs="limits")
        assert chart.limits is not None
        self.assertEqual(
            [row["Start"] for row in chart.limits],
            [date(2024, 2, 4), date(2024, 2, 2), date(2024, 2, 8)],
        )
        self.assertEqual(
            [row["Eligible"] for row in chart.limits], [False, False, True]
        )
        minimum = spc(
            data,
            "key",
            "n",
            tooltips={"Start": "start", "score": "score"},
            aggregations={"tooltips": "min"},
            return_objs="limits",
        )
        assert minimum.limits is not None
        self.assertEqual(
            [row["Start"] for row in minimum.limits],
            [date(2024, 2, 3), date(2024, 2, 1), date(2024, 2, 7)],
        )
        self.assertEqual([row["score"] for row in minimum.limits], [None, 1, 5])

    def test_tooltips_omit_rejected_observations(self) -> None:
        data: dict[str, list[object]] = {
            "key": [30, 10, 20, 40],
            "n": [5, 6, 7, None],
            "d": [100, 0, 100, 100],
            "start": [date(2024, 1, day) for day in (4, 2, 3, 5)],
        }
        with self.assertWarnsRegex(
            UserWarning,
            r"^key 10 removed due to: Denominator is zero\.\nkey 40 removed due to: Numerator missing\.$",
        ):
            chart = funnel(
                data, "key", "n", "d", tooltips="start", return_objs="limits"
            )
        assert chart.limits is not None
        self.assertEqual(
            [row["start"] for row in chart.limits], [date(2024, 1, 3), date(2024, 1, 4)]
        )

    def test_tooltips_cannot_overwrite_limit_columns(self) -> None:
        data = sample_data()
        with self.assertRaisesRegex(ValueError, "Result column names conflict: value"):
            spc(data, "month", "value", tooltips={"value": "label"})
        with self.assertRaisesRegex(TypeError, "'sum' aggregation needs numeric"):
            spc(
                data,
                "month",
                "value",
                tooltips="label",
                aggregations={"tooltips": "sum"},
                return_objs="limits",
            )


if __name__ == "__main__":
    unittest.main()
