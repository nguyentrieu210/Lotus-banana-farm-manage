"""Approved issue quotas must include drafts and cannot trust browser references."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

class TestIssueSources(unittest.TestCase):
    def setUp(self):
        frappe=types.ModuleType('frappe'); frappe.throw=Mock(side_effect=ValueError)
        utils=types.ModuleType('frappe.utils'); utils.flt=lambda x:float(x or 0)
        controls=types.ModuleType('lotus_farm.controls'); controls.lock=Mock()
        spec=importlib.util.spec_from_file_location('issue_test',Path(__file__).parents[1]/'lotus_farm/warehouse_issue.py')
        self.api=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'frappe':frappe,'frappe.utils':utils,'lotus_farm.controls':controls}):spec.loader.exec_module(self.api)
        self.api.approved=Mock();self.api.source_line=Mock(return_value={'item':'FERT','area':'A1','required_qty':5})
        self.api.allocated=Mock(return_value=0)
    def record(self,**kwargs):
        obj=types.SimpleNamespace(**kwargs);obj.get=lambda key:getattr(obj,key,None);return obj
    def doc(self,**kwargs):
        values=dict(name='DRAFT',company='Farm',docstatus=0,stock_entry_type='Material Issue',lotus_issue_mode='Plan',lotus_work_plan='PLAN',lotus_receiver='Team',remarks='Reason')
        values.update(kwargs);return self.record(**values)
    def row(self,**kwargs):
        values=dict(item_code='FERT',qty=2,conversion_factor=1,lotus_usage_area='A1',lotus_requirement='REQ',lotus_requirement_line='LINE')
        values.update(kwargs);return self.record(**values)
    def test_allocated_drafts_reduce_remaining_quantity(self):
        self.api.allocated.return_value=4
        with self.assertRaises(ValueError):self.api.validate_issue(self.doc(items=[self.row()]))
        self.api.allocated.assert_called_with('Material Requirement','REQ','LINE',exclude='DRAFT')
    def test_split_lines_are_checked_as_a_total(self):
        with self.assertRaises(ValueError):self.api.validate_issue(self.doc(items=[self.row(qty=3),self.row(qty=3)]))
    def test_browser_cannot_change_approved_item_or_area(self):
        for row in (self.row(item_code='OTHER'),self.row(lotus_usage_area='B2')):
            with self.assertRaises(ValueError):self.api.validate_issue(self.doc(items=[row]))
    def test_manual_issue_cannot_smuggle_a_request_reference(self):
        with self.assertRaises(ValueError):self.api.validate_issue(self.doc(lotus_issue_mode='Manual',items=[self.row()]))
    def test_pending_quantity_within_limit_is_valid(self):
        self.api.validate_issue(self.doc(items=[self.row(qty=5)]))
    def test_manual_issue_requires_receiver_area_and_reason(self):
        for args in ({'lotus_receiver':''},{'remarks':''},{'items':[self.row(lotus_requirement=None,lotus_requirement_line=None,lotus_usage_area='')]}):
            base=dict(lotus_issue_mode='Manual',items=[self.row(lotus_requirement=None,lotus_requirement_line=None)])
            base.update(args)
            with self.assertRaises(ValueError):self.api.validate_issue(self.doc(**base))
if __name__=='__main__':unittest.main()
