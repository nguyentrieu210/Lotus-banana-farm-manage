"""Tài chính – Kế toán: Vietnamese voucher names and a line of description for every ledger voucher.

ERPNext writes "Accounting Entry for Stock" (or nothing) as the remark of stock vouchers and leaves journal remarks to the
user. The books need a real diễn giải, so it is built from the voucher itself: what moved, how much, for which lot,
from / to which warehouse, which supplier or customer, and the note typed on the document when there is one.
"""
import frappe
from frappe.utils import flt

VOUCHER_LABELS = {
    'Stock Entry': 'Phiếu kho', 'Stock Reconciliation': 'Phiếu kiểm kê', 'Journal Entry': 'Phiếu kế toán', 'Purchase Invoice': 'Hóa đơn mua',
    'Sales Invoice': 'Hóa đơn bán', 'Payment Entry': 'Phiếu thu / chi', 'Purchase Receipt': 'Phiếu nhận hàng', 'Delivery Note': 'Phiếu giao hàng',
    'Period Closing Voucher': 'Kết chuyển cuối năm', 'Asset': 'Tài sản cố định', 'Asset Capitalization': 'Ghi tăng tài sản', 'Landed Cost Voucher': 'Chi phí mua hàng',
}
STOCK_LABELS = {'Material Receipt': 'Phiếu nhập kho', 'Material Issue': 'Phiếu xuất kho', 'Material Transfer': 'Phiếu chuyển kho', 'Repack': 'Phiếu đóng gói',
                'Manufacture': 'Phiếu sản xuất', 'Material Consumption for Manufacture': 'Phiếu xuất tiêu hao'}
JE_KINDS = {'Salary': 'Phiếu chi lương', 'Advance': 'Phiếu tạm ứng lương', 'Statutory': 'Phiếu nộp BH, thuế', 'Closing': 'Kết chuyển chi phí',
            'Result': 'Kết chuyển kết quả kinh doanh'}
EMPTY = ('', 'accounting entry for stock', 'no remarks', 'not applicable')


def unit(uom):
    from lotus_farm.units import label
    return label(uom)


def _note(text):
    text = str(text or '').strip().split('\n')[0]
    return '' if text.lower() in EMPTY else text[:160]


def _qty(value):
    """Vietnamese number: 100.000 / 2,5"""
    value = round(flt(value), 3)
    whole, _, frac = ('%.3f' % value).rstrip('0').rstrip('.').partition('.')
    whole = format(int(whole), ',').replace(',', '.')
    return whole + (',' + frac if frac else '')


def _items(rows, limit=3):
    parts = ['%s %s %s' % (r.item_name or r.item_code, _qty(r.qty), unit(r.uom or r.stock_uom)) for r in rows[:limit]]
    return ', '.join(parts) + (' và %d dòng khác' % (len(rows) - limit) if len(rows) > limit else '')


