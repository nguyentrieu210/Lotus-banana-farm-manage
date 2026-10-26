"""Đọc chứng từ mua hàng bằng AI (Groq): báo giá, hóa đơn, phiếu giao hàng, đơn đặt hàng → gợi ý nhà cung cấp và dòng hàng.

The browser uploads a private File; read() sends the image (or the PDF's text) to the model, parses the JSON answer and
matches supplier / items / units against Lotus masters. Nothing is saved: the form is only pre-filled for the user to check.
API keys live in site_config (groq_api_key, then groq_api_key_backup), never in the repository.
"""
import base64
import difflib
import io
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.request

import frappe
from frappe.utils import getdate

API = 'https://api.groq.com/openai/v1/chat/completions'
MODEL = 'qwen/qwen3.8-27b'
IMAGES = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_BYTES = 10 * 1024 * 1024
HOURLY_LIMIT = 60
PROMPT = """Bạn đọc chứng từ mua hàng của một doanh nghiệp trồng chuối ở Việt Nam (báo giá, hóa đơn GTGT, phiếu giao hàng, đơn đặt hàng).
Chỉ trả về MỘT đối tượng JSON, không giải thích, theo đúng mẫu:
{"document_type":"quote|invoice|delivery_note|purchase_order|other","document_no":"","date":"YYYY-MM-DD","supplier":{"name":"","tax_id":"","phone":"","address":""},"lines":[{"name":"","qty":0,"uom":"","rate":0,"amount":0,"vat_percent":null}],"subtotal":0,"vat_amount":0,"total":0,"notes":""}
Quy tắc:
- Số viết kiểu Việt Nam phải đổi sang số JSON: 850.000 → 850000; 1,5 → 1.5.
- supplier là bên BÁN (người lập báo giá/hóa đơn), không phải bên mua.
- rate là đơn giá chưa VAT nếu chứng từ có; nếu chỉ có đơn giá đã gồm VAT thì ghi đơn giá đó và nêu trong notes.
- uom giữ nguyên chữ trên chứng từ (bao, kg, chai, lít, can, thùng, cái…).
- Không bịa dòng hay con số; ô không đọc được để "" hoặc null."""


def _require_access():
    if frappe.session.user == 'Guest':
        frappe.throw('Vui lòng đăng nhập.', frappe.AuthenticationError)
    if not any(frappe.has_permission(dt, 'create') for dt in ('Purchase Order', 'Supplier Quotation', 'Material Request', 'Stock Entry', 'Purchase Receipt')):
        frappe.throw('Bạn cần quyền lập chứng từ mua hàng hoặc phiếu kho để dùng AI đọc chứng từ.', frappe.PermissionError)
    key = 'lotus-document-ai:' + frappe.session.user
    used = int(frappe.cache().get_value(key) or 0)
    if used >= HOURLY_LIMIT:
        frappe.throw(f'Đã dùng AI đọc chứng từ {HOURLY_LIMIT} lần trong giờ này; thử lại sau.')
    frappe.cache().set_value(key, used + 1, expires_in_sec=3600)


def _file(file_url):
    file = frappe.get_doc('File', {'file_url': file_url})
    if file.owner != frappe.session.user:
        frappe.throw('Chỉ đọc được tệp do chính bạn vừa tải lên.', frappe.PermissionError)
    ext = os.path.splitext(file.file_name or file_url)[1].lower()
    if ext not in IMAGES | {'.pdf'}:
        frappe.throw('AI chỉ đọc được ảnh (JPG, PNG, WEBP) hoặc PDF.')
    content = file.get_content()
    if isinstance(content, str):
        content = content.encode()
    if len(content) > MAX_BYTES:
        frappe.throw('Tệp quá lớn (tối đa 10 MB).')
    return ext, content


def _image_part(data):
    from PIL import Image, ImageOps
    image = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert('RGB')
    image.thumbnail((2000, 2000))
    out = io.BytesIO()
    image.save(out, 'JPEG', quality=85)
    return {'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' + base64.b64encode(out.getvalue()).decode()}}


def _content(ext, data):
    if ext in IMAGES:
        return [{'type': 'text', 'text': PROMPT}, _image_part(data)]
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    text = '\n'.join((page.extract_text() or '') for page in reader.pages[:4]).strip()
    if len(text) >= 60:
        return [{'type': 'text', 'text': PROMPT + '\n\nNội dung chứng từ (chữ trích từ PDF):\n' + text[:15000]}]
    images = [img.data for page in reader.pages[:1] for img in page.images]
    if not images:
        frappe.throw('PDF không có chữ hay ảnh đọc được; hãy chụp ảnh chứng từ rồi tải lên.')
    return [{'type': 'text', 'text': PROMPT}, _image_part(max(images, key=len))]


