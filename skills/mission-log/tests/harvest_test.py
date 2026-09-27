#!/usr/bin/env python3
# harvest_test.py — mission-log 收割器的合成 fixture 測試(純標準庫,零依賴)
# 跑法: python3 skills/mission-log/tests/harvest_test.py
# 全部走子行程實跑(測的是真實 CLI 行為),明確 +08:00 讓日界線判斷跨平台可重現;
# LC_ALL=C 那條驗的是「ssh 到 C locale 機器」情境下中文不得變 ? 或替換字元。
import json, os, subprocess, sys, tempfile, unittest

HARVEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts', 'harvest.py')

# Taipei(+08:00) 的 2026-01-05 00:00 = UTC 2026-01-04T16:00:00Z
DAY = '2026-01-05'


def user_line(ts, text, cwd=None):
    d = {'timestamp': ts, 'type': 'user', 'message': {'role': 'user', 'content': text}}
    if cwd:
        d['cwd'] = cwd
    return d


def asst_line(ts, usage=None, tools=None, model='claude-test-1'):
    msg = {'role': 'assistant', 'model': model,
           'usage': usage or {'input_tokens': 10, 'output_tokens': 5,
                              'cache_creation_input_tokens': 3, 'cache_read_input_tokens': 100}}
    if tools is not None:
        msg['content'] = tools
    return {'timestamp': ts, 'type': 'assistant', 'message': msg}


class HarvestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name

    def write_session(self, proj, name, lines):
        d = os.path.join(self.root, proj)
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, name + '.jsonl')
        with open(path, 'w', encoding='utf-8') as fh:
            for ln in lines:
                fh.write(ln if isinstance(ln, str) else json.dumps(ln, ensure_ascii=False))
                fh.write('\n')
        return path

    def run_harvest(self, date=DAY, fmt='jsonl', env_extra=None):
        env = dict(os.environ)
        env.update(env_extra or {})
        return subprocess.run([sys.executable, HARVEST, '--date', date, '--dir', self.root,
                               '--format', fmt, '--timezone', '+08:00'],
                              capture_output=True, env=env)

    def rows(self, p):
        self.assertEqual(p.returncode, 0, p.stderr.decode('utf-8', 'replace'))
        return [json.loads(l) for l in p.stdout.decode('utf-8').splitlines() if l.strip()]

    def test_date_filter(self):
        self.write_session('proj-a', 'aaaa1111', [
            user_line('2026-01-05T04:00:00Z', '把報告寫完'),
            asst_line('2026-01-05T04:01:00Z'),
        ])
        self.write_session('proj-b', 'bbbb2222', [
            user_line('2026-01-08T04:00:00Z', '別的日子'),
            asst_line('2026-01-08T04:01:00Z'),
        ])
        rows = self.rows(self.run_harvest())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['session'], 'aaaa1111')
        self.assertEqual(rows[0]['prompts'], ['把報告寫完'])

    def test_cross_day_attribution(self):
        # Taipei 23:50 與翌日 00:10;同一個 session 兩天都該計入,各只算落在該日的活動
        self.write_session('proj-x', 'cccc3333', [
            asst_line('2026-01-05T15:50:00Z'),   # Taipei 01-05 23:50
            asst_line('2026-01-05T16:10:00Z'),   # Taipei 01-06 00:10
        ])
        d5 = self.rows(self.run_harvest('2026-01-05'))
        self.assertEqual(len(d5), 1)
        self.assertEqual(d5[0]['turns'], 1)
        self.assertEqual(d5[0]['last'], '23:50')
        d6 = self.rows(self.run_harvest('2026-01-06'))
        self.assertEqual(len(d6), 1)
        self.assertEqual(d6[0]['first'], '00:10')

    def test_bad_json_line(self):
        self.write_session('proj-a', 'dddd4444', [
            user_line('2026-01-05T04:00:00Z', '前面正常'),
            '{this is not json at all',
            asst_line('2026-01-05T04:02:00Z'),
        ])
        rows = self.rows(self.run_harvest())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['turns'], 1)

    def test_missing_tool_name(self):
        self.write_session('proj-a', 'eeee5555', [
            asst_line('2026-01-05T04:00:00Z',
                      tools=[{'type': 'tool_use', 'name': 'Bash'}, {'type': 'tool_use'}]),
        ])
        rows = self.rows(self.run_harvest())
        self.assertEqual(rows[0]['tools'].get('Bash'), 1)
        self.assertEqual(rows[0]['tools'].get('?'), 1)

    def test_cjk_cwd_in_md(self):
        self.write_session('encoded-dir-name', 'ffff6666', [
            user_line('2026-01-05T04:00:00Z', '中文原話要完整保留', cwd='/tmp/測試中文專案'),
            asst_line('2026-01-05T04:01:00Z'),
        ])
        p = self.run_harvest(fmt='md')
        out = p.stdout.decode('utf-8')
        self.assertIn('測試中文專案', out)
        self.assertIn('中文原話要完整保留', out)

    def test_token_definition(self):
        # tokens = in+out+cache_creation(10+5+3=18),cache_read(100)不計
        self.write_session('proj-a', 'gggg7777', [asst_line('2026-01-05T04:00:00Z')])
        rows = self.rows(self.run_harvest())
        self.assertEqual(rows[0]['tokens'], 18)

    def test_lc_all_c_subprocess(self):
        self.write_session('encoded-dir-name', 'hhhh8888', [
            user_line('2026-01-05T04:00:00Z', '中文原話要完整保留', cwd='/tmp/測試中文專案'),
            asst_line('2026-01-05T04:01:00Z'),
        ])
        p = self.run_harvest(fmt='md', env_extra={'LC_ALL': 'C', 'LANG': 'C'})
        self.assertEqual(p.returncode, 0, p.stderr.decode('utf-8', 'replace'))
        out = p.stdout.decode('utf-8')
        self.assertIn('測試中文專案', out)
        self.assertIn('中文原話要完整保留', out)
        self.assertNotIn('�', out)

    def test_bad_timestamp_warning(self):
        self.write_session('proj-a', 'iiii9999', [
            {'timestamp': 'not-a-date', 'type': 'user', 'message': {'role': 'user', 'content': '壞戳'}},
            user_line('2026-01-05T04:00:00Z', '好戳'),
            asst_line('2026-01-05T04:01:00Z'),
        ])
        p = self.run_harvest()
        rows = self.rows(p)
        self.assertEqual(len(rows), 1)
        err = p.stderr.decode('utf-8')
        self.assertIn('1 行時間戳無法解析已略過', err)

    def test_invalid_timezone_is_rejected(self):
        p = subprocess.run([sys.executable, HARVEST, '--date', DAY, '--dir', self.root,
                            '--timezone', 'Asia/Taipei'], capture_output=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('timezone must be local, Z, or an offset',
                      p.stderr.decode('utf-8', 'replace'))

    def test_old_mtime_does_not_hide_matching_activity(self):
        path = self.write_session('proj-a', 'jjjj0000', [asst_line('2026-01-05T04:00:00Z')])
        os.utime(path, (0, 0))
        self.assertEqual(len(self.rows(self.run_harvest())), 1)

    def test_out_of_order_timestamp_does_not_stop_scan(self):
        self.write_session('proj-a', 'kkkk1111', [
            asst_line('2026-01-06T04:00:00Z'),
            asst_line('2026-01-05T04:00:00Z'),
        ])
        rows = self.rows(self.run_harvest())
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['turns'], 1)

    def test_valid_non_object_json_is_ignored(self):
        self.write_session('proj-a', 'llll2222', [
            [],
            asst_line('2026-01-05T04:00:00Z'),
        ])
        self.assertEqual(len(self.rows(self.run_harvest())), 1)

    def test_model_without_hyphen_renders_in_markdown(self):
        self.write_session('proj-a', 'mmmm3333', [
            asst_line('2026-01-05T04:00:00Z', model='opus'),
        ])
        p = self.run_harvest(fmt='md')
        self.assertEqual(p.returncode, 0, p.stderr.decode('utf-8', 'replace'))
        self.assertIn('opus', p.stdout.decode('utf-8'))

    def test_same_eight_character_prefix_stays_separate(self):
        self.write_session('proj-a', 'same0000-one', [asst_line('2026-01-05T04:00:00Z')])
        self.write_session('proj-a', 'same0000-two', [asst_line('2026-01-05T05:00:00Z')])
        rows = self.rows(self.run_harvest())
        self.assertEqual(len(rows), 2)
        self.assertEqual(len({row['session'] for row in rows}), 2)

    def test_malformed_optional_fields_do_not_crash(self):
        line = asst_line(
            '2026-01-05T04:00:00Z',
            usage={'input_tokens': None, 'output_tokens': '5'},
            tools=[{'type': 'tool_use', 'name': []}],
            model={'unexpected': 'object'},
        )
        line.update(cwd=[], gitBranch={})
        self.write_session('proj-a', 'nnnn4444', [line])
        rows = self.rows(self.run_harvest())
        self.assertEqual(rows[0]['tokens'], 0)
        self.assertEqual(rows[0]['tools'], {'?': 1})
        self.assertEqual(rows[0]['models'], [])

    def test_windows_cwd_separator_is_portable(self):
        self.write_session('encoded-dir-name', 'oooo5555', [
            user_line('2026-01-05T04:00:00Z', 'Windows path', cwd=r'C:\work\中文專案'),
        ])
        rows = self.rows(self.run_harvest())
        self.assertEqual(rows[0]['project'], '中文專案')


if __name__ == '__main__':
    unittest.main(verbosity=2)
