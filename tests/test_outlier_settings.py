"""Returned flags follow the chart engine's effective detection settings."""

import unittest

from controlchartspy import funnel, spc


class OutlierSettingsTests(unittest.TestCase):
    def test_scalar_and_vector_switches_match_the_first_chart_row(self) -> None:
        data = {
            "key": [f"2024-01-{i + 1:02}" for i in range(12)],
            "n": [10] * 11 + [100],
            "d": list(range(100, 112)),
        }
        for constructor, flags in (
            (spc, ["astronomical", "shift", "trend", "two_in_three"]),
            (funnel, ["two_sigma", "three_sigma"]),
        ):
            for flag in flags:
                column = flag
                if flag == "astronomical":
                    column = "astpoint"
                for enabled in (False, True):
                    expected = constructor(
                        data, "key", "n", "d", outlier_settings={flag: enabled}
                    )
                    assert isinstance(expected.limits, list)
                    self.assertEqual(column in expected.limits[0], enabled)
                    for value in (
                        [enabled],
                        [enabled] * 12,
                        [enabled] + [not enabled] * 11,
                    ):
                        with self.subTest(
                            chart=constructor.__name__, flag=flag, value=value
                        ):
                            actual = constructor(
                                data, "key", "n", "d", outlier_settings={flag: value}
                            )
                            self.assertEqual(actual.limits, expected.limits)
                            assert actual.static_plot is not None
                            assert expected.static_plot is not None
                            self.assertEqual(
                                actual.static_plot.svg, expected.static_plot.svg
                            )
                            limits_only = constructor(
                                data,
                                "key",
                                "n",
                                "d",
                                outlier_settings={flag: value},
                                return_objs="limits",
                            )
                            self.assertEqual(limits_only.limits, expected.limits)

    def test_switches_follow_sorted_and_aggregated_keys(self) -> None:
        data = {
            "key": ["2024-03-01", "2024-01-01", "2024-01-01", "2024-02-01"],
            "n": [90, 5, 5, 10],
            "d": [120, 50, 50, 110],
        }
        for constructor, flag in ((spc, "astronomical"), (funnel, "three_sigma")):
            for enabled in (False, True):
                with self.subTest(chart=constructor.__name__, enabled=enabled):
                    expected = constructor(
                        data, "key", "n", "d", outlier_settings={flag: enabled}
                    )
                    actual = constructor(
                        data,
                        "key",
                        "n",
                        "d",
                        outlier_settings={
                            flag: [not enabled, enabled, not enabled, not enabled]
                        },
                    )
                    self.assertEqual(actual.limits, expected.limits)
                    assert actual.static_plot is not None
                    assert expected.static_plot is not None
                    self.assertEqual(actual.static_plot.svg, expected.static_plot.svg)

    def test_spc_indicators_have_independent_outlier_columns(self) -> None:
        data = {
            "key": ["2024-02-01", "2024-01-01", "2024-01-01", "2024-02-01"],
            "indicator": ["B", "A", "B", "A"],
            "n": [90, 10, 10, 90],
        }
        chart = spc(
            data,
            "key",
            "n",
            indicators="indicator",
            return_objs="limits",
            outlier_settings={
                "astronomical": [False, False, True, True],
                "shift": [True, True, False, False],
            },
        )
        assert isinstance(chart.limits, dict)
        for indicator, enabled in (("A", False), ("B", True)):
            with self.subTest(indicator=indicator):
                expected = spc(
                    {"key": ["2024-01-01", "2024-02-01"], "n": [10, 90]},
                    "key",
                    "n",
                    return_objs="limits",
                    outlier_settings={"astronomical": enabled, "shift": not enabled},
                )
                self.assertEqual(chart.limits[indicator], expected.limits)


if __name__ == "__main__":
    unittest.main()
