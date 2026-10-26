"""Private, membership-scoped Lotus direct/group messaging. Files never become public."""
import hashlib
import json
import mimetypes
import os
import time
from urllib.parse import quote

import frappe
from frappe.utils import cint, now_datetime

ROOM = 'Lotus Chat Room'
MEMBER = 'Lotus Chat Member'
MESSAGE = 'Lotus Chat Message'
MAX_BYTES = 20 * 1024 * 1024
RATE_LIMIT, RATE_WINDOW = 20, 10          # messages per user per seconds
RECALL_HOURS = 24
# A recalled message keeps its row (sequence, sender, time) but loses its content. The DocType has no flag column and
# this release adds no schema, so the marker lives in file_type, which is never a real MIME type with this prefix.
RECALLED = 'lotus/recalled'
PUSH_COOLDOWN = 30                        # seconds between pushes for one room to one person
EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.pdf', '.doc', '.docx', '.xls', '.xlsx',
              '.csv', '.tsv', '.ppt', '.pptx', '.txt', '.zip', '.rar', '.7z', '.mp4', '.mov', '.mp3', '.wav', '.m4a'}


def _user():
    user = frappe.session.user
    if user == 'Guest':
        frappe.throw('Vui lòng đăng nhập để chat.', frappe.AuthenticationError)
    enabled, kind = frappe.db.get_value('User', user, ['enabled', 'user_type']) or (0, '')
    if not enabled or kind != 'System User':
        frappe.throw('Chat nội bộ dành cho tài khoản nhân viên Lotus.', frappe.PermissionError)
    return user


def _member(room, user=None):
    return frappe.db.get_value(MEMBER, {'parent': room, 'parenttype': ROOM, 'user': user or frappe.session.user},
                               ['name', 'last_read_seq'], as_dict=True)


def _room(name, lock=False):
    _user()
    if not _member(name):
        frappe.throw('Bạn không phải thành viên cuộc trò chuyện này.', frappe.PermissionError)
    if lock:
        frappe.db.sql('select name from `tabLotus Chat Room` where name=%s for update', (name,))
    return frappe.get_doc(ROOM, name)


def permission(doc, ptype=None, user=None, **kwargs):
    if ptype not in ('read', 'select'):
        return False
    user = user or frappe.session.user
    if user == 'Guest' or not frappe.db.get_value('User', user, 'enabled'):
        return False
    room = doc.name if doc.doctype == ROOM else (doc.parent if doc.doctype == MEMBER else doc.room)
    return bool(_member(room, user))


def room_query(user=None):
    return _membership_condition('`tabLotus Chat Room`.name', user)


def message_query(user=None):
    return _membership_condition('`tabLotus Chat Message`.room', user)


def member_query(user=None):
    return _membership_condition('`tabLotus Chat Member`.parent', user)


def _membership_condition(column, user=None):
    value = frappe.db.escape(user or frappe.session.user)
    return f"exists (select 1 from `tabLotus Chat Member` cm where cm.parent={column} and cm.parenttype='{ROOM}' and cm.user={value})"


def _label(user):
    return frappe.get_cached_value('User', user, 'full_name') or user


def _online(user):
    return bool(frappe.cache().get_value('lotus-chat-online:' + user))


def _notify(room, kind, **values):
    event = {'room': room.name, 'kind': kind, **values}
    for row in room.members:
        frappe.publish_realtime('lotus_chat', event, user=row.user, after_commit=kind != 'typing')


def _room_dict(room):
    user = frappe.session.user
    others = [m.user for m in room.members if m.user != user]
    me = next(m for m in room.members if m.user == user)
    owner = room.owner if getattr(room, 'owner', None) else ''
    return {'name': room.name, 'kind': room.kind,
            'title': _label(others[0]) if room.kind == 'Direct' and others else room.title,
            'members': [{'user': m.user, 'label': _label(m.user), 'online': _online(m.user),
                         'last_read_seq': m.last_read_seq or 0} for m in room.members],
            'last_seq': room.last_seq or 0, 'unread': max(0, (room.last_seq or 0) - (me.last_read_seq or 0)),
            'preview': room.last_preview or '', 'last_activity': room.last_activity or room.creation,
            'owner': owner, 'is_owner': owner == user}


