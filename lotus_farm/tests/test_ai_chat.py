"""Read-only tool boundaries; no database or provider calls required."""
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from lotus_farm import ai_chat as ai


class ChatToolsTest(unittest.TestCase):
    def setUp(self):
        self.fields = [SimpleNamespace(fieldname=name, fieldtype=kind, permlevel=0)
                       for name, kind in [('name', 'Data'), ('actual_qty', 'Float'),
                                          ('password', 'Password'), ('api_key', 'Data'), ('private_note', 'Data')]]
        self.meta = SimpleNamespace(name='Bin', istable=False,
                                    has_field=lambda name: name in {f.fieldname for f in self.fields},
                                    get_field=lambda name: next((f for f in self.fields if f.fieldname == name), None),
                                    get_table_fields=lambda: [])
        self.frappe = MagicMock()
        self.frappe.db.exists.return_value = True
        self.frappe.has_permission.return_value = True
        self.frappe.get_meta.return_value = self.meta
        self.frappe.get_list.return_value = [{'total': 5}]
        self.addCleanup(patch.stopall)
        patch.object(ai, 'frappe', self.frappe).start()
        patch.object(ai, 'get_permitted_fields', return_value=['name', 'actual_qty', 'password', 'api_key']).start()

    def test_query_uses_permission_aware_list_and_caps_rows(self):
        result = ai.query('Bin', ['sum(actual_qty) as total'], [['actual_qty', '>', 0]],
                          order_by='total desc', limit=50000)
        self.assertEqual(result['limited_to'], ai.MAX_ROWS)
        self.frappe.get_list.assert_called_once_with('Bin', fields=[{'SUM': 'actual_qty', 'as': 'total'}],
            filters=[['actual_qty', '>', 0]], group_by=None, order_by='total desc', limit_page_length=500)

    def test_denied_doctype_and_direct_child_reads_never_query(self):
        self.frappe.has_permission.return_value = False
        with self.assertRaises(ai.ToolError):
            ai.query('Bin')
        self.frappe.has_permission.return_value = True
        self.meta.istable = True
        with self.assertRaises(ai.ToolError):
            ai.query('Bin')
        self.frappe.get_list.assert_not_called()

    def test_secret_and_restricted_fields_cannot_select_filter_group_or_sort(self):
        for field in ['password', 'api_key', 'private_note']:
            for arguments in [{'fields': [field]}, {'fields': [f'max({field}) as value']},
                              {'filters': [[field, '=', 'x']]}, {'group_by': field}, {'order_by': field}]:
                with self.subTest(field=field, arguments=arguments), self.assertRaises(ai.ToolError):
                    ai.query('Bin', **arguments)
        self.frappe.get_list.assert_not_called()

    def test_sql_expressions_and_unknown_operators_are_rejected(self):
        for arguments in [{'fields': ['name; DROP TABLE tabBin']}, {'fields': ['sleep(10)']},
                          {'group_by': 'name, actual_qty'}, {'filters': [['name', 'sql', 'x']]}]:
            with self.subTest(arguments=arguments), self.assertRaises(ai.ToolError):
                ai.query('Bin', **arguments)
        self.frappe.get_list.assert_not_called()

    def test_document_checks_record_and_field_permissions_and_excludes_secrets(self):
        doc = MagicMock()
        doc.meta = self.meta
        doc.as_dict.return_value = {'name': 'BIN-1', 'actual_qty': 5, 'password': 'hidden',
                                   'api_key': 'hidden', 'private_note': 'restricted'}
        self.frappe.get_doc.return_value = doc
        self.assertEqual(ai.get_document('Bin', 'BIN-1'), {'name': 'BIN-1', 'actual_qty': 5})
        doc.check_permission.assert_called_once_with('read')
        doc.apply_fieldlevel_read_permissions.assert_called_once()

    def test_child_rows_are_redacted_with_parent_permissions(self):
        self.meta.get_table_fields = lambda: [SimpleNamespace(fieldname='items')]
        child = MagicMock()
        child.meta = SimpleNamespace(name='Purchase Order Item', get_field=self.meta.get_field,
                                     get_table_fields=lambda: [])
        child.as_dict.return_value = {'name': 'row', 'actual_qty': 5, 'api_key': 'hidden'}
        doc = MagicMock(meta=self.meta, doctype='Purchase Order')
        doc.as_dict.return_value = {'name': 'PO-1', 'items': [{}]}
        doc.get.return_value = [child]
        self.frappe.get_doc.return_value = doc
        self.assertEqual(ai.get_document('Purchase Order', 'PO-1')['items'], [{'name': 'row', 'actual_qty': 5}])
        ai.get_permitted_fields.assert_any_call('Purchase Order Item', parenttype='Purchase Order', permission_type='read')

    def test_tool_registry_has_no_write_operations(self):
        self.assertEqual(set(ai.RUNNERS), {'search_doctypes', 'describe_doctype', 'query', 'get_document'})


if __name__ == '__main__':
    unittest.main()
