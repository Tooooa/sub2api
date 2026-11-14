import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('monitor', Path(__file__).with_name('monitor.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
SITES = [{'id': 'ny', 'name': '纽约', 'ssh': 'example'}, {'id': 'wh', 'name': '武汉', 'ssh': 'example'}]


def row(account=1, upstream='shared', error='refresh_token_reused', status='error'):
    return {'id': account, 'account_id': upstream, 'name': 'owner@example.com',
            'status': status, 'schedulable': True, 'error_message': error}


def result(ny=None, wh=None):
    return {'ny': {'ok': True, 'rows': ny or []}, 'wh': {'ok': True, 'rows': wh or []}}


class MonitorTests(unittest.TestCase):
    def test_terminal_authorization_errors(self):
        for text in ['refresh_token_reused', 'token_revoked', 'invalid_grant', 'invalid_jwt',
                     'token_expired', 'OAuth 401: expired', 'Token revoked (401)']:
            with self.subTest(text=text):
                self.assertIsNotNone(m.classify(row(error=text)))

    def test_quota_network_and_expiry_are_not_authorization_failures(self):
        for text in ['HTTP 403 Forbidden', 'HTTP 429 quota exceeded', 'network timeout', 'rate_limit 100%']:
            self.assertIsNone(m.classify(row(error=text)))
        active = row(error='token_expired', status='active')
        active['expires_at'] = '2000-01-01T00:00:00Z'
        self.assertIsNone(m.classify(active))
        active['temporary_reason'] = 'OAuth 401: token_expired'
        self.assertIsNotNone(m.classify(active))

    def test_two_sites_and_duplicate_records_merge_by_upstream_account(self):
        data = result([row(17)], [row(22), row(32)])
        state, events = m.evaluate(m.empty_state(), data, SITES, 1000)
        self.assertEqual(events, [])
        state, events = m.evaluate(state, data, SITES, 1300)
        self.assertEqual(len(events), 1)
        self.assertEqual(len(events[0]['sources']), 3)
        text = m.format_message(events, SITES)
        self.assertEqual(text.count('owner@example.com'), 1)
        self.assertIn('武汉#32', text)

    def test_two_checks_need_time_apart(self):
        data = result([row()])
        state, _ = m.evaluate(m.empty_state(), data, SITES, 1000)
        state, events = m.evaluate(state, data, SITES, 1001)
        self.assertEqual(events, [])
        _, events = m.evaluate(state, data, SITES, 1300)
        self.assertEqual(len(events), 1)

    def test_notified_incident_does_not_repeat(self):
        data = result([row()])
        state, _ = m.evaluate(m.empty_state(), data, SITES, 1000)
        state['accounts']['upstream:shared']['notified'] = True
        _, events = m.evaluate(state, data, SITES, 2000)
        self.assertEqual(events, [])

    def test_unknown_site_preserves_failure_and_does_not_confirm(self):
        state, _ = m.evaluate(m.empty_state(), result([row()]), SITES, 1000)
        offline = result(wh=[row(22)])
        offline['ny'] = {'ok': False, 'reason': 'timeout'}
        state, events = m.evaluate(state, offline, SITES, 1500)
        self.assertEqual(events, [])  # New WH evidence cannot confirm an unknown NY source.
        self.assertEqual(len(state['accounts']['upstream:shared']['sources']), 2)

    def test_recovery_requires_two_healthy_checks_then_rearms(self):
        data = result([row()])
        state, _ = m.evaluate(m.empty_state(), data, SITES, 1000)
        state['accounts']['upstream:shared']['notified'] = True
        state, _ = m.evaluate(state, result(), SITES, 1400)
        self.assertTrue(state['accounts']['upstream:shared']['notified'])
        state, _ = m.evaluate(state, result(), SITES, 1700)
        self.assertEqual(state['accounts'], {})
        state, _ = m.evaluate(state, data, SITES, 1800)
        _, events = m.evaluate(state, data, SITES, 2100)
        self.assertEqual(len(events), 1)

    def test_partial_outage_never_rearms_healthy_account(self):
        state, _ = m.evaluate(m.empty_state(), result([row()]), SITES, 1000)
        state['accounts']['upstream:shared']['notified'] = True
        data = result()
        data['wh'] = {'ok': False, 'reason': 'timeout'}
        for at in (1400, 1800, 2200):
            state, _ = m.evaluate(state, data, SITES, at)
        self.assertTrue(state['accounts']['upstream:shared']['notified'])

    def test_site_outage_is_separate_and_debounced(self):
        data = result()
        data['wh'] = {'ok': False, 'reason': 'SSH 查询超时'}
        state = m.empty_state()
        for at in (1000, 1300):
            state, events = m.evaluate(state, data, SITES, at)
            self.assertEqual(events, [])
        _, events = m.evaluate(state, data, SITES, 1600)
        self.assertEqual([e['kind'] for e in events], ['site'])
        self.assertIn('账号状态未知', m.format_message(events, SITES))

    def test_send_failure_is_retried_and_success_is_persisted(self):
        with tempfile.TemporaryDirectory() as temp:
            config = {'state_path': str(Path(temp) / 'state.json'), 'sites': SITES}
            data = result([row()])
            with patch.object(m, 'collect_site', side_effect=lambda site: data[site['id']]):
                with patch.object(m, 'notify', side_effect=RuntimeError('failed')):
                    report = m.run(config, True, 1, 0)
                self.assertEqual(report['exit_code'], 1)
                state = m.load_state(Path(config['state_path']))
                self.assertFalse(state['accounts']['upstream:shared']['notified'])
                with patch.object(m, 'notify', return_value='message-id') as sender:
                    m.run(config, True, 1, 0)
                    m.run(config, True, 1, 0)
                self.assertEqual(sender.call_count, 1)

    def test_preview_does_not_send_or_persist_state(self):
        with tempfile.TemporaryDirectory() as temp:
            config = {'state_path': str(Path(temp) / 'state.json'), 'sites': SITES}
            with patch.object(m, 'collect_site', return_value={'ok': True, 'rows': [row()]}), patch.object(m, 'notify') as sender:
                report = m.run(config, False, 1, 0)
            self.assertEqual(report['pending_alerts'], 1)
            self.assertFalse(Path(config['state_path']).exists())
            sender.assert_not_called()

    def test_corrupt_state_stops_without_sending(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'state.json'
            path.write_text('{broken')
            config = {'state_path': str(path), 'sites': SITES}
            with patch.object(m, 'notify') as sender, self.assertRaises(ValueError):
                m.run(config, True)
            sender.assert_not_called()
            self.assertEqual(path.read_text(), '{broken')

    def test_remote_errors_are_not_exposed(self):
        def runner(*args, **kwargs):
            return subprocess.CompletedProcess([], 1, '', 'Authorization: Bearer SECRET')
        self.assertNotIn('SECRET', json.dumps(m.collect_site(SITES[0], runner)))

    def test_remote_program_strips_provider_error_bodies(self):
        raw = [row(error='401 token_expired Bearer SECRET_REFRESH_TOKEN')]
        fake = subprocess.CompletedProcess([], 0, json.dumps(raw), '')
        import contextlib
        import io
        output = io.StringIO()
        with patch('sys.stdin', io.StringIO(json.dumps({'docker': ['docker'], 'sql': 'SELECT'}))), patch('subprocess.run', return_value=fake), contextlib.redirect_stdout(output):
            exec(m.REMOTE, {})
        self.assertNotIn('SECRET', output.getvalue())
        self.assertIsNotNone(m.classify(json.loads(output.getvalue())[0]))

    def test_email_fallback_and_name_sanitizing(self):
        first, second = row(), row()
        first.pop('account_id')
        second.pop('account_id')
        second['name'] = 'OWNER@EXAMPLE.COM'
        self.assertEqual(m.identity(first), m.identity(second))
        self.assertNotIn('<', m.display_name({'name': '<script>unsafe</script>'}))

    def test_disabled_historical_accounts_are_not_alerted(self):
        old = row()
        old.update(schedulable=False, last_success='2026-01-01T00:00:00Z')
        _, events = m.evaluate(m.empty_state(), result([old]), SITES, 1800000000, 1, 0)
        self.assertEqual(events, [])

    def test_recent_success_is_not_lost_when_failure_disables_scheduling(self):
        recent = row()
        recent.update(schedulable=False, last_success='2026-11-14T00:00:00Z', requests_7d=42, plan='pro')
        now = m.parse_time('2026-11-15T00:00:00Z')
        _, events = m.evaluate(m.empty_state(), result([recent]), SITES, now, 1, 0)
        self.assertEqual(len(events), 1)
        text = m.format_message(events, SITES)
        self.assertIn('登记 PRO', text)
        self.assertIn('当前已停止调度', text)
        self.assertIn('近7天 42 次', text)

    def test_prior_rotation_tracks_new_failure_without_successful_calls(self):
        healthy = row(status='active', error='')
        state, _ = m.evaluate(m.empty_state(), result([healthy]), SITES, 1800000000)
        failed = row()
        failed['schedulable'] = False
        _, events = m.evaluate(state, result([failed]), SITES, 1800000300, 1, 0)
        self.assertEqual(len(events), 1)

    def test_explicit_ignore_overrides_recent_use_and_rotation(self):
        _, events = m.evaluate(m.empty_state(), result([row()]), SITES, 1800000000, 1, 0,
                               ignored_accounts=['OWNER@EXAMPLE.COM'])
        self.assertEqual(events, [])

    def test_same_account_unused_on_one_site_still_shows_both_sites(self):
        now = m.parse_time('2026-11-15T00:00:00Z')
        ny, wh = row(35), row(30)
        ny.update(schedulable=False, last_success='2026-11-11T04:14:28Z', requests_7d=5604)
        wh['schedulable'] = False
        _, events = m.evaluate(m.empty_state(), result([ny], [wh]), SITES, now, 1, 0)
        self.assertEqual(len(events), 1)
        text = m.format_message(events, SITES)
        self.assertIn('纽约#35', text)
        self.assertIn('武汉#30', text)
        self.assertIn('现有日志未见成功调用', text)

    def test_inactive_account_without_history_is_not_assumed_in_use(self):
        unused = row()
        unused['schedulable'] = False
        _, events = m.evaluate(m.empty_state(), result([unused]), SITES, 1800000000, 1, 0)
        self.assertEqual(events, [])


if __name__ == '__main__':
    unittest.main()