def _message_dict(row):
    result = {key: row.get(key) for key in ('name', 'room', 'seq', 'sender', 'body', 'creation')}
    result['sender_name'] = _label(row.sender)
    if row.get('file_type') == RECALLED:
        result.update(body='', recalled=True)
        return result
    if row.file_url:
        url = '/api/method/lotus_farm.chat.download?message=' + quote(row.name, safe='')
        result['file'] = {'name': row.file_name, 'size': row.file_size, 'url': url,
                          'image': row.file_type in ('image/jpeg', 'image/png', 'image/gif', 'image/webp'),
                          'preview_url': url + '&inline=1'}
    return result


@frappe.whitelist()
def inbox():
    user = _user()
    frappe.cache().set_value('lotus-chat-online:' + user, 1, expires_in_sec=70)
    names = frappe.get_all(MEMBER, filters={'user': user, 'parenttype': ROOM}, pluck='parent')
    rows = {r.name: r for r in frappe.get_all(ROOM, filters={'name': ['in', names or ['']]}, limit_page_length=0,
                                              fields=['name', 'kind', 'title', 'last_seq', 'last_preview', 'last_activity', 'creation', 'owner'])}
    members = {}
    for m in frappe.get_all(MEMBER, filters={'parent': ['in', names or ['']], 'parenttype': ROOM}, fields=['parent', 'user', 'last_read_seq'],
                            order_by='idx asc', limit_page_length=0):
        members.setdefault(m.parent, []).append(m)
    rooms = []
    for name in names:
        if name in rows:
            room = rows[name]
            room.members = members.get(name, [])
            rooms.append(_room_dict(room))
    rooms.sort(key=lambda r: str(r['last_activity'] or ''), reverse=True)
    return {'rooms': rooms, 'unread': sum(r['unread'] for r in rooms), 'site': frappe.local.site}


@frappe.whitelist()
def people(search=''):
    _user()
    search = str(search or '').strip()[:80]
    rows = frappe.get_all('User', filters={'enabled': 1, 'user_type': 'System User', 'name': ['!=', frappe.session.user]},
                          or_filters=[['full_name', 'like', '%' + search + '%'], ['name', 'like', '%' + search + '%']],
                          fields=['name', 'full_name'], order_by='full_name asc', limit_page_length=100)
    return [{'user': r.name, 'label': r.full_name or r.name, 'online': _online(r.name)} for r in rows if r.name != 'Guest']


@frappe.whitelist(methods=['POST'])
def create(members, title='', kind='Direct'):
    user = _user()
    if isinstance(members, str):
        members = frappe.parse_json(members)
    if not isinstance(members, list) or any(not isinstance(m, str) for m in members):
        frappe.throw('Danh sách thành viên không hợp lệ.')
    users = sorted(set([user, *members]))
    title = str(title or '').strip()
    if kind not in ('Direct', 'Group') or not 2 <= len(users) <= 50 or (kind == 'Direct' and len(users) != 2):
        frappe.throw('Chọn một người để chat riêng hoặc tối đa 50 người cho nhóm.')
    if kind == 'Group' and not 1 <= len(title) <= 80:
        frappe.throw('Nhập tên nhóm, tối đa 80 ký tự.')
    for member in users:
        enabled, user_type = frappe.db.get_value('User', member, ['enabled', 'user_type']) or (0, '')
        if not enabled or user_type != 'System User':
            frappe.throw('Thành viên phải là tài khoản nhân viên đang hoạt động.')
    direct_key = hashlib.sha256(json.dumps(users).encode()).hexdigest() if kind == 'Direct' else None
    if direct_key and (existing := frappe.db.get_value(ROOM, {'direct_key': direct_key}, 'name')):
        return _room_dict(_room(existing))
    frappe.db.savepoint('lotus_chat_create')
    room = frappe.get_doc({'doctype': ROOM, 'kind': kind, 'title': title if kind == 'Group' else '',
                           'direct_key': direct_key, 'last_seq': 0,
                           'members': [{'user': m, 'last_read_seq': 0} for m in users]})
    room.flags.chat_write = True
    try:
        room.insert(ignore_permissions=True)
    except frappe.DuplicateEntryError:
        frappe.db.rollback(save_point='lotus_chat_create')
        if direct_key and (existing := frappe.db.get_value(ROOM, {'direct_key': direct_key}, 'name')):
            return _room_dict(_room(existing))
        raise
    _notify(room, 'room')
    return _room_dict(room)


