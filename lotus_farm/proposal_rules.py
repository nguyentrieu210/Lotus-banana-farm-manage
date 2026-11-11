"""Signing chain of a purchase proposal (Phiếu đề xuất mua vật tư), pure and unit-tested.

Four signatures in order, as on the farm's Excel form: proposer, head of department,
accounting / purchasing, director. The director's signature approves the request.
A fully priced proposal under SMALL_LIMIT needs only the proposer and the head of department.
"""
from lotus_farm.signing_rules import chain as _chain

# Who signs each step is picked by name when sending (lotus_farm.signing).
STEPS = tuple(dict(action=s['key'], title=s['title'], roles=s['roles']) for s in _chain('purchase_proposal')['steps'])
CHAINS = ('purchase_proposal', 'purchase_proposal_small')
SMALL_LIMIT = 20_000_000
DRAFT = 'Nháp'
RETURNED = 'Trả lại'
APPROVED = 'Đã duyệt'
WAITING = ('Chờ phụ trách bộ phận', 'Chờ kế toán / mua hàng', 'Chờ giám đốc duyệt')
STATES = (DRAFT, *WAITING, APPROVED, RETURNED)


# Stages of the proposal board (spec 003, FR-026/FR-030), computed, never stored. "Chờ tôi ký" is a filter.
STAGE_DRAFT, STAGE_SIGNING, STAGE_RETURNED = 'Nháp', 'Đang ký', 'Bị trả lại'
STAGE_TO_BUY, STAGE_BUYING, STAGE_RECEIVED, STAGE_DONE, STAGE_CANCELLED = 'Chờ mua', 'Đang mua', 'Đã nhận đủ', 'Đã xong', 'Đã hủy'
STAGES = (STAGE_DRAFT, STAGE_SIGNING, STAGE_RETURNED, STAGE_TO_BUY, STAGE_BUYING, STAGE_RECEIVED, STAGE_DONE, STAGE_CANCELLED)
_EPS = 1e-6


def _qty(row, key):
    try:
        value = float(row.get(key) or 0)
    except (TypeError, ValueError):
        return 0.0
    return value if value == value else 0.0


def stage(docstatus, state, lines):
    """Board stage of one proposal.

    docstatus: 0 draft, 1 signed (submitted), 2 cancelled. state: lotus_proposal_state of a draft.
    lines: one dict per proposal line in stock units, independent of who is looking:
      qty, ordered (every order line, drafts included), received, returned, billed,
      closed (unreceived part of closed orders + unordered part once the proposal is stopped).
    A line is settled when received - returned + closed covers qty. All settled: Đã nhận đủ, and
    Đã xong once every received quantity is invoiced. Otherwise Đang mua as soon as any order exists."""
    if docstatus == 2:
        return STAGE_CANCELLED
    if docstatus != 1:
        if state == RETURNED:
            return STAGE_RETURNED
        if state in WAITING:
            return STAGE_SIGNING
        return STAGE_DRAFT
    lines = list(lines or [])
    net = [(_qty(r, 'received') - _qty(r, 'returned'), r) for r in lines]
    if lines and all(got + _qty(r, 'closed') >= _qty(r, 'qty') - _EPS for got, r in net):
        billed = all(_qty(r, 'billed') >= got - _EPS for got, r in net)
        return STAGE_DONE if billed else STAGE_RECEIVED
    if any(_qty(r, 'ordered') > _EPS for r in lines):
        return STAGE_BUYING
    return STAGE_TO_BUY


def current_step(state):
    """Index of the signature the proposal is waiting for, or None when approved."""
    if state in (None, '', DRAFT, RETURNED):
        return 0
    if state in WAITING:
        return WAITING.index(state) + 1
    return None


def state_after(step):
    return WAITING[step] if step < len(WAITING) else APPROVED


def editable(state, step_roles_match=False):
    """Lines can be changed while drafting/returned; purchasing may still set prices and suppliers."""
    if state in (None, '', DRAFT, RETURNED):
        return 'all'
    if state == WAITING[1] and step_roles_match:
        return 'prices'
    return None


def chain_for_lines(rows):
    """Two signatures when every line is priced and the total is under SMALL_LIMIT; otherwise all four."""
    total, priced = 0.0, bool(rows)
    for row in rows or []:
        try:
            qty, rate = float(row.get('qty') or 0), float(row.get('rate') or 0)
        except (TypeError, ValueError):
            qty, rate = 0.0, 0.0
        if not rate > 0:
            priced = False
        total += qty * rate
    return 'purchase_proposal_small' if priced and total < SMALL_LIMIT else 'purchase_proposal'


def line_issues(rows):
    issues = []
    for index, row in enumerate(rows, start=1):
        if not row.get('item_code'):
            issues.append('Dòng %d: chọn vật tư' % index)
        try:
            qty = float(row.get('qty') or 0)
        except (TypeError, ValueError):
            qty = 0
        if not qty > 0:
            issues.append('Dòng %d: số lượng đề xuất phải lớn hơn 0' % index)
        if not row.get('schedule_date'):
            issues.append('Dòng %d: chọn thời gian cần hàng' % index)
        try:
            rate = float(row.get('rate') or 0)
        except (TypeError, ValueError):
            rate = -1
        if rate < 0 or rate != rate:
            issues.append('Dòng %d: đơn giá không hợp lệ' % index)
    return issues
