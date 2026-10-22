"""Additive fixed-asset schema and permissions. Installation never enables or posts assets."""
import frappe


def field(name, label, kind='Data', options=None, **kwargs):
    return dict(fieldname=name, label=label, fieldtype=kind, **({'options': options} if options else {}), **kwargs)


def install():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    from frappe.permissions import add_permission, update_permission_property
    create_custom_fields({
        'Lotus Finance Settings': [field('fixed_assets_enabled', 'Bật tài sản cố định', 'Check', default='0'),
                                  field('asset_previous_auto_depreciation', 'Tự động khấu hao trước khi bật', 'Check', read_only=1)],
        'Asset': [field('lotus_asset_code', 'Mã tài sản Lotus', unique=1), field('lotus_serial_no', 'Số serial', unique=1),
                  field('lotus_managed_asset', 'Quản lý qua Lotus', 'Check', read_only=1, default='0'),
                  field('lotus_usage_suspended', 'Tạm ngừng sử dụng', 'Check', read_only=1),
                  field('lotus_usage_reason', 'Lý do ngừng sử dụng', 'Small Text', read_only=1)],
        'Journal Entry': [field('lotus_asset_operation', 'Nghiệp vụ tài sản', 'Link', 'Lotus Asset Operation', read_only=1, no_copy=1),
                          field('lotus_asset_run', 'Bảng khấu hao Lotus', 'Link', 'Lotus Asset Depreciation Run', read_only=1, no_copy=1),
                          field('lotus_asset_source_journal', 'Bút toán khấu hao gốc', 'Link', 'Journal Entry', read_only=1, no_copy=1)],
    })
    readable = ('Asset', 'Asset Category', 'Asset Finance Book', 'Asset Depreciation Schedule', 'Depreciation Schedule',
                'Asset Movement', 'Asset Repair', 'Asset Capitalization', 'Asset Value Adjustment', 'Asset Activity', 'Location',
                'Lotus Asset Operation', 'Lotus Asset Allocation', 'Lotus Asset Depreciation Run')
    for dt in readable:
        if not frappe.db.exists('DocType', dt) or frappe.get_meta(dt).istable:
            continue
        for role in ('Lotus Accountant', 'Lotus Chief Accountant', 'Lotus Auditor'):
            if not frappe.db.exists('Role', role):
                continue
            if not frappe.db.exists('Custom DocPerm', {'parent': dt, 'role': role, 'permlevel': 0}):
                add_permission(dt, role)
            for operation in ('read', 'report', 'print', 'export'):
                update_permission_property(dt, role, 0, operation, 1)
            # Submission is through the reviewed API; native document guards enforce the same policy in Desk.
            if role != 'Lotus Auditor' and dt in ('Asset', 'Asset Movement', 'Asset Repair', 'Asset Capitalization', 'Asset Value Adjustment'):
                for operation in ('create', 'write'):
                    update_permission_property(dt, role, 0, operation, 1)
                if role == 'Lotus Chief Accountant':
                    for operation in ('submit', 'cancel'):
                        update_permission_property(dt, role, 0, operation, 1)
            if role == 'Lotus Chief Accountant' and dt == 'Asset Depreciation Schedule':
                for operation in ('create', 'write', 'submit', 'cancel'):
                    update_permission_property(dt, role, 0, operation, 1)
