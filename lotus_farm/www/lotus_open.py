"""/lotus/mo?dt=&n= : the one link put in signing e-mails (spec 003, FR-004).

On a phone (narrow screen or an installed Lotus app) it opens the document's signing sheet in the phone app;
on a computer it opens the desktop screen. Guests log in first and come back here. Only people who may see
the document (signing.can_view) get its links.
"""
from urllib.parse import quote, urlencode

import frappe

no_cache = 1


def get_context(context):
    doctype, name = str(frappe.form_dict.get('dt') or ''), str(frappe.form_dict.get('n') or '')
    if frappe.session.user == 'Guest':
        back = '/lotus/mo?' + urlencode(dict(dt=doctype, n=name))
        frappe.local.flags.redirect_location = '/login?redirect-to=' + quote(back, safe='/')
        raise frappe.Redirect
    if not doctype or not name or not frappe.db.exists(doctype, name):
        frappe.throw('Không tìm thấy chứng từ.', frappe.DoesNotExistError)
    from lotus_farm.signing import open_targets
    targets = open_targets(doctype, name)
    # On a computer the signing sheet (with the print and the actions) is the landing page of a signing e-mail.
    context.desktop_url, context.mobile_url = targets['sign_url'], targets['mobile_url']
    context.document_name = name
    context.no_cache = 1
    context.title = 'Mở chứng từ ' + name
