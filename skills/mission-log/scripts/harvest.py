#!/usr/bin/env python3
# harvest.py — mission-log 零 token 收割器(原型 v0)
# 從 ~/.claude/projects/*/*.jsonl 抽出指定日期(當地時區)的活動骨架。
# 純標準庫、不呼叫任何模型;可整檔經 ssh 餵給遠端 python3(單檔自包含)。
# 用法: python3 harvest.py [--date YYYY-MM-DD] [--dir DIR] [--format md|jsonl]
# 語意約定:
# - tokens = 新增 tokens(input+output+cache_creation),不含 cache 讀取——與生態通用口徑一致。
# - 查詢日 = 本機時區的日曆日;session 在該日 00:00-24:00 間有任何活動即計入。
# - 🔴 一則 API 回應只算一次:transcript 把同一則回應拆成多行(每個 content block 一行),每行都帶同一份
#   usage,而 output_tokens 是串流累計快照——逐行相加會把 turns 與 tokens 灌水約 2 倍(實測每天 1.6~7 倍不等,
#   不能用固定倍率還原)。做法:按 message.id 併成一則(沒 id 的行用 requestId 併回唯一對到的那則;兩個都沒有
#   才逐行各算一則),四欄各取最大;turns = 回應數(含 0 token 的 <synthetic>);跨午夜的回應整則歸它時間戳最早
#   那行的那天(兩趟掃描:先整檔求每則回應的最早時間戳,再歸日——不依賴檔案行序),翌日不重算。
# - 🔴 跨檔也只算一次:resume／continue 會把舊訊息(同 message.id、同時間戳、原 sessionId)複寫進新 session 檔。
#   同一個 id 歸行上 sessionId 對得上檔名的那個檔(原 session);都對不上才取時間戳最早、再取檔名排序在前者。
#   其他檔的副本整行不算、只把用量併過去取最大。
# - 🔴 沒見過的形狀不硬加、要回報:同 id 出現兩組都非零且不相等的 input/cache、同 id 對到兩個 requestId、
#   同一個 requestId 對到兩個以上(非 synthetic 的)id ⇒ 該則標矛盾:turns 照算、tokens 不計入、
#   session 記 usage_conflict、stderr 警告。取最大會拼出從沒存在過的用量,寧可擋。
import json, sys, os, glob, argparse, datetime, platform, re

USAGE_KEYS = ('input_tokens', 'output_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens')
SYNTHETIC = '<synthetic>'

def parse_timezone(value):
    if value == 'local':
        return None
    if value in ('Z', '+00:00', '-00:00'):
        return datetime.timezone.utc
    match = re.fullmatch(r'([+-])(\d{2}):(\d{2})', value)
    if not match or int(match.group(2)) > 23 or int(match.group(3)) > 59:
        raise argparse.ArgumentTypeError('timezone must be local, Z, or an offset such as +08:00')
    minutes = int(match.group(2)) * 60 + int(match.group(3))
    if match.group(1) == '-':
        minutes = -minutes
    return datetime.timezone(datetime.timedelta(minutes=minutes))

def parse_ts(s, timezone=None):
    try:
        value = datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
        return value.astimezone(timezone) if timezone else value.astimezone()
    except Exception:
        return None

def user_text(msg):
    """抽出「真人打的字」:排除 tool_result/系統注入(<開頭)/指令包裝。"""
    c = msg.get('content')
    texts = []
    if isinstance(c, str):
        texts = [c]
    elif isinstance(c, list):
        texts = [b.get('text', '') for b in c if isinstance(b, dict) and b.get('type') == 'text']
    for t in texts:
        t = t.strip()
        if t and not t.startswith('<') and not t.startswith('Caveat:'):
            return t
    return None

def session_prefix(project, session_id, keys):
    peers = [other for peer_project, other in keys if peer_project == project and other != session_id]
    length = min(8, len(session_id))
    while length < len(session_id) and any(other.startswith(session_id[:length]) for other in peers):
        length += 1
    return session_id[:length]

def path_leaf(value):
    if not isinstance(value, str) or not value:
        return ''
    parts = re.split(r'[/\\]+', value.rstrip('/\\'))
    return parts[-1] if parts else ''

def usage_vals(u):
    """usage 四欄 → 非負整數 list;沒有這個鍵=0。型別不對(字串/bool/負數)回 None,呼叫端計壞行、不猜不靜默當 0。"""
    out = []
    for k in USAGE_KEYS:
        x = u.get(k)
        if x is None:
            x = 0
        if isinstance(x, bool) or not isinstance(x, int) or x < 0:
            return None
        out.append(x)
    return out

