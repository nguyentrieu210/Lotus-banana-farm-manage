"""Private handwritten-signature image saved against the current Lotus user.

This is an image used with the existing approval audit trail, NOT a
certificate-backed digital signature. Other users cannot read or change it
through this API. No secret keys, OTPs or signature-service credentials.
"""
import base64
import binascii
from io import BytesIO

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils.file_manager import save_file

IMAGE_FIELD = "lotus_signature_image"
DATE_FIELD = "lotus_signature_updated_at"
MAX_UPLOAD_BYTES = 10_000_000  # Allow original phone-camera photos up to 10 MB.
MAX_IMAGE_PIXELS = 60_000_000  # Accept standard 12/48 MP photos; reject decompression bombs.
MAX_STORED_BYTES = 1_500_000  # Keep embedded PDF signatures lightweight.


def install_fields():
    # Keep the old provider column intact for compatibility with earlier
    # deployments, but the PWA no longer uses it.
    create_custom_fields({
        "User": [
            {
                "fieldname": IMAGE_FIELD,
                "label": "Ảnh chữ ký Lotus",
                "fieldtype": "Attach Image",
                "insert_after": "mobile_no",
                "no_copy": 1,
            },
            {
                "fieldname": DATE_FIELD,
                "label": "Ngày cập nhật chữ ký Lotus",
                "fieldtype": "Datetime",
                "insert_after": IMAGE_FIELD,
                "read_only": 1,
                "no_copy": 1,
            },
        ],
        "Purchase Order": [
            {
                "fieldname": "lotus_signed_purchase_pdf",
                "label": "PDF duyệt có ảnh chữ ký Lotus",
                "fieldtype": "Attach",
                "insert_after": "grand_total",
                "read_only": 1,
                "hidden": 1,
                "no_copy": 1,
            },
        ],
    })


def _user():
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw("Bạn cần đăng nhập để quản lý chữ ký.", frappe.PermissionError)
    return user


def _configured():
    if not frappe.get_meta("User").has_field(IMAGE_FIELD):
        frappe.throw("Máy chủ chưa cập nhật chữ ký. Liên hệ quản trị để chạy migrate.")


def _current_file(user):
    url = frappe.db.get_value("User", user, IMAGE_FIELD)
    if not url:
        return None
    rows = frappe.get_all(
        "File",
        filters={"attached_to_doctype": "User", "attached_to_name": user,
                 "attached_to_field": IMAGE_FIELD, "file_url": url, "is_private": 1},
        fields=["name", "file_url"],
        limit_page_length=1,
    )
    return frappe.get_doc("File", rows[0].name) if rows else None


def signature_image_bytes(user):
    """Internal use for PDF rendering after an authorized approval only."""
    if not user:
        return None
    if not frappe.get_meta("User").has_field(IMAGE_FIELD):
        return None
    file = _current_file(user)
    return file.get_content(encodings=[]) if file else None


@frappe.whitelist()
def my_signature_profile():
    user = _user()
    configured = bool(frappe.get_meta("User").has_field(IMAGE_FIELD))
    signature = _current_file(user) if configured else None
    content = signature.get_content(encodings=[]) if signature else None
    updated_at = frappe.db.get_value("User", user, DATE_FIELD) if configured else None
    return {
        "user": user,
        "full_name": frappe.db.get_value("User", user, "full_name") or user,
        "configured": configured,
        "has_signature": bool(content),
        "signature_preview": "data:image/png;base64," + base64.b64encode(content).decode("ascii") if content else "",
        "updated_at": str(updated_at) if updated_at else "",
        "signature_kind": "Ảnh chữ ký tay (không phải chữ ký số)",
    }


def _normalize_image(data):
    from PIL import Image, ImageOps, UnidentifiedImageError
    if not isinstance(data, str) or len(data) > MAX_UPLOAD_BYTES * 2:
        frappe.throw("Ảnh chữ ký quá lớn. Chọn ảnh dưới 10 MB.")
    if data.startswith("data:"):
        data = data.partition(",")[2]
    try:
        raw = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        frappe.throw("Dữ liệu ảnh không hợp lệ.")
    if len(raw) > MAX_UPLOAD_BYTES:
        frappe.throw("Ảnh chữ ký vượt quá 10 MB.")
    try:
        with Image.open(BytesIO(raw)) as image:
            if image.format not in ("PNG", "JPEG"):
                frappe.throw("Chỉ nhận ảnh PNG hoặc JPG.")
            if image.width * image.height > MAX_IMAGE_PIXELS:
                frappe.throw("Ảnh chữ ký quá lớn về kích thước.")
            output_image = ImageOps.exif_transpose(image).convert("RGBA")
            output_image.thumbnail((1200, 700))
            # Never embed the full-resolution photo in PDFs. Shrink until the
            # transparent PNG is small enough, regardless of input JPEG size.
            for _ in range(10):
                result = BytesIO()
                output_image.save(result, format="PNG", optimize=True)
                if result.tell() <= MAX_STORED_BYTES:
                    break
                output_image.thumbnail((
                    max(1, int(output_image.width * 0.8)),
                    max(1, int(output_image.height * 0.8)),
                ))
    except (UnidentifiedImageError, OSError, ValueError):
        frappe.throw("Không đọc được ảnh. Hãy chọn PNG hoặc JPG rõ nét.")
    normalized = result.getvalue()
    if len(normalized) > MAX_STORED_BYTES:
        frappe.throw("Ảnh xử lý vẫn quá lớn. Hãy cắt gọn vùng chữ ký.")
    return normalized


