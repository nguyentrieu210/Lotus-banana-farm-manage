"""Separate mobile PWA for team leaders to request materials and costs."""
import json
from pathlib import Path
from urllib.parse import quote

import frappe

no_cache = 1


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=" + quote("/field-proposals", safe="/")
        raise frappe.Redirect
    manifest = Path(frappe.get_app_path("lotus_farm", "public", "frontend", ".vite", "manifest.json"))
    entries = json.loads(manifest.read_text(encoding="utf-8"))
    key = "field-proposal.html"
    css, visited = [], set()

    def add(entry):
        if entry in visited:
            return
        visited.add(entry)
        data = entries[entry]
        for dependency in data.get("imports", []):
            add(dependency)
        for file in data.get("css", []):
            if file not in css:
                css.append(file)

    add(key)
    context.script = "/assets/lotus_farm/frontend/" + entries[key]["file"]
    context.styles = ["/assets/lotus_farm/frontend/" + name for name in css]
    context.no_cache = 1
