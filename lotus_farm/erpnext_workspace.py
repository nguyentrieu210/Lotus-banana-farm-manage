"""Permission-filtered entrypoints into the installed ERPNext and HRMS workspaces.

The native resolver owns navigation, domain restrictions and module profiles. This
adapter exposes its result in Lotus; it does not grant rights or write documents.
"""
import json
from urllib.parse import quote, urlencode, urlsplit

import frappe
from frappe.utils import getdate, slug


def can_access():
    return frappe.session.user != 'Guest' and frappe.get_cached_value('User', frappe.session.user, 'user_type') == 'System User'


def _filters(value):
    if not value:
        return {}
    value = json.loads(value) if isinstance(value, str) else value
    if isinstance(value, dict):
        return value.copy()
    # Sidebar list filters can contain [field, operator, value].
    return {r[-3]: r[-1] if r[-2] == '=' else r[-2:] for r in value if isinstance(r, list) and len(r) in (3, 4)} if isinstance(value, list) else {}


def _route(row, company, warehouse, from_date, to_date, reports):
    kind, name = row.get('link_type'), row.get('link_to')
    filters = _filters(row.get('filters') or row.get('route_options'))
    if kind == 'DocType':
        if not frappe.db.exists('DocType', name) or not frappe.has_permission(name, 'read'):
            return None
        meta = frappe.get_meta(name)
        if meta.istable:
            return None
        route = '/desk/' + quote(slug(name))
        if meta.issingle:
            route += '/' + quote(name)
        else:
            if company and meta.has_field('company'):
                filters['company'] = company
            if warehouse and meta.has_field('warehouse'):
                filters['warehouse'] = warehouse
    elif kind == 'Report':
        report = reports.get(name)
        if not report:
            return None
        if report.disabled or (report.ref_doctype and not frappe.has_permission(report.ref_doctype, 'report')):
            return None
        from frappe.utils import get_url_to_report
        route = urlsplit(get_url_to_report(name, report.report_type, report.ref_doctype)).path
        if company:
            filters['company'] = company
        # These standard reports use these exact native filters. Other reports
        # retain their own date controls rather than receiving invented filters.
        if name in ('Stock Ledger', 'Stock Balance', 'Stock Ageing', 'General Ledger', 'Trial Balance', 'Purchase Register', 'Sales Register'):
            filters.update({k: v for k, v in dict(from_date=from_date, to_date=to_date).items() if v})
        if warehouse and name in ('Stock Ledger', 'Stock Balance', 'Stock Ageing'):
            filters['warehouse'] = warehouse
    elif kind == 'Workspace':
        page = frappe.get_doc('Workspace', name)
        if not page.public:
            return None
        route = '/desk/' + quote(slug(name))
    elif kind == 'Page':
        route = '/desk/' + quote(name)
    elif kind == 'Dashboard':
        route = '/desk/dashboard-view/' + quote(name)
    else:
        # External links and scripts are not part of the ERP document directory.
        return None
    encoded = {k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in filters.items()}
    route += ('?' + urlencode(encoded)) if encoded else ''
    if row.get('tab'):
        route += '#' + quote(row['tab'])
    return route


@frappe.whitelist()
def catalog(company=None, warehouse=None, from_date=None, to_date=None, module=None):
    if not can_access():
        frappe.throw('Bạn không có quyền mở ERPNext.', frappe.PermissionError)
    companies = frappe.get_list('Company', fields=['name'], limit_page_length=0) if frappe.has_permission('Company', 'read') else []
    if company and company not in {r.name for r in companies}:
        frappe.throw('Bạn không có quyền truy cập công ty này.', frappe.PermissionError)
    stores = frappe.get_list('Warehouse', filters={**({'company': company} if company else {}), 'is_group': 0}, fields=['name', 'warehouse_name', 'company'], limit_page_length=0) if frappe.has_permission('Warehouse', 'read') else []
    if warehouse and warehouse not in {r.name for r in stores}:
        frappe.throw('Kho không thuộc phạm vi được phép.', frappe.PermissionError)
    for value in (from_date, to_date):
        if value:
            getdate(value)
    if from_date and to_date and getdate(from_date) > getdate(to_date):
        frappe.throw('Từ ngày phải trước hoặc bằng đến ngày.')

    from frappe.desk.doctype.sidebar.sidebar import SidebarContext, get_navigable_modules, resolve_sidebar
    from frappe.desk.utils import is_item_allowed
    installed = set(frappe.get_installed_apps()) & {'erpnext', 'hrms'}
    owned = set(frappe.get_all('Module Def', filters={'app_name': ['in', list(installed)]}, pluck='name'))
    modules = [name for name in get_navigable_modules() if name in owned]
    context = SidebarContext.for_modules(modules, frappe.session.user)
    # The canonical native report directory already applies standard/custom roles,
    # Report permissions and user restrictions. Batch metadata rather than loading
    # each Report with its child tables during navigation.
    permitted_reports = list(context.perm_ctx.allowed_reports)
    reports = {r.name: r for r in frappe.get_all('Report',
        filters={'name': ['in', permitted_reports or ['__none__']]},
        fields=['name', 'report_type', 'ref_doctype', 'disabled'], limit_page_length=0)}
    result, groups = [], []
    for shell in context.bases:
        sidebar = resolve_sidebar(shell, frappe.session.user, context)
        if not sidebar or sidebar.app not in installed:
            continue
        # Resolve the directory for every module, but expand the long report/setup
        # lists only for the selected module. A stock user must not wait for every
        # payroll and accounting form's metadata before opening the warehouse.
        if module and module != shell:
            groups.append(dict(value=shell, label=sidebar.label, app=sidebar.app, count=None))
            continue
        rows, seen = [], set()

        def append(row, section=''):
            if not row.get('link_to') or not is_item_allowed(row['link_to'], row.get('link_type') or '', context.perm_ctx):
                return
            href = _route(row, company, warehouse, from_date, to_date, reports)
            if not href or href in seen:
                return
            seen.add(href)
            rows.append(dict(id=shell + ':' + href, module=shell, module_label=sidebar.label, group=frappe._(section), label=row.get('label') or frappe._(row['link_to']), name=row['link_to'], kind=row['link_type'], href=href))

        section = ''
        for row in sidebar.items:
            if row.get('type') == 'Section Break':
                section = row.get('label') or ''
            else:
                append(row, section)
                # A native workspace holds the long tail of reports and setup.
                if row.get('link_type') == 'Workspace' and row.get('link_to') in context.perm_ctx.allowed_workspaces:
                    page = frappe.get_doc('Workspace', row['link_to'])
                    heading = ''
                    for link in page.links:
                        if link.type == 'Card Break':
                            heading = link.label
                        else:
                            append(dict(link_type=link.link_type, link_to=link.link_to, label=frappe._(link.label or link.link_to or '')), heading)
        if rows:
            groups.append(dict(value=shell, label=sidebar.label, app=sidebar.app, count=len(rows)))
            result.extend(rows)
    return dict(modules=groups, rows=result, companies=companies, warehouses=stores)