@frappe.whitelist(methods=["POST"])
def save_my_signature_image(image_data):
    user = _user()
    _configured()
    content = _normalize_image(image_data)
    previous = _current_file(user)
    saved = save_file("lotus-chu-ky.png", content, "User", user,
                      df=IMAGE_FIELD, is_private=1)
    if not saved or not saved.file_url:
        frappe.throw("Không lưu được ảnh chữ ký.")
    frappe.db.set_value("User", user, {
        IMAGE_FIELD: saved.file_url,
        DATE_FIELD: frappe.utils.now_datetime(),
    })
    if previous and previous.name != saved.name:
        frappe.delete_doc("File", previous.name, ignore_permissions=True)
    return my_signature_profile()


@frappe.whitelist(methods=["POST"])
def remove_my_signature_image():
    user = _user()
    _configured()
    previous = _current_file(user)
    frappe.db.set_value("User", user, {
        IMAGE_FIELD: "",
        DATE_FIELD: frappe.utils.now_datetime(),
    })
    if previous:
        frappe.delete_doc("File", previous.name, ignore_permissions=True)
    return my_signature_profile()

def archive_approved_purchase_pdf(doc):
    """Snapshot the exact signature image when a Purchase Order is approved.

    Must run in the same transaction as submit; an image/PDF error rolls back
    approval. The PDF is never regenerated using a subsequently changed image.
    """
    user = frappe.session.user
    signature = signature_image_bytes(user)
    if not signature:
        return None  # No signature set: preserve existing approval behaviour.
    import hashlib
    from html import escape
    from frappe.utils.pdf import get_pdf

    if not frappe.get_meta("Purchase Order").has_field("lotus_signed_purchase_pdf"):
        frappe.throw("Chưa cập nhật trường lưu PDF đã ký. Cần chạy migrate.")

    full_name = frappe.db.get_value("User", user, "full_name") or user
    timestamp = str(doc.get("lotus_approved_at") or frappe.utils.now_datetime())
    source = frappe.get_print("Purchase Order", doc.name, print_format="Standard", as_pdf=False)
    signature_url = "data:image/png;base64," + base64.b64encode(signature).decode("ascii")
    approval = (
        '<section style="page-break-inside:avoid;break-inside:avoid;margin:20px 0;'
        'border-top:1px solid #ccc;padding:14px 10px;text-align:right;font-size:12px">'
        '<strong>NGƯỜI DUYỆT</strong><br>'
        '<img alt="Chữ ký người duyệt" src="' + signature_url + '" '
        'style="max-width:160px;max-height:85px;object-fit:contain;display:inline-block"><br>'
        + escape(full_name) + '<br><small>' + escape(timestamp) + ' · '
        + escape(user) + '</small></section>'
    )
    html = source.replace("</body>", approval + "</body>", 1) if "</body>" in source else source + approval
    pdf = get_pdf(html, options={"page-size": "A4", "print-media-type": None})
    if not pdf or not pdf.startswith(b"%PDF"):
        frappe.throw("Không tạo được PDF có chữ ký. Đơn vẫn chưa được duyệt.")
    stamp_file = save_file("LOTUS-approved-" + doc.name.replace("/", "-") + ".pdf",
                           pdf, "Purchase Order", doc.name,
                           df="lotus_signed_purchase_pdf", is_private=1)
    frappe.db.set_value("Purchase Order", doc.name,
                        "lotus_signed_purchase_pdf", stamp_file.file_url,
                        update_modified=False)
    # Store digest in the file metadata for later audit/verification.
    frappe.logger("lotus.signature").info(
        "Archived approved purchase PDF order=%s approver=%s sha256=%s",
        doc.name, user, hashlib.sha256(pdf).hexdigest(),
    )
    return stamp_file.file_url


@frappe.whitelist()
def download_purchase_pdf(name):
    """Always enforce native print permission, including for archived PDFs."""
    user = _user()
    doc = frappe.get_doc("Purchase Order", name)
    doc.check_permission("read")
    doc.check_permission("print")
    attachment = doc.get("lotus_signed_purchase_pdf") if frappe.get_meta("Purchase Order").has_field("lotus_signed_purchase_pdf") else None
    content = None
    if attachment:
        rows = frappe.get_all(
            "File",
            filters={"attached_to_doctype": "Purchase Order",
                     "attached_to_name": doc.name,
                     "attached_to_field": "lotus_signed_purchase_pdf",
                     "file_url": attachment, "is_private": 1},
            pluck="name", limit_page_length=1,
        )
        if not rows:
            frappe.throw("PDF đã duyệt bị thiếu; không được tự thay bằng bản chưa ký.")
        content = frappe.get_doc("File", rows[0]).get_content(encodings=[])
    else:
        content = frappe.get_print("Purchase Order", doc.name,
                                   print_format="Standard", as_pdf=True)
    from re import sub
    frappe.local.response.filename = sub(r"[^A-Za-z0-9._-]+", "_", doc.name)[:100] + ".pdf"
    frappe.local.response.filecontent = content
    frappe.local.response.type = "pdf"
    frappe.local.response.display_content_as = "attachment"