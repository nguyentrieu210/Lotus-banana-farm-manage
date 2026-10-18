"""Shared, per-user PWA inbox and standards-based Web Push for Lotus mobile apps.

Push subscriptions are never client-readable. All writes bind to the logged-in user.
No ERP or private attachments are stored in the service-worker cache/payload.
"""
import base64
import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

import frappe
from frappe.utils import now_datetime

APPS = {"warehouse": "/warehouse", "buying": "/buying", "work": "/work", "hr": "/hr-mobile"}
DEVICE = "Lotus Push Device"
ALERT = "Lotus Mobile Alert"
ALLOWED_PUSH_HOSTS = {
    "fcm.googleapis.com", "fcm-xm.googleapis.com",
    "updates.push.services.mozilla.com", "push.services.mozilla.com",
    "web.push.apple.com",
}


def _user():
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw("Cần đăng nhập để nhận thông báo.", frappe.AuthenticationError)
    return user


def _app(value):
    if value not in APPS:
        frappe.throw("Ứng dụng không hợp lệ.")
    if value == "hr":
        from lotus_farm.hr_workspace import _hr_access
        _hr_access()
    return value


def _push_host(url):
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower()
        return (
            parsed.scheme == "https" and parsed.port in (None, 443)
            and not parsed.username and not parsed.password and not parsed.fragment
            and len(url) <= 2048
            and (host in ALLOWED_PUSH_HOSTS
                 or host.endswith(".push.services.mozilla.com")
                 or host.endswith(".push.apple.com")
                 or host.endswith(".notify.windows.com"))
        )
    except ValueError:
        return False


def _endpoint_hash(endpoint):
    return hashlib.sha256(endpoint.encode("utf-8")).hexdigest()


def _key(value):
    return isinstance(value, str) and 8 <= len(value) <= 200 and re.fullmatch(r"[A-Za-z0-9_-]+={0,2}", value)


def _vapid_path():
    return Path(frappe.get_site_path("private", "files", "lotus-push-vapid.pem"))


def _vapid_public():
    path = _vapid_path()
    if not path.is_file():
        return None
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    private = serialization.load_pem_private_key(path.read_bytes(), password=None)
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    return base64.urlsafe_b64encode(public).rstrip(b"=").decode("ascii")


def setup_vapid():
    """Admin deployment command, not an HTTP method; preserves existing key on redeploy."""
    path = _vapid_path()
    if not path.exists():
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        path.parent.mkdir(parents=True, exist_ok=True)
        private = ec.generate_private_key(ec.SECP256R1())
        pem = private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as out:
            out.write(pem)
    return {"configured": bool(_vapid_public())}


@frappe.whitelist(methods=["GET"])
def config(app):
    _user()
    app = _app(app)
    return {"app": app, "enabled": bool(_vapid_public()), "public_key": _vapid_public()}


@frappe.whitelist(methods=["POST"])
def subscribe(app, subscription):
    user = _user()
    _app(app)
    if not _vapid_public():
        frappe.throw("Máy chủ chưa bật thông báo đẩy.")
    if isinstance(subscription, str):
        subscription = frappe.parse_json(subscription)
    if not isinstance(subscription, dict):
        frappe.throw("Thiết bị không hợp lệ.")
    endpoint = subscription.get("endpoint", "")
    keys = subscription.get("keys") or {}
    p256dh, auth = keys.get("p256dh"), keys.get("auth")
    if not _push_host(endpoint) or not _key(p256dh) or not _key(auth):
        frappe.throw("Thông tin đăng ký thiết bị không hợp lệ.")
    digest = _endpoint_hash(endpoint)
    existing = frappe.db.get_value(DEVICE, {"endpoint_hash": digest}, "name")
    data = dict(user=user, app=app, endpoint_hash=digest, endpoint=endpoint,
                p256dh=p256dh, auth=auth, enabled=1, last_seen=now_datetime())
    if existing:
        frappe.db.set_value(DEVICE, existing, data, update_modified=False)
    else:
        frappe.get_doc(dict(doctype=DEVICE, **data)).insert(ignore_permissions=True)
    return {"subscribed": True}


@frappe.whitelist(methods=["POST"])
def unsubscribe(app, endpoint):
    user = _user()
    app = _app(app)
    if not _push_host(endpoint):
        frappe.throw("Thiết bị không hợp lệ.")
    filters = {"user": user, "app": app}
    filters["endpoint_hash"] = _endpoint_hash(endpoint)
    names = frappe.get_all(DEVICE, filters=filters, pluck="name", limit_page_length=50)
    for name in names:
        frappe.delete_doc(DEVICE, name, ignore_permissions=True, force=True)
    return {"subscribed": False}