@frappe.whitelist()
def history(room, before=0, after=0):
    doc = _room(room)
    filters = {'room': doc.name}
    if cint(before) > 0:
        filters['seq'] = ['<', cint(before)]
    elif cint(after) > 0:
        filters['seq'] = ['>', cint(after)]
    rows = frappe.get_all(MESSAGE, filters=filters,
                          fields=['name', 'room', 'seq', 'sender', 'body', 'creation', 'file_url', 'file_name', 'file_size', 'file_type'],
                          order_by='seq asc' if cint(after) > 0 else 'seq desc', limit_page_length=50)
    if not cint(after):
        rows.reverse()
    return {'room': _room_dict(doc), 'messages': [_message_dict(r) for r in rows],
            'has_more': bool(rows and rows[0].seq > 1)}


def _attachment(url, file_id=''):
    if not isinstance(url, str) or not url.startswith('/private/files/'):
        frappe.throw('Chỉ gửi được tệp riêng tư vừa tải lên.')
    if file_id:
        file = frappe.get_doc('File', file_id)
        if file.owner != frappe.session.user or not file.is_private or file.file_url != url:
            frappe.throw('Tệp không thuộc tài khoản gửi.', frappe.PermissionError)
    else:
        candidates = frappe.get_all('File', filters={'file_url': url, 'owner': frappe.session.user, 'is_private': 1},
                                    fields=['name', 'attached_to_doctype', 'attached_to_name'], limit_page_length=100)
        if not candidates:
            frappe.throw('Không tìm thấy tệp vừa tải lên.', frappe.DoesNotExistError)
        free = next((row for row in candidates if not row.attached_to_doctype and not row.attached_to_name), candidates[0])
        file = frappe.get_doc('File', free.name)
    if file.attached_to_doctype or file.attached_to_name:
        frappe.throw('Tệp đã thuộc chứng từ hoặc tin nhắn khác.', frappe.PermissionError)
    if os.path.splitext(file.file_name or '')[1].lower() not in EXTENSIONS:
        frappe.throw('Loại tệp này không được hỗ trợ. Hãy gửi ảnh, tài liệu, tệp nén, âm thanh hoặc video.')
    if not 0 < (file.file_size or 0) <= MAX_BYTES:
        frappe.throw('Mỗi tệp tối đa 20 MB và không được rỗng.')
    return file


@frappe.whitelist(methods=['POST'])
def send(room, client_id, body='', file_url='', file_id=''):
    doc = _room(room, lock=True)
    user = frappe.session.user
    if not isinstance(client_id, str) or not 8 <= len(client_id) <= 100:
        frappe.throw('Thiếu mã gửi tin. Hãy thử lại.')
    key = 'LCM-' + hashlib.sha256((room + '\0' + user + '\0' + client_id).encode()).hexdigest()[:40]
    if frappe.db.exists(MESSAGE, key):
        return _message_dict(frappe.get_doc(MESSAGE, key))
    rate_key = 'lotus-chat-rate:' + user
    sent = int(frappe.cache().get_value(rate_key) or 0)
    if sent >= RATE_LIMIT:
        frappe.throw('Bạn gửi quá nhanh. Chờ vài giây rồi gửi tiếp.')
    frappe.cache().set_value(rate_key, sent + 1, expires_in_sec=RATE_WINDOW)
    body = str(body or '').strip()
    if len(body) > 6000 or (not body and not file_url):
        frappe.throw('Nhập tin nhắn hoặc chọn tệp, tối đa 6.000 ký tự.')
    file = _attachment(file_url, file_id) if file_url else None
    seq = (doc.last_seq or 0) + 1
    message = frappe.get_doc({'doctype': MESSAGE, 'room': room, 'seq': seq, 'sender': user, 'body': body,
                              'file_url': file.file_url if file else '', 'file_id': file.name if file else '', 'file_name': file.file_name if file else '',
                              'file_size': file.file_size if file else 0,
                              'file_type': (mimetypes.guess_type(file.file_name)[0] or 'application/octet-stream') if file else ''})
    message.flags.chat_write = True
    message.insert(ignore_permissions=True, set_name=key)
    if file:
        # Frappe may attach the File while inserting the message's Attach field.
        file.reload()
        file.attached_to_doctype, file.attached_to_name = MESSAGE, message.name
        file.flags.chat_write = True
        file.save(ignore_permissions=True)
    frappe.db.set_value(ROOM, room, {'last_seq': seq, 'last_preview': body[:160] or ('Tệp: ' + file.file_name)[:160],
                                   'last_activity': now_datetime()}, update_modified=False)
    me = _member(room)
    frappe.db.set_value(MEMBER, me.name, 'last_read_seq', seq, update_modified=False)
    _notify(doc, 'message', seq=seq)
    _push(doc, message, body or ('Đã gửi tệp: ' + file.file_name if file else ''))
    return _message_dict(message)