def merge_response(resp, key, vals, rq):
    """把一行的 usage 併進 resp[key](同一則回應)。四欄取最大;input/cache 簽名或 requestId 對不上就標矛盾。"""
    sig = (vals[0], vals[2], vals[3])
    sig = sig if any(sig) else None
    e = resp.get(key)
    if e is None:
        resp[key] = {'v': list(vals), 'sig': sig, 'req': rq, 'bad': None}
        return
    for i in range(4):
        if vals[i] > e['v'][i]:
            e['v'][i] = vals[i]
    if sig is not None:
        if e['sig'] is None:
            e['sig'] = sig
        elif sig != e['sig'] and e['bad'] is None:
            e['bad'] = '同 id 用量矛盾'
    if rq:
        if e['req'] is None:
            e['req'] = rq
        elif rq != e['req'] and e['bad'] is None:
            e['bad'] = '同 id 對到兩個 requestId'

def mark_conflicts(resp, req2ids):
    """沒有 message.id 的行若 requestId 對到多個 id(key 仍是 ('req', q))⇒ 矛盾;
    同一個 requestId 對到兩個以上非 synthetic 的 id ⇒ 那幾則都標矛盾。唯一對到的,第一趟已併成同一個 key。"""
    for key, e in resp.items():
        if key[0] == 'req' and len(req2ids.get(key[1], ())) > 1 and e['bad'] is None:
            e['bad'] = 'requestId 對到多個 id'
    for q, ids in req2ids.items():
        if len(ids) > 1:
            for mid in ids:
                e = resp.get(('id', mid))
                if e is not None and e['bad'] is None:
                    e['bad'] = 'requestId 對到多個 id'

def account_assistant(s, m, rq, resp, rkey):
    """一行 assistant 訊息的 usage/模型/工具記進 session。rkey=這行所屬回應的 key(沒有 usage 時為 None)。
    回 1=usage 欄壞行(已略過),0=正常。"""
    bad = 0
    u = m.get('usage')
    if isinstance(u, dict) and rkey is not None:
        vals = usage_vals(u)
        if vals is None:
            bad = 1
        else:
            merge_response(resp, rkey, vals, rq)
    model = m.get('model')
    if isinstance(model, str) and model and model != SYNTHETIC:
        s['models'].add(model)
    c = m.get('content')
    if isinstance(c, list):
        for b in c:
            if isinstance(b, dict) and b.get('type') == 'tool_use':
                n = b.get('name')
                if not isinstance(n, str) or not n:
                    n = '?'
                s['tools'][n] = s['tools'].get(n, 0) + 1
    return bad

def scan_lines(fh, timezone):
    """逐行產出 (lineno, obj, ts, m, mid, rq, has_usage);ts 為 False 表示有時間戳但解析不了。"""
    for lineno, line in enumerate(fh, 1):
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        raw = obj.get('timestamp')
        ts = parse_ts(raw, timezone) if raw else None
        if raw and ts is None:
            yield lineno, obj, False, None, None, None, False
            continue
        if not ts:
            continue
        m = obj.get('message')
        if not isinstance(m, dict):
            m = None
        has_usage = m is not None and isinstance(m.get('usage'), dict)
        mid = m.get('id') if has_usage else None
        mid = mid if isinstance(mid, str) and mid else None
        rq = obj.get('requestId')
        rq = rq if isinstance(rq, str) and rq else None
        yield lineno, obj, ts, m, mid, rq, has_usage

def response_index(fh, timezone, sid=None):
    """第一趟(整檔、與行序無關):建 requestId → 非 synthetic message.id 對照,並求每則回應最早一行的時間戳。
    回 (req2ids, key_of, first_ts, home_ids)。home_ids=有任一行 sessionId 等於本檔 session(sid)的 message.id。key_of(mid, rq, lineno) 給一行所屬回應的 key:有 id 用 id;沒 id 但
    requestId 唯一對到一個 id ⇒ 用那個 id;否則用 requestId;兩個都沒有 ⇒ 逐行各一則。"""
    req2ids, id_first, req_first, home_ids = {}, {}, {}, set()
    for _, obj, ts, m, mid, rq, has_usage in scan_lines(fh, timezone):
        if ts is False or not has_usage:
            continue
        if mid and sid and obj.get('sessionId') == sid:
            home_ids.add(mid)
        if mid and rq and m.get('model') != SYNTHETIC:
            req2ids.setdefault(rq, set()).add(mid)
        if mid:
            id_first[mid] = min(id_first.get(mid, ts), ts)
        elif rq:
            req_first[rq] = min(req_first.get(rq, ts), ts)

    def key_of(mid, rq, lineno):
        if mid:
            return ('id', mid)
        if rq:
            ids = req2ids.get(rq, ())
            return ('id', next(iter(ids))) if len(ids) == 1 else ('req', rq)
        return ('line', lineno)

    first_ts = {('id', mid): ts for mid, ts in id_first.items()}
    for rq, ts in req_first.items():
        k = key_of(None, rq, 0)
        first_ts[k] = min(first_ts.get(k, ts), ts)
    return req2ids, key_of, first_ts, home_ids