def vouchers(pairs):
    """pairs: iterable of (voucher_type, voucher_no) -> {voucher_no: dict(label, description)}."""
    by_type = {}
    for vt, vn in pairs:
        by_type.setdefault(vt, set()).add(vn)
    out = {}
    blocks = {b.name: b.block_code for b in frappe.get_all('Farm Block', fields=['name', 'block_code'], limit_page_length=0)}
    farm_names = {f.name: f.farm_name or f.name for f in frappe.get_all('Farm', fields=['name', 'farm_name'], limit_page_length=0)}
    for vt, names in by_type.items():
        names = list(names)
        label = VOUCHER_LABELS.get(vt, vt)
        if vt == 'Stock Entry':
            heads = {e.name: e for e in frappe.get_all('Stock Entry', filters={'name': ['in', names]},
                                                     fields=['name', 'stock_entry_type', 'remarks', 'lotus_supplier'] if frappe.get_meta('Stock Entry').has_field('lotus_supplier')
                                                     else ['name', 'stock_entry_type', 'remarks'])}
            rows = {}
            for r in frappe.get_all('Stock Entry Detail', filters={'parent': ['in', names]},
                                    fields=['parent', 'item_code', 'item_name', 'qty', 'uom', 'stock_uom', 's_warehouse', 't_warehouse', 'lotus_farm_block', 'lotus_farm'],
                                    order_by='idx', limit_page_length=0):
                rows.setdefault(r.parent, []).append(r)
            suppliers = {s.name: s.supplier_name for s in frappe.get_all('Supplier', filters={'name': ['in', [h.get('lotus_supplier') for h in heads.values()
                                                                                                                if h.get('lotus_supplier')] or ['']]},
                                                                         fields=['name', 'supplier_name'])}
            for n in names:
                h, items = heads.get(n), rows.get(n, [])
                if not h:
                    continue
                kind = STOCK_LABELS.get(h.stock_entry_type, 'Phiếu kho')
                text = _items(items)
                if h.stock_entry_type == 'Material Issue':
                    lots = sorted({blocks.get(r.lotus_farm_block, r.lotus_farm_block) for r in items if r.lotus_farm_block})
                    farms = sorted({r.lotus_farm for r in items if r.lotus_farm and not r.lotus_farm_block})
                    if lots:
                        text += ' cho lô ' + ', '.join(lots)
                    elif farms:
                        text += ' cho ' + ', '.join(farm_names.get(f, f) for f in farms)
                elif h.stock_entry_type == 'Material Transfer' and items:
                    text += ': %s → %s' % (items[0].s_warehouse, items[0].t_warehouse)
                elif h.stock_entry_type == 'Material Receipt' and items:
                    text += ' vào ' + (items[0].t_warehouse or '')
                supplier = suppliers.get(h.get('lotus_supplier')) if h.get('lotus_supplier') else ''
                note = _note(h.remarks)
                out[n] = dict(label=kind, description='%s: %s%s%s' % (kind, text, (' — ' + supplier) if supplier else '', (' — ' + note) if note else ''))
        elif vt == 'Stock Reconciliation':
            meta = frappe.get_meta('Stock Reconciliation')
            heads = {e.name: e for e in frappe.get_all('Stock Reconciliation', filters={'name': ['in', names]},
                                                     fields=['name', 'purpose'] + [f for f in ('remarks',) if meta.has_field(f)])}
            rows = {}
            for r in frappe.db.sql("""select d.parent, d.item_code, i.item_name, d.qty, i.stock_uom uom, i.stock_uom from `tabStock Reconciliation Item` d
                    join tabItem i on i.name=d.item_code where d.parent in %s order by d.idx""", (tuple(names),), as_dict=True):
                rows.setdefault(r.parent, []).append(r)
            for n in names:
                h = heads.get(n)
                if not h:
                    continue
                kind = 'Phiếu tồn đầu kỳ' if h.purpose == 'Opening Stock' else 'Phiếu kiểm kê'
                note = _note(h.get('remarks'))
                out[n] = dict(label=kind, description='%s: %s%s' % (kind, _items(rows.get(n, [])), (' — ' + note) if note else ''))
        elif vt == 'Journal Entry':
            fields = ['name', 'user_remark', 'remark', 'voucher_type'] + (['lotus_payment_kind'] if frappe.get_meta('Journal Entry').has_field('lotus_payment_kind') else [])
            for j in frappe.get_all('Journal Entry', filters={'name': ['in', names]}, fields=fields):
                kind = JE_KINDS.get(j.get('lotus_payment_kind')) or ('Phiếu chi / báo nợ ngân hàng' if j.voucher_type == 'Bank Entry' else 'Phiếu kế toán')
                out[j.name] = dict(label=kind, description=_note(j.user_remark) or _note(j.remark) or kind)
        elif vt == 'Purchase Invoice':
            for p in frappe.get_all('Purchase Invoice', filters={'name': ['in', names]}, fields=['name', 'bill_no', 'supplier_name', 'remarks']):
                out[p.name] = dict(label=label, description='Hóa đơn mua %s — %s%s' % (p.bill_no or p.name, p.supplier_name or '',
                                                                                   (' — ' + _note(p.remarks)) if _note(p.remarks) else ''))
        elif vt == 'Sales Invoice':
            has = frappe.get_meta('Sales Invoice').has_field('lotus_einvoice_no')
            for s in frappe.get_all('Sales Invoice', filters={'name': ['in', names]},
                                    fields=['name', 'customer_name', 'remarks'] + (['lotus_einvoice_series', 'lotus_einvoice_no'] if has else [])):
                number = ' '.join(x for x in (s.get('lotus_einvoice_series'), s.get('lotus_einvoice_no')) if x) or s.name
                out[s.name] = dict(label=label, description='Hóa đơn bán %s — %s' % (number, s.customer_name or ''))
        elif vt == 'Payment Entry':
            for p in frappe.get_all('Payment Entry', filters={'name': ['in', names]}, fields=['name', 'payment_type', 'party_name', 'party', 'reference_no', 'remarks']):
                kind = 'Phiếu thu' if p.payment_type == 'Receive' else 'Phiếu chi' if p.payment_type == 'Pay' else 'Phiếu chuyển tiền'
                ref = (' — số ' + p.reference_no) if p.reference_no else ''
                out[p.name] = dict(label=kind, description='%s %s%s' % ('Thu tiền' if p.payment_type == 'Receive' else 'Trả tiền', p.party_name or p.party or '', ref))
        elif vt == 'Purchase Receipt':
            for p in frappe.get_all('Purchase Receipt', filters={'name': ['in', names]}, fields=['name', 'supplier_name']):
                out[p.name] = dict(label=label, description='Nhận hàng từ ' + (p.supplier_name or ''))
        for n in names:
            out.setdefault(n, dict(label=label, description=label + ' ' + n))
    return out
