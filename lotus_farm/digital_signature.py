"""Private signature images, role-checked approvals, QR verification and audit.

Image-based internal electronic signatures are not certificate-based PDF signing.
"""
import base64
import binascii
import hashlib
import hmac
import secrets
from datetime import timedelta
from io import BytesIO

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils.file_manager import save_file

IMAGE_FIELD = "lotus_signature_image"
DATE_FIELD = "lotus_signature_updated_at"
INITIAL_FIELD = "lotus_initials_image"
INITIAL_UPDATED_FIELD = "lotus_initials_updated_at"
DATE_FORMAT_FIELD = "lotus_signature_date_format"
DATE_FORMATS = ("DD/MM/YYYY", "DD-MM-YYYY", "LONG_VI")
MAX_UPLOAD_BYTES = 10_000_000
MAX_IMAGE_PIXELS = 60_000_000
MAX_STORED_BYTES = 1_500_000


def install_fields():
    # Keep legacy provider field unchanged; do not expose certificate status.
    create_custom_fields({
        "User": [
            {"fieldname": IMAGE_FIELD, "label": "Ảnh chữ ký Lotus",
             "fieldtype": "Attach Image", "insert_after": "mobile_no", "no_copy": 1},
            {"fieldname": DATE_FIELD, "label": "Ngày cập nhật chữ ký",
             "fieldtype": "Datetime", "insert_after": IMAGE_FIELD,
             "read_only": 1, "no_copy": 1},
            {"fieldname": INITIAL_FIELD, "label": "Ảnh ký nháy Lotus",
             "fieldtype": "Attach Image", "insert_after": DATE_FIELD, "no_copy": 1},
            {"fieldname": INITIAL_UPDATED_FIELD, "label": "Ngày cập nhật ký nháy",
             "fieldtype": "Datetime", "insert_after": INITIAL_FIELD,
             "read_only": 1, "no_copy": 1},
            {"fieldname": DATE_FORMAT_FIELD, "label": "Định dạng ngày ký Lotus",
             "fieldtype": "Select", "options": "\n".join(DATE_FORMATS),
             "default": DATE_FORMATS[0], "insert_after": INITIAL_UPDATED_FIELD,
             "no_copy": 1},
        ],
        "Purchase Order": [
            {"fieldname": "lotus_signed_purchase_pdf", "label": "PDF đã duyệt có chữ ký",
             "fieldtype": "Attach", "insert_after": "grand_total",
             "read_only": 1, "hidden": 1, "no_copy": 1},
            {"fieldname": "lotus_signature_verify_hash", "label": "Mã QR kiểm chứng",
             "fieldtype": "Data", "insert_after": "lotus_signed_purchase_pdf",
             "read_only": 1, "hidden": 1, "no_copy": 1},
            {"fieldname": "lotus_signature_pdf_sha256", "label": "Mã băm PDF",
             "fieldtype": "Data", "insert_after": "lotus_signature_verify_hash",
             "read_only": 1, "hidden": 1, "no_copy": 1},
            {"fieldname": "lotus_initials_by", "label": "Người ký nháy",
             "fieldtype": "Link", "options": "User",
             "insert_after": "lotus_signature_pdf_sha256", "read_only": 1, "no_copy": 1},
            {"fieldname": "lotus_initials_at", "label": "Thời điểm ký nháy",
             "fieldtype": "Datetime", "insert_after": "lotus_initials_by",
             "read_only": 1, "no_copy": 1},
            {"fieldname": "lotus_initials_snapshot", "label": "Bản lưu ảnh ký nháy",
             "fieldtype": "Attach Image", "insert_after": "lotus_initials_at",
             "read_only": 1, "hidden": 1, "no_copy": 1},
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


def _current_file(user, field=IMAGE_FIELD):
    if not frappe.get_meta("User").has_field(field):
        return None
    url = frappe.db.get_value("User", user, field)
    if not url:
        return None
    rows = frappe.get_all("File", filters={
        "attached_to_doctype": "User", "attached_to_name": user,
        "attached_to_field": field, "file_url": url, "is_private": 1,
    }, pluck="name", limit_page_length=1)
    return frappe.get_doc("File", rows[0]) if rows else None


def signature_image_bytes(user):
    """Private bytes for PDF rendering after an authorized approval."""
    if not user:
        return None
    file = _current_file(user)
    return file.get_content(encodings=[]) if file else None


def initials_image_bytes(user):
    """Private bytes of the user's ký nháy image, None when it is not set up."""
    if not user or not frappe.get_meta("User").has_field(INITIAL_FIELD):
        return None
    file = _current_file(user, INITIAL_FIELD)
    return file.get_content(encodings=[]) if file else None


@frappe.whitelist()
def my_signature_profile():
    user = _user()
    configured = bool(frappe.get_meta("User").has_field(IMAGE_FIELD))
    signature = _current_file(user) if configured else None
    initials = _current_file(user, INITIAL_FIELD) if configured else None
    content = signature.get_content(encodings=[]) if signature else None
    initial_bytes = initials.get_content(encodings=[]) if initials else None
    updated_at = frappe.db.get_value("User", user, DATE_FIELD) if configured else None
    date_fmt = frappe.db.get_value("User", user, DATE_FORMAT_FIELD) if configured and frappe.get_meta("User").has_field(DATE_FORMAT_FIELD) else ""
    return {
        "user": user,
        "full_name": frappe.db.get_value("User", user, "full_name") or user,
        "configured": configured,
        "has_signature": bool(content),
        "signature_preview": "data:image/png;base64," + base64.b64encode(content).decode("ascii") if content else "",
        "updated_at": str(updated_at) if updated_at else "",
        "signature_kind": "Ảnh chữ ký tay (không phải chữ ký số)",
        "has_initials": bool(initial_bytes),
        "initials_preview": "data:image/png;base64," + base64.b64encode(initial_bytes).decode("ascii") if initial_bytes else "",
        "date_format": date_fmt or DATE_FORMATS[0],
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
            # Paper never reaches the PDF: photos lose their background here even when the
            # phone editor was skipped; already transparent drawings are only trimmed.
            from lotus_farm.signature_image import remove_background
            try:
                output_image = remove_background(output_image)
            except ValueError as exc:
                frappe.throw(str(exc))
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


@frappe.whitelist(methods=["POST"])
def save_my_initials_image(image_data):
    user = _user()
    if not frappe.get_meta("User").has_field(INITIAL_FIELD):
        frappe.throw("Hệ thống chưa cập nhật ký nháy. Cần chạy migrate.")
    content = _normalize_image(image_data)
    previous = _current_file(user, INITIAL_FIELD)
    saved = save_file("lotus-ky-nhay.png", content, "User", user,
                      df=INITIAL_FIELD, is_private=1)
    frappe.db.set_value("User", user, {
        INITIAL_FIELD: saved.file_url,
        INITIAL_UPDATED_FIELD: frappe.utils.now_datetime(),
    })
    if previous and previous.name != saved.name:
        frappe.delete_doc("File", previous.name, ignore_permissions=True)
    return my_signature_profile()


@frappe.whitelist(methods=["POST"])
def remove_my_initials_image():
    user = _user()
    _configured()
    previous = _current_file(user, INITIAL_FIELD)
    frappe.db.set_value("User", user, {
        INITIAL_FIELD: "", INITIAL_UPDATED_FIELD: frappe.utils.now_datetime(),
    })
    if previous:
        frappe.delete_doc("File", previous.name, ignore_permissions=True)
    return my_signature_profile()


@frappe.whitelist(methods=["POST"])
def save_my_signature_date_format(date_format):
    user = _user()
    if date_format not in DATE_FORMATS:
        frappe.throw("Định dạng ngày không hợp lệ.")
    if not frappe.get_meta("User").has_field(DATE_FORMAT_FIELD):
        frappe.throw("Hệ thống chưa cập nhật định dạng ngày. Cần chạy migrate.")
    frappe.db.set_value("User", user, DATE_FORMAT_FIELD, date_format)
    return my_signature_profile()


def _display_date(timestamp, user):
    from frappe.utils import get_datetime
    dt = get_datetime(timestamp)
    choice = frappe.db.get_value("User", user, DATE_FORMAT_FIELD) or DATE_FORMATS[0]
    if choice == "DD-MM-YYYY":
        return dt.strftime("%d-%m-%Y")
    if choice == "LONG_VI":
        return "Ngày %02d tháng %02d năm %04d" % (dt.day, dt.month, dt.year)
    return dt.strftime("%d/%m/%Y")


def _event(doc, action, actor, when, signature_type="", pdf_hash="", revision="", details="", extra=None):
    # One audit record per actual action; do not let client supply actor or clock.
    # extra: typed audit columns (ip, user_agent, roles, designation, round, step_key, content_hash, image_sha256).
    return frappe.get_doc({
        "doctype": "Lotus Signature Event",
        "document_type": doc.doctype, "document_name": doc.name,
        "action": action, "actor": actor, "signed_at": when,
        "signature_type": signature_type,
        "document_version": str(doc.modified),
        "pdf_sha256": pdf_hash,
        "signature_revision": str(revision or ""),
        "details": str(details or "")[:800],
        **(extra or {}),
    }).insert(ignore_permissions=True).name


def _qr_png(url):
    import qrcode
    out = BytesIO()
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=5, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    qr.make_image(fill_color="black", back_color="white").save(out, format="PNG")
    return out.getvalue()


def _verification_url(token):
    from frappe.utils import get_url
    return get_url("/verify/lotus?token=" + token)


@frappe.whitelist(allow_guest=True, methods=["GET"])
def verify_document(token):
    # Public endpoint deliberately returns only a minimal summary. Never a PDF,
    # name of the signer or private attachment. Token is unpredictable (256-bit).
    value = str(token or "")
    if len(value) < 30 or len(value) > 256:
        return {"valid": False}
    token_hash = hashlib.sha256(value.encode("ascii", "ignore")).hexdigest()
    if not frappe.get_meta("Purchase Order").has_field("lotus_signature_verify_hash"):
        return {"valid": False}
    name = frappe.db.get_value("Purchase Order",
                               {"lotus_signature_verify_hash": token_hash}, "name")
    if not name:
        return {"valid": False}
    doc = frappe.get_doc("Purchase Order", name)
    expected = str(doc.get("lotus_signature_pdf_sha256") or "")
    attachment = doc.get("lotus_signed_purchase_pdf")
    matched = frappe.get_all("File", filters={
        "attached_to_doctype": "Purchase Order", "attached_to_name": doc.name,
        "attached_to_field": "lotus_signed_purchase_pdf",
        "file_url": attachment, "is_private": 1,
    }, pluck="name", limit_page_length=1) if attachment else []
    actual = ""
    if matched:
        actual = hashlib.sha256(frappe.get_doc("File", matched[0]).get_content(encodings=[])).hexdigest()
    valid = bool(doc.docstatus == 1 and len(expected) == 64 and hmac.compare_digest(actual, expected))
    return {
        "valid": valid,
        "document_type": "Đơn mua hàng",
        "document_no": doc.name,
        "status": "Đã duyệt" if doc.docstatus == 1 else "Không còn hiệu lực",
        "approved_at": str(doc.get("lotus_approved_at") or ""),
        "pdf_sha256": str(doc.get("lotus_signature_pdf_sha256") or ""),
        "notice": "Đối chiếu với tệp PDF gốc lưu trên Lotus. QR không phải chữ ký số có chứng thư.",
    }


# QR signing on another device, the order initials button and the approval-only PDF were removed in spec 003:
# QR codes only verify, ký nháy is printed from the checking step, and lotus_farm.signed_copy keeps every signed PDF.


@frappe.whitelist()
def download_purchase_pdf(name):
    """The signed copy once the director signed (spec 003); orders approved before keep their archived PDF;
    otherwise the live print. Print permission, or being named in the signing round, is required."""
    user = _user()
    doc = frappe.get_doc("Purchase Order", name)
    from lotus_farm import signed_copy, signing
    if frappe.has_permission("Purchase Order", "read", doc=doc):
        doc.check_permission("print")
    elif not signing.can_view(doc=doc):
        frappe.throw("Không có quyền xem đơn mua này.", frappe.PermissionError)
    attachment = doc.get("lotus_signed_purchase_pdf") if frappe.get_meta("Purchase Order").has_field("lotus_signed_purchase_pdf") else None
    copy = signed_copy.current(doc)
    content = None
    if copy:
        content = signed_copy.pdf_bytes(copy)
    elif attachment:
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
        from lotus_farm import print_kit
        from lotus_farm.www import lotus_purchase_order_print as printer
        content = print_kit.pdf(str(printer.html(doc)))
    from re import sub
    frappe.local.response.filename = sub(r"[^A-Za-z0-9._-]+", "_", doc.name)[:100] + ".pdf"
    frappe.local.response.filecontent = content
    frappe.local.response.type = "pdf"
    frappe.local.response.display_content_as = "attachment"