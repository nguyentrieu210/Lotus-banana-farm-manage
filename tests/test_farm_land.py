import unittest

from lotus_farm import farm_land_rules as fl


def lot(**values):
    base = dict(block_code='A-1', area_ha=2.0, lotus_tree_count=0, variety=None, planting_date=None, lotus_inferred_planting_date=None, plots=1)
    return dict(base, **values)


class FarmLandRules(unittest.TestCase):
    def test_density_only_for_counted_lots(self):
        self.assertEqual(fl.density(4200, 2.0), 2100)
        self.assertIsNone(fl.density(0, 2.0), 'zero trees means not counted, not a density of 0')
        self.assertIsNone(fl.density(500, 0))

    def test_summary_averages_over_counted_land_only(self):
        rows = [lot(lotus_tree_count=4000, area_ha=2), lot(lotus_tree_count=0, area_ha=8, plots=3)]
        for r in rows:
            r['gaps'] = fl.gaps(r, has_map=True)
        s = fl.summary(rows)
        self.assertEqual((s['blocks'], s['area_ha'], s['plots'], s['trees'], s['counted_blocks']), (2, 10.0, 4, 4000, 1))
        self.assertEqual(s['trees_per_ha'], 2000, 'the uncounted 8 ha do not dilute the average')
        self.assertEqual(s['gaps']['trees'], 1)

    def test_gaps_name_what_is_missing(self):
        self.assertEqual(fl.gaps(lot(), has_map=False), ['trees', 'variety', 'map', 'planting'])
        complete = lot(lotus_tree_count=10, variety='VIP 126', lotus_inferred_planting_date='2026-01-01')
        self.assertEqual(fl.gaps(complete, has_map=True), ['planting'], 'an inferred date is not an observed planting date')
        complete['planting_date'] = '2026-01-01'
        self.assertEqual(fl.gaps(complete, has_map=True), [])

    def test_density_bands_for_the_map(self):
        self.assertEqual([fl.density_band(v) for v in (None, 1200, 1500, 2000, 2500)], [None, 0, 1, 2, 4])

    def test_excel_row_changes_and_empty_cells_keep_data(self):
        current = dict(block_name='Lô A-1', farm_zone='A', area_ha=2.0, variety='VIP 126', lotus_tree_count=4000, planting_date='2026-01-05')
        row = dict(block_name='Lô A-1', farm_zone='B', area_ha='2,10', variety='', lotus_tree_count='4100', lotus_tree_count_source='Đếm 20/10 tổ A', planting_date='05/01/2026')
        result = fl.diff_row(current, row, plots_area=2.1, known_zones={'A', 'B'})
        self.assertEqual(set(result['changes']), {'farm_zone', 'area_ha', 'lotus_tree_count', 'lotus_tree_count_source'})
        self.assertEqual(result['changes']['area_ha'], (2.0, 2.1))
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['warnings'], [])

    def test_excel_row_errors_and_warnings(self):
        current = dict(area_ha=2.0, lotus_tree_count=4000)
        result = fl.diff_row(current, dict(area_ha='abc', lotus_tree_count=4100, planting_date='2026/13/01', farm_zone='Z'), plots_area=2.0, known_zones={'A'})
        self.assertIn('Diện tích (ha): cần số không âm', result['errors'])
        self.assertTrue(any('Nguồn số cây' in e for e in result['errors']), 'a new tree count needs its source')
        self.assertTrue(any(e.startswith('Ngày trồng') for e in result['errors']))
        self.assertTrue(any('Khu "Z"' in w for w in result['warnings']))
        far = fl.diff_row(dict(area_ha=2.0), dict(area_ha=3.0), plots_area=2.0)
        self.assertTrue(far['warnings'] and far['errors'] == [], 'an area far from its plots is a warning, not an error')


if __name__ == '__main__':
    unittest.main()
