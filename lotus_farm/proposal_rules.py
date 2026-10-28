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
