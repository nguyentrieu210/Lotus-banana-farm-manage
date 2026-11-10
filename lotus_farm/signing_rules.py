"""Named-signer chains for Lotus documents (pure, unit-tested in tests/test_signing_rules.py).

Every chain is an ordered list of steps. The first step is the person who prepares the document and
signs when sending it. Every later step is assigned to one named person, picked when the chain starts
from employees whose login has one of the step's roles. Only that person may sign, return or hand the
step to someone else; they are notified when their turn comes.
"""
PURCHASE_APPROVER = ('Lotus Purchase Approver',)
HEADS = ('Lotus Farm Manager', 'Lotus Field Supervisor', 'Lotus Warehouse Manager', 'Lotus Team Leader')
PURCHASING = ('Lotus Purchasing Buyer', 'Lotus Accountant', 'Lotus Chief Accountant', 'Purchase Manager', 'Accounts User', 'Accounts Manager')
STOREKEEPERS = ('Lotus Warehouse Manager', 'Lotus Stock Reviewer', 'Stock Manager', 'Lotus Warehouse Receiver')
HR = ('HR Manager', 'HR User')
DIRECTORS = ('Lotus Purchase Approver', 'Lotus Farm Manager')
CHIEF_ACCOUNTANTS = ('Lotus Chief Accountant', 'Accounts Manager')


def _step(key, title, roles=()):
    return dict(key=key, title=title, roles=tuple(roles))


CHAINS = {
    # gate=True: the last signature completes the document (submit / approve / close the period).
    'purchase_proposal': dict(app='buying', gate=True, label='Phiếu đề xuất mua vật tư', steps=(
        _step('PROPOSE', 'Người đề xuất'), _step('DEPARTMENT', 'Phụ trách bộ phận', HEADS),
        _step('PURCHASING', 'Phòng Kế toán / Mua hàng', PURCHASING), _step('APPROVE', 'Giám đốc phê duyệt', PURCHASE_APPROVER))),
    # Fully priced proposals under proposal_rules.SMALL_LIMIT: proposer and head of department only.
    'purchase_proposal_small': dict(app='buying', gate=True, label='Phiếu đề xuất mua vật tư', variant_of='purchase_proposal', steps=(
        _step('PROPOSE', 'Người đề xuất'), _step('DEPARTMENT', 'Phụ trách bộ phận', HEADS))),
    'issue_proposal': dict(app='warehouse', gate=False, label='Phiếu đề xuất cấp vật tư', steps=(
        _step('PROPOSE', 'Người đề xuất'), _step('DEPARTMENT', 'Phụ trách bộ phận', HEADS),
        _step('STOREKEEPER', 'Thủ kho', STOREKEEPERS), _step('APPROVE', 'Giám đốc NT / Người phê duyệt', DIRECTORS))),
    'purchase_order': dict(app='buying', gate=True, label='Đơn mua hàng', steps=(
        _step('PREPARE', 'Người lập đơn'), _step('APPROVE', 'Người duyệt mua', PURCHASE_APPROVER))),
    # Phiếu nhập kho theo đơn (spec 003, FR-043): confirming the receipt is the storekeeper's signature. The person
    # delivering has no Lotus account: they sign on the screen or on the delivery note photographed with the receipt.
    'purchase_receipt': dict(app='warehouse', gate=True, label='Phiếu nhập kho theo đơn', steps=(
        _step('STOREKEEPER', 'Thủ kho nhận hàng'),)),
    'stock_document': dict(app='warehouse', gate=False, label='Phiếu kho', steps=(
        _step('PREPARE', 'Người lập phiếu'), _step('HANDOVER', 'Người giao / nhận', ()),
        _step('STOREKEEPER', 'Thủ kho / người kiểm tra', STOREKEEPERS))),
    'timekeeping_period': dict(app='hr', gate=True, label='Bảng công & bảng lương', steps=(
        _step('PREPARE', 'Người lập'), _step('HR', 'Phụ trách nhân sự', HR), _step('APPROVE', 'Giám đốc', DIRECTORS))),
    # Phiếu chi / ủy nhiệm chi (trả nhà cung cấp, chi lương): the last signature submits the voucher.
    'payment_voucher': dict(app='finance', gate=True, label='Phiếu chi', steps=(
        _step('PREPARE', 'Kế toán lập phiếu'), _step('CHIEF', 'Kế toán trưởng', CHIEF_ACCOUNTANTS), _step('APPROVE', 'Giám đốc duyệt chi', DIRECTORS))),
}

WAITING, SIGNED, RETURNED, PENDING = 'Chờ ký', 'Đã ký', 'Trả lại', 'Chưa đến lượt'

# The step whose signer checked the content; their ký nháy is printed on every page of the signed copy.
CHECKER_STEPS = {'purchase_proposal': 2, 'purchase_order': 0, 'payment_voucher': 1}


