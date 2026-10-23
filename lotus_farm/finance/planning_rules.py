"""Management budgets, independent of Frappe and the statutory ledger.

All selling quantities are kg of finished product. Production budgets are expensed
in their planned month; this model does not value inventory or work in progress.
Cash timing uses explicit whole-month collection/payment delays.
"""
import calendar
import re
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


ROW_FIELDS = (
    'gross_kg', 'sales_kg', 'price_per_kg', 'materials', 'labour', 'services',
    'packing_per_kg', 'transport_per_kg', 'overhead', 'depreciation', 'interest',
    'tax', 'capex', 'funding', 'debt_payment', 'other_receipts', 'other_payments',
)
FACTORS = ('quantity_percent', 'price_percent', 'variable_cost_percent')
MAX_AMOUNT = Decimal('1000000000000000')


def number(value, label, *, negative=False, maximum=MAX_AMOUNT):
    try:
        result = Decimal(str(0 if value in (None, '') else value))
    except (InvalidOperation, ValueError):
        raise ValueError(label + ': phải là số hợp lệ.') from None
    if not result.is_finite() or (not negative and result < 0) or abs(result) > maximum:
        raise ValueError(label + ': số ngoài giới hạn cho phép.')
    return result


def money(value):
    if not value.is_finite() or abs(value) > MAX_AMOUNT:
        raise ValueError('Số tiền tính toán quá lớn; kiểm tra sản lượng, đơn giá và ngân sách.')
    return int(value.quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def quantity(value):
    return float(value.quantize(Decimal('.001'), rounding=ROUND_HALF_UP))


def integer(value, label, low, high):
    result = number(value, label)
    if result != int(result) or not low <= result <= high:
        raise ValueError(f'{label}: chỉ nhận số nguyên từ {low} đến {high}.')
    return int(result)


def month_date(value):
    if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', str(value or '')):
        raise ValueError('Tháng phải có dạng yyyy-mm.')
    try:
        return date.fromisoformat(value + '-01')
    except ValueError:
        raise ValueError('Tháng không hợp lệ.') from None


def shift_month(value, count):
    first = month_date(value)
    index = first.year * 12 + first.month - 1 + count
    try:
        return date(index // 12, index % 12 + 1, 1).strftime('%Y-%m')
    except ValueError:
        raise ValueError('Khoảng kế hoạch vượt giới hạn lịch.') from None


def months(start, count):
    month_date(start)
    count = integer(count, 'Số tháng', 1, 36)
    return [shift_month(start, i) for i in range(count)]


def normalize(values):
    if not isinstance(values, dict):
        raise ValueError('Kế hoạch phải là một đối tượng.')
    title = str(values.get('title') or '').strip()
    if not title or len(title) > 140:
        raise ValueError('Tên kế hoạch cần có từ 1 đến 140 ký tự.')
    start = values.get('start_month')
    count = integer(values.get('month_count', 12), 'Số tháng', 1, 36)
    window = months(start, count)
    collection_delay = integer(values.get('collection_delay', 0), 'Chậm thu tiền', 0, 12)
    payment_delay = integer(values.get('payment_delay', 0), 'Chậm trả chi phí', 0, 12)
    raw_rows = values.get('rows') or []
    if not isinstance(raw_rows, list) or len(raw_rows) > 36:
        raise ValueError('Danh sách tháng không hợp lệ.')
    indexed = {}
    for row in raw_rows:
        if not isinstance(row, dict) or row.get('month') not in window:
            raise ValueError('Có dòng không thuộc khoảng kế hoạch.')
        key = row['month']
        if key in indexed:
            raise ValueError('Trùng tháng ' + key + '.')
        normalized = {f: float(number(row.get(f), f'{key} · {f}')) for f in ROW_FIELDS}
        if normalized['sales_kg'] > normalized['gross_kg']:
            raise ValueError(key + ': kg thành phẩm bán không được vượt kg thu hoạch.')
        indexed[key] = dict(month=key, **normalized)
    factors = {f: float(number(values.get(f, 100), f, maximum=Decimal('300'))) for f in FACTORS}
    return dict(
        title=title, farm=values.get('farm') or None, start_month=start, month_count=count,
        opening_cash=float(number(values.get('opening_cash'), 'Tiền đầu kỳ', negative=True)),
        collection_delay=collection_delay, payment_delay=payment_delay,
        notes=str(values.get('notes') or '')[:4000], **factors,
        rows=[indexed.get(m, dict(month=m, **dict.fromkeys(ROW_FIELDS, 0))) for m in window],
    )


def calculate(values, *, base=False):
    plan = normalize(values)
    q, p, v = [Decimal('1') if base else Decimal(str(plan[f])) / 100 for f in FACTORS]
    cash = money(Decimal(str(plan['opening_cash'])))
    receipts, payments = {}, {}
    result = []
    warnings = []
    for row in plan['rows']:
        get = lambda key: Decimal(str(row[key]))
        key = row['month']
        gross, sales = get('gross_kg') * q, get('sales_kg') * q
        revenue = money(sales * get('price_per_kg') * p)
        packing = money(sales * get('packing_per_kg') * v)
        transport = money(sales * get('transport_per_kg') * v)
        fixed = sum(money(get(f)) for f in ('materials', 'labour', 'services', 'overhead'))
        operating_cost = fixed + packing + transport
        depreciation, interest, tax = [money(get(f)) for f in ('depreciation', 'interest', 'tax')]
        profit_before_tax = revenue - operating_cost - depreciation - interest
        receive_month = shift_month(key, plan['collection_delay'])
        pay_month = shift_month(key, plan['payment_delay'])
        receipts[receive_month] = receipts.get(receive_month, 0) + revenue
        payments[pay_month] = payments.get(pay_month, 0) + operating_cost
        cash_in = receipts.get(key, 0) + money(get('funding')) + money(get('other_receipts'))
        cash_out = payments.get(key, 0) + interest + tax + sum(money(get(f)) for f in ('capex', 'debt_payment', 'other_payments'))
        opening = cash
        cash += cash_in - cash_out
        result.append(dict(
            month=key, gross_kg=quantity(gross), sales_kg=quantity(sales), revenue=revenue,
            operating_cost=operating_cost, packing=packing, transport=transport,
            depreciation=depreciation, interest=interest, tax=tax,
            profit_before_tax=profit_before_tax, profit=profit_before_tax - tax,
            operating_receipts=receipts.get(key, 0), operating_payments=payments.get(key, 0),
            opening_cash=opening, cash_in=cash_in, cash_out=cash_out,
            net_cash=cash_in - cash_out, closing_cash=cash, funding_gap=max(0, -cash),
        ))
        if row['sales_kg'] and not row['price_per_kg']:
            warnings.append(key + ': có sản lượng bán nhưng chưa nhập giá bán.')
    last = plan['rows'][-1]['month']
    totals = {f: sum(r[f] for r in result) for f in (
        'revenue', 'operating_cost', 'depreciation', 'interest', 'tax', 'profit_before_tax',
        'profit', 'cash_in', 'cash_out', 'net_cash',
    )}
    totals.update(
        gross_kg=quantity(sum(Decimal(str(r['gross_kg'])) for r in result)),
        sales_kg=quantity(sum(Decimal(str(r['sales_kg'])) for r in result)),
        opening_cash=money(Decimal(str(plan['opening_cash']))), closing_cash=cash,
        funding_gap=max([max(0, -money(Decimal(str(plan['opening_cash']))))] + [r['funding_gap'] for r in result]),
        receivables_after_horizon=sum(amount for m, amount in receipts.items() if m > last),
        payables_after_horizon=sum(amount for m, amount in payments.items() if m > last),
    )
    if any(abs(value) > 9_000_000_000_000_000 for row in [*result, totals] for value in row.values() if isinstance(value, (int, float))):
        raise ValueError('Tổng kế hoạch quá lớn; kiểm tra sản lượng, đơn giá và ngân sách.')
    return dict(rows=result, totals=totals, warnings=warnings)


def forecast_quantities(start, count, forecasts):
    """Count each released document once in its starting month; never prorate it.

    Documents partly outside the planning horizon are excluded. Cross-month
    documents are visible as warnings so a planner can split them upstream.
    """
    window = months(start, count)
    end_month = month_date(window[-1])
    end = date(end_month.year, end_month.month, calendar.monthrange(end_month.year, end_month.month)[1])
    first = month_date(start)
    rows = {m: dict(month=m, gross_kg=0, sales_kg=0) for m in window}
    sources, warnings, seen = [], [], set()
    for source in forecasts:
        if source.get('supply_state') != 'Released':
            continue
        name = source['name']
        if name in seen:
            raise ValueError('Trùng phiếu dự thu ' + name + '.')
        seen.add(name)
        a = date.fromisoformat(str(source['period_start_date'])[:10])
        b = date.fromisoformat(str(source['period_end_date'])[:10])
        if b < first or a > end:
            continue
        if a < first or b > end or b < a:
            warnings.append(name + ': vượt khoảng kế hoạch, chưa lấy sản lượng.')
            continue
        key = a.strftime('%Y-%m')
        if key != b.strftime('%Y-%m'):
            warnings.append(name + ': trải nhiều tháng; toàn bộ sản lượng xếp vào ' + key + '.')
        gross = number(source.get('gross_forecast_kg'), name)
        sales = number(source.get('packed_forecast_kg'), name)
        if sales > gross:
            raise ValueError(name + ': sản lượng thành phẩm vượt sản lượng thu hoạch.')
        rows[key]['gross_kg'] += gross
        rows[key]['sales_kg'] += sales
        sources.append(dict(
            name=name, month=key, farm=source.get('farm'), farm_block=source.get('farm_block'),
            from_date=str(a), to_date=str(b), modified=str(source.get('modified') or ''),
            gross_kg=float(gross), sales_kg=float(sales),
        ))
    for row in rows.values():
        row['gross_kg'] = quantity(Decimal(str(row['gross_kg'])))
        row['sales_kg'] = quantity(Decimal(str(row['sales_kg'])))
    return dict(rows=list(rows.values()), sources=sources, warnings=warnings)
