"""Private print/PDF for the Lotus employee intake record.

The employee's full ID and the approving signature are never available via
anonymous HTML or a publicly addressable File URL.
"""
import base64
import json
import re
from pathlib import Path
from urllib.parse import urlencode

import frappe

no_cache = 1


def get_context(context, company=None, employee=None):
    from lotus_farm.hr_workspace import _manager, _company, _choose

    _manager()
    company = company or frappe.form_dict.get("company")
    employee = employee or frappe.form_dict.get("employee")
    company_doc = _company(company)
    doc = _choose("Employee", employee, company)
    doc.check_permission("read")

    context.employee = doc
    context.company_name = company_doc.get("company_name") or company_doc.name
    context.issuer = doc.get("lotus_id_issue_at") or ""
    context.cccd = doc.get_password("lotus_cccd", raise_exception=False) if doc.get("lotus_cccd_hash") else ""
    context.logo_data = "data:image/png;base64," + base64.b64encode(
        Path(frappe.get_app_path("lotus_farm", "public", "images", "lotus-agritech-header-v2.png")).read_bytes()
    ).decode("ascii")
    context.signed_at = ""
    context.signed_by = ""
    context.signature_image = ""
    if doc.get("lotus_onboarding_state") == "Ready":
        events = frappe.get_all(
            "Lotus Signature Event",
            filters={"document_type": "Employee", "document_name": doc.name, "action": "ONBOARD_APPROVE"},
            fields=["actor", "signed_at", "details"],
            order_by="signed_at desc", limit_page_length=1,
        )
        if events:
            event = events[0]
            context.signed_by = frappe.db.get_value("User", event.actor, "full_name") or event.actor
            context.signed_at = frappe.utils.get_datetime(event.signed_at).strftime("%d/%m/%Y %H:%M")
            snapshot_id = json.loads(event.details or "{}").get("signature_file")
            if snapshot_id:
                file = frappe.get_doc("File", snapshot_id)
                if (file.attached_to_doctype == "Employee"
                        and file.attached_to_name == doc.name and file.is_private):
                    context.signature_image = "data:image/png;base64," + base64.b64encode(
                        file.get_content(encodings=[])
                    ).decode("ascii")
    context.pdf_url = "/api/method/lotus_farm.www.lotus_employee_print.download_pdf?" + urlencode(
        {"company": company, "employee": employee}
    )
    context.no_cache = 1


@frappe.whitelist()
def download_pdf(company, employee):
    from frappe.utils.pdf import get_pdf

    context = frappe._dict()
    get_context(context, company, employee)
    html = frappe.render_template("lotus_farm/www/lotus_employee_print.html", context)
    pdf = get_pdf(html, options={"page-size": "A4", "print-media-type": None})
    frappe.local.response.filename = "phieu-tiep-nhan-" + re.sub(r"[^a-zA-Z0-9._-]", "_", employee)[:80] + ".pdf"
    frappe.local.response.filecontent = pdf
    frappe.local.response.type = "pdf"
    frappe.local.response.display_content_as = "attachment"
