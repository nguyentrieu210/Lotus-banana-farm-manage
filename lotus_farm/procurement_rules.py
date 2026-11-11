"""Pure purchase rules. Amounts are VND; quantities are in stock UOM at API boundaries."""
from decimal import Decimal, InvalidOperation
import hashlib
import json

KINDS = ('Material', 'Tool', 'Asset', 'Service')
KIND_LABELS = dict(Material='Nguyên vật liệu', Tool='Công cụ', Asset='Tài sản', Service='Dịch vụ')


def number(value, label='Số', positive=False):
    try:
        result = Decimal(str(value if value not in ('', None) else 0))
    except (InvalidOperation, ValueError):
        raise ValueError(label + ' không hợp lệ.')
    if not result.is_finite() or result < 0 or positive and result == 0:
        raise ValueError(label + ' phải ' + ('lớn hơn 0.' if positive else 'không âm.'))
    return result


def kind_for(item, selected=None):
    kind = selected or ('Asset' if item.get('is_fixed_asset') else 'Material' if item.get('is_stock_item') else 'Service')
    if kind not in KINDS:
        raise ValueError('Loại mua không hợp lệ.')
    if kind == 'Asset' and (not item.get('is_fixed_asset') or item.get('is_stock_item')):
        raise ValueError('Tài sản cần Item tài sản cố định không theo dõi tồn kho.')
    if kind in ('Material', 'Tool') and not item.get('is_stock_item'):
        raise ValueError('Nguyên vật liệu/công cụ cần Item có theo dõi tồn kho.')
    if kind == 'Service' and (item.get('is_stock_item') or item.get('is_fixed_asset')):
        raise ValueError('Dịch vụ cần Item không theo dõi tồn kho, không phải tài sản.')
    return kind


def quote_total(qty, rate, factor=1, vat='KCT', freight=0):
    """Blank/zero quote price is unknown, never a free offer."""
    q = number(qty, 'Số lượng', True)
    f = number(factor, 'Quy đổi', True)
    shipping = number(freight, 'Vận chuyển')
    if vat not in ('KCT', '0', '5', '8', '10'):
        raise ValueError('Thuế suất không hợp lệ.')
    if rate in (None, '') or number(rate) == 0:
        return dict(stock_qty=float(q*f), unit_cost=None, net=None, tax=None, freight=float(shipping), gross=None)
    net = q * number(rate)
    tax = net * Decimal(0 if vat == 'KCT' else vat) / 100
    return dict(stock_qty=float(q*f), unit_cost=float((net+tax+shipping)/(q*f)), net=float(net),
                tax=float(tax), freight=float(shipping), gross=float(net+tax+shipping))


def needs_reason(chosen_cost, offer_costs):
    """A reason is required only when the chosen landed cost (per stock unit) is above the cheapest priced
    offer for the same need. Unpriced offers (None) never count as cheaper."""
    priced = [float(c) for c in offer_costs if c is not None]
    if chosen_cost is None or not priced:
        return True
    return float(chosen_cost) > min(priced) * (1 + 1e-9) + 0.005


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def evidence_key(supplier, reference, day, amount):
    """Business identity catches different photographs of the same evidence."""
    ref = ''.join(str(reference or '').upper().split())
    return digest([supplier, ref, str(day), str(number(amount))])


def remaining(total, posted=0, reserved=0, requested=None):
    available = number(total)-number(posted)-number(reserved)
    if requested is not None and number(requested, 'Số tiền', True) > available + Decimal('0.5'):
        raise ValueError('Số tiền vượt phần còn lại sau các phiếu đang chờ ký.')
    return float(max(Decimal(0), available))


def printed_total_gap(computed, printed, goods_lines):
    """(printed − computed, accepted). The total printed on a supplier invoice may differ from the sum of its
    lines by at most 1 đ per goods line (rounding of decimal prices and per-line VAT); more is an entry error."""
    gap = round(float(printed) - float(computed), 2)
    return gap, abs(gap) <= max(1, int(goods_lines or 0)) + 1e-6


VAT_RATES = (0.0, 0.05, 0.08, 0.10)


def suspect_lines(lines, gap):
    """Lines that could explain a gap between the printed total and the lines: another VAT rate on one line, or a
    whole number of units more or less. lines: [{line, name, qty, rate, vat}] (vat as a fraction)."""
    found = []
    for row in lines:
        qty, rate, vat = float(row.get('qty') or 0), float(row.get('rate') or 0), float(row.get('vat') or 0)
        net = qty * rate
        if not net:
            continue
        for other in VAT_RATES:
            if abs(other - vat) > 1e-9 and abs(net * (other - vat) - gap) <= 1:
                found.append(dict(line=row.get('line'), name=row.get('name') or '', reason='thuế suất có thể là %g%%' % (other * 100)))
                break
        else:
            unit = rate * (1 + vat)
            units = gap / unit if unit else 0
            if unit and abs(units) >= 0.999 and abs(units - round(units)) * unit <= 1 and abs(units) <= max(qty, 1) * 10:
                found.append(dict(line=row.get('line'), name=row.get('name') or '',
                                  reason='số lượng có thể %s %g' % ('thiếu' if units > 0 else 'thừa', abs(round(units)))))
    return found


AGING_BUCKETS = ('current', 'd1_30', 'd31_60', 'd61_90', 'd90_plus', 'no_due')
AGING_LABELS = dict(current='Chưa đến hạn', d1_30='Quá hạn 1–30 ngày', d31_60='Quá hạn 31–60 ngày', d61_90='Quá hạn 61–90 ngày',
                    d90_plus='Quá hạn trên 90 ngày', no_due='Không có hạn trả')


def _day(value):
    from datetime import date, datetime
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10]) if value else None


def aging_bucket(due_date, as_of):
    """Bucket of an amount still owed on the closing date, by days past its due date."""
    due, day = _day(due_date), _day(as_of)
    if not due:
        return 'no_due'
    late = (day - due).days
    if late <= 0:
        return 'current'
    return 'd1_30' if late <= 30 else 'd31_60' if late <= 60 else 'd61_90' if late <= 90 else 'd90_plus'


def due_within(due_date, as_of, days=7):
    """Falls due in the next `days` days after the closing date (not yet overdue on it)."""
    due, day = _day(due_date), _day(as_of)
    return bool(due) and 0 < (due - day).days <= int(days)


def age(rows, as_of):
    """rows: [{amount, due_date}] with amount > 0 still owed → {bucket: total} over every bucket."""
    totals = {key: 0.0 for key in AGING_BUCKETS}
    for row in rows:
        totals[aging_bucket(row.get('due_date'), as_of)] += float(row.get('amount') or 0)
    return totals
