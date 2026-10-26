"""Regression checks for the 26/10 Book2 parameter reference."""
import datetime as dt
import unittest

from lotus_farm import cut_forecast_rules as rules
from lotus_farm import forecast_book2_reference as book2


class Book2ParameterReferenceTest(unittest.TestCase):
    def test_reference_is_valid_and_four_waves_add_to_one(self):
        clean, errors = rules.validate_profile(book2.PROFILE_PATCH)
        self.assertEqual(errors, [])
        self.assertEqual(sum(clean[x] for x in rules.WAVES), 1.0)
        self.assertEqual((clean['days_to_first_shoot'],
                          clean['shoot_to_inject_days'],
                          clean['inject_to_budcut_days'],
                          clean['budcut_to_harvest_days']), (180, 5, 16, 65))
        self.assertEqual(clean['sucker_per_tree'], 1)

    def test_old_defaults_are_not_silently_replaced(self):
        self.assertEqual(rules.DEFAULTS['days_to_first_shoot'], 120)
        self.assertEqual(rules.DEFAULTS['inject_to_budcut_days'], 15)
        data = book2.reference(rules.DEFAULTS)
        differences = {r['field'] for r in data['comparisons'] if r['changed']}
        self.assertEqual(differences, {'days_to_first_shoot', 'inject_to_budcut_days'})
        self.assertEqual(data['different_count'], 2)

    def test_using_explicit_new_profile_changes_dates_only(self):
        entries = [dict(zone='A', cut_date=dt.date(2026, 1, 1), tree_qty=1000)]
        old = rules.compute(entries, rules.DEFAULTS)['totals']
        new = rules.compute(entries, book2.PROFILE_PATCH)['totals']
        self.assertEqual(old['trees'], new['trees'])
        self.assertEqual(old['pack'], new['pack'])
        self.assertEqual(old['tonnes'], new['tonnes'])
        self.assertEqual(new['first_harvest'] - old['first_harvest'], dt.timedelta(days=61))

    def test_extra_excel_facts_are_not_applied_to_engine(self):
        entries = {x['code']: x for x in book2.reference()['extras']}
        self.assertEqual(entries['next_generation_sucker_yield']['value'], 0.97)
        self.assertEqual(entries['apply_next_generation_yield_to_existing_trees']['value'], 0)
        self.assertEqual(entries['flower_removal_days_after_injection']['value'], [7, 10, 13])
        self.assertEqual(entries['fruit_measure_days_before_harvest']['value'], [10, 7])
        self.assertEqual([entries[f'finished_kg_per_bunch_cycle_{i}']['value'] for i in (1, 2)], [19, 20])


if __name__ == '__main__':
    unittest.main()
