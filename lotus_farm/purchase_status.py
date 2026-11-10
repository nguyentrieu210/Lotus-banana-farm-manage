"""One status vocabulary for purchase documents (spec 003, FR-003), pure and unit-tested.

Every screen (Kho, Mua hàng, Tài chính, phone and desktop) and every print shows these names. They are
computed from the ERPNext documents, never stored. Proposal stages live in lotus_farm.proposal_rules.
frontend/src/purchase-status.js mirrors the names and adds display tones.
"""
EPS = 1e-6

# Purchase Order
ORDER_DRAFT, ORDER_PENDING, ORDER_RETURNED = 'Nháp', 'Chờ duyệt', 'Bị trả lại'
ORDER_APPROVED, ORDER_SENT, ORDER_CONFIRMED = 'Đã duyệt', 'Đã gửi NCC', 'NCC đã xác nhận'
ORDER_RECEIVING, ORDER_RECEIVED, ORDER_CLOSED, ORDER_CANCELLED = 'Đang nhận', 'Đã nhận đủ', 'Đã đóng', 'Đã hủy'
ORDER_STATES = (ORDER_DRAFT, ORDER_PENDING, ORDER_RETURNED, ORDER_APPROVED, ORDER_SENT, ORDER_CONFIRMED,
                ORDER_RECEIVING, ORDER_RECEIVED, ORDER_CLOSED, ORDER_CANCELLED)
# Stored lotus_approval_status values of a draft order (older data says Từ chối for a returned order).
APPROVAL_PENDING, APPROVAL_RETURNED = 'Chờ duyệt', ('Từ chối', 'Bị trả lại', 'Trả lại')

# Purchase Receipt / Mua nhanh receipt
RECEIPT_DRAFT, RECEIPT_POSTED, RECEIPT_CANCELLED = 'Nháp', 'Đã nhập kho', 'Đã hủy'
RECEIPT_STATES = (RECEIPT_DRAFT, RECEIPT_POSTED, RECEIPT_CANCELLED)
BILL_NONE, BILL_PART, BILL_FULL = 'Chưa có hóa đơn', 'Có hóa đơn một phần', 'Đã có hóa đơn'
BILLING_STATES = (BILL_NONE, BILL_PART, BILL_FULL)
QUICK_PURCHASE = 'Mua nhanh'

# Purchase Invoice
INVOICE_DRAFT, INVOICE_UNPAID, INVOICE_PARTLY = 'Nháp', 'Chưa trả', 'Trả một phần'
INVOICE_PAID, INVOICE_OVERDUE, INVOICE_CANCELLED = 'Đã trả', 'Quá hạn', 'Đã hủy'
INVOICE_STATES = (INVOICE_UNPAID, INVOICE_PARTLY, INVOICE_PAID, INVOICE_OVERDUE, INVOICE_CANCELLED)

# Payment voucher (Payment Entry / Journal Entry on the payment_voucher chain)
VOUCHER_DRAFT, VOUCHER_SIGNING, VOUCHER_RETURNED = 'Nháp', 'Đang ký', 'Bị trả lại'
VOUCHER_PAID, VOUCHER_REVERSED = 'Đã chi', 'Đã đảo'
VOUCHER_STATES = (VOUCHER_DRAFT, VOUCHER_SIGNING, VOUCHER_RETURNED, VOUCHER_PAID, VOUCHER_REVERSED)

# Supplier Quotation
QUOTE_DRAFT, QUOTE_CONFIRMED, QUOTE_CHOSEN, QUOTE_CANCELLED = 'Nháp', 'Đã xác nhận', 'Đã chọn', 'Đã hủy'
QUOTE_STATES = (QUOTE_DRAFT, QUOTE_CONFIRMED, QUOTE_CHOSEN, QUOTE_CANCELLED)


def _num(value):
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    return number if number == number else 0.0


def order_state(docstatus, approval='', status='', sent=False, confirmed=False, ordered=0, received=0):
    """Purchase order status. docstatus 0/1/2; approval = lotus_approval_status; status = ERPNext status;
    ordered / received in the same unit (stock qty). Order of precedence after approval: closed, fully
    received, receiving, supplier confirmed, sent to supplier, approved."""
    if docstatus == 2:
        return ORDER_CANCELLED
    if docstatus == 0:
        if approval == APPROVAL_PENDING:
            return ORDER_PENDING
        if approval in APPROVAL_RETURNED:
            return ORDER_RETURNED
        return ORDER_DRAFT
    ordered, received = _num(ordered), _num(received)
    if status == 'Closed':
        return ORDER_CLOSED
    if status in ('Completed', 'Delivered') or (ordered > EPS and received >= ordered - EPS):
        return ORDER_RECEIVED
    if received > EPS:
        return ORDER_RECEIVING
    if confirmed:
        return ORDER_CONFIRMED
    if sent:
        return ORDER_SENT
    return ORDER_APPROVED


def order_overdue(docstatus, status, schedule_date, today, ordered=0, received=0):
    """Late delivery is a flag beside the status, not a status of its own."""
    if docstatus != 1 or status in ('Closed', 'Completed', 'Delivered') or not schedule_date or not today:
        return False
    return _num(received) < _num(ordered) - EPS and str(schedule_date)[:10] < str(today)[:10]


def receipt_state(docstatus):
    return {0: RECEIPT_DRAFT, 1: RECEIPT_POSTED, 2: RECEIPT_CANCELLED}.get(docstatus, RECEIPT_DRAFT)


def billing_state(per_billed=0, invoiced=False):
    """per_billed: ERPNext percentage on Purchase Receipt; invoiced: a Mua nhanh receipt linked to an invoice."""
    if invoiced or _num(per_billed) >= 99.99:
        return BILL_FULL
    if _num(per_billed) > EPS:
        return BILL_PART
    return BILL_NONE


def invoice_state(docstatus, grand_total, outstanding, due_date=None, as_of=None):
    """Overdue takes precedence while money is still owed; a fully paid invoice is never overdue."""
    if docstatus == 2:
        return INVOICE_CANCELLED
    if docstatus == 0:
        return INVOICE_DRAFT
    # A debit note (trả hàng) has negative amounts: what the supplier still owes back reads the same way.
    total, left = abs(_num(grand_total)), abs(_num(outstanding))
    if left <= 0.5:  # under half a đồng: settled
        return INVOICE_PAID
    if due_date and as_of and str(due_date)[:10] < str(as_of)[:10]:
        return INVOICE_OVERDUE
    if left < total - 0.5:
        return INVOICE_PARTLY
    return INVOICE_UNPAID


def voucher_state(docstatus, round_started=False, returned=False):
    if docstatus == 2:
        return VOUCHER_REVERSED
    if docstatus == 1:
        return VOUCHER_PAID
    if returned:
        return VOUCHER_RETURNED
    if round_started:
        return VOUCHER_SIGNING
    return VOUCHER_DRAFT


def quote_state(docstatus, chosen=False):
    if docstatus == 2:
        return QUOTE_CANCELLED
    if docstatus == 0:
        return QUOTE_DRAFT
    return QUOTE_CHOSEN if chosen else QUOTE_CONFIRMED
