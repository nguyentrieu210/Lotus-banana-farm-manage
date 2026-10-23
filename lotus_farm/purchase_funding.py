"""Personal funding and reimbursements. Only native, signed JEs affect the books."""
import frappe
from frappe.utils import flt, getdate
from lotus_farm import procurement_rules as rules
from lotus_farm.procurement import parse, document
from lotus_farm.controls import lock
from lotus_farm.finance import setup, posting, payments
from lotus_farm.procurement_setup import FUNDING_KEYS, check_funding_account, funding_accounts

DT = 'Lotus Purchase Funding'
JE = 'Journal Entry'
KINDS = ('PurchaseFunding', 'PurchaseReimbursement')


def _company(company):
    frappe.get_doc('Company', company).check_permission('read')
    if company != setup.company():
        frappe.throw('Chỉ ghi sổ cho công ty đã cấu hình tài chính.')


def snapshot(doc):
    return rules.digest({k: str(doc.get(k) or '') for k in ('company', 'supplier', 'posting_date', 'payer_type', 'payer',
        'classification', 'evidence', 'external_reference', 'duplicate_reason', 'notes', 'funding_account')} |
        {'amount':flt(doc.amount)} |
        {'allocations': [[a.reference_type, a.reference_name, flt(a.amount)] for a in doc.allocations]})


def validate(doc):
    setup.require_post()
    _company(doc.company)
    old = doc.get_doc_before_save()
    if old and (old.get('cancelled') or old.get('cancelled')!=doc.get('cancelled') or old.get('cancel_reason')!=doc.get('cancel_reason') or old.get('cancelled_voucher')!=doc.get('cancelled_voucher')):
        frappe.throw('Trạng thái hủy khoản chi hộ chỉ thay đổi qua Hủy phiếu chưa ghi sổ.')
    if old and old.journal_entry:
        if snapshot(old) != snapshot(doc) or old.journal_entry != doc.journal_entry:
            frappe.throw('Khoản chi hộ đã trình ký, không được sửa. Hủy bút toán trước và lập chứng từ thay thế.')
        return
    if (doc.journal_entry or doc.funding_account or doc.client_key or doc.payload_hash or doc.get('cancelled') or doc.get('cancel_reason')) and not doc.flags.get('procurement_write'):
        frappe.throw('Trình ký khoản chi hộ bằng chức năng Mua hàng.', frappe.PermissionError)
    if doc.payer_type not in ('Employee', 'Shareholder') or doc.classification not in ('Reimbursable', 'Equity'):
        frappe.throw('Chọn người chi và phân loại khoản chi hộ.')
    person = frappe.get_doc(doc.payer_type, doc.payer)
    if person.get('company') != doc.company:
        frappe.throw('Người chi hộ phải thuộc công ty của khoản mua.')
    if doc.payer_type == 'Employee' and person.status != 'Active':
        frappe.throw('Nhân viên chi hộ đã nghỉ việc.')
    file = frappe.db.get_value('File', {'file_url': doc.evidence, 'is_private': 1}, ['name', 'owner', 'attached_to_doctype', 'attached_to_name'], as_dict=True)
    if not file or not ((file.owner == frappe.session.user and not file.attached_to_name) or
                        (file.attached_to_doctype == DT and file.attached_to_name == doc.name)):
        frappe.throw('Đính kèm chứng từ gốc riêng tư của khoản chi hộ này.')
    if not doc.external_reference or not str(doc.notes or '').strip():
        frappe.throw('Cần số chứng từ và nội dung khoản chi hộ.')
    try:
        rules.number(doc.amount, 'Số tiền chi hộ', True)
    except ValueError as exc:
        frappe.throw(str(exc))
    if not doc.allocations or abs(sum(flt(a.amount) for a in doc.allocations)-flt(doc.amount)) > .5:
        frappe.throw('Tổng phân bổ phải bằng số tiền chi hộ.')
    seen = set()
    for a in doc.allocations:
        if a.reference_type not in ('Purchase Invoice', 'Purchase Order') or (a.reference_type, a.reference_name) in seen or flt(a.amount) <= 0:
            frappe.throw('Nguồn phân bổ bị trùng hoặc không hợp lệ.')
        seen.add((a.reference_type, a.reference_name))
        source = document(a.reference_type, a.reference_name, doc.company)
        if source.docstatus != 1 or source.supplier != doc.supplier or source.get('is_return'):
            frappe.throw('Nguồn mua phải đã xác nhận, cùng công ty và nhà cung cấp.')
        if getdate(doc.posting_date) < getdate(source.get('posting_date') or source.get('transaction_date')):
            frappe.throw('Ngày chi hộ không được trước ngày chứng từ nguồn.')
    doc.evidence_key = rules.evidence_key(doc.supplier, doc.external_reference, doc.posting_date, doc.amount)
    duplicate = frappe.db.get_value(DT, {'evidence_key': doc.evidence_key, 'name': ['!=', doc.name or '']}, 'name')
    if duplicate and not str(doc.duplicate_reason or '').strip():
        frappe.throw('Chứng từ có thể trùng '+duplicate+'. Kiểm tra và ghi rõ lý do nếu là khoản chi khác.')


