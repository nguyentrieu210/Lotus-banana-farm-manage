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
