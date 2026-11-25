import contextlib
import datetime as dt
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import time
import unittest
from unittest.mock import patch

HELPER = Path(__file__).resolve().parents[1] / 'home/.local/bin/juarchy-agent-usage'
loader = importlib.machinery.SourceFileLoader('juarchy_agent_usage', str(HELPER))
spec = importlib.util.spec_from_loader(loader.name, loader)
usage = importlib.util.module_from_spec(spec)
loader.exec_module(usage)

SECRET = 'sk-ant-oat01-SECRET-TOKEN-VALUE'
TODAY = dt.date.today().isoformat()


def stamp(days_ago=0, hour=12):
    day = dt.date.today() - dt.timedelta(days=days_ago)
    return dt.datetime(day.year, day.month, day.day, hour).astimezone().isoformat()


def write_lines(path, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(entry) + '\n' for entry in entries))


def reply(message_id, output, model='claude-sonnet-4-5-20250929', when=None, request='req1', session='s1', **extra):
    entry = {'type': 'assistant', 'sessionId': session, 'requestId': request, 'timestamp': when or stamp(),
             'message': {'id': message_id, 'model': model,
                         'usage': {'input_tokens': 10, 'output_tokens': output,
                                   'cache_read_input_tokens': 100, 'cache_creation_input_tokens': 5}}}
    entry.update(extra)
    return entry


def prompt(text='hello', when=None, session='s1', **extra):
    entry = {'type': 'user', 'sessionId': session, 'timestamp': when or stamp(), 'message': {'role': 'user', 'content': text}}
    entry.update(extra)
    return entry


