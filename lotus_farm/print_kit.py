"""Lotus Print: one layout for every printed or PDF document (web /lotus/in-*, Desk print formats, archived PDFs).

Pure helpers (numbers, dates, Vietnamese amount in words) are unit-tested in tests/test_print_kit.py.
Templates live in lotus_farm/templates/print/; every template reads a single context object `p`.
"""
import re
from datetime import date, datetime

TEMPLATES = 'lotus_farm/templates/print/'
STATUS = {0: 'Nháp', 1: 'Đã duyệt', 2: 'Đã hủy'}
WATERMARK = {0: 'BẢN NHÁP', 2: 'ĐÃ HỦY'}
UNITS = {'Kg': 'kg', 'Litre': 'Lít', 'Nos': 'Cái', 'Tonne': 'Tấn', 'Gram': 'g', 'Millilitre': 'ml', 'Box': 'Hộp / thùng',
         'Pair': 'Đôi', 'Meter': 'Mét', 'Unit': 'Đơn vị', 'Hour': 'Giờ', 'Day': 'Ngày'}
DIGITS = ('không', 'một', 'hai', 'ba', 'bốn', 'năm', 'sáu', 'bảy', 'tám', 'chín')


def _float(value):
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    return number if number == number and abs(number) != float('inf') else 0.0


def number(value, decimals=3):
    """19500000 -> '19.500.000', 3.5 -> '3,5' (Vietnamese separators, trailing zeros dropped)."""
    text = format(_float(value), ',.' + str(decimals) + 'f')
    if decimals:
        text = text.rstrip('0').rstrip('.')
    return text.replace(',', '_').replace('.', ',').replace('_', '.')


def money(value, currency='VND'):
    if currency in ('VND', '', None):
        return number(round(_float(value)), 0) + ' ₫'
    return number(value, 2) + ' ' + currency


def unit(name):
    return UNITS.get(name, name or '')


def _as_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return value
    text = str(value).strip()
    return datetime.fromisoformat(text.replace(' ', 'T')[:19]) if len(text) > 10 else date.fromisoformat(text[:10])


def vn_date(value):
    day = _as_date(value)
    return day.strftime('%d/%m/%Y') if day else ''


def vn_datetime(value):
    moment = _as_date(value)
    if not moment:
        return ''
    return moment.strftime('%d/%m/%Y %H:%M') if isinstance(moment, datetime) else moment.strftime('%d/%m/%Y')


def _triple(value, full):
    """Read 0..999. `full` reads the hundreds even when zero (inner groups: 'không trăm linh năm')."""
    hundreds, tens, ones = value // 100, value // 10 % 10, value % 10
    words = []
    if full or hundreds:
        words += [DIGITS[hundreds], 'trăm']
    if tens == 0:
        if ones and (full or hundreds):
            words.append('linh')
    elif tens == 1:
        words.append('mười')
    else:
        words += [DIGITS[tens], 'mươi']
    if ones:
        words.append('mốt' if ones == 1 and tens >= 2 else 'lăm' if ones == 5 and tens >= 1 else DIGITS[ones])
    return words


