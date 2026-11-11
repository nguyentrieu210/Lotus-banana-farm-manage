"""Bulk delete of ticked drafts: every document goes through its own screen's guarded delete (pure, frappe stubbed)."""
import sys
import types
import unittest
from unittest import mock


class _Throw(Exception):
    pass


def _frappe():
    fake = types.ModuleType("frappe")
    fake.whitelist = lambda **kw: (lambda fn: fn)
    fake.parse_json = lambda v: __import__("json").loads(v) if isinstance(v, str) else v
    def throw(msg, exc=None):
        raise _Throw(msg)
    fake.throw = throw
    fake.clear_messages = lambda: None
    fake.utils = types.SimpleNamespace(strip_html=lambda s: s)
    fake.db = mock.MagicMock()
    return fake


class BulkDeleteTest(unittest.TestCase):
    def setUp(self):
        self.fake = _frappe()
        lotus = types.ModuleType("lotus_farm")
        lotus.__path__ = []
        self.warehouse = types.SimpleNamespace(delete_draft=mock.Mock())
        lotus.warehouse = self.warehouse
        modules = {"frappe": self.fake, "lotus_farm": lotus, "lotus_farm.warehouse": self.warehouse}
        self.patch = mock.patch.dict(sys.modules, modules)
        self.patch.start()
        sys.modules.pop("lotus_farm.bulk_delete", None)
        import importlib.util, pathlib
        spec = importlib.util.spec_from_file_location("lotus_farm.bulk_delete", pathlib.Path(__file__).resolve().parents[1] / "lotus_farm" / "bulk_delete.py")
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)

    def tearDown(self):
        self.patch.stop()

    def test_one_refusal_does_not_stop_the_rest(self):
        self.fake.db.exists.return_value = True
        self.fake.db.get_value.return_value = "2026-11-11 10:00:00"
        def delete(doctype, name, modified):
            if name == "B":
                raise _Throw("Chỉ xóa phiếu nháp đơn giản chưa ghi sổ.")
        self.warehouse.delete_draft.side_effect = delete
        result = self.mod.drafts('[{"doctype":"Stock Entry","name":"A"},{"doctype":"Stock Entry","name":"B"},{"doctype":"Stock Entry","name":"A"}]')
        self.assertEqual(result["deleted"], [{"doctype": "Stock Entry", "name": "A"}])
        self.assertEqual(result["failed"][0]["name"], "B")
        self.assertIn("chưa ghi sổ", result["failed"][0]["message"])
        self.fake.db.rollback.assert_called_once_with(save_point="bulk_delete")
        self.assertEqual(self.warehouse.delete_draft.call_count, 2)

    def test_unknown_doctype_is_refused_not_deleted(self):
        self.fake.db.exists.return_value = True
        self.fake.db.get_value.return_value = "2026-11-11 10:00:00"
        result = self.mod.drafts([{"doctype": "GL Entry", "name": "X"}])
        self.assertEqual(result["deleted"], [])
        self.assertIn("không xóa hàng loạt", result["failed"][0]["message"])

    def test_limit(self):
        with self.assertRaises(_Throw):
            self.mod.drafts([{"doctype": "Stock Entry", "name": str(i)} for i in range(201)])


if __name__ == "__main__":
    unittest.main()
