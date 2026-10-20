"""Private signature images, role-checked approvals, QR verification and audit.

Image-based internal electronic signatures are not certificate-based PDF signing.
"""
import base64
import binascii
import hashlib
import hmac
import secrets
from datetime import timedelta
from html import escape
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


def _event(doc, action, actor, when, signature_type="", pdf_hash="", revision="", details=""):
    # One audit record per actual action; do not let client supply actor or clock.
    frappe.get_doc({
        "doctype": "Lotus Signature Event",
        "document_type": doc.doctype, "document_name": doc.name,
        "action": action, "actor": actor, "signed_at": when,
        "signature_type": signature_type,
        "document_version": str(doc.modified),
        "pdf_sha256": pdf_hash,
        "signature_revision": str(revision or ""),
        "details": str(details or "")[:800],
    }).insert(ignore_permissions=True)


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


@frappe.whitelist(methods=["POST"])
def initial_purchase_order(name, modified):
    from lotus_farm.purchasing import PENDING, _approver
    from lotus_farm.controls import lock
    actor = _user()
    lock("Purchase Order", name)
    doc = frappe.get_doc("Purchase Order", name)
    doc.check_permission("read")
    if (str(doc.modified) != str(modified) or doc.docstatus != 0
        or doc.get("lotus_approval_status") != PENDING
        or not (_approver() or "Lotus Purchase Reviewer" in frappe.get_roles(actor))):
        frappe.throw("Bạn không có quyền ký nháy hoặc đơn đã thay đổi.", frappe.PermissionError)
    image = _current_file(actor, INITIAL_FIELD)
    if not image:
        frappe.throw("Hãy thiết lập mẫu ký nháy trong mục Tôi trước.")
    bytes_data = image.get_content(encodings=[])
    previous = doc.get("lotus_initials_snapshot")
    snapshot = save_file("lotus-initial-" + doc.name.replace("/", "-") + ".png",
                         bytes_data, "Purchase Order", doc.name,
                         df="lotus_initials_snapshot", is_private=1)
    when = frappe.utils.now_datetime()
    frappe.db.set_value("Purchase Order", doc.name, {
        "lotus_initials_by": actor, "lotus_initials_at": when,
        "lotus_initials_snapshot": snapshot.file_url,
    })
    _event(doc, "INITIAL", actor, when, signature_type="INITIALS",
           revision=frappe.db.get_value("User", actor, INITIAL_UPDATED_FIELD))
    # Keep the private snapshot for audit, including earlier snapshots if reinitialed.
    return {"name": doc.name, "status": "Đã ký nháy", "by": actor, "signed_at": str(when)}


def _assert_signer_qr(token, name, modified):
    if not token:
        return None
    token_hash = hashlib.sha256(str(token).encode("ascii", "ignore")).hexdigest()
    record_name = frappe.db.get_value("Lotus Signing Challenge",
                                      {"token_hash": token_hash}, "name")
    if not record_name:
        frappe.throw("QR xác nhận không hợp lệ.")
    record = frappe.get_doc("Lotus Signing Challenge", record_name)
    if (record.user != frappe.session.user or record.document_name != name
        or record.document_type != "Purchase Order"
        or record.document_version != str(modified)
        or record.used_at or frappe.utils.now_datetime() >= frappe.utils.get_datetime(record.expires_at)):
        frappe.throw("Mã QR đã hết hạn hoặc không thuộc phiên duyệt này.")
    return record


@frappe.whitelist(methods=["POST"])
def create_signing_challenge(name, modified):
    from lotus_farm.purchasing import _po, can_approve
    actor = _user()
    doc = _po(name)
    if str(doc.modified) != str(modified) or not can_approve(doc):
        frappe.throw("Bạn không có quyền duyệt đơn này.", frappe.PermissionError)
    token = secrets.token_urlsafe(32)
    expiry = frappe.utils.now_datetime() + timedelta(seconds=120)
    frappe.get_doc({
        "doctype": "Lotus Signing Challenge",
        "token_hash": hashlib.sha256(token.encode()).hexdigest(),
        "document_type": "Purchase Order",
        "document_name": name, "document_version": str(modified),
        "user": actor, "expires_at": expiry,
    }).insert(ignore_permissions=True)
    from frappe.utils import get_url
    url = get_url("/buying?sign_token=" + token)
    return {"qr_image": "data:image/png;base64,"+base64.b64encode(_qr_png(url)).decode("ascii"),
            "expires_at": str(expiry), "url": url}


@frappe.whitelist()
def signing_challenge_details(token):
    actor = _user()
    token_hash = hashlib.sha256(str(token or "").encode("ascii", "ignore")).hexdigest()
    name = frappe.db.get_value("Lotus Signing Challenge", {"token_hash": token_hash}, "name")
    if not name:
        frappe.throw("Không tìm thấy phiên ký QR.")
    record = frappe.get_doc("Lotus Signing Challenge", name)
    if (record.user != actor or record.used_at or frappe.utils.now_datetime() >= frappe.utils.get_datetime(record.expires_at)):
        frappe.throw("Mã QR không thuộc tài khoản hoặc đã hết hạn.", frappe.PermissionError)
    doc = frappe.get_doc("Purchase Order", record.document_name)
    from lotus_farm.purchasing import can_approve
    if str(doc.modified) != record.document_version or not can_approve(doc):
        frappe.throw("Đơn đã thay đổi hoặc không còn quyền duyệt.")
    return {"name": doc.name, "modified": str(doc.modified),
            "expires_at": str(record.expires_at), "needs_confirmation": True}