class Environment(unittest.TestCase):
    """Each test gets its own home, so nothing touches the real one."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.home = Path(self.directory.name)
        environment = {'HOME': str(self.home), 'XDG_STATE_HOME': str(self.home / 'state'),
                       'XDG_CACHE_HOME': str(self.home / 'cache'), 'XDG_CONFIG_HOME': str(self.home / 'config')}
        patcher = patch.dict(os.environ, environment)
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in ('CLAUDE_CONFIG_DIR', 'CODEX_HOME', 'CODEX_ACCESS_TOKEN'):
            os.environ.pop(name, None)
        self.claude = self.home / '.claude'
        self.codex = self.home / '.codex'

    def sign_in_claude(self, expires=None, refresh_expires=None, **extra):
        credentials = {'accessToken': SECRET, 'refreshToken': 'refresh-secret', 'subscriptionType': 'pro',
                       'rateLimitTier': 'default_claude_ai',
                       'expiresAt': expires if expires is not None else usage.now_ms() + 3_600_000,
                       'refreshTokenExpiresAt': refresh_expires if refresh_expires is not None else usage.now_ms() + 86_400_000}
        credentials.update(extra)
        self.claude.mkdir(parents=True, exist_ok=True)
        (self.claude / '.credentials.json').write_text(json.dumps({'claudeAiOauth': credentials}))


class HelperTests(unittest.TestCase):
    def test_claude_plan_labels(self):
        self.assertEqual(usage.plan_label('default_claude_ai', 'pro'), 'Pro')
        self.assertEqual(usage.plan_label('default_claude_max_5x', 'max'), 'Max 5x')
        self.assertEqual(usage.plan_label('default_claude_max_5x', 'team'), 'Team 5x')
        self.assertEqual(usage.plan_label('', ''), '')

    def test_percentages_are_percentages_not_fractions(self):
        self.assertAlmostEqual(usage.percent_used(0.6), 0.006)
        self.assertEqual(usage.percent_used('42%'), 0.42)
        self.assertEqual(usage.percent_used(250), 1.0)
        for junk in (None, 'x', -3, float('nan'), True):
            self.assertEqual(usage.percent_used(junk), -1)

    def test_model_labels(self):
        self.assertEqual(usage.model_label('claude-sonnet-4-5-20250929'), 'Sonnet 4.5')
        self.assertEqual(usage.model_label('claude-opus-4-1'), 'Opus 4.1')
        self.assertEqual(usage.model_label('claude-sonnet-5-5'), 'Sonnet 5.5')
        self.assertEqual(usage.model_label('gpt-5-codex'), 'gpt-5-codex')
        self.assertEqual(usage.model_label(''), 'unknown')

    def test_untrusted_numbers_are_skipped(self):
        for junk in (True, 'abc', None, float('inf'), float('nan'), -5):
            self.assertEqual(usage.tokens(junk), 0)
        self.assertEqual(usage.tokens('1200'), 1200)

    def test_reset_times(self):
        self.assertEqual(usage.reset_iso(''), '')
        self.assertEqual(usage.reset_iso(None), '')
        self.assertTrue(usage.reset_iso(1_900_000_000).startswith('2030-'))
        self.assertTrue(usage.reset_iso(1_900_000_000_000).startswith('2030-'))
        self.assertEqual(usage.reset_iso('2026-10-29T04:00:00Z'), '2026-10-29T04:00:00+00:00')
        self.assertEqual(usage.reset_iso('garbage'), '')

    def test_elapsed_windows_read_as_untouched(self):
        old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)).isoformat()
        soon = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)).isoformat()
        settled = usage.settle([{'label': 'a', 'percent': 0.9, 'resetsAt': old},
                                {'label': 'b', 'percent': 0.5, 'resetsAt': soon},
                                {'label': 'c', 'percent': 0.4, 'resetsAt': ''}])
        self.assertEqual([(w['percent'], bool(w['resetsAt'])) for w in settled], [(0, False), (0.5, True), (0.4, False)])

    def test_redirects_are_refused_so_a_token_cannot_follow_one(self):
        self.assertIsNone(usage._NoRedirect().redirect_request(None, None, 302, 'Found', {}, 'https://evil.example/'))


class ClaudeLimitParsing(unittest.TestCase):
    def test_session_weekly_and_model_scoped_windows(self):
        limits = usage.parse_claude_limits({
            'five_hour': {'utilization': 15.0, 'resets_at': '2026-10-29T04:00:00+00:00'},
            'seven_day': {'utilization': 12, 'resets_at': '2026-11-01T13:00:00+00:00'},
            'seven_day_opus': None,
            'limits': [{'kind': 'weekly_scoped', 'percent': 30, 'resets_at': '2026-11-01T13:00:00+00:00',
                        'scope': {'model': {'display_name': 'Fable'}}},
                       {'kind': 'weekly_scoped', 'percent': 30, 'scope': {'model': {'display_name': 'Fable'}}},
                       {'kind': 'weekly_scoped', 'percent': 'x', 'scope': {'model': {'display_name': 'Broken'}}}]})
        self.assertEqual([(w['title'], round(w['percent'], 2)) for w in limits],
                         [('Session', 0.15), ('Weekly', 0.12), ('Fable Weekly', 0.3)])
        self.assertTrue(limits[2]['scoped'])

    def test_nothing_usable_gives_no_limits(self):
        self.assertEqual(usage.parse_claude_limits({}), [])
        self.assertEqual(usage.parse_claude_limits({'five_hour': {'utilization': 'many'}}), [])


class ClaudeTranscripts(Environment):
    def test_a_streamed_reply_counts_once_at_its_final_size(self):
        path = self.claude / 'projects/p/a.jsonl'
        write_lines(path, [reply('m1', 5), reply('m1', 40), reply('m1', 90), reply('m2', 10, request='req2')])
        parsed = usage.parse_claude_transcript(path)
        totals = sorted(value[4] for value in parsed['replies'].values())
        self.assertEqual(totals, [10 + 10 + 100 + 5, 10 + 90 + 100 + 5])

    def test_prompts_exclude_tool_results_commands_and_subagents(self):
        path = self.claude / 'projects/p/a.jsonl'
        write_lines(path, [
            prompt('real question'),
            prompt('<command-name>/model</command-name>'),
            prompt('Caveat: local command output'),
            prompt('meta', isMeta=True),
            prompt('subagent', isSidechain=True),
            {'type': 'user', 'timestamp': stamp(), 'message': {'content': [{'type': 'tool_result', 'content': 'x'}]}},
            {'type': 'user', 'timestamp': stamp(), 'message': {'content': [{'type': 'text', 'text': 'with blocks'}]}},
        ])
        self.assertEqual(len(usage.parse_claude_transcript(path)['prompts']), 2)

    def test_synthetic_empty_and_untimed_replies_are_ignored(self):
        path = self.claude / 'projects/p/a.jsonl'
        empty = reply('m3', 0)
        empty['message']['usage'] = {'input_tokens': 0, 'output_tokens': 0}
        untimed = reply('m4', 7)
        untimed.pop('timestamp')
        write_lines(path, [reply('m1', 5, model='<synthetic>'), empty, untimed])
        self.assertEqual(usage.parse_claude_transcript(path)['replies'], {})

    def test_a_forked_copy_in_another_file_is_not_counted_twice(self):
        write_lines(self.claude / 'projects/p/a.jsonl', [prompt(), reply('m1', 50)])
        write_lines(self.claude / 'projects/p/b.jsonl', [reply('m1', 50), reply('m2', 20, request='r2')])
        stats = usage.claude_stats(self.claude, TODAY)
        self.assertEqual(stats['todayTokens'], (10 + 50 + 105) + (10 + 20 + 105))
        self.assertEqual(stats['todayPrompts'], 1)

    def test_days_models_and_sessions(self):
        write_lines(self.claude / 'projects/p/a.jsonl', [
            prompt(session='one'), reply('m1', 50, session='one'),
            prompt(when=stamp(2), session='two'), reply('m2', 30, when=stamp(2), request='r2', session='two'),
            reply('m3', 70, when=stamp(1), request='r3', model='claude-opus-4-1', session='two'),
            reply('old', 99, when=stamp(20), request='r4')])
        stats = usage.claude_stats(self.claude, TODAY)
        self.assertEqual(len(stats['recentDays']), 7)
        self.assertEqual(stats['recentDays'][-1]['date'], TODAY)
        self.assertEqual(stats['todaySessions'], 1)
        self.assertEqual(stats['weekPrompts'], 2)
        self.assertEqual(stats['weekTokens'], (10 + 50 + 105) + (10 + 30 + 105) + (10 + 70 + 105))
        self.assertEqual(stats['topModel'], 'Sonnet 4.5')
        self.assertEqual(stats['busiestDay']['tokens'], 10 + 70 + 105)  # yesterday's Opus reply
        self.assertTrue(stats['hasLocal'])

    def test_unchanged_files_are_not_read_again(self):
        path = self.claude / 'projects/p/a.jsonl'
        write_lines(path, [reply('m1', 5)])
        usage.claude_stats(self.claude, TODAY)
        with patch.object(usage, 'parse_claude_transcript', side_effect=AssertionError('reread')):
            self.assertEqual(usage.claude_stats(self.claude, TODAY)['todayTokens'], 10 + 5 + 105)
        write_lines(path, [reply('m1', 5), reply('m2', 6, request='r2')])
        self.assertEqual(usage.claude_stats(self.claude, TODAY)['todayTokens'], (10 + 5 + 105) + (10 + 6 + 105))

    def test_garbage_lines_are_skipped(self):
        path = self.claude / 'projects/p/a.jsonl'
        path.parent.mkdir(parents=True)
        path.write_text('not json\n{"type": "assistant"\n[1,2]\n' + json.dumps(reply('m1', 5)) + '\n')
        self.assertEqual(usage.claude_stats(self.claude, TODAY)['todayTokens'], 10 + 5 + 105)


class ClaudeCollector(Environment):
    OK = {'ok': True, 'limits': [{'label': 'Session (5-hour)', 'title': 'Session', 'percent': 0.4, 'resetsAt': ''}]}

    def test_not_installed_is_not_ready(self):
        with patch.object(usage.shutil, 'which', return_value=None):
            record = usage.collect_claude()
        self.assertFalse(record['ready'])
        self.assertFalse(record['installed'])

    def test_signed_in_shows_plan_and_limits_and_never_the_token(self):
        self.sign_in_claude()
        with patch.object(usage, 'probe_claude', return_value=self.OK) as probe:
            record = usage.collect_claude(force=True)
        probe.assert_called_once_with(SECRET)
        self.assertEqual((record['ready'], record['tierLabel'], record['usageStatusText']), (True, 'Pro', ''))
        self.assertEqual(record['limits'][0]['percent'], 0.4)
        self.assertNotIn(SECRET, json.dumps(record))
        written = (self.home / 'state/juarchy/agents/usage')
        self.assertFalse(written.exists())  # Only collect() writes records.
        for path in (self.home / 'cache').rglob('*'):
            if path.is_file():
                self.assertNotIn(SECRET, path.read_text())

    def test_a_recent_answer_stands_in_for_a_probe(self):
        self.sign_in_claude()
        with patch.object(usage, 'probe_claude', return_value=self.OK) as probe:
            usage.collect_claude()
            record = usage.collect_claude()
            self.assertEqual(probe.call_count, 1)
            self.assertEqual(record['limits'][0]['percent'], 0.4)
            self.assertFalse(record['limitsStale'])
            usage.collect_claude(force=True)
            self.assertEqual(probe.call_count, 2)

    def test_a_failed_check_keeps_the_last_limits_as_stale(self):
        self.sign_in_claude()
        with patch.object(usage, 'probe_claude', return_value=self.OK):
            usage.collect_claude()
        failure = {'ok': False, 'kind': 'other', 'help': 'status 500'}
        with patch.object(usage, 'probe_claude', return_value=failure):
            record = usage.collect_claude(force=True)
        self.assertEqual(record['limits'][0]['percent'], 0.4)
        self.assertTrue(record['limitsStale'])
        self.assertEqual(record['authHelpText'], 'status 500')
        self.assertEqual(record['usageStatusText'], '')
        self.assertFalse(record['retryAdvised'])

    def test_a_rate_limit_answer_leaves_recent_numbers_current(self):
        self.sign_in_claude()
        with patch.object(usage, 'probe_claude', return_value=self.OK):
            usage.collect_claude()
        with patch.object(usage, 'probe_claude', return_value={'ok': False, 'kind': 'rate', 'help': 'slow down'}):
            record = usage.collect_claude(force=True)
        self.assertFalse(record['limitsStale'])

    def test_unreachable_service_asks_for_a_sooner_retry(self):
        self.sign_in_claude()
        with patch.object(usage, 'probe_claude', return_value={'ok': False, 'kind': 'transport', 'help': 'offline'}):
            record = usage.collect_claude()
        self.assertTrue(record['retryAdvised'])
        self.assertEqual(record['usageStatusText'], 'Claude limits unavailable')
        cache = usage.LimitsCache('claude', usage.claude_login(self.claude)[4])
        self.assertTrue(cache.due(False, usage.now_ms() + 61_000))
        self.assertFalse(cache.due(False, usage.now_ms() + 30_000))

    def test_refused_sign_in_is_reported(self):
        self.sign_in_claude()
        with patch.object(usage, 'probe_claude', return_value={'ok': False, 'kind': 'refused', 'help': 'sign in again'}):
            self.assertEqual(usage.collect_claude()['usageStatusText'], 'Sign-in expired')

    def test_a_lapsed_access_token_is_not_sent(self):
        self.sign_in_claude(expires=usage.now_ms() - 1000)
        with patch.object(usage, 'probe_claude', side_effect=AssertionError('sent a lapsed token')):
            record = usage.collect_claude(force=True)
        self.assertEqual(record['usageStatusText'], 'Limits paused')
        self.sign_in_claude(expires=usage.now_ms() - 1000, refresh_expires=usage.now_ms() - 1000)
        with patch.object(usage, 'probe_claude', side_effect=AssertionError('sent a lapsed token')):
            self.assertEqual(usage.collect_claude(force=True)['usageStatusText'], 'Sign-in expired')

    def test_limit_checks_off_never_touches_the_network(self):
        self.sign_in_claude()
        with patch.object(usage, 'probe_claude', side_effect=AssertionError('network')):
            record = usage.collect_claude(force=True, limits=False)
        self.assertEqual(record['usageStatusText'], 'Limits off')
        self.assertEqual(record['limits'], [])

    def test_limit_checks_wait_for_consent_in_the_privacy_file(self):
        self.assertFalse(usage.privacy_allows_limits())  # No file, no consent.
        path = self.home / 'config/juarchy/privacy.json'
        path.parent.mkdir(parents=True)
        for value, allowed in ((True, True), (False, False), ('yes', False), (1, False)):
            path.write_text(json.dumps({'agentUsageLimits': value}))
            self.assertEqual(usage.privacy_allows_limits(), allowed, value)
        path.write_text('not json')
        self.assertFalse(usage.privacy_allows_limits())

    def test_a_cache_keeps_each_account_apart(self):
        self.sign_in_claude()
        (self.home / '.claude.json').write_text(json.dumps({'oauthAccount': {'accountUuid': 'one'}}))
        with patch.object(usage, 'probe_claude', return_value=self.OK):
            usage.collect_claude()
        (self.home / '.claude.json').write_text(json.dumps({'oauthAccount': {'accountUuid': 'two'}}))
        failure = {'ok': False, 'kind': 'other', 'help': 'x'}
        with patch.object(usage, 'probe_claude', return_value=failure):
            self.assertEqual(usage.collect_claude(force=True)['limits'], [])

    def test_profile_tier_upgrades_the_plan(self):
        self.sign_in_claude()
        (self.home / '.claude.json').write_text(json.dumps({'oauthAccount': {'userRateLimitTier': 'default_claude_max_20x'}}))
        self.assertEqual(usage.claude_login(self.claude)[3], 'Pro 20x')


FAKE_CODEX = '''#!/usr/bin/env python3
import json, os, sys, time
mode = os.environ.get("FAKE_CODEX_MODE", "ok")
if mode == "crash":
    sys.stderr.write("could not reach api.openai.com\\n"); sys.exit(1)
for line in sys.stdin:
    message = json.loads(line)
    if "id" not in message:
        continue
    if mode == "silent" and message["method"] != "initialize":
        time.sleep(60)
    if message["method"] == "initialize":
        reply = {"id": message["id"], "result": {}}
    elif mode == "noauth":
        reply = {"id": message["id"], "error": {"message": "Authentication required"}}
    else:
        reply = {"id": message["id"], "result": {
            "rateLimits": {},
            "rateLimitsByLimitId": {
                "codex_bengalfox": {"limitName": "GPT-5.3-Codex-Spark", "planType": "pro",
                                    "primary": {"usedPercent": 5, "windowDurationMins": 300, "resetsAt": 1900000000}},
                "codex": {"planType": "plus",
                          "primary": {"usedPercent": 42.5, "windowDurationMins": 300, "resetsAt": 1900000000},
                          "secondary": {"usedPercent": 10, "windowDurationMins": 10080, "resetsAt": 1900500000}}}}}
    sys.stdout.write(json.dumps(reply) + "\\n"); sys.stdout.flush()
'''


class CodexTests(Environment):
    def install_codex(self, mode='ok'):
        binary = self.home / 'bin/codex'
        binary.parent.mkdir(parents=True, exist_ok=True)
        binary.write_text(FAKE_CODEX)
        binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
        os.environ['PATH'] = '%s:%s' % (binary.parent, os.environ['PATH'])
        os.environ['FAKE_CODEX_MODE'] = mode
        self.addCleanup(os.environ.pop, 'FAKE_CODEX_MODE', None)

    def sign_in(self, **tokens):
        self.codex.mkdir(parents=True, exist_ok=True)
        (self.codex / 'auth.json').write_text(json.dumps({'tokens': dict({'access_token': 'a', 'account_id': 'acct'}, **tokens)}))

    def setUp(self):
        super().setUp()
        saved = os.environ['PATH']
        self.addCleanup(os.environ.__setitem__, 'PATH', saved)

    def test_limits_plan_and_model_allowances_come_from_the_app_server(self):
        self.install_codex()
        self.sign_in()
        record = usage.collect_codex(force=True)
        self.assertEqual((record['ready'], record['tierLabel'], record['usageStatusText']), (True, 'Plus', ''))
        self.assertEqual([(w['title'], w['percent']) for w in record['limits']],
                         [('Session', 0.425), ('Weekly', 0.1), ('GPT-5.3-Codex-Spark Session', 0.05)])
        self.assertTrue(record['limits'][2]['scoped'])
        self.assertTrue(record['limits'][0]['resetsAt'].startswith('2030-'))

    def test_app_server_is_not_started_again_within_the_reuse_window(self):
        self.install_codex()
        self.sign_in()
        usage.collect_codex(force=True)
        with patch.object(usage, 'probe_codex', side_effect=AssertionError('probed again')):
            self.assertEqual(usage.collect_codex()['tierLabel'], 'Plus')

    def test_not_signed_in_asks_to_log_in_only_when_there_is_usage(self):
        self.install_codex()
        self.assertFalse(usage.collect_codex()['ready'])
        self.sign_in()
        self.install_codex('noauth')
        record = usage.collect_codex(force=True)
        self.assertEqual(record['usageStatusText'], 'Waiting for auth')
        self.assertIn('codex login', record['authHelpText'])

    def test_a_crashed_or_silent_app_server_asks_for_a_retry(self):
        self.sign_in()
        self.install_codex('crash')
        record = usage.collect_codex(force=True)
        self.assertTrue(record['retryAdvised'])
        self.assertEqual(record['usageStatusText'], 'Codex limits unavailable')

    def test_missing_binary_still_shows_local_counts(self):
        self.sign_in()
        os.environ['PATH'] = '/nonexistent'
        with patch.object(usage, 'find_codex', return_value=''):
            record = usage.collect_codex(force=True)
        self.assertEqual(record['usageStatusText'], 'Codex limits unavailable')
        self.assertTrue(record['ready'])

    def test_api_key_login_has_no_limits_to_check(self):
        self.codex.mkdir()
        (self.codex / 'auth.json').write_text(json.dumps({'OPENAI_API_KEY': 'sk-secret'}))
        with patch.object(usage, 'probe_codex', side_effect=AssertionError('probed')):
            record = usage.collect_codex(force=True)
        self.assertEqual(record['tierLabel'], 'API key')
        self.assertNotIn('sk-secret', json.dumps(record))

    def test_rollouts_count_native_openai_turns_once(self):
        usage_line = lambda total: {'type': 'event_msg', 'timestamp': stamp(), 'payload': {'type': 'token_count', 'info': {
            'last_token_usage': {'input_tokens': 1000, 'cached_input_tokens': 600, 'output_tokens': 50},
            'total_token_usage': {'total_tokens': total}}}}
        write_lines(self.codex / 'sessions/2026/10/28/rollout-a.jsonl', [
            {'type': 'session_meta', 'payload': {'id': 'sess-a', 'model_provider': 'openai'}},
            {'type': 'turn_context', 'payload': {'model': 'gpt-5-codex'}},
            {'type': 'event_msg', 'timestamp': stamp(), 'payload': {'type': 'user_message', 'kind': 'plain'}},
            usage_line(1050), usage_line(1050), usage_line(2100)])
        write_lines(self.codex / 'sessions/2026/10/28/rollout-b.jsonl', [
            {'type': 'session_meta', 'payload': {'id': 'sess-b', 'model_provider': 'ollama'}}, usage_line(5)])
        stats = usage.codex_stats(self.codex, TODAY)
        self.assertEqual(stats['todayTokens'], 2 * (400 + 50 + 600))
        self.assertEqual(stats['todayPrompts'], 1)
        self.assertEqual(stats['todaySessions'], 1)
        self.assertEqual(stats['topModel'], 'gpt-5-codex')

    def test_token_usage_records_win_over_token_count_events(self):
        record = lambda response, total: {'type': 'token_usage_record', 'timestamp': stamp(), 'payload': {
            'response_id': response, 'thread_token_usage': {'total_tokens': total},
            'usage': {'input_tokens': 100, 'output_tokens': 10}}}
        count = {'type': 'event_msg', 'timestamp': stamp(), 'payload': {'type': 'token_count', 'info': {
            'last_token_usage': {'input_tokens': 999, 'output_tokens': 999}, 'total_token_usage': {'total_tokens': 1}}}}
        write_lines(self.codex / 'sessions/rollout-a.jsonl', [
            {'type': 'session_meta', 'payload': {'id': 'x'}}, record('r1', 110), record('r1', 110), record('r2', 220), count])
        self.assertEqual(usage.codex_stats(self.codex, TODAY)['todayTokens'], 220)


class ShellLogic(unittest.TestCase):
    def test_formatting_and_percentages_in_the_qml_service(self):
        import shutil
        import subprocess
        if not shutil.which('node'):
            self.skipTest('Node is required to exercise QML JavaScript functions')
        result = subprocess.run(['node', str(HELPER.parents[3] / 'tests/agent_usage_runtime.cjs')],
                                cwd=HELPER.parents[3], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class WholeRun(Environment):
    def test_a_failing_agent_does_not_hide_the_other(self):
        with patch.dict(usage.COLLECTORS, {'claude': lambda **k: 1 / 0}):
            result = usage.collect(['claude', 'codex'])
        by_id = {record['id']: record for record in result['agents']}
        self.assertEqual(by_id['claude']['usageStatusText'], 'Claude Code unavailable')
        self.assertIn('codex', by_id)

    def test_records_are_written_for_other_tools(self):
        result = usage.collect(['claude', 'codex'])
        for record in result['agents']:
            saved = json.loads((self.home / 'state/juarchy/agents/usage' / (record['id'] + '.json')).read_text())
            self.assertEqual(saved['id'], record['id'])
            self.assertEqual(saved['schemaVersion'], 1)

    def test_an_unused_machine_prints_unready_records(self):
        with patch.object(usage.shutil, 'which', return_value=None), patch.object(usage, 'find_codex', return_value=''):
            result = usage.collect(['claude', 'codex'])
        self.assertEqual([record['ready'] for record in result['agents']], [False, False])
        self.assertFalse(any(record['stats']['hasLocal'] for record in result['agents']))


if __name__ == '__main__':
    unittest.main()
