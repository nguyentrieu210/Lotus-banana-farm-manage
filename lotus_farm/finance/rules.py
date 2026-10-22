"""Tài chính – Kế toán: pure rules (no Frappe), unit-tested in tests/test_finance_rules.py.

The ledger is ERPNext's GL Entry; these rules only decide which accounts and dimensions a Lotus document
posts to, split amounts in whole đồng, and check that every entry balances. Account numbers come from the
company's configuration (Lotus Finance Settings), never from code.
"""
import json
from collections import OrderedDict
from pathlib import Path

COA_FILE = Path(__file__).resolve().parents[1] / 'data' / 'coa_tt99.json'
ROOT_TYPES = ('Asset', 'Liability', 'Equity', 'Income', 'Expense')
# Accounting dimensions on every ledger line: (Lotus field / dimension fieldname, DocType, label).
DIMENSIONS = (('lotus_farm', 'Farm', 'Vườn'), ('lotus_farm_block', 'Farm Block', 'Lô'),
              ('lotus_crop_cycle', 'Crop Cycle', 'Vụ'), ('lotus_work_type', 'Work Type', 'Công việc'))
DIM_FIELDS = tuple(d[0] for d in DIMENSIONS)

# Mapping key -> (label, allowed root types, required account_type or None). The account each key points
# to is chosen by the chief accountant in Lotus Finance Settings.
KEYS = OrderedDict((
    ('inventory_material', ('Kho nguyên liệu, vật liệu', ('Asset',), 'Stock')),
    ('finished_goods', ('Kho thành phẩm', ('Asset',), 'Stock')),
    ('material_cost', ('Chi phí nguyên liệu, vật liệu trực tiếp (xuất kho cho vườn/lô)', ('Expense',), None)),
    ('labour_cost', ('Chi phí nhân công trực tiếp (lương có công ở lô, tiền khoán)', ('Expense',), None)),
    ('overhead_service', ('Chi phí sản xuất chung – dịch vụ mua ngoài (thuê máy, vận chuyển cho lô)', ('Expense',), None)),
    ('production_cost', ('Chi phí sản xuất, kinh doanh dở dang (nhận kết chuyển 621/622/627)', ('Asset',), None)),
    ('admin_labour', ('Chi phí nhân viên quản lý (lương gián tiếp)', ('Expense',), None)),
    ('admin_expense', ('Chi phí quản lý – dịch vụ mua ngoài', ('Expense',), None)),
    ('received_not_billed', ('Hàng về chưa có hóa đơn', ('Liability',), 'Stock Received But Not Billed')),
    ('payable_supplier', ('Phải trả người bán', ('Liability',), 'Payable')),
    ('payable_employee', ('Phải trả người lao động', ('Liability',), None)),
    ('crew_payable', ('Phải trả tiền khoán đội', ('Liability',), None)),
    ('social_insurance', ('Bảo hiểm xã hội phải nộp', ('Liability',), None)),
    ('health_insurance', ('Bảo hiểm y tế phải nộp', ('Liability',), None)),
    ('unemployment_insurance', ('Bảo hiểm thất nghiệp phải nộp', ('Liability',), None)),
    ('cash', ('Tiền mặt', ('Asset',), 'Cash')),
    ('bank', ('Tiền gửi ngân hàng', ('Asset',), 'Bank')),
    ('stock_adjustment', ('Thừa kiểm kê / tài sản thừa chờ xử lý', ('Asset', 'Liability', 'Expense', 'Income', 'Equity'), None)),
    ('stock_shortage', ('Thiếu kiểm kê / tài sản thiếu chờ xử lý', ('Asset', 'Liability', 'Expense'), None)),
    ('cost_of_goods_sold', ('Giá vốn hàng bán', ('Expense',), None)),
    ('other_expense', ('Chi phí khác (xuất hủy, hư hỏng)', ('Expense',), None)),
    ('opening_equity', ('Đối ứng số dư đầu kỳ', ('Equity',), None)),
    ('round_off', ('Làm tròn', ('Expense', 'Income'), None)),
))
INSURANCE_KEYS = (('bhxh', 'social_insurance'), ('bhyt', 'health_insurance'), ('bhtn', 'unemployment_insurance'))


