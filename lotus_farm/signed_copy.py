"""Fixed PDF of a document once a signing round is complete (spec 003, research R1).

signing._completed calls archive() inside the signing transaction, after the document's own effect
(submit, close) ran, so a failure to render or store the PDF undoes the last signature. There is one copy
per document and round (the Lotus Signed Copy name refuses a second one), stored as a private File
attached to the document, with the SHA-256 the QR verification page compares against.
"""
import hashlib
import re
from contextlib import contextmanager

import frappe
from frappe.utils import now_datetime

COPY = 'Lotus Signed Copy'


@contextmanager
def system_rights():
    """Render with system rights: a named signer may not read every linked record (a director signing a
    stock document). What is rendered is fixed by the document, not by who looks. Only the session user
    and the permission caches are swapped; request data and the session id are left untouched. The print
    footer still names the real person (frappe.flags.lotus_print_user)."""
    local = frappe.local
    user = local.session.user
    previous = getattr(frappe.flags, 'lotus_print_user', None)
    frappe.flags.lotus_print_user = previous or user
    local.session.user, local.user_perms = 'Administrator', None
    try:
        yield
    finally:
        local.session.user, local.user_perms = user, None
        frappe.flags.lotus_print_user = previous


def as_reader(doc, build):
    """Run a print builder for the current user: with their own rights when they may read (and print) the document,
    with system rights when they are only named in its signing round (spec 003, FR-027)."""
    from lotus_farm import signing
    if frappe.has_permission(doc.doctype, 'read', doc=doc):
        doc.check_permission('print')
        return build()
    if not signing.can_view(doc=doc):
        doc.check_permission('read')  # raises the standard permission error
    with system_rights():
        return build()


def _proposal(doc):
    from lotus_farm import print_kit as pk
    from lotus_farm.www import lotus_material_proposal_print as printer
    return pk.render('proposal.html', printer.build(doc.name)), True


def _order(doc):
    from lotus_farm.www import lotus_purchase_order_print as printer
    return printer.html(doc), False


def _payment(doc):
    from lotus_farm.www import lotus_payment_print as printer
    return printer.html(doc), False


def _stock(doc):
    from lotus_farm import print_kit as pk
    from lotus_farm.www import lotus_stock_print as printer
    return pk.render('stock.html', printer.build(doc.doctype, doc.name)), False


# Document types with a Lotus Print layout. Others (e.g. the timekeeping period) keep their live print.
RENDERERS = {'Material Request': _proposal, 'Purchase Order': _order, 'Purchase Receipt': _stock,
             'Stock Entry': _stock, 'Stock Reconciliation': _stock, 'Payment Entry': _payment}


def register(doctype, render):
    """Modules with their own print (payment vouchers) add their layout here."""
    RENDERERS[doctype] = render


def _slug(name):
    return re.sub(r'[^A-Za-z0-9._-]+', '-', str(name))[:80]


def archive(doc, chain, round_):
    """Render, store and record the signed copy of one round. None when the document has no print layout."""
    render = RENDERERS.get(doc.doctype)
    if not render:
        return None
    from lotus_farm.lotus_farm.doctype.lotus_signed_copy.lotus_signed_copy import copy_name
    name = copy_name(doc.doctype, doc.name, round_)
    if frappe.db.exists(COPY, name):
        return frappe.get_doc(COPY, name)
    from frappe.utils.file_manager import save_file
    from lotus_farm import print_kit as pk, signing
    signer = frappe.session.user
    frappe.flags.lotus_signed_copy_by = signer  # the print footer names the last signer, not the system user
    try:
        with system_rights():
            html, landscape = render(doc)
            pdf = pk.pdf(str(html), landscape=landscape)
    finally:
        frappe.flags.lotus_signed_copy_by = None
    if not pdf or not pdf.startswith(b'%PDF'):
        frappe.throw('Không tạo được bản PDF đã ký. Chữ ký cuối chưa được ghi; hãy ký lại.')
    digest = hashlib.sha256(pdf).hexdigest()
    stored = save_file('da-ky-%s-luot-%s.pdf' % (_slug(doc.name), round_), pdf, doc.doctype, doc.name, is_private=1)
    when = now_datetime()
    copy = frappe.get_doc(dict(doctype=COPY, document_type=doc.doctype, document_name=doc.name, round=round_, chain=chain,
                               file_name=stored.name, file_url=stored.file_url, pdf_sha256=digest,
                               content_hash=signing.fingerprint(doc),
                               pages=max(1, pdf.count(b'/Type /Page') - pdf.count(b'/Type /Pages')),
                               created_by=signer, created_at=when)).insert(ignore_permissions=True)
    from lotus_farm.digital_signature import _event
    _event(doc, 'ARCHIVED', signer, when, pdf_hash=digest, details='Bản PDF đã ký, lượt %s' % round_,
           extra=dict(round=round_, content_hash=copy.content_hash))
    return copy


def latest(doctype, name, round_=None):
    filters = {'document_type': doctype, 'document_name': name}
    if round_:
        filters['round'] = int(round_)
    rows = frappe.get_all(COPY, filters=filters, fields=['name', 'round', 'file_name', 'file_url', 'pdf_sha256', 'created_at'],
                          order_by='round desc', limit_page_length=1)
    return rows[0] if rows else None


def current(doc):
    """The signed copy of the document's latest signing round, None while that round is not complete (a new
    round after a return has no copy yet) or once the document is no longer in force."""
    from lotus_farm import signing
    if doc.docstatus != 1:
        return None
    _, round_ = signing._rows(doc)
    return latest(doc.doctype, doc.name, round_) if round_ else None


def respond(copy, name):
    """Send the stored PDF as the HTTP response."""
    frappe.local.response.filename = _slug(name) + '.pdf'
    frappe.local.response.filecontent = pdf_bytes(copy)
    frappe.local.response.type = 'pdf'


def pdf_bytes(copy):
    return frappe.get_doc('File', copy['file_name'] if isinstance(copy, dict) else copy.file_name).get_content(encodings=[])


def matches(copy):
    """The stored file still hashes to what was recorded when the round completed."""
    try:
        return hashlib.sha256(pdf_bytes(copy)).hexdigest() == (copy['pdf_sha256'] if isinstance(copy, dict) else copy.pdf_sha256)
    except Exception:
        return False
