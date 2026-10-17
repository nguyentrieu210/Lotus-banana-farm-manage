"""Independent phone work app: same authenticated Frappe session as ERP."""
import json
from pathlib import Path
from urllib.parse import quote
import frappe

no_cache = 1

def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=" + quote("/work", safe="/")
        raise frappe.Redirect
    manifest = Path(frappe.get_app_path("lotus_farm", "public", "frontend", ".vite", "manifest.json"))
    if not manifest.exists():
        frappe.throw("Cần build giao diện Công việc ngoài Vườn.")
    entries = json.loads(manifest.read_text(encoding="utf-8"))
    key = "work-mobile.html"
    styles, seen = [], set()
    def collect(entry):
        if entry in seen:
            return
        seen.add(entry)
        chunk = entries[entry]
        for dep in chunk.get("imports", []):
            collect(dep)
        for css in chunk.get("css", []):
            if css not in styles:
                styles.append(css)
    collect(key)
    context.script = "/assets/lotus_farm/frontend/" + entries[key]["file"]
    context.styles = ["/assets/lotus_farm/frontend/" + file for file in styles]
    context.no_cache = 1