def load_coa(path=COA_FILE):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    columns = data['columns']
    data['accounts'] = [dict(zip(columns, row)) for row in data['accounts']]
    return data


def validate_coa(coa):
    """Numbers unique, parents defined before children with the same root type, valid root types and defaults."""
    errors, seen = [], {}
    for a in coa['accounts']:
        number = str(a['number'])
        if number in seen:
            errors.append('Số tài khoản %s bị trùng' % number)
        if a['root_type'] not in ROOT_TYPES:
            errors.append('Tài khoản %s có loại gốc không hợp lệ: %s' % (number, a['root_type']))
        parent = a.get('parent')
        if parent is not None:
            if parent not in seen:
                errors.append('Tài khoản %s có tài khoản cha %s chưa khai báo phía trên' % (number, parent))
            elif seen[parent]['root_type'] != a['root_type']:
                errors.append('Tài khoản %s khác loại gốc với tài khoản cha %s' % (number, parent))
            elif not number.startswith(str(parent)) and len(str(parent)) > 1:
                errors.append('Số tài khoản %s không bắt đầu bằng số tài khoản cha %s' % (number, parent))
        seen[number] = a
    groups = {a['parent'] for a in coa['accounts'] if a.get('parent')}
    for key, number in coa.get('defaults', {}).items():
        if number not in seen:
            errors.append('Tài khoản mặc định %s = %s không có trong danh mục' % (key, number))
        elif number in groups:
            errors.append('Tài khoản mặc định %s = %s là tài khoản tổng hợp, không ghi trực tiếp được' % (key, number))
    return errors


def coa_plan(coa, existing_numbers):
    """Accounts to create (parents first), each with is_group; accounts already present are skipped."""
    groups = {a['parent'] for a in coa['accounts'] if a.get('parent')}
    return [dict(a, is_group=1 if a['number'] in groups else 0) for a in coa['accounts'] if str(a['number']) not in existing_numbers]


def validate_mapping(mapping, accounts):
    """mapping: key -> account name; accounts: name -> dict(root_type, account_type, is_group, disabled, company_ok).
    Returns Vietnamese messages for every key that cannot be posted to."""
    errors = []
    for key, (label, roots, account_type) in KEYS.items():
        name = mapping.get(key)
        if not name:
            errors.append('Chưa chọn tài khoản cho "%s"' % label)
            continue
        a = accounts.get(name)
        if not a:
            errors.append('"%s": tài khoản %s không tồn tại' % (label, name))
        elif not a.get('company_ok', True):
            errors.append('"%s": tài khoản %s thuộc công ty khác' % (label, name))
        elif a.get('is_group'):
            errors.append('"%s": %s là tài khoản tổng hợp, không ghi trực tiếp được' % (label, name))
        elif a.get('disabled'):
            errors.append('"%s": tài khoản %s đang ngừng dùng' % (label, name))
        elif a.get('root_type') not in roots:
            errors.append('"%s": tài khoản %s không đúng loại (cần %s)' % (label, name, ' / '.join(roots)))
        elif account_type and a.get('account_type') != account_type:
            errors.append('"%s": tài khoản %s cần đặt kiểu "%s"' % (label, name, account_type))
    return errors