@frappe.whitelist(methods=["GET"])
def inbox(app):
    user = _user()
    app = _app(app)
    rows = frappe.get_all(ALERT, filters={"user": user, "app": app},
                          fields=["name", "title", "body", "url", "is_read", "creation"],
                          order_by="creation desc", limit_page_length=50)
    unread = frappe.db.count(ALERT, filters={"user": user, "app": app, "is_read": 0})
    active = bool(frappe.db.exists(DEVICE, {"user": user, "app": app, "enabled": 1}))
    return {"rows": rows, "unread": unread, "subscribed": active}


@frappe.whitelist(methods=["POST"])
def mark_read(app, name):
    user = _user()
    app = _app(app)
    if not frappe.db.exists(ALERT, {"name": name, "user": user, "app": app}):
        frappe.throw("Không tìm thấy thông báo.", frappe.PermissionError)
    frappe.db.set_value(ALERT, name, "is_read", 1, update_modified=False)
    return {"read": True}


def _add_alert(user, app, title, body, url, doctype="", docname="", key=""):
    if not user or user == "Guest" or app not in APPS:
        return None
    if not url.startswith(APPS[app]) or url.startswith("//") or "\n" in url:
        raise ValueError("Push target must remain in the matching PWA")
    digest = hashlib.sha256(f"{user}|{app}|{key or title + docname}".encode()).hexdigest()
    if frappe.db.exists(ALERT, {"event_key": digest}):
        return None
    return frappe.get_doc(dict(doctype=ALERT, user=user, app=app, event_key=digest,
                               title=title[:130], body=body[:500], url=url[:255],
                               document_type=doctype, document_name=docname)).insert(ignore_permissions=True).name


def _send_alert(alert_name):
    alert = frappe.get_doc(ALERT, alert_name)
    path = _vapid_path()
    if not path.exists():
        return
    from pywebpush import webpush, WebPushException
    payload = json.dumps({
        "title": alert.title, "body": alert.body, "url": alert.url,
        "tag": f"lotus-{alert.app}-{alert.name}",
    }, ensure_ascii=False)
    devices = frappe.get_all(DEVICE, filters={"user": alert.user, "app": alert.app, "enabled": 1},
                             fields=["name", "endpoint", "p256dh", "auth"], limit_page_length=25)
    contact = frappe.conf.get("lotus_push_contact") or "mailto:admin@lotus.local"
    if not contact.startswith(("mailto:", "https:")):
        contact = "mailto:" + contact
    success = False
    for device in devices:
        if not _push_host(device.endpoint):
            continue
        try:
            webpush(
                subscription_info={"endpoint": device.endpoint,
                                   "keys": {"p256dh": device.p256dh, "auth": device.auth}},
                data=payload, vapid_private_key=str(path),
                vapid_claims={"sub": contact}, ttl=3600,
            )
            success = True
        except WebPushException as error:
            status = getattr(getattr(error, "response", None), "status_code", None)
            if status in (404, 410):
                frappe.delete_doc(DEVICE, device.name, ignore_permissions=True, force=True)
            else:
                frappe.log_error(f"Push failed, HTTP {status or 'unknown'}", "Lotus Web Push")
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Lotus Web Push")
    if success:
        frappe.db.set_value(ALERT, alert.name, "pushed", 1, update_modified=False)


@frappe.whitelist(methods=["POST"])
def test_push(app):
    user = _user()
    app = _app(app)
    if not frappe.db.exists(DEVICE, {"user": user, "app": app, "enabled": 1}):
        frappe.throw("Hãy bật thông báo trên điện thoại này trước.")
    name = _add_alert(user, app, "Lotus đã kết nối", "Thông báo thử từ " + app,
                      APPS[app], key="test-" + frappe.generate_hash(length=20))
    frappe.enqueue("lotus_farm.push_notifications._send_alert", queue="short",
                   enqueue_after_commit=True, alert_name=name)
    return {"queued": True}


def _visible_to(user, doc):
    if not user or user in ("Guest", "Administrator") and user == "Guest":
        return False
    if not frappe.db.get_value("User", user, "enabled"):
        return False
    try:
        return bool(doc.has_permission("read", user=user))
    except Exception:
        return False


def _recipients(doc, event):
    users = set()
    if doc.doctype == "Purchase Order":
        if event == "pending":
            users.update(frappe.get_all("Has Role", filters={"role": "Lotus Purchase Approver"},
                                        pluck="parent", limit_page_length=1000))
            users.add("Administrator")
            users.discard(doc.owner)
            users.discard(doc.get("lotus_requested_by"))
        elif event in ("approved", "rejected"):
            users.update((doc.owner, doc.get("lotus_requested_by")))
    elif doc.doctype == "Material Request":
        users.update(frappe.get_all("Has Role", filters={"role": "Lotus Purchase Approver"},
                                    pluck="parent", limit_page_length=1000))
    elif doc.doctype == "Purchase Receipt":
        for item in doc.items:
            if item.purchase_order:
                users.add(frappe.db.get_value("Purchase Order", item.purchase_order, "owner"))
    elif doc.doctype == "Stock Entry":
        users.update(frappe.get_all("Has Role", filters={"role": "Lotus Stock Reviewer"},
                                    pluck="parent", limit_page_length=1000))
        users.discard(doc.owner)
    elif doc.doctype == "Daily Work Plan":
        users.update(frappe.get_all("ToDo", filters={"reference_type": doc.doctype,
                          "reference_name": doc.name, "status": "Open"},
                          pluck="allocated_to", limit_page_length=300))
    elif doc.doctype == "Daily Work Result":
        if doc.get("work_plan"):
            users.add(frappe.db.get_value("Daily Work Plan", doc.work_plan, "owner"))
    if doc.doctype == "Employee":
        users.update(frappe.get_all(
            "Has Role", filters={"role": "HR Manager"},
            pluck="parent", limit_page_length=1000))
        users.add("Administrator")
    return sorted(user for user in users if user and _visible_to(user, doc))


