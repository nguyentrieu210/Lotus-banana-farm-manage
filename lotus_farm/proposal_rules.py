"""Signing chain of a purchase proposal (Phiếu đề xuất mua vật tư), pure and unit-tested.

Four signatures in order, as on the farm's Excel form: proposer, head of department,
accounting / purchasing, director. The director's signature approves the request.
"""
STEPS = (
    dict(action='PROPOSE', title='Người đề xuất', roles=()),
    dict(action='DEPARTMENT', title='Phụ trách bộ phận', roles=('Lotus Farm Manager', 'Lotus Field Supervisor', 'Lotus Warehouse Manager')),
    dict(action='PURCHASING', title='Phòng Kế toán / Mua hàng', roles=('Lotus Purchasing Buyer', 'Purchase Manager', 'Accounts User', 'Accounts Manager')),
    dict(action='APPROVE', title='Giám đốc phê duyệt', roles=('Lotus Purchase Approver',)),
)
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


def may_sign(step, roles, is_owner, is_admin=False):
    if step is None:
        return False
    if is_admin:
        return True
    if step == 0:
        return is_owner
    return bool(set(STEPS[step]['roles']) & set(roles))


def editable(state, step_roles_match=False):
    """Lines can be changed while drafting/returned; purchasing may still set prices and suppliers."""
    if state in (None, '', DRAFT, RETURNED):
        return 'all'
    if state == WAITING[1] and step_roles_match:
        return 'prices'
    return None


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