def protect_delete(doc):
    if doc.journal_entry or doc.get('cancelled'):
        frappe.throw('Không xóa khoản chi hộ đã có bút toán; giữ chứng từ để đối chiếu.')


def _remaining_source(dt, name, exclude=None, lock_rows=True):
    d = frappe.get_doc(dt, name, for_update=lock_rows)
    if dt == 'Purchase Invoice':
        base = flt(d.outstanding_amount)
    else:
        base = max(0, flt(d.grand_total)-flt(d.advance_paid))
        if d.status in ('Closed', 'Cancelled', 'Stopped'):
            frappe.throw('Đơn mua đã dừng hoặc đóng.')
    held = flt(frappe.db.sql('''select sum(a.debit_in_account_currency-a.credit_in_account_currency)
        from `tabJournal Entry Account` a join `tabJournal Entry` j on j.name=a.parent
        where j.docstatus=0 and a.party_type='Supplier' and a.reference_type=%s and a.reference_name=%s
        and j.name!=%s'''+(' for update' if lock_rows else ''), (dt, name, exclude or ''))[0][0])
    held += flt(frappe.db.sql('''select sum(r.allocated_amount) from `tabPayment Entry Reference` r
        join `tabPayment Entry` p on p.name=r.parent where p.docstatus=0 and p.payment_type='Pay'
        and r.reference_doctype=%s and r.reference_name=%s and p.name!=%s'''+(' for update' if lock_rows else ''), (dt, name, exclude or ''))[0][0])
    return max(0, base-held)


@frappe.whitelist()
def options(company):
    setup.require_post()
    _company(company)
    return dict(employees=frappe.get_list('Employee', filters={'company': company, 'status': 'Active'}, fields=['name', 'employee_name'], limit_page_length=0),
        shareholders=frappe.get_list('Shareholder', filters={'company': company}, fields=['name', 'title'], limit_page_length=0)
            if frappe.has_permission('Shareholder', 'read') else [],
        mapping=funding_accounts(), is_chief=setup.is_chief(),
        accounts=frappe.get_list('Account', filters={'company': company, 'is_group': 0, 'disabled': 0, 'root_type': ['in', ['Liability', 'Equity']]},
            fields=['name', 'account_name', 'root_type', 'account_type'], limit_page_length=0),
        sources={dt: [dict(name=r.name, supplier=r.supplier, amount=_remaining_source(dt, r.name,lock_rows=False))
            for r in frappe.get_list(dt, filters={'company': company, 'docstatus': 1}, fields=['name', 'supplier'], limit_page_length=0)]
            for dt in ('Purchase Invoice', 'Purchase Order')})


@frappe.whitelist(methods=['POST'])
def save_accounts(company, mapping):
    setup.require_chief()
    _company(company)
    cfg = setup.settings()
    for key, value in parse(mapping).items():
        if key not in FUNDING_KEYS:
            frappe.throw('Tài khoản cấu hình không hợp lệ.')
        cfg.set('acct_'+key, value or None)
    # Validate any supplied mapping without requiring both optional mappings to be filled.
    cfg.flags.ignore_permissions = True
    cfg.save()
    for key in FUNDING_KEYS:
        if cfg.get('acct_'+key):
            check_funding_account(key, company)
    return options(company)


