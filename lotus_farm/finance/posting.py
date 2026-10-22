"""Tài chính – Kế toán: the link from a Lotus document to the ERPNext voucher that posted it, reversal, and
month locking. One active posting per (source document, purpose): the unique active_key refuses a second
one even when two requests race; a reversed posting frees the key so the corrected document can post again.
"""
import calendar

import frappe
from frappe.utils import getdate, now_datetime

from lotus_farm.finance import setup

POSTING = 'Lotus Accounting Posting'
# Vouchers a closed month refuses (ERPNext Accounting Period checks them on submit and cancel).
LOCKED_DOCTYPES = ('Journal Entry', 'Purchase Invoice', 'Payment Entry', 'Purchase Receipt', 'Stock Entry', 'Stock Reconciliation')
MONTHS = 'Tháng %02d/%04d'


def active_key(source_doctype, source_name, purpose):
    return '%s|%s|%s' % (source_doctype, source_name, purpose)


def active(source_doctype, source_name, purpose):
    name = frappe.db.get_value(POSTING, {'active_key': active_key(source_doctype, source_name, purpose)})
    return frappe.get_doc(POSTING, name) if name else None


def guard(source_doctype, source_name, purpose):
    """Refuse a second posting of the same document for the same purpose (before any voucher is created)."""
    from lotus_farm.controls import lock
    lock(source_doctype, source_name)
    existing = active(source_doctype, source_name, purpose)
    if existing:
        frappe.throw('%s %s đã được ghi sổ (%s %s). Đảo bút toán đó trước nếu cần ghi lại.' % (
            source_doctype, source_name, existing.voucher_type, existing.voucher_name))


def record(source_doctype, source_name, purpose, voucher, amount=0, source_hash=''):
    doc = frappe.get_doc(dict(doctype=POSTING, company=voucher.get('company'), source_doctype=source_doctype, source_name=source_name, purpose=purpose,
                              source_hash=source_hash, voucher_type=voucher.doctype, voucher_name=voucher.name, posting_date=voucher.get('posting_date'),
                              amount=amount, state='Posted' if voucher.docstatus == 1 else 'Draft', active_key=active_key(source_doctype, source_name, purpose),
                              posted_by=frappe.session.user, posted_at=now_datetime()))
    doc.flags.ignore_permissions = True
    doc.flags.ignore_links = True
    try:
        doc.insert()
    except frappe.UniqueValidationError:
        frappe.throw('%s %s vừa được người khác ghi sổ. Tải lại để xem.' % (source_doctype, source_name))
    return doc


def mark_posted(voucher):
    """A draft voucher (payment waiting for signatures) was submitted: its posting becomes Posted."""
    name = frappe.db.get_value(POSTING, {'voucher_type': voucher.doctype, 'voucher_name': voucher.name, 'state': 'Draft'})
    if name:
        frappe.db.set_value(POSTING, name, dict(state='Posted', posting_date=voucher.posting_date, posted_at=now_datetime()))


def check_open(company, on_date, doctype='Journal Entry'):
    """Friendly refusal before ERPNext's own period check."""
    on_date = getdate(on_date)
    frozen = frappe.get_cached_value('Company', company, 'accounts_frozen_till_date') if frappe.get_meta('Company').has_field('accounts_frozen_till_date') else None
    if frozen and on_date <= getdate(frozen):
        frappe.throw('Sổ đã khóa đến ngày %s. Không ghi được chứng từ ngày %s.' % (frozen.strftime('%d/%m/%Y'), on_date.strftime('%d/%m/%Y')))
    period = frappe.db.sql("""select ap.period_name from `tabAccounting Period` ap join `tabClosed Document` cd on cd.parent=ap.name
        where ap.company=%s and ap.disabled=0 and %s between ap.start_date and ap.end_date and cd.document_type=%s and cd.closed=1 limit 1""",
                           (company, on_date, doctype))
    if period:
        frappe.throw('%s đã khóa sổ. Kế toán trưởng mở lại kỳ trước khi ghi chứng từ ngày %s.' % (period[0][0], on_date.strftime('%d/%m/%Y')))


