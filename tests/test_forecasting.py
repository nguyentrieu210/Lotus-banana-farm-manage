import unittest

from lotus_farm.forecasting import ForecastInputError, calculate_availability


class ForecastingTestCase(unittest.TestCase):
    def test_available_forecast(self):
        result = calculate_availability(
            source_bunch_qty=1000,
            avg_bunch_weight_kg=20,
            expected_defect_rate_percent=5,
            safety_buffer_percent=5,
            committed_qty_kg=10000,
        )
        self.assertEqual(result["gross_forecast_kg"], 20000)
        self.assertEqual(result["saleable_forecast_kg"], 19000)
        self.assertEqual(result["safe_saleable_kg"], 18050)
        self.assertEqual(result["available_to_promise_kg"], 8050)
        self.assertEqual(result["shortage_kg"], 0)
        self.assertEqual(result["availability_status"], "Available")

    def test_overcommitted_forecast(self):
        result = calculate_availability(
            source_bunch_qty=100,
            avg_bunch_weight_kg=20,
            committed_qty_kg=2500,
        )
        self.assertEqual(result["available_to_promise_kg"], -500)
        self.assertEqual(result["shortage_kg"], 500)
        self.assertEqual(result["availability_status"], "Overcommitted")

    def test_invalid_rate(self):
        with self.assertRaises(ForecastInputError):
            calculate_availability(100, 20, expected_defect_rate_percent=101)


if __name__ == "__main__":
    unittest.main()