@frappe.whitelist(methods=['POST'])
def prepare(company, data, signers, client_key):
    setup.require_post()
    setup.require_enabled()
    _company(company)
    data = parse(data)
    lock('Company', company)
    token, fingerprint = rules.digest([frappe.session.user, client_key]), rules.digest(data)
    if not client_key:
        frappe.throw('Thiếu mã yêu cầu.')
    old = frappe.db.get_value(DT, {'client_key': token}, ['name', 'payload_hash', 'journal_entry'], as_dict=True, for_update=True)
    if old:
        document(DT, old.name, company, for_update=True)
        if old.payload_hash != fingerprint:
            frappe.throw('Mã yêu cầu đã sử dụng với nội dung khác.')
        if not old.journal_entry:
            frappe.throw('Phiếu chi hộ này đã hủy. Lập khoản chi hộ mới để trình ký lại.')
        return dict(name=old.name, voucher=old.journal_entry, doctype=JE)
    allowed = ('supplier', 'posting_date', 'payer_type', 'payer', 'classification', 'amount', 'evidence', 'external_reference', 'duplicate_reason', 'notes', 'allocations')
    d = frappe.get_doc(dict(doctype=DT, company=company, **{k: data.get(k) for k in allowed}))
    d.client_key, d.payload_hash = token, fingerprint
    d.flags.procurement_write = True
    d.insert()
    file = frappe.get_doc('File', {'file_url': d.evidence, 'is_private': 1})
    file.db_set(dict(attached_to_doctype=DT, attached_to_name=d.name))
    d.funding_account = check_funding_account('purchase_funding_liability' if d.classification == 'Reimbursable' else 'purchase_funding_equity', company)
    d.save()
    setup.check_cutover(d.posting_date)
    posting.check_open(company, d.posting_date, JE)
    accounts = []
    for a in sorted(d.allocations, key=lambda r: (r.reference_type, r.reference_name)):
        lock(a.reference_type, a.reference_name)
        if flt(a.amount) > _remaining_source(a.reference_type, a.reference_name)+.5:
            frappe.throw('Phân bổ vượt số còn trả của '+a.reference_name)
        accounts.append(dict(account=setup.mapping()['payable_supplier'], party_type='Supplier', party=d.supplier,
            reference_type=a.reference_type, reference_name=a.reference_name, debit_in_account_currency=a.amount,
            is_advance='Yes' if a.reference_type=='Purchase Order' else 'No'))
    accounts.append(dict(account=d.funding_account, credit_in_account_currency=d.amount))
    j = _journal(d, 'PurchaseFunding', d.posting_date, accounts, client_key)
    d.journal_entry = j.name
    d.save()
    return dict(name=d.name, **payments.start_signing(j, signers))


def _journal(funding, kind, date, accounts, key, reference=None):
    cc = frappe.get_cached_value('Company', funding.company, 'cost_center')
    for row in accounts:
        row['cost_center'] = cc
    j = frappe.get_doc(dict(doctype=JE, company=funding.company, voucher_type='Journal Entry', posting_date=date,
        user_remark=funding.notes, lotus_payment_kind=kind, lotus_purchase_funding=funding.name,
        lotus_funding_hash=snapshot(funding), lotus_procurement_key=rules.digest([frappe.session.user, kind, key]),
        lotus_procurement_hash=rules.digest([date, accounts, reference]), cheque_no=reference or None, cheque_date=date if reference else None,
        accounts=accounts))
    j.flags.ignore_permissions = True
    j.flags.procurement_write = True
    j.insert()
    return j


def reimbursement_balance(d, exclude=None, lock_rows=False):
    rows = frappe.db.sql('''select total_debit,docstatus from `tabJournal Entry` where lotus_purchase_funding=%s
        and lotus_payment_kind='PurchaseReimbursement' and docstatus<2 and name!=%s'''+(' for update' if lock_rows else ''),
        (d.name,exclude or ''),as_dict=True)
    posted = sum(flt(r.total_debit) for r in rows if r.docstatus == 1)
    held = sum(flt(r.total_debit) for r in rows if r.docstatus == 0)
    return dict(reimbursed=posted, reserved=held, remaining=max(0, flt(d.amount)-posted-held))


