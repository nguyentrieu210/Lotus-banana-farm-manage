import email.message
import io
import json
import time
import unittest
import urllib.error
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from lotus_farm import ai_chat as ai


class Cache:
    def __init__(self):
        self.values = {}
        self.ttls = {}

    def get_value(self, key):
        return self.values.get(key)

    def set_value(self, key, value, expires_in_sec=None):
        self.values[key] = value
        self.ttls[key] = expires_in_sec


class ProviderTest(unittest.TestCase):
    def setUp(self):
        self.cache = Cache()
        self.frappe = MagicMock()
        self.frappe.cache.return_value = self.cache
        self.frappe.throw.side_effect = lambda message, *args: (_ for _ in ()).throw(ValueError(message))
        self.addCleanup(patch.stopall)
        patch.object(ai, 'frappe', self.frappe).start()
        patch.object(ai, '_keys', return_value=['slot-one', 'slot-two']).start()
        self.requests = []

    def response(self):
        result = MagicMock()
        result.__enter__.return_value = io.StringIO(json.dumps({'choices': [{'message': {'content': 'OK'}}]}))
        return result

    def http_error(self, status=429, retry=3600):
        headers = email.message.Message()
        headers['Retry-After'] = str(retry)
        return urllib.error.HTTPError('https://provider.invalid', status, 'Limited', headers, io.BytesIO(b'quota'))

    def test_exhausted_slots_are_skipped_and_both_keys_rotate(self):
        def open(request, **kwargs):
            body = json.loads(request.data)
            self.requests.append((body, request.get_header('Authorization')))
            if body['model'] == ai.MODELS[0]:
                raise self.http_error()
            return self.response()
        with patch.object(ai.urllib.request, 'urlopen', side_effect=open):
            for _ in range(2):
                self.assertEqual(ai._complete({'messages': []}, time.monotonic() + 45)['content'], 'OK')
        self.assertEqual([r[0]['model'] for r in self.requests], [ai.MODELS[0], ai.MODELS[0], ai.MODELS[1], ai.MODELS[1]])
        self.assertNotEqual(self.requests[2][1], self.requests[3][1])
        self.assertEqual(self.cache.ttls[ai._cooldown_key(ai.MODELS[0], 'slot-one')], 3601)
        self.assertEqual(self.requests[0][0]['reasoning_effort'], 'none')
        self.assertEqual(self.requests[2][0]['reasoning_effort'], 'low')

    def test_all_quota_cooldowns_fail_immediately_without_network_or_sleep(self):
        for model in ai.MODELS:
            for key in ('slot-one', 'slot-two'):
                self.cache.values[ai._cooldown_key(model, key)] = 'quota'
        with patch.object(ai.urllib.request, 'urlopen') as network, patch.object(ai.time, 'sleep') as sleep:
            with self.assertRaisesRegex(ValueError, 'chạm hạn mức'):
                ai._complete({}, time.monotonic() + 45)
            network.assert_not_called()
            sleep.assert_not_called()

    def test_network_timeout_does_not_keep_hitting_the_same_slot(self):
        def open(request, **kwargs):
            self.requests.append(request)
            self.assertLessEqual(kwargs['timeout'], 8)
            if len(self.requests) == 1:
                raise TimeoutError()
            return self.response()
        with patch.object(ai.urllib.request, 'urlopen', side_effect=open):
            ai._complete({}, time.monotonic() + 45)
            ai._complete({}, time.monotonic() + 45)
        self.assertEqual(len(self.requests), 3)
        self.assertEqual(self.cache.values[ai._cooldown_key(ai.MODELS[0], 'slot-one')], 'error')

    def test_retry_after_uses_real_daily_duration(self):
        self.assertEqual(ai._retry_seconds({}, 'Please try again in 22m42.96s.'), 1363)
        self.assertEqual(ai._retry_seconds({}, 'tokens per day exceeded'), 3600)


class AskRoutingTest(unittest.TestCase):
    def setUp(self):
        self.fake = MagicMock()
        self.fake.session = SimpleNamespace(user='operator')
        self.fake.cache.return_value = Cache()
        self.fake.PermissionError = PermissionError
        self.addCleanup(patch.stopall)
        patch.object(ai, 'frappe', self.fake).start()
        patch.object(ai, 'nowdate', return_value='2026-10-26').start()

    def test_common_lookup_never_calls_a_provider(self):
        with patch.object(ai, 'query', return_value={'rows': [{'total': 118}]}) as query, patch.object(ai, '_complete') as provider:
            result = ai.ask([{'role': 'user', 'content': 'Có bao nhiêu nhân viên đang làm việc?'}])
        self.assertIn('118 nhân viên', result['answer'])
        self.assertEqual(result['timing']['model_calls'], 0)
        query.assert_called_once()
        provider.assert_not_called()

    def test_permission_denial_does_not_use_ai_to_attempt_another_route(self):
        with patch.object(ai, 'query', side_effect=ai.ToolError('Không có quyền xem Employee')), patch.object(ai, '_complete') as provider:
            result = ai.ask([{'role': 'user', 'content': 'Có bao nhiêu nhân viên đang làm việc?'}])
        self.assertIn('quyền', result['answer'])
        provider.assert_not_called()

    def test_old_identical_failed_retries_do_not_expand_the_prompt(self):
        with patch.object(ai, 'query', return_value={'rows': [{'total': 118}]}), patch.object(ai, '_complete') as provider:
            result = ai.ask([{'role': 'user', 'content': 'Có bao nhiêu nhân viên đang làm việc?'}] * 6)
        self.assertEqual(result['timing']['model_calls'], 0)
        provider.assert_not_called()

    def test_only_older_context_is_shortened_not_the_current_question(self):
        with patch.object(ai, '_complete', return_value={'content': 'OK'}) as provider:
            ai.ask([{'role': 'user', 'content': 'U' * 3000}, {'role': 'assistant', 'content': 'A' * 3000},
                    {'role': 'user', 'content': 'X' * 3900}])
        sent = provider.call_args.args[0]['messages']
        self.assertEqual(len(sent[-1]['content']), 3900)
        self.assertEqual(len(sent[-2]['content']), 1600)


if __name__ == '__main__':
    unittest.main()
