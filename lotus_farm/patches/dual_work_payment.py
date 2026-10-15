import frappe


def execute():
    frappe.reload_doc('lotus_farm', 'doctype', 'work_type')
    # Preserve an earlier single-mode setting when adding independent switches.
    for row in frappe.get_all('Work Type', fields=['name', 'payment_basis', 'allow_piecework', 'allow_daywork']):
        if not row.allow_piecework and not row.allow_daywork and row.payment_basis:
            frappe.db.set_value('Work Type', row.name, {
                'allow_piecework': int(row.payment_basis in ('Piece', 'Both')),
                'allow_daywork': int(row.payment_basis in ('Daywork', 'Both')),
            }, update_modified=False)
