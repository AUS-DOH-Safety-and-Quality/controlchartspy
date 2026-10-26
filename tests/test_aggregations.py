"""Power BI column aggregation semantics for missing observations."""

import unittest
import warnings

from controlchartspy import funnel, spc


class AggregationTests(unittest.TestCase):
    def test_numeric_aggregations_ignore_missing_values_and_keep_zero(self) -> None:
        expected = {
            "sum": [30, 0],
            "mean": [15, 0],
            "min": [10, 0],
            "max": [20, 0],
            "median": [15, 0],
            "count": [2, 1, 0],
        }
        for missing in (None, float("nan")):
            data = {
                "key": ["2024-01-01"] * 3 + ["2024-02-01"] * 3 + ["2024-03-01"] * 3,
                "n": [10, missing, 20, missing, 0, missing, missing, missing, missing],
                "d": [100] * 9,
            }
            for method, values in expected.items():
                with self.subTest(method=method, missing=missing):
                    # An all-missing key counts 0 and is kept; other methods drop it
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter("always")
                        spc_chart = spc(
                            data,
                            "key",
                            "n",
                            aggregations={"numerators": method},
                            return_objs="limits",
                        )
                        funnel_chart = funnel(
                            data,
                            "key",
                            "n",
                            "d",
                            aggregations={"numerators": method},
                            return_objs="limits",
                        )
                    self.assertEqual(
                        [str(warning.message) for warning in caught],
                        []
                        if method == "count"
                        else [
                            "key 01/03/2024 removed due to: Numerator missing.",
                            "key 2024-03-01 removed due to: Numerator missing.",
                        ],
                    )
                    assert isinstance(spc_chart.limits, list)
                    assert isinstance(funnel_chart.limits, list)
                    spc_values = [row["value"] for row in spc_chart.limits]
                    funnel_values = [row["numerator"] for row in funnel_chart.limits]
                    self.assertEqual(spc_values, values)
                    self.assertEqual(funnel_values, values)

    def test_extrema_ignore_blanks_between_negative_values(self) -> None:
        data = {
            "key": ["2024-01-01"] * 3 + ["2024-02-01"] * 3,
            "n": [-10, None, -20, -30, None, -40],
        }
        for method, expected in (("min", [-20, -40]), ("max", [-10, -30])):
            with self.subTest(method=method):
                chart = spc(
                    data,
                    "key",
                    "n",
                    aggregations={"numerators": method},
                    return_objs="limits",
                )
                assert isinstance(chart.limits, list)
                values = [row["value"] for row in chart.limits]
                self.assertEqual(values, expected)

    def test_numerators_and_denominators_aggregate_independently(self) -> None:
        data = {
            "key": ["A"] * 3 + ["B"] * 3 + ["C"] * 3,
            "n": [10, None, 20, None, 40, None, 10, 20, 30],
            "d": [100, 200, None, 100, None, 300, None, None, None],
        }
        expected = funnel(
            {"key": ["A", "B"], "n": [30, 40], "d": [300, 400]},
            "key",
            "n",
            "d",
            return_objs="limits",
        )
        with self.assertWarnsRegex(
            UserWarning, r"^key C removed due to: Denominator missing\.$"
        ):
            actual = funnel(data, "key", "n", "d", return_objs="limits")
        self.assertEqual(actual.limits, expected.limits)

    def test_first_and_last_skip_missing_values_and_tooltips(self) -> None:
        data = {
            "key": ["A"] * 3 + ["B"] * 3,
            "n": [None, 10, 20, 30, None, None],
            "note": [None, "a1", "a2", "b1", None, None],
        }
        expected = {
            "first": ([10, 30], ["a1", "b1"]),
            "last": ([20, 30], ["a2", "b1"]),
        }
        for method, (values, notes) in expected.items():
            with self.subTest(method=method):
                chart = spc(
                    data,
                    "key",
                    "n",
                    tooltips="note",
                    aggregations={"numerators": method, "tooltips": method},
                    return_objs="limits",
                )
                assert isinstance(chart.limits, list)
                self.assertEqual([row["value"] for row in chart.limits], values)
                self.assertEqual([row["note"] for row in chart.limits], notes)
        counted = spc(
            data,
            "key",
            "n",
            tooltips="note",
            aggregations={"numerators": "count", "tooltips": "count"},
            return_objs="limits",
        )
        assert isinstance(counted.limits, list)
        self.assertEqual([row["note"] for row in counted.limits], [2, 1])
        none = spc(
            {"key": ["A", "A"], "n": [1, 2], "note": [None, None]},
            "key",
            "n",
            tooltips="note",
            aggregations={"tooltips": "count"},
            return_objs="limits",
        )
        assert isinstance(none.limits, list)
        self.assertEqual([row["note"] for row in none.limits], [0])


if __name__ == "__main__":
    unittest.main()