def archive_approved_purchase_pdf(doc):
    """Snapshot the approval evidence into a private immutable PDF in the submit transaction."""
    actor = _user()
    signature = signature_image_bytes(actor)
    if not signature:
        _event(doc, "APPROVE", actor, doc.get("lotus_approved_at") or frappe.utils.now_datetime(),
               signature_type="NO_IMAGE", details="Duyệt trên hệ thống, chưa cấu hình ảnh chữ ký")
        return None  # Keep the existing approval workflow for users without an image.
    from frappe.utils.pdf import get_pdf
    required = ("lotus_signed_purchase_pdf", "lotus_signature_verify_hash", "lotus_signature_pdf_sha256")
    if any(not frappe.get_meta("Purchase Order").has_field(field) for field in required):
        frappe.throw("Cần chạy migrate để bật lưu PDF chữ ký và QR xác minh.")
    full_name = frappe.db.get_value("User", actor, "full_name") or actor
    when = doc.get("lotus_approved_at") or frappe.utils.now_datetime()
    date_label = _display_date(when, actor)
    source = frappe.get_print("Purchase Order", doc.name, print_format="Standard", as_pdf=False)
    signature_data = "data:image/png;base64," + base64.b64encode(signature).decode("ascii")
    initials_html = ""
    initial_user = doc.get("lotus_initials_by")
    initial_url = doc.get("lotus_initials_snapshot")
    if initial_user and initial_url:
        matched = frappe.get_all("File", filters={
            "attached_to_doctype": "Purchase Order", "attached_to_name": doc.name,
            "attached_to_field": "lotus_initials_snapshot",
            "file_url": initial_url, "is_private": 1,
        }, pluck="name", limit_page_length=1)
        if not matched:
            frappe.throw("Không tìm thấy ảnh ký nháy đã lưu của người kiểm tra.")
        pixels = frappe.get_doc("File", matched[0]).get_content(encodings=[])
        initial_image = "data:image/png;base64," + base64.b64encode(pixels).decode("ascii")
        initial_name = frappe.db.get_value("User", initial_user, "full_name") or initial_user
        initials_html = (
            '<div style="display:inline-block;width:45%;vertical-align:top;text-align:center">'
            '<strong>NGƯỜI KIỂM TRA (KÝ NHÁY)</strong><br>'
            '<img src="' + initial_image + '" alt="Ký nháy" '
            'style="max-width:125px;max-height:55px"><br>'
            + escape(initial_name) + '<br><small>'
            + escape(str(doc.get("lotus_initials_at") or "")) + '</small></div>'
        )
    verify_token = secrets.token_urlsafe(32)
    qr_image = "data:image/png;base64," + base64.b64encode(
        _qr_png(_verification_url(verify_token))
    ).decode("ascii")
    approval = (
        '<section style="page-break-inside:avoid;margin:22px 0;'
        'border-top:1px solid #ccc;padding:12px 8px;text-align:center;font-size:12px">'
        + initials_html +
        '<div style="display:inline-block;width:50%;vertical-align:top;text-align:center">'
        '<strong>NGƯỜI DUYỆT</strong><br>'
        '<img alt="Chữ ký người duyệt" src="' + signature_data + '" '
        'style="max-width:160px;max-height:85px"><br>'
        + escape(full_name) + '<br><small>Ngày ký: '
        + escape(date_label) + ' · ' + escape(str(when))
        + '</small></div>'
        '<div style="text-align:center;margin-top:12px">'
        '<img src="' + qr_image + '" alt="QR xác minh Lotus" style="width:86px;height:86px">'
        '<br><small>Quét QR để xác minh chứng từ Lotus — Không phải chữ ký số có chứng thư</small>'
        '</div></section>'
    )
    html = source.replace("</body>", approval + "</body>", 1) if "</body>" in source else source + approval
    pdf = get_pdf(html, options={"page-size": "A4", "print-media-type": None})
    if not pdf or not pdf.startswith(b"%PDF"):
        frappe.throw("Không tạo được PDF có chữ ký. Đơn vẫn chưa được duyệt.")
    digest = hashlib.sha256(pdf).hexdigest()
    stamp = save_file("LOTUS-approved-" + doc.name.replace("/", "-") + ".pdf",
                      pdf, "Purchase Order", doc.name,
                      df="lotus_signed_purchase_pdf", is_private=1)
    frappe.db.set_value("Purchase Order", doc.name, {
        "lotus_signed_purchase_pdf": stamp.file_url,
        "lotus_signature_verify_hash": hashlib.sha256(verify_token.encode("ascii")).hexdigest(),
        "lotus_signature_pdf_sha256": digest,
    }, update_modified=False)
    _event(doc, "APPROVE", actor, when, signature_type="IMAGE",
           pdf_hash=digest, revision=frappe.db.get_value("User", actor, DATE_FIELD),
           details="PDF có QR xác minh và thời điểm duyệt máy chủ")
    return stamp.file_url


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