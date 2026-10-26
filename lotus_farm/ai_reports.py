"""Fast, fresh, permission-aware answers for unambiguous first-turn lookups.

The caller supplies the same validated query tool the model uses. Follow-ups remain
with the model so a previous garden/date scope is never silently discarded.
"""
import datetime
import re
import unicodedata
from decimal import Decimal


def normalize(value):
    value = unicodedata.normalize('NFD', str(value).lower().replace('đ', 'd'))
    value = ''.join(c for c in value if unicodedata.category(c) != 'Mn')
    return ' '.join(re.sub(r'[^a-z0-9 ]', ' ', value).split())


QUESTIONS = {
    'inventory': {'ton kho hien tai o tung kho vat tu nao sap het', 'ton kho hien tai o cac kho la bao nhieu',
                  'ton kho hien tai', 'xem ton kho hien tai', 'vat tu nao sap het'},
    'employees': {'co bao nhieu nhan vien dang lam viec', 'co bao nhieu nhan vien dang lam viec o moi vuon',
                  'hien co bao nhieu nhan vien dang lam viec', 'tong so nhan vien dang lam viec', 'so nhan vien hien tai'},
    'orders': {'don mua nao dang cho nhan hang', 'don mua nao chua nhan du hang'},
    'expenses': {'chi phi thang nay theo tai khoan la bao nhieu', 'chi phi thang nay la bao nhieu'},
    'attendance': {'hom nay co bao nhieu nhan vien di lam', 'nhan vien di lam hom nay'},
}


def _amount(value):
    return Decimal(str(value or 0))


def _number(value, places=3):
    text = format(_amount(value), f',.{places}f')
    if places:
        text = text.rstrip('0').rstrip('.')
    return text.replace(',', '_').replace('.', ',').replace('_', '.')


def _cell(value):
    return str(value if value is not None else '').replace('|', '/').replace('\n', ' ').replace('\r', ' ')


def _table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '|' + '---|' * len(headers)] +
                     ['| ' + ' | '.join(_cell(value) for value in row) + ' |' for row in rows])


