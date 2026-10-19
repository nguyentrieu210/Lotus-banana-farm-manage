"""Public, limited-information QR verification page for Lotus approved documents."""
import frappe

no_cache = 1

def get_context(context):
    from lotus_farm.digital_signature import verify_document
    token = frappe.form_dict.get("token") or ""
    context.result = verify_document(token)
    context.no_cache = 1
    context.no_breadcrumbs = 1
    context.show_sidebar = False
    context.title = "Xác minh chứng từ Lotus"
