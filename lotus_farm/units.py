"""Vietnamese names of units of measure for text Lotus builds on the server (Excel files, prints, ledger descriptions).
Mirrors frontend/src/units.js; ERPNext keeps its canonical UOM codes, only the displayed words change."""
import re

NAMES = {
    'bao': 'Bao', 'chai': 'Chai', 'gói': 'Gói', 'bó': 'Bó', 'can': 'Can', 'thùng': 'Thùng', 'bunch': 'Buồng', 'bunches': 'Buồng', 'tree': 'Cây',
    'trees': 'Cây', 'ha': 'ha', 'hectare': 'ha', 'hectares': 'ha', 'kg': 'kg', 'kilogram': 'kg', 'kilograms': 'kg', 'liter': 'Lít', 'litre': 'Lít',
    'liters': 'Lít', 'litres': 'Lít', 'nos': 'Cái', 'piece': 'Cái', 'pieces': 'Cái', 'day': 'Ngày', 'days': 'Ngày', 'hour': 'Giờ', 'hours': 'Giờ',
    'unit': 'Đơn vị', 'set': 'Bộ', 'pair': 'Đôi', 'box': 'Hộp / thùng', 'bag': 'Bao', 'bottle': 'Chai', 'pack': 'Gói', 'packet': 'Gói',
    'roll': 'Cuộn', 'bundle': 'Bó', 'carton': 'Thùng', 'drum': 'Phuy', 'sheet': 'Tấm', 'tray': 'Khay', 'pallet': 'Pallet', 'tube': 'Tuýp',
    'dozen': 'Tá', 'gram': 'g', 'milligram': 'mg', 'tonne': 'Tấn', 'ton': 'Tấn', 'quintal': 'Tạ', 'meter': 'Mét', 'metre': 'Mét',
    'centimeter': 'cm', 'millimeter': 'mm', 'kilometer': 'km', 'millilitre': 'ml', 'milliliter': 'ml', 'minute': 'Phút', 'second': 'Giây',
    'week': 'Tuần', 'month': 'Tháng', 'year': 'Năm', 'percent': 'Phần trăm',
}


def _part(value):
    key = value.strip().lower()
    if key in NAMES:
        return NAMES[key]
    if key.startswith('square '):
        return _part(value.strip()[7:]) + '²'
    if key.startswith('cubic '):
        return _part(value.strip()[6:]) + '³'
    return value.strip()


def label(value):
    """'Tonne' -> 'Tấn', 'Nos' -> 'Cái', 'Square Meter' -> 'Mét²', '1 kg/gói' unchanged; unknown codes are shown as they are."""
    if not value:
        return ''
    raw = str(value)
    if raw.strip().lower() in NAMES:
        return NAMES[raw.strip().lower()]
    if re.search(r'\d', raw):
        return raw
    return '/'.join(_part(p) for p in raw.split('/'))
