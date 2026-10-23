"""Versioned financial plans. These endpoints never post to accounting books."""
import hashlib
import json
from calendar import monthrange
from datetime import date

import frappe
from frappe.utils import now_datetime

from lotus_farm.finance import planning_rules as model, setup
from lotus_farm.reporting import records
from lotus_farm.scoping import land_filters, land_scope

DOCTYPE = 'Lotus Financial Plan'
FORMULA_VERSION = 'financial-plan-v1'


def permission(doc, user=None, permission_type=None):
    """Use the same scope for native Desk/REST reads as for the planning API."""
    user = user or frappe.session.user
    if doc.company != setup.company():
        return False
    return not doc.farm or frappe.has_permission('Farm', 'read', doc=doc.farm, user=user)


def query_condition(user=None):
    user = user or frappe.session.user
    company = '`tabLotus Financial Plan`.company=' + frappe.db.escape(setup.company())
    if user == 'Administrator':
        return company
    farms = frappe.get_all('User Permission', filters={'user': user, 'allow': 'Farm'}, pluck='for_value') if frappe.has_permission('Farm', 'read', user=user) else []
    scope = "ifnull(`tabLotus Financial Plan`.farm,'')=''"
    if farms:
        scope += ' or `tabLotus Financial Plan`.farm in (' + ','.join(frappe.db.escape(f) for f in farms) + ')'
    return company + ' and (' + scope + ')'


def _json(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            frappe.throw('Nội dung kế hoạch không hợp lệ.')
    return value


def _normalize(values):
    try:
        return model.normalize(_json(values))
    except (ValueError, TypeError) as exc:
        frappe.throw(str(exc))


def _calculate(values):
    try:
        return dict(base=model.calculate(values, base=True), scenario=model.calculate(values))
    except (ValueError, TypeError) as exc:
        frappe.throw(str(exc))


def _company():
    from frappe.permissions import has_user_permission
    company = setup.company()
    # Finance viewers already have the module's read role. Keep Company user
    # restrictions without requiring an unrelated native Desk role (e.g. auditor).
    if not has_user_permission(frappe.get_doc('Company', company)):
        frappe.throw('Không có quyền xem công ty của kế hoạch.', frappe.PermissionError)
    return company


def _scope(farm=None):
    return land_scope(company=_company(), farm=farm)


def _get(name, *, lock=False, modified=None):
    company = _company()
    if lock:
        frappe.db.sql('select name from `tabLotus Financial Plan` where name=%s for update', (name,))
    doc = frappe.get_doc(DOCTYPE, name)
    doc.check_permission('read')
    if doc.company != company:
        frappe.throw('Kế hoạch không thuộc công ty đang chọn.', frappe.PermissionError)
    _scope(doc.farm)
    if lock:
        if not modified or str(doc.modified) != str(modified):
            frappe.throw('Kế hoạch đã thay đổi. Mở lại trước khi lưu.', frappe.TimestampMismatchError)
        if doc.state != 'Draft':
            frappe.throw('Kế hoạch đã duyệt. Nhân bản để lập phương án mới.')
    return doc


def validate_document(doc):
    """No native REST/Desk edits can bypass the API's version/state checks."""
    if not doc.flags.get('financial_plan_write'):
        frappe.throw('Sửa kế hoạch tại Tài chính – Kế toán → Kế hoạch tài chính.', frappe.PermissionError)
    values = _normalize(doc.plan_data)
    _scope(values['farm'])
    _calculate(values)
    if doc.company != _company():
        frappe.throw('Công ty không khớp kế hoạch.', frappe.PermissionError)
    doc.title = values['title']
    doc.farm = values['farm']
    doc.start_month = values['start_month']
    doc.month_count = values['month_count']
    doc.formula_version = FORMULA_VERSION
    doc.plan_data = json.dumps(values, ensure_ascii=False, sort_keys=True)


def _write(doc):
    doc.flags.financial_plan_write = True
    if doc.is_new():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)
    return _detail(doc)


def _detail(doc):
    values = _normalize(doc.plan_data)
    return dict(
        name=doc.name, company=doc.company, state=doc.state, modified=str(doc.modified),
        approved_by=doc.approved_by, approved_at=str(doc.approved_at or ''),
        copied_from=doc.copied_from, values=values, formula_version=doc.formula_version or FORMULA_VERSION,
        source_snapshot=_json(doc.source_snapshot or '{}'),
        result=_json(doc.approved_result) if doc.state == 'Approved' and doc.approved_result else _calculate(values),
    )


@frappe.whitelist()
def overview():
    setup.require_view()
    company = _company()
    plans = records(DOCTYPE, {'company': company}, [
        'name', 'title', 'farm', 'start_month', 'month_count', 'state', 'modified', 'approved_by',
    ])
    # Reading a saved farm plan has the same scope check as opening its details.
    readable = []
    for row in plans:
        if row.farm and not frappe.has_permission('Farm', 'read', doc=row.farm):
            continue
        readable.append(dict(row, modified=str(row.modified)))
    readable.sort(key=lambda r: r['modified'], reverse=True)
    farms = records('Farm', {'company': company}, ['name', 'farm_name']) if frappe.has_permission('Farm', 'read') else []
    return dict(
        company=company, currency=frappe.get_cached_value('Company', company, 'default_currency'),
        plans=readable, farms=farms, can_write=setup.can_post(), can_approve=setup.is_chief(),
        can_forecast=frappe.has_permission('Harvest Forecast', 'read'),
    )


@frappe.whitelist()
def detail(name):
    setup.require_view()
    return _detail(_get(name))


