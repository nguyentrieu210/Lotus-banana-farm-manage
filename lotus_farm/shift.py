"""Packhouse shift operational evidence; ERP remains the stock authority."""
import frappe
from frappe.utils import flt, get_datetime, getdate
from lotus_farm.daily_operations import DailyDocument, number, day_guard
from lotus_farm.controls import lock, whole_count


class ShiftDocument(DailyDocument):
    def validate_daily(self):
        if get_datetime(self.ended_at) <= get_datetime(self.started_at):
            frappe.throw('Giờ kết thúc ca phải sau giờ bắt đầu.')
        if getdate(self.started_at) != getdate(self.posting_date):
            frappe.throw('Giờ bắt đầu ca phải đúng ngày làm việc.')
        if frappe.db.exists(self.doctype, {'farm':self.farm,'posting_date':self.posting_date,'shift_code':self.shift_code,'docstatus':['<',2],'name':['!=',self.name]}):
            frappe.throw('Ca này đã tồn tại cho vườn/ngày.')
        seen=set()
        for row in self.labor:
            if row.employee in seen:frappe.throw('Nhân viên xuất hiện hai lần trong ca.')
            seen.add(row.employee)
            employee=frappe.get_doc('Employee',row.employee);employee.check_permission('read')
            lock('Employee',row.employee)
            if employee.company!=self.company or employee.status!='Active':frappe.throw('Nhân viên của ca phải đang làm việc trong công ty này.')
            days=number(row.workdays,'Shift workdays',positive=True)
            other=frappe.db.sql('''select l.workdays from `tabPackhouse Shift Labor` l join `tabPackhouse Shift` s on s.name=l.parent where s.posting_date=%s and s.docstatus=1 and l.employee=%s and s.name!=%s FOR UPDATE''',(self.posting_date,row.employee,self.name))
            field_days=sum(flt(v) for v in frappe.get_all('Labor Allocation',filters={'employee':row.employee,'posting_date':self.posting_date,'docstatus':1},pluck='allocated_workdays'))
            capacity=1
            if frappe.db.exists('DocType','Attendance'):
                statuses=set(frappe.get_all('Attendance',filters={'employee':row.employee,'attendance_date':self.posting_date,'docstatus':1},pluck='status'))
                capacity=0 if statuses.intersection({'Absent','On Leave'}) else (0.5 if 'Half Day' in statuses else 1)
            if sum(flt(v[0]) for v in other)+field_days+days>capacity+0.000001:frappe.throw('Phân bổ ngoài vườn và ở xưởng vượt một công của nhân viên.')
        for row in self.preprocessing:
            lot=frappe.get_doc('Harvest Lot',row.harvest_lot);lot.check_permission('read');lock('Harvest Lot',lot.name)
            if lot.farm!=self.farm or lot.docstatus!=1:frappe.throw('Sơ chế cần lô nhận hàng đã duyệt của vườn này.')
            if whole_count(row.processed_bunches,'Processed bunches')<1:frappe.throw('Sơ chế cần số buồng là số nguyên dương.')
            number(row.processed_kg,'Processed kg',positive=True)
            if row.started_at and row.ended_at and get_datetime(row.ended_at)<=get_datetime(row.started_at):frappe.throw('Giờ kết thúc sơ chế phải sau giờ bắt đầu.')
        values=shift_summary(self)
        for field in ('input_kg','finished_kg','secondary_kg','loss_kg','cartons','packout_percent'):self.set(field,values[field])

    def before_submit(self):
        values=shift_summary(self)
        if not values['runs']:frappe.throw('Ca cần ít nhất một đợt đóng gói.')
        if any(r['docstatus']!=1 or r['stock_status']!=1 for r in values['runs']):frappe.throw('Duyệt đóng gói đã qua QC và ghi sổ kho ERP trước khi đóng ca.')
        by_lot={}
        for row in self.preprocessing:by_lot[row.harvest_lot]=by_lot.get(row.harvest_lot,0)+flt(row.processed_kg)
        expected={}
        for run in values['runs']:
            for source in frappe.get_doc('Packout Run',run['name']).sources:expected[source.harvest_lot]=expected.get(source.harvest_lot,0)+flt(source.input_kg)
        if set(by_lot)!=set(expected) or any(abs(by_lot[k]-expected[k])>0.0005 for k in expected):frappe.throw('Số kg sơ chế phải khớp khối lượng đưa vào đóng gói theo từng lô.')
        if not self.labor:frappe.throw('Ca cần có số liệu nhân công thực tế.')

    def before_cancel(self):
        day_guard(self)
        if frappe.db.exists('Packout Run',{'packhouse_shift':self.name,'docstatus':1}):frappe.throw('Hủy các đợt đóng gói phụ thuộc trước khi hủy ca này.')


def shift_summary(shift):
    result=dict(input_kg=0,finished_kg=0,secondary_kg=0,loss_kg=0,cartons=0,packout_percent=None,runs=[])
    for name in frappe.get_list('Packout Run',filters={'packhouse_shift':shift.name,'docstatus':['<',2]},pluck='name',limit_page_length=10000):
        run=frappe.get_doc('Packout Run',name);run.check_permission('read')
        result['runs'].append(dict(name=name,docstatus=run.docstatus,stock_status=frappe.db.get_value('Stock Entry',run.stock_entry,'docstatus') if run.stock_entry else None))
        if run.docstatus!=1:continue
        result['input_kg']+=flt(run.input_kg);result['loss_kg']+=flt(run.reject_kg)+flt(run.other_loss_kg)
        for row in run.outputs:
            result['finished_kg' if row.output_type=='Finished' else 'secondary_kg']+=flt(row.net_kg)
            if row.output_type=='Finished':result['cartons']+=int(row.cartons or 0)
    if result['input_kg']:result['packout_percent']=result['finished_kg']/result['input_kg']*100
    return result


def shift_link_guard(doc, method=None):
    if not doc.get('packhouse_shift'):return
    shift=frappe.get_doc('Packhouse Shift',doc.packhouse_shift);shift.check_permission('read');lock('Packhouse Shift',shift.name)
    date=doc.get('packing_date') or doc.get('posting_date')
    if shift.farm!=doc.farm or getdate(date)!=getdate(shift.posting_date):frappe.throw('Ca phải khớp vườn và ngày làm việc.')
    if shift.docstatus!=0:frappe.throw('Ca đã đóng/hủy không nhận thay đổi; mở lại bằng cách hủy rồi lập bản sửa.')


def scale_link_guard(doc,method=None):
    references=[(doc.get('scale_reading'),doc.get('gross_weight_kg') or doc.get('released_raw_kg'))]
    if doc.doctype=='Packout Run':references=[(r.get('scale_reading'),r.net_kg) for r in doc.outputs]
    for name,weight in references:
        if not name:continue
        reading=frappe.get_doc('Scale Reading',name);reading.check_permission('read')
        if reading.farm!=doc.farm or abs(flt(reading.net_kg)-flt(weight))>0.0005:frappe.throw('Vườn/số kg tịnh của lần cân phải khớp giao dịch.')
