import unittest

from lotus_farm import units


class Units(unittest.TestCase):
    def test_vietnamese_names(self):
        for code, name in (('Tonne', 'Tấn'), ('Nos', 'Cái'), ('Litre', 'Lít'), ('Set', 'Bộ'), ('Meter', 'Mét'), ('Kg', 'kg'), ('Box', 'Hộp / thùng'),
                           ('Square Meter', 'Mét²'), ('Cubic Meter', 'Mét³'), ('Bunch', 'Buồng')):
            self.assertEqual(units.label(code), name)
        self.assertEqual(units.label('1 kg/gói'), '1 kg/gói', 'a pack size keeps its own words')
        self.assertEqual(units.label('Thùng 13kg'), 'Thùng 13kg')
        self.assertEqual(units.label(''), '')
        self.assertEqual(units.label('Bao'), 'Bao')


if __name__ == '__main__':
    unittest.main()