@frappe.whitelist(methods=['POST'])
def preview(values):
    setup.require_view()
    values = _normalize(values)
    _scope(values['farm'])
    return _calculate(values)


@frappe.whitelist(methods=['POST'])
def save(values, name=None, modified=None, request_key=None):
    setup.require_post()
    values = _normalize(values)
    _scope(values['farm'])
    if name:
        doc = _get(name, lock=True, modified=modified)
        # The source snapshot belongs to a specific scope and period.
        if (doc.farm, doc.start_month, doc.month_count) != (values['farm'], values['start_month'], values['month_count']):
            doc.source_snapshot = None
    else:
        request_key = str(request_key or '')
        if not request_key or len(request_key) > 100:
            frappe.throw('Thiếu mã yêu cầu lưu; mở lại biểu mẫu.')
        # Stable browser request id makes a retry after a lost response safe.
        frappe.db.sql('select name from `tabCompany` where name=%s for update', (_company(),))
        existing = frappe.db.get_value(DOCTYPE, {'request_key': request_key}, 'name')
        if existing:
            doc = _get(existing)
            if doc.owner != frappe.session.user:
                frappe.throw('Mã yêu cầu đã được sử dụng.', frappe.PermissionError)
            return _detail(doc)
        doc = frappe.new_doc(DOCTYPE)
        doc.company = _company()
        doc.state = 'Draft'
        doc.request_key = request_key
    doc.plan_data = json.dumps(values, ensure_ascii=False)
    return _write(doc)


@frappe.whitelist(methods=['POST'])
def approve(name, modified):
    setup.require_chief()
    doc = _get(name, lock=True, modified=modified)
    values = _normalize(doc.plan_data)
    result = _calculate(values)
    if result['base']['warnings']:
        frappe.throw('Bổ sung giá bán cho các tháng có sản lượng trước khi duyệt.')
    doc.state = 'Approved'
    doc.approved_by = frappe.session.user
    doc.approved_at = now_datetime()
    doc.approved_result = json.dumps(result, ensure_ascii=False, sort_keys=True)
    return _write(doc)


@frappe.whitelist(methods=['POST'])
def duplicate(name, request_key):
    setup.require_post()
    original = _get(name)
    if not request_key or len(str(request_key)) > 100:
        frappe.throw('Thiếu mã yêu cầu nhân bản.')
    key = 'copy:' + hashlib.sha256((name + ':' + str(request_key)).encode()).hexdigest()
    frappe.db.sql('select name from `tabCompany` where name=%s for update', (_company(),))
    existing = frappe.db.get_value(DOCTYPE, {'request_key': key}, 'name')
    if existing:
        doc = _get(existing)
        if doc.owner != frappe.session.user or doc.copied_from != original.name:
            frappe.throw('Mã yêu cầu đã được sử dụng.', frappe.PermissionError)
        return _detail(doc)
    values = _normalize(original.plan_data)
    values['title'] = (values['title'][:125] + ' (bản sao)')
    doc = frappe.new_doc(DOCTYPE)
    doc.company = original.company
    doc.state = 'Draft'
    doc.request_key = key
    doc.plan_data = json.dumps(values, ensure_ascii=False)
    doc.copied_from = original.name
    doc.source_snapshot = original.source_snapshot
    return _write(doc)


def _forecast(doc):
    values = _normalize(doc.plan_data)
    first = model.month_date(values['start_month'])
    last = model.month_date(model.months(values['start_month'], values['month_count'])[-1])
    end = date(last.year, last.month, monthrange(last.year, last.month)[1])
    scope = _scope(doc.farm)
    filters = {'supply_state': 'Released', 'period_start_date': ['<=', end], 'period_end_date': ['>=', first]}
    filters.update(land_filters(frappe.get_meta('Harvest Forecast'), scope))
    forecasts = records('Harvest Forecast', filters, [
        'name', 'farm', 'farm_block', 'period_start_date', 'period_end_date',
        'gross_forecast_kg', 'packed_forecast_kg', 'supply_state', 'modified',
    ])
    forecasts.sort(key=lambda r: r.name)
    try:
        proposal = model.forecast_quantities(values['start_month'], values['month_count'], forecasts)
    except ValueError as exc:
        frappe.throw(str(exc))
    payload = json.dumps(proposal, ensure_ascii=False, sort_keys=True)
    proposal['fingerprint'] = hashlib.sha256(payload.encode()).hexdigest()
    return proposal


@frappe.whitelist()
def forecast_preview(name):
    setup.require_view()
    return _forecast(_get(name))


@frappe.whitelist(methods=['POST'])
def apply_forecast(name, modified, fingerprint):
    setup.require_post()
    doc = _get(name, lock=True, modified=modified)
    proposal = _forecast(doc)
    if proposal['fingerprint'] != fingerprint:
        frappe.throw('Dự thu đã thay đổi. Xem lại nguồn trước khi lấy sản lượng.')
    if not proposal['sources']:
        frappe.throw('Không có dự thu đã phát hành trong phạm vi kế hoạch.')
    values = _normalize(doc.plan_data)
    indexed = {r['month']: r for r in proposal['rows']}
    for row in values['rows']:
        row.update({f: indexed[row['month']][f] for f in ('gross_kg', 'sales_kg')})
    doc.plan_data = json.dumps(values, ensure_ascii=False)
    doc.source_snapshot = json.dumps(dict(imported_at=str(now_datetime()), imported_by=frappe.session.user, **proposal), ensure_ascii=False)
    return _write(doc)
