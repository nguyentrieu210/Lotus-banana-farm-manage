"""Independent authenticated purchasing PWA page.

Keep the installed app launch inside its /buying scope even if login expires.
"""
import json
from pathlib import Path
import frappe

no_cache = 1


def get_context(context):
    context.guest = frappe.session.user == "Guest"
    context.no_cache = 1
    context.styles = []
    context.script = ""

    # Redirecting an installed PWA to /login (outside /buying scope) can
    # strand it on Android. The guest shell below gives a clear login action.
    if context.guest:
        return

    from lotus_farm.purchasing import access
    access()
    path = Path(frappe.get_app_path("lotus_farm", "public", "frontend", ".vite", "manifest.json"))
    if not path.exists():
        frappe.throw("Cần build giao diện Mua hàng Lotus.")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    css = []
    seen = set()

    def add(key):
        if key in seen:
            return
        seen.add(key)
        entry = manifest[key]
        for dependency in entry.get("imports", []):
            add(dependency)
        for file in entry.get("css", []):
            if file not in css:
                css.append(file)

    add("buying.html")
    context.script = "/assets/lotus_farm/frontend/" + manifest["buying.html"]["file"]
    context.styles = ["/assets/lotus_farm/frontend/" + file for file in css]