def _words(value):
    if value == 0:
        return ['không']
    billions, rest = divmod(value, 1_000_000_000)
    words = _words(billions) + ['tỷ'] if billions else []
    started = bool(billions)
    for group, name in ((rest // 1_000_000, 'triệu'), (rest // 1000 % 1000, 'nghìn'), (rest % 1000, '')):
        if not group:
            continue
        words += _triple(group, started)
        if name:
            words.append(name)
        started = True
    return words


def number_in_words_vi(value):
    value = int(round(_float(value)))
    text = ' '.join(_words(abs(value)))
    return ('âm ' + text) if value < 0 else text


def amount_in_words_vi(value, currency='VND'):
    """19500000 -> 'Mười chín triệu năm trăm nghìn đồng chẵn.'"""
    text = number_in_words_vi(value) + (' đồng chẵn.' if currency in ('VND', '', None) else ' ' + currency + '.')
    return text[:1].upper() + text[1:]


def status_label(docstatus):
    return STATUS.get(int(docstatus or 0), '')


def watermark(docstatus):
    return WATERMARK.get(int(docstatus or 0))


def garden_label(raw):
    # Older Company settings may still say 'DỰ ÁN CHUỐI'; print uses the actual garden name.
    return re.sub(r'^\s*dự\s+án\s+chuối\b', 'VƯỜN CHUỐI', raw or '', flags=re.IGNORECASE)


# Frappe side -----------------------------------------------------------------------------------

_logo = None


def logo_data():
    global _logo
    if _logo is None:
        import frappe
        from base64 import b64encode
        from pathlib import Path
        path = Path(frappe.get_app_path('lotus_farm', 'public', 'images', 'lotus-agritech-header-v2.png'))
        _logo = 'data:image/png;base64,' + b64encode(path.read_bytes()).decode('ascii')
    return _logo


def identity(company):
    import frappe
    values = frappe.get_cached_value('Company', company, ['company_name', 'lotus_print_farm', 'lotus_print_project'], as_dict=True) or {}
    return dict(logo=logo_data(), company=(values.get('company_name') or company or '').upper(),
                farm=values.get('lotus_print_farm') or '', project=garden_label(values.get('lotus_print_project')))


def page(company, title, number_, posting_date=None, docstatus=None, landscape=False, **extra):
    """Common context: identity, document block, printed by/at. Callers add info rows, body data and signatures."""
    import frappe
    from frappe.utils import now_datetime
    user = frappe.session.user
    printer = frappe.db.get_value('User', user, 'full_name') if user and user != 'Guest' else ''
    context = frappe._dict(identity=identity(company), title=title, number=number_, date=vn_date(posting_date),
                           status=status_label(docstatus) if docstatus is not None else '', watermark=watermark(docstatus) if docstatus is not None else None,
                           landscape=landscape, printed_at=vn_datetime(now_datetime()), printed_by=printer or user,
                           info=[], signatures=[], notes='', pdf_url='', back_url='', letterhead=False, desk=False,
                           fmt=frappe._dict(number=number, money=money, date=vn_date, datetime=vn_datetime, unit=unit, words=amount_in_words_vi))
    context.update(extra)
    return context


def signature(title, name='', image=None, signed_at=None, hint='(Ký, ghi rõ họ tên)'):
    return dict(title=title, name=name or '', image=image, signed_at=vn_datetime(signed_at) if signed_at else '', hint=hint)


_env = None


def _environment():
    """Own Jinja environment with autoescape: item names, notes and reasons are user text.

    Frappe's shared environment does not escape, so printing it raw would let markup through.
    """
    global _env
    if _env is None:
        from jinja2 import Environment
        from frappe.utils.jinja import get_jloader
        _env = Environment(loader=get_jloader(), autoescape=True, trim_blocks=True, lstrip_blocks=True)
    return _env


def render(body, p, shell='document.html'):
    """shell: document.html (web page / PDF) or desk.html (fragment inside the Desk print view). Returns safe HTML."""
    from markupsafe import Markup
    p.body = TEMPLATES + 'body/' + body
    return Markup(_environment().get_template(TEMPLATES + shell).render(p=p))


def pdf(html, landscape=False):
    from frappe.utils.pdf import get_pdf
    return get_pdf(html, options={'page-size': 'A4', 'orientation': 'Landscape' if landscape else 'Portrait',
                                  'margin-top': '12mm', 'margin-bottom': '16mm', 'margin-left': '12mm', 'margin-right': '12mm'})


def send_pdf(html, filename, landscape=False):
    import frappe
    frappe.local.response.filename = re.sub(r'[^A-Za-z0-9._-]+', '_', filename)[:100] + '.pdf'
    frappe.local.response.filecontent = pdf(html, landscape)
    frappe.local.response.type = 'pdf'
    frappe.local.response.display_content_as = 'attachment'
