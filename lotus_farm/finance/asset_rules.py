"""Fixed-asset rules without database access. Allocations preserve native ledger precision."""
from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_FLOOR, ROUND_HALF_UP
import hashlib
import json

DIMENSIONS = ('lotus_farm', 'lotus_farm_block', 'lotus_crop_cycle', 'lotus_work_type')
METHODS = ('Straight Line', 'Written Down Value', 'Double Declining Balance')
KINDS = ('Create', 'Profile', 'Move', 'Repair', 'Upgrade', 'Suspend', 'Resume', 'Sell', 'Scrap', 'Restore')


def decimal(value):
    try:
        result = Decimal(str(value if value not in (None, '') else 0))
    except (InvalidOperation, ValueError):
        raise ValueError('Giá trị số không hợp lệ.')
    if not result.is_finite():
        raise ValueError('Giá trị số không hợp lệ.')
    return result


def money(value):
    return int(decimal(value).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def bounds(month):
    try:
        year, mon = map(int, str(month).split('-'))
        first = date(year, mon, 1)
        if str(month) != first.isoformat()[:7]:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError('Tháng phải có dạng yyyy-mm.')
    return first.isoformat(), date(year, mon, monthrange(year, mon)[1]).isoformat()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str,
                                     separators=(',', ':')).encode()).hexdigest()


def allocation_rows(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError('Khai ít nhất một dòng phân bổ, tổng tỷ lệ 100%.')
    result, keys = [], set()
    for index, row in enumerate(rows, 1):
        percent = decimal(row.get('percent'))
        if percent <= 0 or percent > 100:
            raise ValueError('Dòng %d: tỷ lệ phải lớn hơn 0 và không quá 100%%.' % index)
        if not row.get('expense_account') or not row.get('cost_center'):
            raise ValueError('Dòng %d: chọn tài khoản chi phí và trung tâm chi phí.' % index)
        entry = {k: row.get(k) or None for k in (*DIMENSIONS, 'expense_account', 'cost_center')}
        key = tuple(entry.values())
        if key in keys:
            raise ValueError('Dòng %d: đích phân bổ bị trùng.' % index)
        keys.add(key)
        result.append(dict(entry, percent=str(percent)))
    if sum(decimal(r['percent']) for r in result) != Decimal('100'):
        raise ValueError('Tổng tỷ lệ phân bổ phải bằng đúng 100%.')
    return result


def split_amount(amount, rows):
    """Largest remainder, stable input-order tie breaking; allocations always sum to amount."""
    rows = allocation_rows(rows)
    source = decimal(amount)
    if source < 0:
        raise ValueError('Số tiền khấu hao không được âm.')
    quantum = Decimal(1) if source == source.to_integral_value() else Decimal(10) ** min(-2, source.as_tuple().exponent)
    units = int(source / quantum)
    raw = [Decimal(units) * decimal(r['percent']) / 100 for r in rows]
    parts = [int(n.to_integral_value(rounding=ROUND_FLOOR)) for n in raw]
    order = sorted(range(len(rows)), key=lambda i: (-(raw[i] - parts[i]), i))
    for i in order[:units - sum(parts)]:
        parts[i] += 1
    return [dict(row, amount=parts[i] if quantum == 1 else float(parts[i] * quantum)) for i, row in enumerate(rows)]


def profile(values):
    result = dict(values)
    result['existing'] = values.get('existing') in (True, 1, '1', 'true')
    result['serial_no'] = str(values.get('serial_no') or '').strip()
    errors = {}
    for key, label in [('code', 'Mã tài sản'), ('asset_name', 'Tên tài sản'),
                       ('asset_category', 'Nhóm tài sản'), ('location', 'Vị trí')]:
        result[key] = str(values.get(key) or '').strip()
        if not result[key]:
            errors[key] = 'Nhập ' + label.lower() + '.'
    result['method'] = values.get('method') or 'Straight Line'
    if result['method'] not in METHODS:
        errors['method'] = 'Phương pháp khấu hao chưa hỗ trợ.'
    for key in ('purchase_date', 'available_for_use_date'):
        try:
            text = str(values.get(key) or '')
            result[key] = (datetime.strptime(text, '%d/%m/%Y').date() if '/' in text else date.fromisoformat(text)).isoformat()
        except ValueError:
            errors[key] = 'Chọn ngày hợp lệ.'
    for key in ('amount', 'opening_depreciation', 'salvage_value'):
        try:
            result[key] = money(values.get(key))
            if result[key] < 0:
                errors[key] = 'Số tiền không được âm.'
        except ValueError as exc:
            errors[key] = str(exc)
    if not result.get('amount'):
        errors['amount'] = 'Nguyên giá phải lớn hơn 0.'
    try:
        for key in ('months', 'booked_months'):
            val = decimal(values.get(key) or 0)
            if val != int(val) or val < 0:
                raise ValueError()
            result[key] = int(val)
        if (result['months'] < 1 and not values.get('non_depreciable')) or result['booked_months'] > result['months']:
            raise ValueError()
    except ValueError:
        errors['months'] = 'Số tháng khấu hao phải là số nguyên dương; số kỳ đã trích không vượt tổng số kỳ.'
    if not errors.get('amount') and not errors.get('opening_depreciation') and not errors.get('salvage_value'):
        if result['opening_depreciation'] + result['salvage_value'] > result['amount']:
            errors['opening_depreciation'] = 'Hao mòn đầu kỳ và giá trị thu hồi vượt nguyên giá.'
    if all(result.get(k) for k in ('purchase_date', 'available_for_use_date')) and result['available_for_use_date'] < result['purchase_date']:
        errors['available_for_use_date'] = 'Ngày sử dụng không được trước ngày mua.'
    if not result['existing'] and not (values.get('purchase_invoice') or values.get('purchase_receipt') or values.get('supplier')):
        errors['supplier'] = 'Chọn chứng từ mua đã duyệt hoặc nhà cung cấp để lập hóa đơn mua tài sản.'
    return result, errors
