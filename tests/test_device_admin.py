import sys
import types
import unittest

try:
    import frappe  # noqa: F401
    from lotus_farm import device_admin
except ImportError:
    utils = types.ModuleType('frappe.utils')
    for name in ('get_datetime', 'get_url', 'getdate', 'now_datetime', 'nowdate'):
        setattr(utils, name, lambda *a: None)
    sys.modules['frappe'], sys.modules['frappe.utils'] = types.ModuleType('frappe'), utils
    sys.modules['frappe'].whitelist = lambda *args, **kwargs: lambda fn: fn
    try:
        from lotus_farm import device_admin
    finally:
        del sys.modules['frappe'], sys.modules['frappe.utils']

PEOPLE = [dict(name='E1', employee_name='Thị Phiêu'), dict(name='E2', employee_name='Lìu Ní Kiệt'), dict(name='E3', employee_name='Thị Linh'),
          dict(name='E4', employee_name='Thị Linh')]


class SuggestEmployee(unittest.TestCase):
    def test_name_on_the_clock_matches_without_accents(self):
        self.assertEqual(device_admin.suggest('THI PHIEU', PEOPLE), 'E1')
        self.assertEqual(device_admin.suggest('Liu Ni Kiet', PEOPLE), 'E2')
        self.assertEqual(device_admin.suggest('Kiet', PEOPLE), 'E2', 'a clock often keeps only the given name')

    def test_ambiguous_or_empty_names_are_not_guessed(self):
        self.assertIsNone(device_admin.suggest('Thi Linh', PEOPLE), 'two employees share the name')
        self.assertIsNone(device_admin.suggest('', PEOPLE))
        self.assertIsNone(device_admin.suggest('Nguyen Van A', PEOPLE))


if __name__ == '__main__':
    unittest.main()
