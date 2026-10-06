import json
import unittest
from pathlib import Path

from lotus_farm.domain import SupplyError, mass_balance, quantity, require_capacity, stock_quantity
from lotus_farm.forecasting import ForecastInputError, calculate_availability


class SupplyRulesTest(unittest.TestCase):
    def test_decimal_balance_includes_waste_and_recorded_loss(self):
        self.assertEqual(mass_balance("1000.3", ["800.1", "100.1"], "100.1"), 0)

    def test_unexplained_mass_is_rejected_in_both_directions(self):
        for output in (900, 1100):
            with self.assertRaises(SupplyError):
                mass_balance(1000, [output], tolerance_kg=1)

    def test_tolerance_is_absolute_kg(self):
        self.assertAlmostEqual(mass_balance(1000, [999.5], tolerance_kg=.5), .5)
        with self.assertRaises(SupplyError):
            mass_balance(1000, [999.4], tolerance_kg=.5)

    def test_second_reservation_cannot_exceed_remaining_capacity(self):
        require_capacity(8000, 10000)
        with self.assertRaises(SupplyError):
            require_capacity(8000, 10000, already_reserved=8000)
        require_capacity(2000, 10000, already_reserved=8000)

    def test_zero_negative_and_nonfinite_inputs(self):
        for value in (-1, float("nan"), float("inf"), "bad"):
            with self.assertRaises(SupplyError):
                quantity(value)
            with self.assertRaises(ForecastInputError):
                calculate_availability(value, 25)
        with self.assertRaises(SupplyError):
            require_capacity(0, 10)

    def test_uom_is_explicit_and_positive(self):
        self.assertEqual(stock_quantity(1000, 10), 100)
        with self.assertRaises(SupplyError):
            stock_quantity(1000, 0)

    def test_safe_commit_never_exceeds_packed_and_shortage_keeps_sign(self):
        for survival in (0, 50, 100):
            for release in (0, 50, 100):
                for packout in (0, 50, 100):
                    r = calculate_availability(1000, 25, bunch_survival_rate_percent=survival,
                                               quality_pass_rate_percent=release, packout_rate_percent=packout,
                                               safety_buffer_percent=5, committed_qty_kg=30000)
                    self.assertLessEqual(r['safe_saleable_kg'], r['packed_forecast_kg'])
                    self.assertLess(r['available_to_promise_kg'], 0)
                    self.assertEqual(r['shortage_kg'], -r['available_to_promise_kg'])


class DocTypeSchemaTest(unittest.TestCase):
    def test_field_orders_and_select_options(self):
        for path in Path('lotus_farm').rglob('*.json'):
            d = json.loads(path.read_text())
            if d.get('doctype') != 'DocType':
                continue
            with self.subTest(path=str(path)):
                names = [f['fieldname'] for f in d['fields']]
                self.assertEqual(len(names), len(set(names)))
                self.assertEqual(set(names), set(d['field_order']))
                for f in d['fields']:
                    if f['fieldtype'] == 'Select':
                        self.assertNotIn('\\n', f['options'])


if __name__ == '__main__':
    unittest.main()