def harvest(projects_dir, day, timezone=None):
    if timezone:
        day_start = datetime.datetime.combine(day, datetime.time.min, tzinfo=timezone)
    else:
        day_start = datetime.datetime.combine(day, datetime.time.min).astimezone()
    day_end = day_start + datetime.timedelta(days=1)
    sessions = {}
    bad_ts = bad_usage = conflicts = 0
    # 第一趟(全部檔案):每檔的回應索引,以及每個 message.id 跨檔歸哪個檔、哪天。
    # resume／continue 會把舊訊息(同 message.id、同時間戳、保留原 sessionId)複寫進新 session 檔;
    # 同一則回應跨檔只算一次。歸屬順序:① 行上 sessionId 等於檔名 session 的那個檔(原 session);
    # ② 沒有檔對得上才取時間戳最早者;③ 再平手取檔名排序在前者。其他檔的副本只把用量併過去(取最大)。
    indexes = []
    id_owner = {}  # message.id → (排序鍵 (非原檔, ts, 檔案序號), 歸日用的 ts, 檔案序號)
    for tx in sorted(glob.glob(os.path.join(projects_dir, '*', '*.jsonl'))):
        try:
            with open(tx, encoding='utf-8', errors='replace') as fh:
                index = response_index(fh, timezone, os.path.splitext(os.path.basename(tx))[0])
        except OSError:
            continue
        fileno = len(indexes)
        indexes.append((tx, index))
        for k, ts in index[2].items():
            if k[0] == 'id':
                rank = (k[1] not in index[3], ts, fileno)
                cur = id_owner.get(k[1])
                if cur is None or rank < cur[0]:
                    id_owner[k[1]] = (rank, ts, fileno)
    files = []     # 第二趟每檔的結果:(s, resp, req2ids)
    foreign = {}   # 檔案序號 → 別檔裡屬於它的回應副本 [(m, rq, rkey)]
    for fileno, (tx, (req2ids, key_of, first_ts, _home)) in enumerate(indexes):
        try:
            fh = open(tx, encoding='utf-8', errors='replace')
        except OSError:
            continue
        proj = os.path.basename(os.path.dirname(tx))
        full_sid = os.path.splitext(os.path.basename(tx))[0]
        key = (proj, full_sid)
        s = None
        # 一則回應整則歸「它最早一行」那天(first_ts 來自第一趟,與行序無關):跨午夜的後續行併回那天,翌日整行不算。
        resp = {}    # 本檔歸當天的「一則回應」表
        spill = []   # 歸當天、但時間戳落在當天之外的後續行:session 建好後再併(只計用量/模型/工具,不動 first/last)
        with fh:
            for lineno, obj, ts, m, mid, rq, has_usage in scan_lines(fh, timezone):
                if ts is False:
                    bad_ts += 1  # 有時間戳但解析不了:計數
                    continue
                rkey = key_of(mid, rq, lineno) if has_usage else None
                if rkey is not None:
                    owner_file = fileno
                    if rkey[0] == 'id' and rkey[1] in id_owner:
                        _, owner, owner_file = id_owner[rkey[1]]
                    else:
                        owner = first_ts.get(rkey, ts)
                    if not day_start <= owner < day_end:
                        continue  # 這行屬於別天開始的回應,整行(含工具)歸那天
                    if owner_file != fileno:
                        # 別檔先出現過的回應(resume 複寫的副本):整行不算在本檔,用量併回原檔那則
                        foreign.setdefault(owner_file, []).append((m, rq, rkey))
                        continue
                    if not day_start <= ts < day_end:
                        spill.append((m, rq, rkey))
                        continue
                elif not day_start <= ts < day_end:
                    continue
                s = sessions.setdefault(key, {
                    'project': proj.split('-')[-1] or proj, 'session': full_sid,
                    'first': ts, 'last': ts, 'turns': 0, 'tokens': 0, 'usage_conflict': 0,
                    'tools': {}, 'models': set(), 'prompts': [], 'branch': None, '_cwd': None})
                s['first'] = min(s['first'], ts); s['last'] = max(s['last'], ts)
                cwd = obj.get('cwd')
                if isinstance(cwd, str) and cwd and not s['_cwd']:
                    s['_cwd'] = cwd
                    s['project'] = path_leaf(cwd) or s['project']
                branch = obj.get('gitBranch')
                if isinstance(branch, str) and branch and not s['branch']:
                    s['branch'] = branch
                if m is None:
                    continue
                if obj.get('type') == 'user' and not obj.get('isMeta'):
                    t = user_text(m)
                    if t:
                        s['prompts'].append(t[:70])
                bad_usage += account_assistant(s, m, rq, resp, rkey)
        if s is not None:
            for m, rq, rkey in spill:
                bad_usage += account_assistant(s, m, rq, resp, rkey)
        files.append((fileno, s, resp, req2ids))
    for fileno, s, resp, req2ids in files:
        if s is not None:
            for m, rq, rkey in foreign.get(fileno, ()):
                vals = usage_vals(m['usage'])
                if vals is None:
                    bad_usage += 1
                else:
                    merge_response(resp, rkey, vals, rq)
            mark_conflicts(resp, req2ids)
            for e in resp.values():
                s['turns'] += 1
                if e['bad']:
                    s['usage_conflict'] += 1
                else:
                    s['tokens'] += e['v'][0] + e['v'][1] + e['v'][2]
            conflicts += s['usage_conflict']
    for (project, full_sid), session in sessions.items():
        session['session'] = session_prefix(project, full_sid, sessions.keys())
    return sorted(sessions.values(), key=lambda s: s['first']), bad_ts, bad_usage, conflicts

