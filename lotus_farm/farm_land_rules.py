"""Vườn & lô: per-lot figures, data gaps and the Excel round-trip (pure, unit-tested in tests/test_farm_land.py).

A tree count of 0 or empty means "not counted", never a density of 0: densities and the farm average are
taken over counted lots only, so uncounted land never dilutes them.
"""
import math

# Fields a land manager may change from the lot page or the Excel file (Excel column -> Farm Block field).
EDITABLE = (
    ('block_name', 'Tên lô', 'text'), ('farm_zone', 'Khu', 'text'), ('area_ha', 'Diện tích (ha)', 'float'),
    ('variety', 'Giống', 'text'), ('planting_date', 'Ngày trồng', 'date'), ('planting_density', 'Mật độ trồng (cây/ha)', 'float'),
    ('irrigation_zone', 'Khu tưới', 'text'), ('lotus_tree_count', 'Số cây gốc đã chốt', 'int'),
    ('lotus_tree_count_source', 'Nguồn số cây', 'text'), ('active', 'Đang dùng (1/0)', 'int'), ('notes', 'Ghi chú', 'text'),
)
FIELD_LABELS = {f: label for f, label, _ in EDITABLE}
GAPS = {'trees': 'Chưa có số cây', 'variety': 'Chưa có giống', 'map': 'Chưa có ranh giới', 'planting': 'Chưa có ngày trồng'}


def _num(value):
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def density(trees, area_ha):
    """Trees per hectare, or None when the lot is not counted or has no area."""
    trees, area = _num(trees), _num(area_ha)
    return round(trees / area) if trees > 0 and area > 0 else None


def gaps(block, has_map):
    """Missing data of one lot, as GAPS keys (the lot list filters on these)."""
    found = []
    if _num(block.get('lotus_tree_count')) <= 0:
        found.append('trees')
    if not block.get('variety'):
        found.append('variety')
    if not has_map:
        found.append('map')
    if not (block.get('planting_date') or block.get('lotus_inferred_planting_date')):
        found.append('planting')
    return found


def summary(blocks):
    """Totals of the lot list: area, trees and the density over counted lots only."""
    counted = [b for b in blocks if _num(b.get('lotus_tree_count')) > 0]
    trees = sum(_num(b.get('lotus_tree_count')) for b in counted)
    counted_area = sum(_num(b.get('area_ha')) for b in counted)
    return dict(blocks=len(blocks), area_ha=round(sum(_num(b.get('area_ha')) for b in blocks), 2), plots=sum(int(b.get('plots') or 0) for b in blocks),
                counted_blocks=len(counted), trees=int(trees), counted_area_ha=round(counted_area, 2),
                trees_per_ha=round(trees / counted_area) if counted_area else None,
                gaps={key: sum(key in (b.get('gaps') or []) for b in blocks) for key in GAPS})


def density_band(value, bands=(1500, 1800, 2100, 2400)):
    """0..len(bands) for a sequential map colour; None when not counted."""
    if value is None:
        return None
    return sum(value >= edge for edge in bands)


def parse_cell(kind, value):
    """Excel cell -> stored value; raises ValueError with a readable message."""
    if value in (None, ''):
        return None
    if kind == 'text':
        return str(value).strip()[:140] or None
    if kind == 'date':
        text = str(value).strip()[:10]
        if len(text) == 10 and text[4] == '-' and text[7] == '-':
            return text
        if len(text) == 10 and text[2] == '/' and text[5] == '/':
            return text[6:10] + '-' + text[3:5] + '-' + text[0:2]
        raise ValueError('ngày cần dạng dd/mm/yyyy')
    try:
        number = float(str(value).replace(',', '.'))
    except ValueError:
        raise ValueError('cần số không âm') from None
    if not math.isfinite(number) or number < 0:
        raise ValueError('cần số không âm')
    return int(round(number)) if kind == 'int' else round(number, 4)


def _same(kind, a, b):
    if kind in ('float', 'int'):
        return round(_num(a), 4) == round(_num(b), 4)
    return str(a or '')[:10 if kind == 'date' else 140].strip() == str(b or '').strip()


def diff_row(current, incoming, plots_area=None, known_zones=None):
    """Compare one Excel row with the stored lot -> dict(changes={field: (old, new)}, errors, warnings).

    Empty cells keep the stored value (the file never erases data). A changed tree count needs a source;
    an area far from the sum of its plots, or an unknown zone, is flagged but allowed.
    """
    changes, errors, warnings = {}, [], []
    for field, label, kind in EDITABLE:
        if field not in incoming:
            continue
        try:
            value = parse_cell(kind, incoming.get(field))
        except (TypeError, ValueError) as exc:
            errors.append(label + ': ' + str(exc))
            continue
        if value is None or _same(kind, current.get(field), value):
            continue
        changes[field] = (current.get(field), value)
    if 'active' in changes and changes['active'][1] not in (0, 1):
        errors.append('Đang dùng: chỉ nhận 1 hoặc 0')
    if 'lotus_tree_count' in changes and 'lotus_tree_count_source' not in changes:
        errors.append('Đổi số cây cần ghi Nguồn số cây (bảng chốt và thời điểm cập nhật)')
    area = changes.get('area_ha', (None, current.get('area_ha')))[1]
    if plots_area and _num(area) > 0 and abs(_num(area) - _num(plots_area)) > max(0.05, 0.03 * _num(plots_area)):
        warnings.append('Diện tích %.2f ha khác tổng các thửa %.2f ha' % (_num(area), _num(plots_area)))
    zone = changes.get('farm_zone', (None, None))[1]
    if zone and known_zones and zone not in known_zones:
        warnings.append('Khu "%s" chưa có trong vườn' % zone)
    return dict(changes=changes, errors=errors, warnings=warnings)
