"""Integration checks on the disposable site, including real document/file permissions."""
import os
import unittest
from pathlib import Path
from unittest import mock

import frappe
from lotus_farm import chat


class ChatIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        frappe.init(site=os.environ.get('LOTUS_CHAT_TEST_SITE', 'kho.test'), sites_path='/home/frappe/frappe-bench/sites')
        if frappe.local.site == 'frontend':
            raise RuntimeError('Chat fixtures must run on a disposable test site.')
        frappe.connect()
        frappe.set_user('Administrator')
        cls.users = []
        tag = frappe.generate_hash(length=8)
        for label in ('One', 'Two', 'Outside'):
            user = f'chat-test-{label.lower()}-{tag}@example.invalid'
            frappe.get_doc({'doctype': 'User', 'email': user, 'first_name': 'Chat ' + label,
                            'enabled': 1, 'user_type': 'System User', 'send_welcome_email': 0,
                            'roles': [{'role': 'Employee'}]}).insert(ignore_permissions=True)
            cls.users.append(user)

    @classmethod
    def tearDownClass(cls):
        frappe.db.rollback()
        frappe.destroy()

    def setUp(self):
        frappe.set_user(self.users[0])
        frappe.db.savepoint('chat_case')
        self.paths = []
        # The send rate limit lives in the cache, which a savepoint rollback does not undo.
        for user in self.users:
            frappe.cache().delete_value('lotus-chat-rate:' + user)

    def tearDown(self):
        frappe.db.rollback(save_point='chat_case')
        root = Path(frappe.get_site_path('private', 'files')).resolve()
        for file in self.paths:
            path = Path(file).resolve()
            if root in path.parents and path.name.startswith('chat-test-'):
                path.unlink(missing_ok=True)

    def direct(self):
        return chat.create([self.users[1]])['name']

    def file(self, name='chat-test-note.txt'):
        file = frappe.get_doc({'doctype': 'File', 'file_name': name, 'content': b'chat attachment test', 'is_private': 1})
        file.insert(ignore_permissions=True)
        self.paths.append(file.get_full_path())
        return file

    def test_direct_is_unique_in_both_directions(self):
        room = self.direct()
        frappe.set_user(self.users[1])
        self.assertEqual(chat.create([self.users[0]])['name'], room)
        self.assertEqual(len(chat.inbox()['rooms']), 1)

    def test_group_contains_only_selected_users(self):
        room = chat.create([self.users[1]], title='Nhóm kho', kind='Group')
        self.assertEqual(room['title'], 'Nhóm kho')
        self.assertEqual({m['user'] for m in room['members']}, set(self.users[:2]))
        frappe.set_user(self.users[2])
        self.assertEqual(chat.inbox()['rooms'], [])

    def test_outsider_cannot_read_write_mark_or_subscribe(self):
        room = self.direct()
        sent = chat.send(room, 'test-id-privacy', body='Private')
        frappe.set_user(self.users[2])
        for operation in (lambda: chat.history(room), lambda: chat.send(room, 'outsider-id', body='No'),
                          lambda: chat.mark_read(room, 1), lambda: chat.typing(room), lambda: chat.download(sent['name'])):
            with self.assertRaises(frappe.PermissionError):
                operation()
        self.assertFalse(frappe.has_permission(chat.ROOM, 'read', doc=frappe.get_doc(chat.ROOM, room)))
        self.assertEqual(frappe.get_list(chat.ROOM, fields=['name']), [])
        self.assertEqual(frappe.get_list(chat.MESSAGE, fields=['name']), [])
        self.assertEqual(frappe.get_list(chat.MEMBER, fields=['user', 'parent'], parent_doctype=chat.ROOM), [])

    def test_send_is_ordered_and_idempotent(self):
        room = self.direct()
        first = chat.send(room, 'test-id-repeat', body='<img src=x onerror=alert(1)>')
        again = chat.send(room, 'test-id-repeat', body='Retry')
        second = chat.send(room, 'test-id-second', body='Next')
        self.assertEqual(first['name'], again['name'])
        self.assertEqual([first['seq'], second['seq']], [1, 2])
        self.assertEqual(chat.history(room)['messages'][0]['body'], '<img src=x onerror=alert(1)>')
        frappe.set_user(self.users[1])
        self.assertEqual(chat.inbox()['unread'], 2)
        chat.mark_read(room, 1)
        self.assertEqual(chat.inbox()['unread'], 1)
        chat.mark_read(room, 999)
        self.assertEqual(chat.inbox()['unread'], 0)
        chat.mark_read(room, 0)
        self.assertEqual(chat.inbox()['unread'], 0)

    def test_history_paginates_without_duplicates(self):
        room = self.direct()
        with mock.patch.object(chat, 'RATE_LIMIT', 100):
            for i in range(55):
                chat.send(room, 'pagination-id-' + str(i), body=str(i))
        latest = chat.history(room)
        older = chat.history(room, before=latest['messages'][0]['seq'])
        self.assertEqual([r['seq'] for r in older['messages'] + latest['messages']], list(range(1, 56)))
        self.assertFalse(older['has_more'])
        self.assertEqual([r['seq'] for r in chat.history(room, after=53)['messages']], [54, 55])

    def test_files_stay_private_and_download_checks_membership(self):
        room = self.direct()
        file = self.file()
        sent = chat.send(room, 'attachment-id-1', file_url=file.file_url)
        self.assertIn('/api/method/lotus_farm.chat.download?', sent['file']['url'])
        self.assertNotIn(file.file_url, str(sent))
        file.reload()
        self.assertEqual(file.is_private, 1)
        frappe.set_user(self.users[1])
        self.assertTrue(frappe.has_permission('File', 'read', doc=file))
        chat.download(sent['name'])
        self.assertEqual(frappe.local.response['filecontent'], b'chat attachment test')
        frappe.set_user(self.users[2])
        self.assertFalse(frappe.has_permission('File', 'read', doc=file))
        with self.assertRaises(frappe.PermissionError):
            chat.download(sent['name'])

    def test_cannot_attach_others_or_reuse_attached_files(self):
        room = self.direct()
        file = self.file()
        frappe.set_user(self.users[1])
        with self.assertRaises(frappe.DoesNotExistError):
            chat.send(room, 'stolen-file-id', file_url=file.file_url)
        frappe.set_user(self.users[0])
        chat.send(room, 'original-file-id', file_url=file.file_url)
        with self.assertRaises(frappe.PermissionError):
            chat.send(room, 'reused-file-id', file_url=file.file_url)

    def test_chat_attachment_cannot_be_made_public_or_detached(self):
        room = self.direct()
        file = self.file('chat-test-private.txt')
        chat.send(room, 'private-file-id', file_url=file.file_url)
        file.reload()
        private_path = Path(file.get_full_path())
        file.is_private = 0
        with self.assertRaises(frappe.PermissionError):
            file.save(ignore_permissions=True)
        self.assertTrue(private_path.is_file(), 'reject before Frappe can move bytes to public files')
        file.reload()
        file.attached_to_doctype = ''
        file.attached_to_name = ''
        with self.assertRaises(frappe.PermissionError):
            file.save(ignore_permissions=True)

    def test_reupload_identical_file_preserves_each_message_attachment(self):
        room = self.direct()
        first = self.file('chat-test-repeat-a.txt')
        a = chat.send(room, 'reupload-first-id', file_url=first.file_url, file_id=first.name)
        second = self.file('chat-test-repeat-b.txt')
        b = chat.send(room, 'reupload-second-id', file_url=second.file_url, file_id=second.name)
        chat.download(a['name'])
        self.assertEqual(frappe.local.response['filecontent'], b'chat attachment test')
        chat.download(b['name'])
        self.assertEqual(frappe.local.response['filecontent'], b'chat attachment test')

    def test_message_and_room_cannot_be_edited_through_generic_api(self):
        room = self.direct()
        sent = chat.send(room, 'immutable-msg-id', body='Original')
        doc = frappe.get_doc(chat.MESSAGE, sent['name'])
        doc.body = 'Changed'
        with self.assertRaises(frappe.PermissionError):
            doc.save(ignore_permissions=True)
        doc = frappe.get_doc(chat.ROOM, room)
        doc.title = 'Changed'
        with self.assertRaises(frappe.PermissionError):
            doc.save(ignore_permissions=True)

    def test_invalid_members_and_messages_are_rejected(self):
        for args in ({'members': []}, {'members': self.users, 'kind': 'Direct'},
                     {'members': [self.users[1]], 'kind': 'Group', 'title': ''}):
            with self.assertRaises(frappe.ValidationError):
                chat.create(**args)
        room = self.direct()
        with self.assertRaises(frappe.ValidationError):
            chat.send(room, 'empty-message-id')
        with self.assertRaises(frappe.ValidationError):
            chat.send(room, 'long-message-id', body='x' * 6001)
        frappe.set_user('Guest')
        with self.assertRaises(frappe.AuthenticationError):
            chat.inbox()


    def test_group_rename_add_leave_and_owner_only_removal(self):
        two, three = self.users[1], self.users[2]
        room = chat.create([two], title='Tổ A', kind='Group')['name']
        self.assertEqual(chat.rename(room, 'Tổ bao buồng')['title'], 'Tổ bao buồng')
        self.assertEqual(len(chat.add_members(room, [three])['members']), 3)
        frappe.set_user(two)
        with self.assertRaises(frappe.PermissionError):
            chat.remove_member(room, three)
        self.assertTrue(chat.remove_member(room, two)['left'])
        with self.assertRaises(frappe.PermissionError):
            chat.history(room)

    def test_recall_is_sender_only_and_blocks_the_file(self):
        room = chat.create([self.users[1]])['name']
        message = chat.send(room, 'client-recall-1', body='Nhầm phòng')
        frappe.set_user(self.users[1])
        with self.assertRaises(frappe.PermissionError):
            chat.recall(message['name'])
        frappe.set_user(self.users[0])
        self.assertTrue(chat.recall(message['name'])['recalled'])
        self.assertTrue(chat.history(room)['messages'][-1]['recalled'])

    def test_online_member_still_receives_registered_phone_push(self):
        from lotus_farm import push_notifications

        room_name = self.direct()
        recipient = self.users[1]
        online_key = 'lotus-chat-online:' + recipient
        cooldown_key = f'lotus-chat-push:{recipient}:{room_name}'
        frappe.cache().set_value(online_key, 1, expires_in_sec=70)
        frappe.cache().delete_value(cooldown_key)
        actual_get_all = frappe.get_all

        def get_all(doctype, *args, **kwargs):
            if doctype == push_notifications.DEVICE:
                return ['work']
            return actual_get_all(doctype, *args, **kwargs)

        try:
            with mock.patch.object(frappe, 'get_all', side_effect=get_all), \
                 mock.patch.object(push_notifications, '_add_alert', return_value='alert-test') as alert, \
                 mock.patch.object(frappe, 'enqueue') as enqueue:
                chat._push(frappe.get_doc(chat.ROOM, room_name),
                           frappe._dict(name='LCM-test-notification'), 'Hello')
                self.assertEqual(alert.call_count, 1)
                self.assertEqual(alert.call_args.args[0], recipient)
                self.assertEqual(alert.call_args.args[4], '/work?chat=1')
                self.assertEqual(enqueue.call_count, 1)
        finally:
            frappe.cache().delete_value(online_key)
            frappe.cache().delete_value(cooldown_key)

    def test_send_is_rate_limited(self):
        room = chat.create([self.users[1]])['name']
        for index in range(chat.RATE_LIMIT):
            chat.send(room, f'client-rate-{index:04d}', body=str(index))
        with self.assertRaises(frappe.ValidationError):
            chat.send(room, 'client-rate-over', body='quá nhanh')


if __name__ == '__main__':
    unittest.main()
