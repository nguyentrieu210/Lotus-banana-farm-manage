"""Remove the paper background from signature / initials images saved before background removal worked.

Only the user's current profile images are rewritten (new private file, profile field repointed).
Images already embedded in archived PDFs and signature events are left untouched.
"""
from io import BytesIO

import frappe


def execute():
    from PIL import Image
    from frappe.utils.file_manager import save_file
    from lotus_farm.digital_signature import IMAGE_FIELD, INITIAL_FIELD, _current_file
    from lotus_farm.signature_image import already_transparent, remove_background
    meta = frappe.get_meta('User')
    for field, name in ((IMAGE_FIELD, 'lotus-chu-ky.png'), (INITIAL_FIELD, 'lotus-ky-nhay.png')):
        if not meta.has_field(field):
            continue
        for user in frappe.get_all('User', filters={field: ['is', 'set']}, pluck='name'):
            current = _current_file(user, field)
            if not current:
                continue
            try:
                with Image.open(BytesIO(current.get_content(encodings=[]))) as image:
                    image = image.convert('RGBA')
                    if already_transparent(image):
                        continue
                    cleaned = remove_background(image)
            except (OSError, ValueError):
                continue  # unreadable or no strokes: leave it for the user to replace
            out = BytesIO()
            cleaned.save(out, format='PNG', optimize=True)
            saved = save_file(name, out.getvalue(), 'User', user, df=field, is_private=1)
            frappe.db.set_value('User', user, field, saved.file_url, update_modified=False)