def _event_content(doc, event):
    mapping = {
        ("Purchase Order", "pending"): ("buying", "Có đơn mua cần duyệt", "Đơn " + doc.name, "/buying?doc=" + doc.name),
        ("Purchase Order", "approved"): ("buying", "Đơn mua đã được duyệt", "Đơn " + doc.name, "/buying?doc=" + doc.name),
        ("Purchase Order", "rejected"): ("buying", "Đơn mua bị từ chối", "Đơn " + doc.name, "/buying?doc=" + doc.name),
        ("Material Request", "submitted"): ("buying", "Có đề nghị mua mới", "Đề nghị " + doc.name, "/buying?tab=home"),
        ("Purchase Receipt", "submitted"): ("warehouse", "Đã nhận hàng theo đơn", "Phiếu " + doc.name, "/warehouse?doc=" + doc.name + "&doctype=Purchase%20Receipt"),
        ("Stock Entry", "submitted"): ("warehouse", "Có phiếu kho mới", "Phiếu " + doc.name, "/warehouse?doc=" + doc.name + "&doctype=Stock%20Entry"),
        ("Daily Work Plan", "submitted"): ("work", "Có công việc được giao", "Kế hoạch " + doc.name, "/work?tab=tasks"),
        ("Daily Work Result", "submitted"): ("work", "Đã báo cáo công việc", "Báo cáo " + doc.name, "/work?tab=history"),
        ("Employee", "pending"): ("hr", "Có hồ sơ chờ tiếp nhận", "Mã nhân viên " + doc.name, "/hr-mobile?tab=onboarding"),
        ("Employee", "ready"): ("hr", "Đã duyệt tiếp nhận", "Mã nhân viên " + doc.name, "/hr-mobile?tab=employees"),
    }
    return mapping.get((doc.doctype, event))


def dispatch_document(doctype, name, event):
    doc = frappe.get_doc(doctype, name)
    content = _event_content(doc, event)
    if not content:
        return
    if doc.doctype == "Purchase Order" and event == "pending" and doc.get("lotus_approval_status") != "Chờ duyệt":
        return
    app, title, body, url = content
    for user in _recipients(doc, event):
        alert_name = _add_alert(user, app, title, body, url, doctype, name,
                                key=f"{doctype}:{name}:{event}:{doc.modified}")
        if alert_name:
            _send_alert(alert_name)


def document_hook(doc, method=None):
    if doc.doctype == "Purchase Order" and method == "on_update":
        previous = doc.get_doc_before_save()
        old = previous.get("lotus_approval_status") if previous else None
        new = doc.get("lotus_approval_status")
        if new == "Chờ duyệt" and old != new:
            event = "pending"
        elif new == "Từ chối" and old != new:
            event = "rejected"
        else:
            return
    elif doc.doctype == "Purchase Order" and method == "on_submit":
        event = "approved"
    elif doc.doctype == "Employee" and method == "on_update":
        old = doc.get_doc_before_save()
        before = old.get("lotus_onboarding_state") if old else None
        after = doc.get("lotus_onboarding_state")
        if not old and after == "Pending":
            event = "pending"
        elif old and before != "Ready" and after == "Ready":
            event = "ready"
        else:
            return
    elif method == "on_submit":
        event = "submitted"
    else:
        return
    frappe.enqueue("lotus_farm.push_notifications.dispatch_document",
                   queue="short", enqueue_after_commit=True,
                   doctype=doc.doctype, name=doc.name, event=event)

def allow_hr_notifications():
    """One-time idempotent metadata update; preserves all existing push devices and alerts."""
    updated = []
    for doctype in (DEVICE, ALERT):
        row = frappe.db.get_value(
            "DocField", {"parent": doctype, "fieldname": "app"},
            ["name", "options"], as_dict=True)
        if not row:
            frappe.throw("Thiếu trường ứng dụng của " + doctype)
        options = [x.strip() for x in (row.options or "").splitlines() if x.strip()]
        if "hr" not in options:
            options.append("hr")
            frappe.db.set_value("DocField", row.name, "options", "\n".join(options))
            updated.append(doctype)
        frappe.clear_cache(doctype=doctype)
    return {"updated": updated, "hr_enabled": True}