def _push(room, message, preview):
    """Phone notification for members who are not looking at Lotus right now (one per room every 30 s)."""
    try:
        from lotus_farm.push_notifications import APPS, DEVICE, _add_alert
        sender = frappe.session.user
        title = _label(sender) if room.kind == 'Direct' else (room.title or 'Nhóm chat')
        body = (preview if room.kind == 'Direct' else _label(sender) + ': ' + preview)[:200]
        for row in room.members:
            if row.user == sender or _online(row.user):
                continue
            cooldown = f'lotus-chat-push:{row.user}:{room.name}'
            if frappe.cache().get_value(cooldown):
                continue
            apps = set(frappe.get_all(DEVICE, filters={'user': row.user, 'enabled': 1}, pluck='app'))
            for app in apps & set(APPS):
                name = _add_alert(row.user, app, title, body, APPS[app], MESSAGE, message.name, key='chat-' + message.name)
                if name:
                    frappe.enqueue('lotus_farm.push_notifications._send_alert', queue='short', enqueue_after_commit=True, alert_name=name)
            frappe.cache().set_value(cooldown, 1, expires_in_sec=PUSH_COOLDOWN)
    except Exception:
        # A failed notification never blocks the message itself.
        frappe.log_error(title='Lotus chat push', message=frappe.get_traceback())


def _group(room):
    doc = _room(room, lock=True)
    if doc.kind != 'Group':
        frappe.throw('Chỉ nhóm mới đổi tên hoặc đổi thành viên được.')
    return doc


def _save_room(doc):
    doc.flags.chat_write = True
    doc.save(ignore_permissions=True)


@frappe.whitelist(methods=['POST'])
def rename(room, title):
    doc = _group(room)
    title = str(title or '').strip()
    if not 1 <= len(title) <= 80:
        frappe.throw('Nhập tên nhóm, tối đa 80 ký tự.')
    doc.title = title
    _save_room(doc)
    _notify(doc, 'room')
    return _room_dict(doc)


@frappe.whitelist(methods=['POST'])
def add_members(room, members):
    doc = _group(room)
    if isinstance(members, str):
        members = frappe.parse_json(members)
    current = {m.user for m in doc.members}
    new = [m for m in dict.fromkeys(members or []) if isinstance(m, str) and m not in current]
    if not new:
        frappe.throw('Chọn ít nhất một người chưa có trong nhóm.')
    if len(current) + len(new) > 50:
        frappe.throw('Nhóm tối đa 50 người.')
    for member in new:
        enabled, user_type = frappe.db.get_value('User', member, ['enabled', 'user_type']) or (0, '')
        if not enabled or user_type != 'System User':
            frappe.throw('Thành viên phải là tài khoản nhân viên đang hoạt động.')
        # New members see the history from now on, like joining a group chat.
        doc.append('members', {'user': member, 'last_read_seq': doc.last_seq or 0})
    _save_room(doc)
    _notify(doc, 'room')
    return _room_dict(doc)