@frappe.whitelist(methods=['POST'])
def reimburse(name, amount, posting_date, mode, signers, client_key, reference_no=None):
    setup.require_post()
    setup.require_enabled()
    d = document(DT, name)
    _company(d.company)
    lock('Company', d.company)
    lock(DT, name)
    d.reload()
    token = rules.digest([frappe.session.user, 'PurchaseReimbursement', client_key])
    old = frappe.db.get_value(JE, {'lotus_procurement_key': token}, 'name', for_update=True)
    if old:
        j = document(JE, old, d.company, for_update=True)
        if j.lotus_purchase_funding != name or abs(flt(j.total_debit)-flt(amount))>.5 or str(j.posting_date)!=str(posting_date) or j.cheque_no!=(reference_no or None):
            frappe.throw('Mã hoàn ứng đã dùng với nội dung khác.')
        return dict(voucher=old, doctype=JE)
    if not client_key or d.classification != 'Reimbursable' or not d.journal_entry or frappe.db.get_value(JE, d.journal_entry, 'docstatus') != 1:
        frappe.throw('Chỉ hoàn khoản phải hoàn đã được ký và ghi sổ; không hoàn vốn góp.')
    if mode not in ('bank', 'cash') or mode == 'bank' and not reference_no:
        frappe.throw('Chọn tiền mặt/chuyển khoản; chuyển khoản cần số giao dịch.')
    if getdate(posting_date) < getdate(d.posting_date):
        frappe.throw('Ngày hoàn không trước ngày chi hộ.')
    setup.check_cutover(posting_date)
    posting.check_open(d.company, posting_date, JE)
    balance = reimbursement_balance(d, lock_rows=True)
    try:
        rules.remaining(d.amount, balance['reimbursed'], balance['reserved'], amount)
    except ValueError as exc:
        frappe.throw(str(exc))
    j = _journal(d, 'PurchaseReimbursement', posting_date, [dict(account=d.funding_account, debit_in_account_currency=flt(amount)),
        dict(account=setup.mapping()[mode], credit_in_account_currency=flt(amount))], client_key, reference_no)
    return payments.start_signing(j, signers)


@frappe.whitelist()
def list_funding(company):
    setup._login()
    _company(company)
    result = []
    for r in frappe.get_list(DT, filters={'company': company}, fields=['name'], limit_page_length=0, order_by='posting_date desc, name desc'):
        d = document(DT, r.name, company)
        j = frappe.db.get_value(JE, d.journal_entry, ['docstatus'], as_dict=True) if d.journal_entry else None
        result.append(dict(name=d.name, date=str(d.posting_date), supplier=d.supplier, payer_type=d.payer_type, payer=d.payer,
            classification=d.classification, amount=flt(d.amount), journal_entry=d.journal_entry,
            status='Đã hủy' if d.get('cancelled') or j and j.docstatus==2 else 'Đã ghi sổ' if j and j.docstatus==1 else 'Chờ ký',
            evidence=d.evidence, external_reference=d.external_reference, allocations=[a.as_dict() for a in d.allocations],
            **reimbursement_balance(d)))
    return result


def cancel_voucher(voucher, reason):
    d=document(DT,voucher.lotus_purchase_funding)
    _company(d.company)
    if not str(reason or '').strip():frappe.throw('Nhập lý do hủy phiếu chưa ghi sổ.')
    lock('Company',d.company)
    lock(DT,d.name)
    lock(JE,voucher.name)
    voucher.reload()
    if voucher.docstatus!=0:frappe.throw('Chỉ hủy phiếu chưa ghi sổ.')
    if voucher.lotus_payment_kind=='PurchaseFunding':
        if d.journal_entry!=voucher.name:frappe.throw('Bút toán không khớp khoản chi hộ.')
        frappe.db.set_value(DT,d.name,dict(journal_entry=None,cancelled=1,cancel_reason=str(reason)[:500],cancelled_voucher=voucher.name))
    d.add_comment('Info','Hủy phiếu nháp '+voucher.name+': '+str(reason)[:500])
    posting.drop_draft(voucher)
    return dict(state='Deleted',funding=d.name)