def answer(history, query, today):
    if len(history) != 1 or history[0].get('role') != 'user':
        return None
    question = normalize(history[0]['content'])
    kind = next((name for name, questions in QUESTIONS.items() if question in questions), None)
    if not kind:
        return None
    steps = []

    def read(doctype, fields, filters=None, **kwargs):
        result = query(doctype, fields, filters=filters, **kwargs)
        steps.append({'tool': 'query', 'doctype': doctype, 'rows': len(result['rows'])})
        return result['rows']

    if kind == 'employees':
        if 'moi vuon' in question:
            rows = read('Employee', ['lotus_farm', 'count(name) as total'], [['status', '=', 'Active']],
                        group_by='lotus_farm', order_by='total desc', limit=500)
            total = sum(int(r['total'] or 0) for r in rows)
            text = f'Có **{"ít nhất " if len(rows) == 500 else ""}{_number(total, 0)} nhân viên đang làm việc** (trạng thái Active).\n\n'
            text += _table(['Vườn', 'Nhân viên'], [(r['lotus_farm'] or 'Chưa gán vườn', _number(r['total'], 0)) for r in rows])
        else:
            rows = read('Employee', ['count(name) as total'], [['status', '=', 'Active']])
            text = f'Có **{_number(rows[0]["total"], 0)} nhân viên đang làm việc** (trạng thái Active).'
        text += '\n\nNguồn: Employee, status = Active, theo quyền tài khoản.'
    elif kind == 'attendance':
        rows = read('Attendance', ['employee'], [['attendance_date', '=', today], ['docstatus', '=', 1],
                    ['status', 'in', ['Present', 'Half Day', 'Work From Home']]], group_by='employee', order_by='employee asc', limit=500)
        count = len(rows)
        if count:
            text = f'Hôm nay ({today[8:10]}/{today[5:7]}/{today[:4]}) có **{"ít nhất " if count == 500 else ""}{count} nhân viên** có chấm công đã duyệt: có mặt, nửa ngày hoặc làm việc từ xa.'
        else:
            text = 'Hôm nay chưa có chấm công đã duyệt ghi nhận nhân viên đi làm. Điều này không đồng nghĩa không có người đang làm việc.'
        text += '\n\nNguồn: Attendance, ngày hôm nay, docstatus = 1; mỗi nhân viên chỉ đếm một lần.'
    elif kind == 'orders':
        filters = [['docstatus', '=', 1], ['per_received', '<', 100], ['status', 'not in', ['Closed', 'Stopped', 'Cancelled']]]
        total = int(read('Purchase Order', ['count(name) as total'], filters)[0]['total'] or 0)
        rows = read('Purchase Order', ['name', 'supplier_name', 'schedule_date', 'per_received'], filters,
                    order_by='schedule_date asc', limit=30)
        text = f'Có **{total} đơn mua đang chờ nhận đủ hàng** trong phạm vi bạn được xem.'
        if rows:
            text += '\n\n' + _table(['Đơn mua', 'Nhà cung cấp', 'Hẹn nhận', 'Đã nhận'],
                [(r['name'], r['supplier_name'], str(r['schedule_date'] or ''), _number(r['per_received']) + '%') for r in rows])
        if total > len(rows):
            text += f'\n\nHiển thị {len(rows)}/{total} đơn; có thể hỏi theo nhà cung cấp hoặc kỳ nhận.'
        text += '\n\nNguồn: Purchase Order đã duyệt, nhận dưới 100%, chưa đóng/dừng/hủy.'
    elif kind == 'inventory':
        rows = read('Bin', ['warehouse', 'item_code', 'stock_uom', 'actual_qty'], order_by='warehouse asc', limit=500)
        capped = len(rows) == 500
        codes = sorted({r['item_code'] for r in rows})
        items = read('Item', ['name', 'item_name', 'lotus_minimum_stock_global'], [['name', 'in', codes]], limit=500) if codes else []
        details = {r['name']: r for r in items}
        warehouses = sorted({r['warehouse'] for r in rows})
        stores = {r['name']: r['company'] for r in read('Warehouse', ['name', 'company'],
                  [['name', 'in', warehouses]], limit=500)} if warehouses else {}
        # Do not expose a Bin row whose linked item is outside the readable Item set.
        rows = [r for r in rows if r['item_code'] in details and r['warehouse'] in stores]
        visible = rows[:30]
        text = '**Tồn kho hiện tại theo vật tư và kho bạn được xem**\n\n'
        text += _table(['Kho', 'Vật tư', 'ĐVT', 'Tồn'],
            [(r['warehouse'], details[r['item_code']]['item_name'], r['stock_uom'], _number(r['actual_qty'])) for r in visible]) if rows else 'Không có dữ liệu tồn kho trong phạm vi được xem.'
        if len(rows) > len(visible):
            text += f'\n\nHiển thị {len(visible)}/{"ít nhất " if capped else ""}{len(rows)} dòng.'
        totals = {}
        units = {}
        for row in rows:
            key = (stores[row['warehouse']], row['item_code'])
            totals[key] = totals.get(key, Decimal(0)) + _amount(row['actual_qty'])
            units[key] = row['stock_uom']
        low = [key for key, total in totals.items() if _amount(details[key[1]]['lotus_minimum_stock_global']) > 0
               and total <= _amount(details[key[1]]['lotus_minimum_stock_global'])] if not capped else []
        if low:
            text += '\n\n**Tồn trong các kho được xem không vượt ngưỡng tối thiểu đã cấu hình**\n\n'
            text += _table(['Công ty', 'Vật tư', 'ĐVT', 'Tồn', 'Tối thiểu'], [(key[0], details[key[1]]['item_name'], units[key], _number(totals[key]),
                _number(details[key[1]]['lotus_minimum_stock_global'])) for key in low[:15]])
        elif capped:
            text += '\n\nDữ liệu đã đạt giới hạn 500 dòng; chưa kết luận mức tồn tối thiểu. Hãy chọn một kho hoặc vật tư để xem đủ dữ liệu.'
        else:
            text += '\n\nKhông có vật tư nằm dưới ngưỡng tối thiểu trong dữ liệu được xem, hoặc vật tư chưa được cấu hình ngưỡng.'
        empty = [r for r in rows if _amount(r['actual_qty']) <= 0]
        if empty:
            text += '\n\n**Vật tư hết hàng hoặc tồn âm tại kho**\n\n' + _table(['Kho', 'Vật tư', 'Tồn'],
                [(r['warehouse'], details[r['item_code']]['item_name'], _number(r['actual_qty'])) for r in empty[:10]])
        text += '\n\nNguồn: Bin và Item; ngưỡng tồn áp dụng trong các kho bạn được xem. Không cộng các đơn vị khác nhau thành một tổng.'
    else:
        day = datetime.date.fromisoformat(today)
        first = day.replace(day=1).isoformat()
        accounts = read('Account', ['name', 'account_name', 'company'], [['root_type', '=', 'Expense'], ['is_group', '=', 0]], limit=500)
        names = {r['name']: r for r in accounts}
        rows = read('GL Entry', ['account', 'sum(debit) as debit', 'sum(credit) as credit'],
                    [['account', 'in', list(names)], ['is_cancelled', '=', 0], ['posting_date', 'between', [first, today]]],
                    group_by='account', order_by='account asc', limit=500) if names else []
        companies = sorted({r['company'] for r in accounts})
        currencies = {r['name']: r['default_currency'] for r in read('Company', ['name', 'default_currency'],
                      [['name', 'in', companies]], limit=500)} if companies else {}
        values = [(r, _amount(r['debit']) - _amount(r['credit'])) for r in rows]
        values = [(r, net) for r, net in values if net]
        text = f'**Chi phí theo tài khoản từ 01/{today[5:7]}/{today[:4]} đến {today[8:10]}/{today[5:7]}/{today[:4]}** (phát sinh Nợ − Có):'
        if values:
            text += '\n\n' + _table(['Công ty', 'Tài khoản', 'Chi phí', 'Tiền tệ'],
                [(names[r['account']]['company'], names[r['account']]['account_name'], _number(net, 2),
                  currencies.get(names[r['account']]['company'], 'Theo công ty')) for r, net in values[:30]])
            if len(values) > 30:
                text += f'\n\nHiển thị 30/{len(values)} tài khoản có phát sinh.'
        else:
            text += '\n\nChưa có chi phí phát sinh trong các tài khoản và kỳ bạn được xem.'
        if len(accounts) == 500:
            text += '\n\nDanh mục đã đạt giới hạn 500 tài khoản; báo cáo này chỉ phản ánh các tài khoản đã đọc.'
        text += '\n\nNguồn: GL Entry không hủy; Account loại Expense. Không cộng tiền khác công ty/tiền tệ thành một tổng.'
    return {'answer': text, 'steps': steps, 'route': 'direct'}