def _keys():
    """Primary key first, then backups: groq_api_key, groq_api_key_backup, or a groq_api_keys list in site_config."""
    keys = [frappe.conf.get('groq_api_key'), frappe.conf.get('groq_api_key_backup'), *(frappe.conf.get('groq_api_keys') or [])]
    return [k for i, k in enumerate(keys) if k and k not in keys[:i]]


def _call(key, body):
    request = urllib.request.Request(API, data=body, headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json', 'User-Agent': 'lotus-farm'})
    # Connection resets / TLS EOF happen now and then on the farm uplink: retry twice before giving up on this key.
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.load(response)['choices'][0]['message']['content'] or ''
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(1.5 * (attempt + 1))


def _ask(content):
    keys = _keys()
    if not keys:
        frappe.throw('Chưa cấu hình khóa AI trên máy chủ (groq_api_key).')
    body = json.dumps({'model': MODEL, 'messages': [{'role': 'user', 'content': content}], 'temperature': 0, 'max_tokens': 3000}).encode()
    status = None
    # Fall back to the next key when one is rate-limited, rejected, or the provider/network fails for it.
    for index, key in enumerate(keys):
        try:
            answer = _call(key, body)
            break
        except urllib.error.HTTPError as exc:
            status = exc.code
            frappe.log_error(title='Lotus document AI', message=f'Key {index + 1}/{len(keys)} HTTP {status}: {exc.read()[:500]!r}')
            if status not in (401, 403, 408, 429) and status < 500:
                frappe.throw(f'AI không đọc được chứng từ (lỗi {status}).')
        except Exception:
            status = None
            frappe.log_error(title='Lotus document AI', message=f'Key {index + 1}/{len(keys)}: {frappe.get_traceback()}')
    else:
        frappe.throw('AI đang quá tải, thử lại sau ít phút.' if status == 429 else 'Không kết nối được dịch vụ AI; thử lại sau.')
    answer = re.sub(r'<think>.*?</think>', '', answer, flags=re.S)
    start, end = answer.find('{'), answer.rfind('}')
    try:
        return json.loads(answer[start:end + 1])
    except Exception:
        frappe.throw('AI trả kết quả không đúng định dạng; hãy chụp lại rõ hơn rồi thử lại.')


def _norm(value):
    text = unicodedata.normalize('NFD', str(value or '')).replace('đ', 'd').replace('Đ', 'D')
    text = ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn').lower()
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', text).split())


def _score(a, b):
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return 0.0
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    ta, tb = set(a.split()), set(b.split())
    overlap = len(ta & tb) / max(len(ta), len(tb))
    contained = 0.9 if (a in b or b in a) and min(len(a), len(b)) >= 4 else 0
    return round(max(ratio, overlap, contained), 3)


COMPANY_WORDS = {'cong', 'ty', 'tnhh', 'co', 'phan', 'cp', 'cty', 'mtv', 'sx', 'tm', 'dv', 'xnk', 'thuong', 'mai', 'san', 'xuat', 'dich', 'vu',
                 'mot', 'thanh', 'vien', 'hai', 'tu', 'doanh', 'nghiep', 'dntn', 'ho', 'kinh', 'hkd', 'chi', 'nhanh', 'va', 'company', 'ltd', 'jsc'}


def _company_core(name):
    """Supplier name without legal-form words, so 'Công ty TNHH …' prefixes do not make two companies look alike."""
    return ' '.join(word for word in _norm(name).split() if word not in COMPANY_WORDS)


def _number(value):
    if isinstance(value, (int, float)):
        return float(value)
    text = re.sub(r'[^0-9,.-]', '', str(value or ''))
    if not text:
        return None
    if ',' in text and '.' in text:
        text = text.replace('.', '').replace(',', '.')
    elif text.count('.') > 1 or re.fullmatch(r'-?\d{1,3}(\.\d{3})+', text):
        text = text.replace('.', '')
    else:
        text = text.replace(',', '.')
    try:
        return float(text)
    except ValueError:
        return None


UNIT_WORDS = {'bao': 'bao', 'bag': 'bao', 'kg': 'kg', 'kilogram': 'kg', 'ki lo': 'kg', 'lit': 'litre', 'l': 'litre', 'liter': 'litre', 'litre': 'litre',
              'chai': 'chai', 'can': 'can', 'thung': 'thung', 'cai': 'nos', 'chiec': 'nos', 'bo': 'set', 'goi': 'goi', 'tan': 'tonne', 'tấn': 'tonne', 'cuon': 'roll', 'm': 'meter', 'met': 'meter'}


def _unit(text, allowed):
    word = _norm(text)
    word = UNIT_WORDS.get(word, word)
    for uom in allowed:
        if _norm(uom) == word or UNIT_WORDS.get(_norm(uom)) == word:
            return uom
    return None


@frappe.whitelist(methods=['POST'])
def read(file_url):
    _require_access()
    ext, data = _file(file_url)
    found = _ask(_content(ext, data))
    suppliers = frappe.get_all('Supplier', filters={'disabled': 0}, fields=['name', 'supplier_name', 'tax_id'], limit_page_length=0)
    items = frappe.get_all('Item', filters={'disabled': 0}, fields=['name', 'item_name', 'stock_uom'], limit_page_length=0)
    conversions = {}
    for row in frappe.get_all('UOM Conversion Detail', filters={'parenttype': 'Item'}, fields=['parent', 'uom'], limit_page_length=0):
        conversions.setdefault(row.parent, set()).add(row.uom)

    supplier = found.get('supplier') or {}
    tax = re.sub(r'\D', '', str(supplier.get('tax_id') or ''))
    match = next((s for s in suppliers if tax and re.sub(r'\D', '', s.tax_id or '') == tax), None)
    score = 1.0 if match else 0
    if not match and _company_core(supplier.get('name')):
        best = max(suppliers, key=lambda s: _score(_company_core(supplier['name']), _company_core(s.supplier_name)), default=None)
        best_score = _score(_company_core(supplier['name']), _company_core(best.supplier_name)) if best else 0
        if best_score >= 0.75:
            match, score = best, best_score

    lines, warnings = [], []
    for raw in (found.get('lines') or [])[:100]:
        name = str(raw.get('name') or '').strip()
        if not name:
            continue
        ranked = sorted(((max(_score(name, i.item_name), _score(name, i.name)), i) for i in items), key=lambda pair: -pair[0])[:3]
        best_score, best = ranked[0] if ranked else (0, None)
        item = best if best_score >= 0.62 else None
        units = ({item.stock_uom} | conversions.get(item.name, set())) if item else set()
        uom = _unit(raw.get('uom'), sorted(units)) if item else None
        if item and raw.get('uom') and not uom:
            warnings.append(f'"{name}": đơn vị "{raw.get("uom")}" chưa khai báo quy đổi cho {item.item_name}; đang để đơn vị gốc {item.stock_uom}.')
        lines.append(dict(text=name, qty=_number(raw.get('qty')), uom_text=raw.get('uom') or '', uom=uom or (item.stock_uom if item else ''),
                          rate=_number(raw.get('rate')), amount=_number(raw.get('amount')), vat_percent=_number(raw.get('vat_percent')),
                          item=dict(code=item.name, label=item.item_name, score=best_score) if item else None,
                          candidates=[dict(code=i.name, label=i.item_name, score=s) for s, i in ranked if s >= 0.4]))
    unmatched = sum(1 for line in lines if not line['item'])
    if unmatched:
        warnings.append(f'{unmatched} dòng chưa khớp vật tư trong danh mục: chọn vật tư hoặc thêm mặt hàng mới.')
    if supplier.get('name') and not match:
        warnings.append(f'Chưa có nhà cung cấp "{supplier.get("name")}" trong danh mục.')
    try:
        date = str(getdate(found.get('date'))) if found.get('date') else None
    except Exception:
        date = None
    return dict(
        document=dict(type=found.get('document_type') or 'other', number=found.get('document_no') or '', date=date,
                      subtotal=_number(found.get('subtotal')), vat_amount=_number(found.get('vat_amount')), total=_number(found.get('total')), notes=found.get('notes') or ''),
        supplier=dict(text=supplier.get('name') or '', tax_id=supplier.get('tax_id') or '', phone=supplier.get('phone') or '', address=supplier.get('address') or '',
                      match=dict(name=match.name, label=match.supplier_name, score=score) if match else None),
        lines=lines, warnings=warnings, model=MODEL)
