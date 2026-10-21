"""Dự thu theo nhật ký chặt mẹ lần 2 on the real site: upload the Lotus forecast workbook (preview, then
commit), the board reproduces the workbook totals, a second upload adds nothing, a Sales Planner reads but
cannot import, a Team Leader does not see it, a parameter change creates the next version, undo removes the rows. Rolls back.

The workbook path is $LOTUS_FORECAST_XLSX (default /tmp/xl/f.xlsx)."""
import base64
import json
import os
import uuid

import frappe

frappe.init(site='frontend', sites_path='/home/frappe/frappe-bench/sites')
frappe.connect()
frappe.set_user('Administrator')

from lotus_farm import cut_forecast as cf  # noqa: E402

FARM = 'LOTUS-222'
path = os.environ.get('LOTUS_FORECAST_XLSX', '/tmp/xl/f.xlsx')
content = base64.b64encode(open(path, 'rb').read()).decode()
tag = uuid.uuid4().hex[:6]
report = {}


def user(key, roles):
    email = 'lotus-cutfc-%s-%s@example.com' % (key, tag)
    doc = frappe.get_doc(dict(doctype='User', email=email, first_name='Cut ' + key, send_welcome_email=0, enabled=1,
                              roles=[dict(role=r) for r in roles])).insert(ignore_permissions=True)
    frappe.get_doc(dict(doctype='User Permission', user=doc.name, allow='Farm', for_value=FARM, apply_to_all_doctypes=1)).insert(ignore_permissions=True)
    return doc.name


def as_user(name, fn, *args, **kwargs):
    frappe.set_user(name)
    try:
        return fn(*args, **kwargs)
    finally:
        frappe.set_user('Administrator')


try:
    before = frappe.db.count(cf.ENTRY, {'farm': FARM})
    manager = user('manager', ['Lotus Farm Manager'])
    planner = user('planner', ['Lotus Sales Planner'])
    leader = user('leader', ['Lotus Team Leader'])

    preview = as_user(manager, cf.preview_import, FARM, content, 'du-thu.xlsx')
    assert preview['errors'] == 0 and preview['conflict'] == 0, (preview['errors'], preview['conflict'])
    assert preview['new'] + preview['same'] == 358, (preview['new'], preview['same'])
    assert preview['file_totals']['tonnes'] == 7375.0, preview['file_totals']
    done = as_user(manager, cf.commit_import, FARM, preview['token'], 1)
    assert done['saved'] == preview['new'], done

    board = as_user(manager, cf.board, FARM)
    t = board['totals']
    assert (t['trees'], t['budcut'], t['harvest'], t['pack'], t['tonnes']) == (430871, 387859, 376247, 368750, 7375.0), t
    months = {m['month']: m['tonnes'] for m in board['months']}
    assert (months['2027-02'], months['2027-05']) == (513.72, 1852.64), months
    assert board['profile'] and board['profile']['source'] in ('Excel', 'Web'), board['profile']
    batch = frappe.get_doc(cf.IMPORT, done['batch'])
    assert batch.source_file and batch.sha256 and batch.new_rows == done['saved'], batch.as_dict()

    again = as_user(manager, cf.preview_import, FARM, content, 'du-thu.xlsx')
    assert again['new'] == 0 and again['same'] == 358 and not again['param_changes'], (again['new'], again['same'], again['param_changes'])

    try:
        as_user(leader, cf.board, FARM)
        raise AssertionError('a team leader does not see forecasts')
    except frappe.PermissionError:
        pass
    seen = as_user(planner, cf.board, FARM, 'C')
    assert seen['can_edit'] is False and seen['totals']['trees'] == 98701, seen['totals']
    for fn, args in ((cf.preview_import, (FARM, content)), (cf.save_profile, (FARM, {'days_to_first_shoot': 180}))):
        try:
            as_user(planner, fn, *args)
            raise AssertionError('a sales planner cannot ' + fn.__name__)
        except frappe.PermissionError:
            pass

    version = board['profile']['version']
    try:
        as_user(manager, cf.save_profile, FARM, {'wave_4_share': 0.1})
        raise AssertionError('shares must add up to 100%')
    except frappe.ValidationError as exc:
        assert '100%' in str(exc), exc
    saved = as_user(manager, cf.save_profile, FARM, json.dumps({'days_to_first_shoot': 180}), 'Thử 180 ngày')
    assert saved['version'] == version + 1, saved
    later = as_user(manager, cf.board, FARM)
    assert later['totals']['pack'] == 368750 and later['totals']['first_harvest'] > t['first_harvest'], later['totals']
    old = frappe.get_doc(cf.PROFILE, board['profile']['name'])
    old.days_to_first_shoot = 90
    try:
        old.save(ignore_permissions=True)
        raise AssertionError('an approved profile is frozen')
    except frappe.ValidationError:
        pass

    undone = as_user(manager, cf.undo_import, FARM, done['batch'])
    assert undone['removed'] == done['saved'] and frappe.db.count(cf.ENTRY, {'farm': FARM}) == before, undone
    report.update(new_rows=done['saved'], already=preview['same'], trees=t['trees'], tonnes=t['tonnes'], peak=t['peak_month'],
                  first_harvest=t['first_harvest'], profile_versions=[version, saved['version']], rollback=True)
finally:
    frappe.set_user('Administrator')
    frappe.db.rollback()
print(json.dumps(report, ensure_ascii=False, default=str))
