import unittest
from resource_discrepancy_engine import (
    analyze_facility, consumption_status, range_status
)


class TestResourceDiscrepancyEngine(unittest.TestCase):
    def test_high_is_red(self):
        self.assertEqual(consumption_status(110, 100)["alert_color"], "red")

    def test_low_is_orange(self):
        self.assertEqual(consumption_status(90, 100)["alert_color"], "orange")

    def test_within_tolerance_is_green(self):
        self.assertEqual(consumption_status(103, 100)["alert_color"], "green")

    def test_missing_is_grey(self):
        self.assertEqual(consumption_status(None, 100)["alert_color"], "grey")

    def test_zero_baseline_is_insufficient(self):
        self.assertEqual(consumption_status(10, 0)["status"], "insufficient_data")

    def test_factor_range(self):
        self.assertEqual(range_status(.975, .97, .98)["alert_color"], "green")
        self.assertEqual(range_status(.95, .97, .98)["alert_color"], "orange")
        self.assertEqual(range_status(.99, .97, .98)["alert_color"], "red")

    def test_facility_overall(self):
        result = analyze_facility({
            "facility_code": "FS-001",
            "energy_kwh": 110, "expected_energy_kwh": 100,
            "water_kl": 100, "expected_water_kl": 100,
            "power_factor": .975, "load_factor": .72
        })
        self.assertEqual(result["overall_alert_color"], "red")
        self.assertFalse(result["metadata"]["live_data_connected"])

    def test_score_is_zero_within_tolerance(self):
        self.assertEqual(consumption_status(103, 100)["discrepancy_score"], 15.0)

    def test_score_caps_at_100(self):
        self.assertEqual(consumption_status(150, 100)["discrepancy_score"], 100.0)

    def test_missing_metrics_do_not_inflate_score(self):
        result = analyze_facility({
            "energy_kwh": 100, "expected_energy_kwh": 100,
            "water_kl": None, "expected_water_kl": None,
            "power_factor": None, "load_factor": None,
        })
        self.assertEqual(result["discrepancy_score"], 0.0)
        self.assertEqual(result["severity"], "low")
        self.assertEqual(result["overall_status"], "partial_data")

    def test_invalid_numbers_are_handled(self):
        self.assertEqual(consumption_status(float("nan"), 100)["status"], "insufficient_data")
        self.assertEqual(consumption_status(float("inf"), 100)["discrepancy_score"], None)
        self.assertEqual(range_status(None, .97, .98)["discrepancy_score"], None)

    def test_invalid_configuration_raises(self):
        with self.assertRaises(ValueError):
            consumption_status(100, 100, tolerance_percent=-1)
        with self.assertRaises(ValueError):
            range_status(.9, .98, .97)

    def test_cross_resource_indicator_does_not_claim_correlation(self):
        result = analyze_facility({
            "energy_kwh": 120, "expected_energy_kwh": 100,
            "water_kl": 40, "expected_water_kl": 30,
        })
        self.assertEqual(
            result["cross_resource_indicator"]["status"], "both_above_expected"
        )
        self.assertFalse(
            result["cross_resource_indicator"]["correlation_confirmed"]
        )

    def test_mixed_resource_deviations(self):
        result = analyze_facility({
            "energy_kwh": 120, "expected_energy_kwh": 100,
            "water_kl": 25, "expected_water_kl": 30,
        })
        self.assertEqual(
            result["cross_resource_indicator"]["status"], "opposite_deviations"
        )

    def test_exact_threshold_is_balanced(self):
        self.assertEqual(consumption_status(105, 100)["status"], "balanced")
        self.assertEqual(consumption_status(95, 100)["status"], "balanced")


if __name__ == "__main__":
    unittest.main()
