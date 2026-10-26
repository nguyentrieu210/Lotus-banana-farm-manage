"""Persistent farm risk alerts, with acknowledgement and automatic resolution."""
import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, now_datetime
from lotus_farm.controls import command, command_allowed, check_farm, lock, require_role
from lotus_farm.rules import canonical_hash


class AlertDocument(Document):
    def validate(self):
        check_farm(self)
        if command_allowed(self,'alert_compute'):return
        require_role('Lotus Farm Manager')
        before=self.get_doc_before_save()
        if not before:frappe.throw('Cảnh báo được tạo tự động từ số liệu của vườn.')
        for field in ('farm','posting_date','event_key','kind','severity','metric_value','message'):
            if self.get(field)!=before.get(field):frappe.throw('Bằng chứng của cảnh báo do hệ thống tính, không được sửa.')
        if self.status!=before.status:
            if self.status!='Acknowledged' or before.status!='Open' or not (self.acknowledgement_reason or '').strip():
                frappe.throw('Xác nhận cảnh báo đang mở kèm lý do; cảnh báo chỉ được đóng khi số liệu nguồn đã khớp.')
            self.acknowledged_by=frappe.session.user;self.acknowledged_at=now_datetime()
        elif self.acknowledged_by!=before.acknowledged_by or self.acknowledged_at!=before.acknowledged_at:
            frappe.throw('Thông tin người xác nhận do máy chủ ghi, không được sửa.')

    def on_trash(self):frappe.throw('Không được xóa lịch sử cảnh báo.')


def refresh_alerts():
    if not frappe.db.get_single_value('Lotus Farm Settings','enable_proactive_alerts'):return
    from lotus_farm.reporting import dashboard
    from lotus_farm.console import material_status
    date=nowdate()
    for farm in frappe.get_all('Farm',filters={'active':1},pluck='name'):
        lock('Farm',farm)
        result=dashboard(date,date,farm=farm)['farms']
        if not result:continue
        active={a['kind']:a for a in result[0]['alerts']}
        material=material_status(farm,date)
        shortage=sum(1 for r in material['rows'] if r['shortage_qty'] and r['shortage_qty']>0)
        if shortage:active['Material']=dict(kind='Material',value=shortage)
        for kind,alert in active.items():
            key=canonical_hash([farm,date,kind])
            existing=frappe.db.get_value('Lotus Alert',{'event_key':key},'name')
            doc=frappe.get_doc('Lotus Alert',existing) if existing else frappe.new_doc('Lotus Alert')
            doc.update(dict(farm=farm,posting_date=date,event_key=key,kind=kind,severity='Warning',metric_value=alert['value'],message=f'{kind}: {alert["value"]}'))
            if doc.status=='Resolved':doc.status='Open';doc.acknowledged_by=None;doc.acknowledged_at=None;doc.acknowledgement_reason=None
            with command(doc,'alert_compute'):doc.save(ignore_permissions=True)
        for row in frappe.get_all('Lotus Alert',filters={'farm':farm,'posting_date':date,'status':['!=','Resolved']},fields=['name','kind']):
            if row.kind not in active:
                doc=frappe.get_doc('Lotus Alert',row.name);doc.status='Resolved'
                with command(doc,'alert_compute'):doc.save(ignore_permissions=True)