@frappe.whitelist(methods=['POST'])
def reverse(posting, reason):
    """Cancel the ERPNext voucher (ERPNext writes the reversing ledger lines) and keep the link with the reason."""
    setup.require_chief()
    reason = str(reason or '').strip()
    if len(reason) < 5:
        frappe.throw('Ghi lý do đảo bút toán (ít nhất 5 ký tự).')
    doc = frappe.get_doc(POSTING, posting)
    if doc.state == 'Reversed':
        frappe.throw('Bút toán này đã được đảo.')
    voucher = frappe.get_doc(doc.voucher_type, doc.voucher_name)
    check_open(voucher.company, voucher.posting_date, voucher.doctype)
    voucher.flags.ignore_permissions = True
    if voucher.docstatus == 1:
        voucher.cancel()
    elif voucher.docstatus == 0:
        voucher.delete()
    doc.db_set(dict(state='Reversed', active_key=None, reversed_by=frappe.session.user, reversed_at=now_datetime(), reason=reason[:500]))
    doc.add_comment('Info', 'Đảo bút toán %s %s: %s' % (doc.voucher_type, doc.voucher_name, reason[:300]))
    return dict(state='Reversed', voucher=doc.voucher_name)


# Month locking ---------------------------------------------------------------------------------------

def _month_bounds(month):
    year, mon = (int(x) for x in str(month).split('-')[:2])
    return '%04d-%02d-01' % (year, mon), '%04d-%02d-%02d' % (year, mon, calendar.monthrange(year, mon)[1]), MONTHS % (mon, year)


def periods(company, year=None):
    rows = frappe.db.sql("""select ap.name, ap.period_name, ap.start_date, ap.end_date, ap.disabled,
        sum(cd.closed) closed_docs, count(cd.name) docs from `tabAccounting Period` ap left join `tabClosed Document` cd on cd.parent=ap.name
        where ap.company=%s group by ap.name order by ap.start_date""", (company,), as_dict=True)
    return [dict(r, closed=bool(r.closed_docs) and not r.disabled) for r in rows if not year or str(r.start_date)[:4] == str(year)]


@frappe.whitelist(methods=['POST'])
def close_month(month):
    """Lock one month for every voucher type Lotus posts (chief accountant)."""
    setup.require_chief()
    company = setup.company()
    start, end, label = _month_bounds(month)
    name = frappe.db.get_value('Accounting Period', {'company': company, 'start_date': start, 'end_date': end})
    doc = frappe.get_doc('Accounting Period', name) if name else frappe.get_doc(dict(doctype='Accounting Period', company=company, start_date=start, end_date=end,
                                                                                       period_name=label + ' - ' + frappe.get_cached_value('Company', company, 'abbr')))
    doc.disabled = 0
    existing = {d.document_type: d for d in doc.get('closed_documents') or []}
    for doctype in LOCKED_DOCTYPES:
        if doctype in existing:
            existing[doctype].closed = 1
        else:
            doc.append('closed_documents', dict(document_type=doctype, closed=1))
    doc.flags.ignore_permissions = True
    doc.save()
    doc.add_comment('Info', 'Khóa sổ %s bởi %s' % (label, frappe.session.user))
    return dict(period=doc.name, closed=True)


@frappe.whitelist(methods=['POST'])
def reopen_month(month, reason):
    setup.require_chief()
    reason = str(reason or '').strip()
    if len(reason) < 5:
        frappe.throw('Ghi lý do mở lại kỳ (ít nhất 5 ký tự).')
    company = setup.company()
    start, end, label = _month_bounds(month)
    name = frappe.db.get_value('Accounting Period', {'company': company, 'start_date': start, 'end_date': end})
    if not name:
        frappe.throw('%s chưa khóa.' % label)
    doc = frappe.get_doc('Accounting Period', name)
    for d in doc.get('closed_documents') or []:
        d.closed = 0
    doc.flags.ignore_permissions = True
    doc.save()
    doc.add_comment('Info', 'Mở lại %s bởi %s: %s' % (label, frappe.session.user, reason[:300]))
    return dict(period=doc.name, closed=False)
