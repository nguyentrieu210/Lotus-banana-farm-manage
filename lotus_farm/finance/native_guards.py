"""Server checks for finance documents submitted/cancelled via normal ERPNext REST or Desk.

Lotus buttons are not a security boundary. Native document events protect
approval signatures, posting locks and the unique voucher/source link.
"""
import frappe
from frappe.utils import flt, getdate, now_datetime

from lotus_farm.finance import posting, setup


def _enabled_for(doc):
    if getattr(frappe.flags, 'in_install', False) or getattr(frappe.flags, 'in_migrate', False):
        return False
    if not frappe.db.exists('DocType', setup.SETTINGS):
        return False
    cfg = setup.settings()
    return bool(cfg.finance_enabled and doc.get('company') and doc.company == cfg.company)


def payment_approved(doc):
    from lotus_farm import signing, signing_rules
    steps, _ = signing._rows(doc)
    required = signing_rules.chain('payment_voucher')['steps']
    current = signing.fingerprint(doc)
    return len(steps) == len(required) and all(
        r.step_index == i and r.state == signing_rules.SIGNED
        and r.content_hash and r.content_hash == current
        for i, r in enumerate(steps))


def guard(doc, method=None):
    if not _enabled_for(doc):
        return
    if method in ('before_submit', 'before_cancel', 'before_update_after_submit'):
        date = doc.get('posting_date')
        if date:
            month = str(getdate(date))[:7]
            result = posting.active(setup.SETTINGS, setup.SETTINGS, 'Result Closing', month)
            result_reverse = (method == 'before_cancel' and result and doc.doctype == 'Journal Entry'
                              and doc.name == result.voucher_name and getattr(frappe.flags, 'lotus_finance_reverse', False))
            if result and not result_reverse:
                frappe.throw('Tháng %s đã kết chuyển. Phải đảo kết chuyển kết quả trước khi thay đổi sổ.' % month)
    if method == 'before_cancel':
        deps = frappe.get_all(posting.POSTING, filters={'voucher_type': doc.doctype, 'voucher_name': doc.name, 'state': 'Posted'},
                              fields=['purpose'])
        if any(x.purpose in ('Cost Closing', 'Costing', 'Result Closing') for x in deps):
            if not getattr(frappe.flags, 'lotus_finance_reverse', False):
                frappe.throw('Phải đảo kết chuyển qua quy trình Tài chính – Kế toán.')
    if method != 'before_submit':
        return
    if doc.doctype == 'Payment Entry' and (doc.get('payment_type') == 'Pay' or doc.get('payment_type')=='Receive' and doc.get('party_type')=='Supplier'):
        if not payment_approved(doc):
            frappe.throw('Phiếu chi chưa ký đủ hoặc đã đổi nội dung sau khi ký. Không được ghi sổ.')
    if doc.doctype == 'Journal Entry':
        if doc.get('lotus_payment_kind') in setup.SIGNED_JE_KINDS:
            if not payment_approved(doc):
                frappe.throw('Phiếu chi chưa ký đủ hoặc đã đổi nội dung sau khi ký. Không được ghi sổ.')
        elif any(flt(r.credit_in_account_currency) > 0
                 and r.account in (setup.mapping().get('cash'), setup.mapping().get('bank'))
                 for r in doc.get('accounts') or []):
            frappe.throw('Không thể chi tiền bằng bút toán trực tiếp; phải dùng phiếu chi có duyệt.')


def sync_cancel(doc, method=None):
    """Release active_key when a voucher is cancelled outside Lotus finance screens."""
    if not _enabled_for(doc):
        return
    matches = frappe.get_all(posting.POSTING,
                             filters={'voucher_type': doc.doctype, 'voucher_name': doc.name, 'state': ['!=', 'Reversed']},
                             pluck='name')
    for name in matches:
        frappe.db.set_value(posting.POSTING, name,
                            dict(state='Reversed', active_key=None,
                                 reversed_by=frappe.session.user, reversed_at=now_datetime(),
                                 reason='Đã hủy từ ERPNext (tự đồng bộ)'),
                            update_modified=False)