@frappe.whitelist(methods=['POST'])
def remove_member(room, member):
    doc = _group(room)
    user = frappe.session.user
    if member != user and doc.owner != user:
        frappe.throw('Chỉ người tạo nhóm mới mời người khác ra khỏi nhóm.', frappe.PermissionError)
    if member == doc.owner and member != user:
        frappe.throw('Không thể mời người tạo nhóm ra khỏi nhóm.')
    rows = [m for m in doc.members if m.user == member]
    if not rows:
        frappe.throw('Người này không có trong nhóm.')
    if len(doc.members) <= 1:
        frappe.throw('Nhóm phải còn ít nhất một người.')
    everyone = list(doc.members)
    doc.remove(rows[0])
    _save_room(doc)
    # Tell everyone, including the person who left, so their inbox drops the room.
    for row in everyone:
        frappe.publish_realtime('lotus_chat', {'room': doc.name, 'kind': 'room'}, user=row.user, after_commit=True)
    return {'left': member == user, 'room': _room_dict(doc) if member != user else None}


@frappe.whitelist(methods=['POST'])
def recall(message):
    _user()
    row = frappe.get_doc(MESSAGE, message)
    doc = _room(row.room, lock=True)
    if row.sender != frappe.session.user:
        frappe.throw('Chỉ thu hồi được tin nhắn của chính bạn.', frappe.PermissionError)
    if row.file_type == RECALLED:
        return _message_dict(row)
    if (now_datetime() - row.creation).total_seconds() > RECALL_HOURS * 3600:
        frappe.throw(f'Chỉ thu hồi được tin nhắn trong vòng {RECALL_HOURS} giờ.')
    # Content goes; the private file stays attached to the row (no one can download it any more).
    frappe.db.set_value(MESSAGE, row.name, {'body': '', 'file_url': '', 'file_type': RECALLED}, update_modified=False)
    if row.seq == doc.last_seq:
        frappe.db.set_value(ROOM, doc.name, 'last_preview', 'Tin nhắn đã thu hồi', update_modified=False)
    _notify(doc, 'message', seq=row.seq)
    return _message_dict(frappe.get_doc(MESSAGE, row.name))


@frappe.whitelist(methods=['POST'])
def mark_read(room, seq):
    doc = _room(room, lock=True)
    me = _member(room)
    seq = max(0, min(cint(seq), doc.last_seq or 0))
    if seq > (me.last_read_seq or 0):
        frappe.db.set_value(MEMBER, me.name, 'last_read_seq', seq, update_modified=False)
        _notify(doc, 'read', user=frappe.session.user, seq=seq)
    return {'seq': max(seq, me.last_read_seq or 0)}


@frappe.whitelist(methods=['POST'])
def typing(room):
    doc = _room(room)
    key = 'lotus-chat-typing:' + room + ':' + frappe.session.user
    if not frappe.cache().get_value(key):
        frappe.cache().set_value(key, 1, expires_in_sec=3)
        _notify(doc, 'typing', user=frappe.session.user, label=_label(frappe.session.user))


@frappe.whitelist()
def download(message, inline=0):
    _user()
    row = frappe.get_doc(MESSAGE, message)
    _room(row.room)
    if not row.file_url:
        frappe.throw('Tin nhắn không có tệp đính kèm.', frappe.DoesNotExistError)
    file = frappe.get_doc('File', row.file_id)
    if not file.is_private or (file.attached_to_doctype, file.attached_to_name) != (MESSAGE, row.name):
        frappe.throw('Tệp không còn thuộc tin nhắn này.', frappe.PermissionError)
    data = file.get_content()
    if isinstance(data, str):
        data = data.encode('utf-8')
    safe_image = row.file_type in ('image/jpeg', 'image/png', 'image/gif', 'image/webp')
    frappe.local.response.update({'type': 'download', 'filename': row.file_name,
                                  'filecontent': data, 'content_type': row.file_type,
                                  'display_content_as': 'inline' if cint(inline) and safe_image else 'attachment'})


def install():
    """Add only the three messaging DocTypes; do not migrate existing business schemas."""
    for name in ('lotus_chat_member', 'lotus_chat_room', 'lotus_chat_message'):
        frappe.reload_doc('lotus_farm', 'doctype', name, force=True)
    frappe.clear_cache()


def file_guard(doc, method=None):
    old = doc.get_doc_before_save() if not doc.is_new() else None
    related = doc.attached_to_doctype == MESSAGE or (old and old.attached_to_doctype == MESSAGE)
    if related and (not doc.flags.get('chat_write') or not doc.is_private or method == 'on_trash'):
        frappe.throw('Tệp chat được giữ riêng tư cùng lịch sử hội thoại.', frappe.PermissionError)