def native_guard(doc, method=None):
    """Funding links cannot be forged or relabelled through generic ERPNext REST."""
    if doc.doctype != JE:
        return
    old = doc.get_doc_before_save()
    old_kind = old.get('lotus_payment_kind') if old else None
    if old_kind in KINDS and (doc.get('lotus_payment_kind') != old_kind or doc.get('lotus_purchase_funding') != old.get('lotus_purchase_funding')):
        frappe.throw('Không đổi loại hoặc nguồn bút toán chi hộ.')
    if doc.get('lotus_payment_kind') not in KINDS and not doc.get('lotus_purchase_funding'):
        return
    if doc.is_new() and not doc.flags.get('procurement_write'):
        frappe.throw('Lập bút toán chi hộ/hoàn ứng từ Mua hàng.', frappe.PermissionError)
    d = frappe.get_doc(DT, doc.lotus_purchase_funding, for_update=True)
    lock('Company', d.company)
    lock(DT, d.name)
    if doc.company != d.company or doc.lotus_funding_hash != snapshot(d) or doc.lotus_payment_kind not in KINDS:
        frappe.throw('Bút toán không khớp khoản chi hộ đã trình ký.')
    if method == 'before_cancel' and doc.lotus_payment_kind == 'PurchaseFunding':
        if any(reimbursement_balance(d).values()):
            rows = frappe.db.exists(JE, {'lotus_purchase_funding': d.name, 'lotus_payment_kind': 'PurchaseReimbursement', 'docstatus': ['<', 2]})
            if rows:
                frappe.throw('Hủy các phiếu hoàn ứng trước khi hủy khoản chi hộ.')
    if method != 'before_submit':
        return
    if doc.lotus_payment_kind == 'PurchaseFunding':
        if doc.name != d.journal_entry:
            frappe.throw('Khoản chi hộ đã gắn bút toán khác.')
        expected = [(a.reference_type, a.reference_name, flt(a.amount)) for a in d.allocations]
        actual = [(a.reference_type, a.reference_name, flt(a.debit_in_account_currency)) for a in doc.accounts if a.party_type == 'Supplier' and a.party == d.supplier and a.account == setup.mapping()['payable_supplier'] and not flt(a.credit_in_account_currency)]
        if sorted(expected) != sorted(actual) or len(doc.accounts) != len(expected)+1:
            frappe.throw('Các phân bổ bút toán chi hộ không khớp chứng từ nguồn.')
        credit = [a for a in doc.accounts if a.account == d.funding_account and flt(a.credit_in_account_currency) == flt(d.amount) and not flt(a.debit_in_account_currency)]
        if len(credit) != 1:
            frappe.throw('Tài khoản nguồn tiền chi hộ không khớp.')
        for a in d.allocations:
            lock(a.reference_type, a.reference_name)
            if flt(a.amount) > _remaining_source(a.reference_type, a.reference_name, doc.name)+.5:
                frappe.throw('Số còn trả đã đổi. Trả lại phiếu chi hộ để lập lại.')
    else:
        balance = reimbursement_balance(d, doc.name, lock_rows=True)
        if d.classification != 'Reimbursable' or frappe.db.get_value(JE, d.journal_entry, 'docstatus') != 1:
            frappe.throw('Khoản chi hộ không đủ điều kiện hoàn.')
        if flt(doc.total_debit) > balance['remaining']+.5 or len(doc.accounts) != 2:
            frappe.throw('Hoàn ứng vượt số còn lại.')
        debit = [a for a in doc.accounts if a.account == d.funding_account and flt(a.debit_in_account_currency) == flt(doc.total_debit) and not flt(a.credit_in_account_currency)]
        credit = [a for a in doc.accounts if a.account in (setup.mapping()['cash'], setup.mapping()['bank']) and flt(a.credit_in_account_currency) == flt(doc.total_debit) and not flt(a.debit_in_account_currency)]
        if len(debit) != 1 or len(credit) != 1:
            frappe.throw('Tài khoản hoàn ứng không khớp.')
