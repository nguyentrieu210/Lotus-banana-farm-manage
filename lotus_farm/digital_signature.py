"""Lotus per-user signing preferences.

Selecting a provider does NOT activate a certificate or sign PDFs. Actual PDF
PAdES signing will require a verified provider integration with server-side
authorization and certificate validation. Never receive private keys or PINs.
"""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

PROVIDERS = ("", "VNPT SmartCA", "Viettel-CA", "FPT.eSign", "Khác")
FIELD = "lotus_signature_provider"


def install_fields():
    create_custom_fields({
        "User": [
            {
                "fieldname": FIELD,
                "label": "Nhà cung cấp chữ ký số Lotus",
                "fieldtype": "Select",
                "options": "\n".join(PROVIDERS),
                "insert_after": "mobile_no",
                "no_copy": 1,
            },
        ],
    })


def _user():
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw("Bạn cần đăng nhập để quản lý chữ ký số.", frappe.PermissionError)
    return user


@frappe.whitelist()
def my_signature_profile():
    user = _user()
    registered = bool(frappe.get_meta("User").has_field(FIELD))
    provider = frappe.db.get_value("User", user, FIELD) if registered else ""
    return {
        "user": user,
        "full_name": frappe.db.get_value("User", user, "full_name") or user,
        "provider": provider or "",
        "providers": [{"value": key, "label": key or "Chưa chọn"} for key in PROVIDERS],
        "connected": False,
        "certificate_verified": False,
        "can_sign_pdf": False,
        "configured": registered,
        "message": "Chưa kết nối chứng thư số. Chọn nhà cung cấp chỉ là bước chuẩn bị, chưa ký được PDF.",
    }


@frappe.whitelist(methods=["POST"])
def set_signature_provider(provider=""):
    user = _user()
    provider = str(provider or "").strip()
    if provider not in PROVIDERS:
        frappe.throw("Nhà cung cấp chữ ký số không hợp lệ.")
    if not frappe.get_meta("User").has_field(FIELD):
        frappe.throw("Chức năng chưa được cập nhật trên máy chủ. Cần chạy migrate trước khi lưu.")
    # Only the logged-in user's preference may be changed. Never let clients
    # change another user's provider, certificate state or signing authority.
    frappe.db.set_value("User", user, FIELD, provider)
    return my_signature_profile()
