"""Check standard SPC formulas independently of the shared JavaScript engine."""

import math
import unittest

from controlchartspy import spc


class NumericalTests(unittest.TestCase):
    def assert_limits(self, row, target, sigma, multiplier=1):
        self.assertAlmostEqual(row["target"], target * multiplier, places=12)
        for count, suffix in ((1, "68"), (2, "95"), (3, "99")):
            self.assertAlmostEqual(
                row["ll" + suffix], (target - count * sigma) * multiplier, places=12
            )
            self.assertAlmostEqual(
                row["ul" + suffix], (target + count * sigma) * multiplier, places=12
            )

    def test_p_chart_uses_pooled_proportion_and_binomial_variance(self):
        data = {
            "date": ["2024-01-01", "2024-02-01", "2024-03-01"],
            "count": [10, 30, 20],
            "population": [100, 200, 100],
        }
        chart = spc(
            data, "date", "count", "population",
            spc_settings={"chart_type": "p"}, return_objs="limits",
        )
        target = 60 / 400
        for row in chart.limits:
            sigma = math.sqrt(target * (1 - target) / row["denominator"])
            self.assert_limits(row, target, sigma, multiplier=100)
            self.assertAlmostEqual(
                row["value"], 100 * row["numerator"] / row["denominator"], places=12
            )

    def test_c_chart_uses_mean_count_and_poisson_variance(self):
        chart = spc(
            {"date": ["2024-01-01", "2024-02-01", "2024-03-01"],
             "count": [10, 20, 30]},
            "date", "count", spc_settings={"chart_type": "c"}, return_objs="limits",
        )
        for row in chart.limits:
            self.assert_limits(row, 20, math.sqrt(20))

    def test_u_chart_uses_pooled_rate_and_poisson_variance(self):
        chart = spc(
            {"date": ["2024-01-01", "2024-02-01", "2024-03-01"],
             "count": [10, 30, 20], "population": [100, 200, 100]},
            "date", "count", "population",
            spc_settings={"chart_type": "u"}, return_objs="limits",
        )
        target = 60 / 400
        for row in chart.limits:
            self.assert_limits(row, target, math.sqrt(target / row["denominator"]))


if __name__ == "__main__":
    unittest.main()
