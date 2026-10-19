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


if __name__ == "__main__":
    unittest.main()
