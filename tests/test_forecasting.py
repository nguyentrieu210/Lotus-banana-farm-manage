import unittest

from lotus_farm.forecasting import ForecastInputError, calculate_availability


class ForecastingTestCase(unittest.TestCase):
    def test_v0_backward_compatible_defect_calculation(self):
        result = calculate_availability(
            source_bunch_qty=1000,
            avg_bunch_weight_kg=20,
            expected_defect_rate_percent=5,
            safety_buffer_percent=5,
            committed_qty_kg=10000,
        )
        self.assertEqual(result["gross_forecast_kg"], 20000)
        self.assertEqual(result["saleable_forecast_kg"], 19000)
        self.assertEqual(result["packed_forecast_kg"], 19000)
        self.assertEqual(result["safe_saleable_kg"], 18050)
        self.assertEqual(result["available_to_promise_kg"], 8050)

    def test_v1_full_pipeline(self):
        result = calculate_availability(
            source_bunch_qty=1000,
            avg_bunch_weight_kg=25,
            bunch_survival_rate_percent=97,
            quality_pass_rate_percent=92,
            packout_rate_percent=84,
            safety_buffer_percent=5,
            committed_qty_kg=10000,
        )
        self.assertEqual(result["expected_harvest_bunch_qty"], 970)
        self.assertEqual(result["gross_forecast_kg"], 24250)
        self.assertEqual(result["saleable_forecast_kg"], 22310)
        self.assertEqual(result["packed_forecast_kg"], 18740.4)
        self.assertEqual(result["safe_saleable_kg"], 17803.38)
        self.assertEqual(result["available_to_promise_kg"], 7803.38)
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

    def test_invalid_rates(self):
        with self.assertRaises(ForecastInputError):
            calculate_availability(
                100,
                20,
                quality_pass_rate_percent=101,
            )
        with self.assertRaises(ForecastInputError):
            calculate_availability(
                100,
                20,
                packout_rate_percent=-1,
            )


if __name__ == "__main__":
    unittest.main()