def split_amount(total, weights):
    """Split a whole-đồng amount by weights; the parts are whole numbers that add up exactly (largest remainder)."""
    total = int(round(total))
    weights = [max(0.0, float(w or 0)) for w in weights]
    s = sum(weights)
    if not weights:
        return []
    if s <= 0:
        weights, s = [1.0] * len(weights), float(len(weights))
    raw = [total * w / s for w in weights]
    parts = [int(r // 1) for r in raw]
    order = sorted(range(len(raw)), key=lambda i: (raw[i] - parts[i]), reverse=True)
    for i in order[:total - sum(parts)]:
        parts[i] += 1
    return parts


def dims_key(dims):
    return tuple((dims or {}).get(f) or '' for f in DIM_FIELDS)


def line(account, debit=0, credit=0, dims=None, note=''):
    return dict(account=account, debit=int(round(debit)), credit=int(round(credit)), **{f: (dims or {}).get(f) or None for f in DIM_FIELDS}, note=note)


def merge(lines):
    """Aggregate lines with the same account, side, dimensions and note (the note tells labour from crew pay); drop zero lines."""
    out = OrderedDict()
    for ln in lines:
        side = 'debit' if ln['debit'] else 'credit'
        if not ln['debit'] and not ln['credit']:
            continue
        key = (ln['account'], side, dims_key(ln), ln.get('note') or '')
        if key in out:
            out[key][side] += ln[side]
        else:
            out[key] = dict(ln)
    return list(out.values())


def check_entry(lines):
    """Every line one-sided and non-negative, totals equal and above zero."""
    errors = []
    for i, ln in enumerate(lines, start=1):
        if ln['debit'] < 0 or ln['credit'] < 0:
            errors.append('Dòng %d có số âm' % i)
        if bool(ln['debit']) == bool(ln['credit']):
            errors.append('Dòng %d phải ghi một bên Nợ hoặc Có' % i)
        if not ln.get('account'):
            errors.append('Dòng %d chưa có tài khoản' % i)
    debit, credit = sum(ln['debit'] for ln in lines), sum(ln['credit'] for ln in lines)
    if debit != credit:
        errors.append('Tổng Nợ %s khác tổng Có %s' % (format(debit, ',').replace(',', '.'), format(credit, ',').replace(',', '.')))
    if not debit:
        errors.append('Bút toán không có số tiền')
    return errors


def snapshot_people(snapshot):
    """The employees of a frozen payroll sheet (hr_period._sheet stores them under 'employees')."""
    return (snapshot or {}).get('employees') or (snapshot or {}).get('rows') or []


def payroll_entry(snapshot, shares, accounts, employee_rates, employer_rates, crew_farms=None, employee_farms=None):
    """Journal lines for an approved month.

    snapshot: Lotus Timekeeping Period snapshot (rows with employee, base, gross, employee_insurance, employer_insurance,
      net; crews with work_team, work_type, amount).
    shares: employee -> [(dims, workdays)] of the month's actual work by lot (empty -> indirect cost).
    accounts: mapping key -> account. employee_farms: employee -> farm (dimension of indirect cost).
    Debits: gross + employer insurance of each person to direct labour (622) by workday share, or to management
    staff cost (6421) without lot work; crew piece-rate to direct labour by farm and work type. Credits: net pay, insurance (employee + employer
    shares), crew payable.
    """
    lines, issues = [], []
    insurance = {k: 0 for k, _ in INSURANCE_KEYS}
    employee_farms, crew_farms = employee_farms or {}, crew_farms or {}
    for r in snapshot_people(snapshot):
        gross, er = int(round(r.get('gross') or 0)), int(round(r.get('employer_insurance') or 0))
        ee, net = int(round(r.get('employee_insurance') or 0)), int(round(r.get('net') or 0))
        if gross - ee != net:
            issues.append('%s: lương thực nhận %s khác tổng lương trừ bảo hiểm' % (r.get('employee'), net))
        cost = gross + er
        if not cost:
            continue
        work = [(d, w) for d, w in shares.get(r.get('employee')) or [] if w]
        if work:
            for (dims, _), part in zip(work, split_amount(cost, [w for _, w in work])):
                lines.append(line(accounts['labour_cost'], debit=part, dims=dims, note='Lương'))
        else:
            farm = employee_farms.get(r.get('employee'))
            lines.append(line(accounts['admin_labour'], debit=cost, dims={'lotus_farm': farm} if farm else None, note='Lương gián tiếp'))
        for (k, _), part in zip(INSURANCE_KEYS, _parts(ee, r.get('base'), employee_rates)):
            insurance[k] += part
        for (k, _), part in zip(INSURANCE_KEYS, _parts(er, r.get('base'), employer_rates)):
            insurance[k] += part
        lines.append(line(accounts['payable_employee'], credit=net, note='Thực nhận'))
    for k, key in INSURANCE_KEYS:
        lines.append(line(accounts[key], credit=insurance[k], note='Bảo hiểm (người lao động + doanh nghiệp)'))
    for c in snapshot.get('crews') or []:
        amount = int(round(c.get('amount') or 0))
        if not amount:
            continue
        farm = crew_farms.get(c.get('work_team'))
        if not farm:
            issues.append('Đội %s chưa gắn vườn' % c.get('work_team'))
        lines.append(line(accounts['labour_cost'], debit=amount, dims={'lotus_farm': farm, 'lotus_work_type': c.get('work_type')}, note='Khoán ' + str(c.get('work_team'))))
        lines.append(line(accounts['crew_payable'], credit=amount, note='Khoán ' + str(c.get('work_team'))))
    lines = merge(lines)
    return lines, issues + ([] if not lines else check_entry(lines))


def _parts(total, base, rates):
    """Insurance total -> parts in INSURANCE_KEYS order, exact to the đồng. payroll_rules.hourly_pay rounds each
    part as round(base x rate), so the same rounding reproduces the parts; otherwise split the total by the rates."""
    total = int(round(total or 0))
    if not total:
        return [0] * len(INSURANCE_KEYS)
    exact = [round(float(base or 0) * rates.get(k, 0)) for k, _ in INSURANCE_KEYS]
    if sum(exact) == total:
        return exact
    return split_amount(total, [rates.get(k, 0) for k, _ in INSURANCE_KEYS])


def shares_from_work(rows):
    """rows: dict(employee, workdays, lotus_farm, lotus_farm_block, lotus_crop_cycle, lotus_work_type)
    -> employee -> [(dims, workdays)] summed by dimension set."""
    out = {}
    for r in rows:
        if not r.get('employee') or not r.get('workdays'):
            continue
        bucket = out.setdefault(r['employee'], OrderedDict())
        dims = {f: r.get(f) for f in DIM_FIELDS}
        key = dims_key(dims)
        bucket[key] = (dims, bucket.get(key, (dims, 0))[1] + float(r['workdays']))
    return {e: list(b.values()) for e, b in out.items()}


def closing_entry(rows, wip_account):
    """Month-end transfer of production costs to work in progress, lot by lot.
    rows: dict(account, net, lotus_farm, lotus_farm_block, lotus_crop_cycle, lotus_work_type) = the month's balance of
    621 / 622 / 627x per dimension set -> Nợ 154 (same dimensions) / Có each cost account. Zero balances are skipped."""
    lines = []
    for r in rows:
        net = int(round(r.get('net') or 0))
        if not net:
            continue
        dims = {f: r.get(f) for f in DIM_FIELDS}
        if net > 0:
            lines += [line(wip_account, debit=net, dims=dims, note='Kết chuyển ' + r['account']), line(r['account'], credit=net, dims=dims, note='Kết chuyển')]
        else:
            lines += [line(wip_account, credit=-net, dims=dims, note='Kết chuyển ' + r['account']), line(r['account'], debit=-net, dims=dims, note='Kết chuyển')]
    return lines


def aging(due_date, today):
    """Days overdue -> bucket label for the payables list."""
    days = (today - due_date).days if due_date else 0
    if days <= 0:
        return 'Trong hạn'
    if days <= 30:
        return 'Quá hạn 1–30 ngày'
    if days <= 60:
        return 'Quá hạn 31–60 ngày'
    if days <= 90:
        return 'Quá hạn 61–90 ngày'
    return 'Quá hạn trên 90 ngày'
