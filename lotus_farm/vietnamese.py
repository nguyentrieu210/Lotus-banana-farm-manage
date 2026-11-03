"""Import the Vietnamese language pack and set site/user language preferences.

Run using bench execute, with dry_run=False only after the site backup succeeds.
Uses the native Translation doctype; core gettext catalogs are compiled separately.
No business records, identifiers or stored Select values are changed.
"""

import csv
import json
import os
import re
from pathlib import Path

import frappe
from frappe.core.doctype.translation.translation import clear_user_translation_cache
from frappe.utils import sanitize_html


def _rows():
    path = Path(__file__).parent / "translations" / "vi.csv"
    result = {}
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.reader(stream):
            if not row:
                continue
            if len(row) not in (2, 3):
                raise ValueError("Invalid Vietnamese translation CSV row")
            source, target = (value.replace("\\n", "\n") for value in row[:2])
            context = row[2] if len(row) == 3 else ""
            if not source or not target:
                raise ValueError("Empty Vietnamese translation")
            result[(source, context)] = target
    return result


def _audit_path(audit_id):
    if not audit_id or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", audit_id):
        raise ValueError("A unique audit_id is required")
    return Path(frappe.get_site_path("private", "backups", f"vietnamese-{audit_id}.json"))


def _write_audit(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, path)


def install_vietnamese(dry_run=True, audit_id=None):
    if not frappe.db.exists("Language", "vi"):
        raise ValueError("Vietnamese is unavailable on this site")
    existing = {}
    for row in frappe.get_all("Translation", filters={"language": "vi"}, fields=[
        "name", "source_text", "translated_text", "context", "modified", "modified_by"
    ]):
        existing.setdefault((row.source_text, row.context or ""), []).append(dict(row))
    plan, skipped = [], 0
    for (source, context), target in _rows().items():
        # Native Translation validates HTML. Keep code-bearing templates whose
        # markup would be sanitized in the compiled PO catalog/frontend pack.
        if sanitize_html(target) != target:
            skipped += 1
            continue
        matches = existing.get((source, context), [])
        if not matches or any(row["translated_text"] != target for row in matches):
            plan.append((source, context, target, matches))
    users = [dict(row) for row in frappe.get_all("User", filters={"enabled": 1}, fields=["name", "language"])]
    changed_users = [row for row in users if row["language"] != "vi"]
    old_language = frappe.db.get_single_value("System Settings", "language")
    result = {"site": frappe.local.site, "language": "vi", "translation_keys_to_update": len(plan),
              "user_preferences_to_update": len(changed_users), "templates_kept_in_catalogs": skipped}
    if dry_run:
        return result
    path = _audit_path(audit_id)
    if path.exists():
        raise ValueError("This audit_id already exists; use a new deployment attempt ID")
    audit = {"site": frappe.local.site, "state": "prepared", "language": old_language,
             "users": changed_users, "before": [row for _, _, _, rows in plan for row in rows], "created": []}
    _write_audit(path, audit)
    try:
        for source, context, target, matches in plan:
            if matches:
                for previous in matches:
                    doc = frappe.get_doc("Translation", previous["name"])
                    doc.translated_text = target
                    doc.save(ignore_permissions=True)
            else:
                doc = frappe.get_doc({"doctype": "Translation", "language": "vi", "source_text": source,
                                      "translated_text": target, "context": context or None})
                doc.insert(ignore_permissions=True)
                audit["created"].append(doc.name)
            if doc.translated_text != target:
                raise ValueError("Translation changed during native import validation")
        if old_language != "vi":
            settings = frappe.get_single("System Settings")
            settings.language = "vi"
            settings.save(ignore_permissions=True)
        for user in changed_users:
            frappe.db.set_value("User", user["name"], "language", "vi", update_modified=False)
        audit["state"] = "applied"
        _write_audit(path, audit)
        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        audit["state"] = "rolled_back"
        _write_audit(path, audit)
        raise
    clear_user_translation_cache("vi")
    frappe.clear_cache()
    for user in changed_users:
        frappe.clear_cache(user=user["name"])
    result["audit_file"] = str(path)
    return result


def rollback_vietnamese(audit_id):
    path = _audit_path(audit_id)
    audit = json.loads(path.read_text(encoding="utf-8"))
    if audit["site"] != frappe.local.site or audit["state"] != "applied":
        raise ValueError("No applied localization operation for this site/audit")
    for name in audit["created"]:
        frappe.db.delete("Translation", {"name": name})
    for row in audit["before"]:
        values = {key: value for key, value in row.items() if key != "name"}
        frappe.db.set_value("Translation", row["name"], values, update_modified=False)
    for user in audit["users"]:
        frappe.db.set_value("User", user["name"], "language", user["language"], update_modified=False)
    if frappe.db.get_single_value("System Settings", "language") != audit["language"]:
        frappe.db.set_single_value("System Settings", "language", audit["language"])
    audit["state"] = "rolled_back"
    _write_audit(path, audit)
    frappe.db.commit()
    clear_user_translation_cache("vi")
    frappe.clear_cache()
    for user in audit["users"]:
        frappe.clear_cache(user=user["name"])
    return {"site": frappe.local.site, "state": "rolled_back"}
