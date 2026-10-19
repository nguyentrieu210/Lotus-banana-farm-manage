"""Lotus login shell, with Frappe's original authentication and recovery flows."""
import json
from pathlib import Path
import frappe
from frappe.www.login import get_context as native_login_context

no_cache = True


def get_context(context):
    native_login_context(context)
    manifest = json.loads(Path(frappe.get_app_path('lotus_farm', 'public', 'frontend',
                                                  '.vite', 'manifest.json')).read_text(encoding='utf8'))
    context.lotus_login_css = manifest['login.html'].get('css', [])
    context.logo = '/assets/lotus_farm/images/lotus-agritech-header-v2.png'
    context.title = 'Đăng nhập · Lotus Agritech'
    context.no_header = True
    context.no_footer = True
    context.show_footer_on_login = False