def checker_step(key):
    return CHECKER_STEPS.get(key)

# Phone apps (PWA) that can show a signing alert, with their root path. A chain whose own app is not a
# phone app (payment vouchers live in the desktop Finance app) is announced in the fallback app.
PHONE_APPS = {'buying': '/buying', 'warehouse': '/warehouse', 'work': '/work', 'hr': '/hr-mobile'}
FALLBACK_APP = {'finance': 'buying'}


def notify_app(chain_app, device_apps):
    """The phone app that carries a signing alert for one signer.

    The chain's own app (or its fallback) when the signer has a phone subscribed there or has no phone
    at all (the alert still waits in that app's bell); otherwise the app they last used with a phone,
    so the push actually reaches them. device_apps is ordered most recently used first."""
    devices = [app for app in device_apps if app in PHONE_APPS]
    home = chain_app if chain_app in PHONE_APPS else FALLBACK_APP.get(chain_app)
    if home and (home in devices or not devices):
        return home
    return devices[0] if devices else home


def sign_link(app, doctype, name):
    """Link inside a phone app that opens the signing sheet of one document."""
    from urllib.parse import urlencode
    return PHONE_APPS[app] + '?' + urlencode({'sign_dt': doctype, 'sign_dn': name})


def push_link(app, link, doctype, name):
    """Keep a chain's own link when it already points inside the chosen phone app; otherwise open the
    document's signing sheet in that app. Push targets must stay inside the app that shows them."""
    from urllib.parse import urlsplit
    if urlsplit(link).path == PHONE_APPS[app]:
        return link
    return sign_link(app, doctype, name)
# Fields of a line that define what was signed (quantities, prices, places); labels and notes may change.
LINE_FIELDS = ('item_code', 'qty', 'uom', 'rate', 'amount', 'warehouse', 's_warehouse', 't_warehouse', 'schedule_date')


def chain(key):
    if key not in CHAINS:
        raise KeyError('Không có quy trình ký ' + str(key))
    return CHAINS[key]


def eligible(step, roles):
    """A step without roles accepts any active employee with a login (e.g. the person handing goods over)."""
    return not step['roles'] or bool(set(step['roles']) & set(roles))


def validate_assignment(key, signers, roles_of, owner):
    """signers: {step_key: user} for every step after the first. roles_of(user) -> roles. Returns issues."""
    issues = []
    for step in chain(key)['steps'][1:]:
        user = (signers or {}).get(step['key'])
        if not user:
            issues.append('Chọn người ký: ' + step['title'])
        elif not eligible(step, roles_of(user)):
            issues.append(step['title'] + ': người được chọn không có quyền ký bước này')
    return issues


def current(rows):
    """rows: sign requests of the latest round in step order -> index waiting for a signature, or None."""
    for index, row in enumerate(rows):
        if row['state'] != SIGNED:
            return index
    return None


def after_sign(rows, index):
    """New states after rows[index] signs: that step signed, the next one waiting. Returns (states, done)."""
    states = [row['state'] for row in rows]
    states[index] = SIGNED
    if index + 1 < len(states):
        states[index + 1] = WAITING
        return states, False
    return states, True


def may_act(rows, index, user, is_admin=False):
    """Only the named assignee of the waiting step (or Administrator) acts on it."""
    if index is None or index >= len(rows) or rows[index]['state'] != WAITING:
        return False
    return is_admin or rows[index]['assignee'] == user


def fingerprint(header, lines):
    """SHA-256 of what was signed: header values and each line's LINE_FIELDS, numbers rounded to 6 places."""
    import hashlib
    import json

    def norm(value):
        if isinstance(value, float):
            return round(value, 6)
        return value if isinstance(value, (int, str)) or value is None else str(value)
    payload = dict(header={k: norm(v) for k, v in sorted((header or {}).items())},
                   lines=[[norm((line or {}).get(field)) for field in LINE_FIELDS] for line in (lines or [])])
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def verify_token(secret, doctype, name, round_):
    """Unguessable, reproducible token for the QR link of one signing round."""
    import hashlib
    import hmac
    message = '%s|%s|%s' % (doctype, name, int(round_))
    return hmac.new(str(secret).encode(), message.encode(), hashlib.sha256).hexdigest()[:40]


def verdict(states, content_matches, cancelled=False):
    """Plain status for the public verify page."""
    if cancelled:
        return 'Chứng từ đã hủy — không còn hiệu lực'
    if RETURNED in states:
        return 'Đã bị trả lại — bản in này không còn hiệu lực'
    if not content_matches:
        return 'Nội dung đã thay đổi sau khi ký — không khớp bản đã ký'
    if states and all(s == SIGNED for s in states):
        return 'Đã ký đủ'
    return 'Đang trình ký (%d/%d chữ ký)' % (sum(1 for s in states if s == SIGNED), len(states))
