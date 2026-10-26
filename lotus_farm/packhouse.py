"""Quick receiving commands still use the same reviewed QC documents."""
import frappe
from lotus_farm.controls import require_role, lock
from lotus_farm.api import _insert_idempotent
from lotus_farm.rules import canonical_hash


@frappe.whitelist(methods=['POST'])
def receive_quality(client_event_id,farm,posting_date,harvest_lot,accepted_kg,defect_reason=None):
    require_role('Lotus QC Manager')
    if not client_event_id:frappe.throw('Thiếu mã sự kiện nhận hàng để thử lại.')
    frappe.get_doc('Farm',farm).check_permission('read');lock('Farm',farm)
    lot=frappe.get_doc('Harvest Lot',harvest_lot);lot.check_permission('read')
    if lot.farm!=farm or lot.docstatus!=1:frappe.throw('Chọn một lô đã duyệt trong vườn này.')
    from lotus_farm.daily_operations import number
    accepted=number(accepted_kg,'Accepted kg');rejected=float(lot.released_raw_kg)-accepted
    if rejected>0 and not defect_reason:frappe.throw('Chọn lý do cho khối lượng đầu vào bị loại.')
    payload=dict(farm=farm,posting_date=str(posting_date),harvest_lot=harvest_lot,accepted_kg=accepted,
        defects=[dict(defect_reason=defect_reason,weight_kg=rejected,affected_units=0,occurrences=0)] if rejected>0 else [])
    key=canonical_hash(['incoming-qc',frappe.session.user,client_event_id])
    doc=_insert_idempotent('Incoming Quality Inspection','client_event_id',key,payload,submit=True)
    return dict(document=doc.name,accepted_kg=doc.accepted_kg,rejected_kg=doc.rejected_kg)