def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='backslashreplace')
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=None)
    ap.add_argument('--dir', default=os.path.expanduser('~/.claude/projects'))
    ap.add_argument('--format', choices=['md', 'jsonl'], default='md')
    ap.add_argument('--timezone', type=parse_timezone, default=None,
                    metavar='local|Z|+08:00', help='calendar-day timezone (default: system local)')
    a = ap.parse_args()
    if a.date:
        day = datetime.date.fromisoformat(a.date)
    else:
        today = datetime.datetime.now(a.timezone).date() if a.timezone else datetime.date.today()
        day = today - datetime.timedelta(days=1)
    rows, bad_ts, bad_usage, conflicts = harvest(a.dir, day, a.timezone)
    if bad_ts:
        print(f"⚠️ {bad_ts} 行時間戳無法解析已略過", file=sys.stderr)
    if bad_usage:
        print(f"⚠️ {bad_usage} 行 usage 欄型別不對已略過(不猜、不當 0)", file=sys.stderr)
    if conflicts:
        print(f"⚠️ {conflicts} 則回應用量矛盾(同 id 兩組不同用量或對到兩個 requestId):turns 照算、tokens 未計入,見各列 usage_conflict", file=sys.stderr)
    host = platform.node().split('.')[0]
    if a.format == 'jsonl':
        for s in rows:
            out = dict(s, first=s['first'].strftime('%H:%M'), last=s['last'].strftime('%H:%M'),
                       models=sorted(s['models']), host=host,
                       tools=dict(sorted(s['tools'].items(), key=lambda x: -x[1])[:6]),
                       prompts=s['prompts'][:5] + (['…+%d' % (len(s['prompts']) - 5)] if len(s['prompts']) > 5 else []))
            print(json.dumps(out, ensure_ascii=False, default=str))
        return
    print(f"## {day} @ {host} — {len(rows)} 個活躍 session (tok=新增 in+out+cache_creation, 不含 cache 讀取; turns=回應數, 同一則回應拆成的多行只算一次)")
    for s in rows:
        tools = ' '.join(f"{k}×{v}" for k, v in sorted(s['tools'].items(), key=lambda x: -x[1])[:4])
        models = ','.join(m.split('-', 1)[1] if '-' in m else m for m in sorted(s['models']))
        warn = f" ⚠️用量矛盾×{s['usage_conflict']}" if s['usage_conflict'] else ''
        print(f"\n### {s['first'].strftime('%H:%M')}–{s['last'].strftime('%H:%M')}  {s['project']}"
              f"{'@' + s['branch'] if s['branch'] else ''}  ({s['turns']} turns, {s['tokens']:,} tok{warn}, {models})")
        print(f"  工具: {tools or '（無）'}")
        for p in s['prompts'][:5]:
            print(f"  › {p}")
        if len(s['prompts']) > 5:
            print(f"  › …共 {len(s['prompts'])} 句")

if __name__ == '__main__':
    main()
