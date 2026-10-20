"""Public, limited-information QR verification page for Lotus documents.

?dt=&n=&r=&t= : QR printed on every signed Lotus document (lotus_farm.signing.verify).
?token=       : QR on signed purchase order PDFs archived before named signers (digital_signature).
"""
import frappe

no_cache = 1

def get_context(context):
    form = frappe.form_dict
    if form.get("t"):
        from lotus_farm.signing import verify
        context.result = verify(form.get("dt"), form.get("n"), form.get("r"), form.get("t"))
    else:
        from lotus_farm.digital_signature import verify_document
        context.result = verify_document(form.get("token") or "")
    context.no_cache = 1
    context.no_breadcrumbs = 1
    context.show_sidebar = False
    context.title = "Xác minh chứng từ Lotus"
