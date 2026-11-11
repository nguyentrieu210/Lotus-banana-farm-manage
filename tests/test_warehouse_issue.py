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
        values=dict(name='DRAFT',company='Farm',docstatus=0,stock_entry_type='Material Issue',lotus_issue_mode='Request',lotus_receiver='Team',remarks='Reason')
        values.update(kwargs);return self.record(**values)
    def row(self,**kwargs):
        values=dict(item_code='FERT',qty=2,conversion_factor=1,lotus_usage_area='A1',material_request='REQ',material_request_item='LINE')
        values.update(kwargs);return self.record(**values)
    def test_allocated_drafts_reduce_remaining_quantity(self):
        self.api.allocated.return_value=4
        with self.assertRaises(ValueError):self.api.validate_issue(self.doc(items=[self.row()]))
        self.api.allocated.assert_called_with('REQ','LINE',exclude='DRAFT')
    def test_split_lines_are_checked_as_a_total(self):
        with self.assertRaises(ValueError):self.api.validate_issue(self.doc(items=[self.row(qty=3),self.row(qty=3)]))
    def test_browser_cannot_change_approved_item_or_area(self):
        for row in (self.row(item_code='OTHER'),self.row(lotus_usage_area='B2')):
            with self.assertRaises(ValueError):self.api.validate_issue(self.doc(items=[row]))
    def test_manual_issue_cannot_smuggle_a_request_reference(self):
        with self.assertRaises(ValueError):self.api.validate_issue(self.doc(lotus_issue_mode='Manual',items=[self.row()]))
    def test_pending_quantity_within_limit_is_valid(self):
        self.api.validate_issue(self.doc(items=[self.row(qty=5)]))
    def test_request_issue_requires_a_request_line_on_every_row(self):
        with self.assertRaises(ValueError):self.api.validate_issue(self.doc(items=[self.row(),self.row(material_request=None,material_request_item=None)]))
    def test_unknown_issue_mode_is_rejected(self):
        with self.assertRaises(ValueError):self.api.validate_issue(self.doc(lotus_issue_mode='Other',items=[self.row()]))
    def test_manual_issue_requires_receiver_area_and_reason(self):
        for args in ({'lotus_receiver':''},{'remarks':''},{'items':[self.row(material_request=None,material_request_item=None,lotus_usage_area='')]}):
            base=dict(lotus_issue_mode='Manual',items=[self.row(material_request=None,material_request_item=None)])
            base.update(args)
            with self.assertRaises(ValueError):self.api.validate_issue(self.doc(**base))
        self.api.validate_issue(self.doc(lotus_issue_mode='Manual',items=[self.row(material_request=None,material_request_item=None)]))
    # Spec 005: the issue line carries the lô and việc of the approved request line, not what the browser sent.
    def test_request_line_takes_lot_and_work_of_the_source(self):
        self.api.source_line.return_value={'item':'FERT','area':'A1','required_qty':5,'farm':'LOTUS-222','farm_block':'BLK-A1','work_type':'PHUN'}
        row=self.row(lotus_farm_block='BLK-B9',lotus_work_type='OTHER',lotus_farm='X')
        self.api.validate_issue(self.doc(items=[row]))
        self.assertEqual((row.lotus_farm,row.lotus_farm_block,row.lotus_work_type),('LOTUS-222','BLK-A1','PHUN'))
    def test_old_request_without_lot_column_keeps_the_row(self):
        row=self.row(lotus_farm_block='BLK-A1')
        self.api.validate_issue(self.doc(items=[row]))
        self.assertEqual(row.lotus_farm_block,'BLK-A1')
    def test_mismatch_still_refused_with_dimensions(self):
        self.api.source_line.return_value={'item':'FERT','area':'A1','required_qty':5,'farm_block':'BLK-A1','work_type':'PHUN'}
        with self.assertRaises(ValueError):self.api.validate_issue(self.doc(items=[self.row(item_code='OTHER')]))
    def warehouse_stub(self):
        stub=types.ModuleType('lotus_farm.warehouse');stub._access=Mock();stub._company=Mock()
        masters=types.ModuleType('lotus_farm.warehouse_masters');masters.item_uoms=lambda item:[dict(uom='Kg',conversion_factor=1)]
        return patch.dict(sys.modules,{'lotus_farm.warehouse':stub,'lotus_farm.warehouse_masters':masters})
    def test_choices_leave_out_issued_requests_and_name_them(self):
        import datetime
        frappe=self.api.frappe;frappe.has_permission=Mock(return_value=True)
        frappe.get_list=Mock(return_value=[self.record(name='MR-1',transaction_date='2026-11-10',schedule_date=datetime.date(2026,11,12),title='Phun thuốc · Tổ 3 · A12')])
        with self.warehouse_stub():result=self.api.choices('Farm','Request')
        filters=frappe.get_list.call_args.kwargs['filters']
        self.assertIn('Issued',filters['status'][1])
        self.assertEqual(result['rows'][0]['label'],'MR-1 · Phun thuốc · Tổ 3 · A12 · cần 12/11')
    def test_lines_carry_the_request_header(self):
        frappe=self.api.frappe
        request=self.record(name='MR-1',owner='doi@x',title='Phun',set_warehouse='KHO',schedule_date='2026-11-12',lotus_issue_receiver='EMP-1',
                            lotus_crew='DOI',lotus_work_team='T3',lotus_issue_approved_by='doi@x',lotus_issue_approved_at=None,lotus_request_note='',
                            items=[self.record(name='LINE',lotus_work_type='PHUN')])
        self.api.approved=Mock(return_value=request)
        self.api.source_line.return_value={'item':'FERT','area':'A1','required_qty':5}
        frappe.get_doc=Mock(return_value=self.record(stock_uom='Kg'))
        frappe.db=types.SimpleNamespace(get_value=lambda dt,name,field=None,*a,**k:{'Employee':'Nguyễn Văn A','User':'Đội trưởng','Work Team':'Tổ','Work Type':'Phun thuốc'}[dt])
        with self.warehouse_stub():result=self.api.lines('Farm','Request','MR-1')
        header=result['header']
        self.assertEqual((header['warehouse'],header['receiver'],header['receiver_name'],header['work_name'],header['approved_by']),('KHO','EMP-1','Nguyễn Văn A','Phun thuốc','doi@x'))
        self.assertEqual(len(result['rows']),1)
if __name__=='__main__':unittest.main()
