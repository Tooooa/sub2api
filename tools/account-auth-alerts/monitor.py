#!/usr/bin/env python3
"""Read relay OAuth error metadata and notify the owner through feishu-ask."""
import argparse
import concurrent.futures
import copy
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

SCHEMA = 1
DEFAULT_LABEL = 'com.toooa.sub2api.account-auth-alerts'
SQL = """SELECT COALESCE(jsonb_agg(jsonb_build_object(
 'id',a.id,'name',a.name,'email',a.credentials->>'email',
 'account_id',a.credentials->>'chatgpt_account_id','plan',a.credentials->>'plan_type',
 'status',a.status,'schedulable',a.schedulable,'error_message',a.error_message,
 'last_success',(SELECT created_at FROM usage_logs WHERE account_id=a.id ORDER BY created_at DESC LIMIT 1),
 'requests_7d',(SELECT count(*) FROM usage_logs WHERE account_id=a.id AND created_at>NOW()-INTERVAL '7 days'),
 'temporary_reason',CASE WHEN a.temp_unschedulable_until>NOW()
   THEN a.temp_unschedulable_reason ELSE NULL END) ORDER BY a.id), '[]'::jsonb)
 FROM accounts a WHERE a.deleted_at IS NULL AND a.platform='openai' AND a.type='oauth'"""
# The remote program emits only selected account metadata, never OAuth tokens.
REMOTE = r'''
import json,re,subprocess,sys
settings=json.load(sys.stdin)
command=settings['docker']+['exec','-e','PGOPTIONS=-c statement_timeout=20000','sub2api-postgres','sh','-c',
 'exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "$1"',
 'psql',settings['sql']]
result=subprocess.run(command,text=True,capture_output=True,timeout=25)
if result.returncode:
    raise SystemExit('database metadata query failed')
rows=json.loads(result.stdout)
if not isinstance(rows,list):
    raise SystemExit('invalid account metadata')
patterns=('refresh_token_reused','token_revoked','token revoked',
 'invalidated oauth token','invalid_grant','invalid_jwt','token_expired',
 'authentication token has expired','authentication token is expired')
for row in rows:
    primary=row.get('error_message') if row.get('status')=='error' else ''
    text=(str(primary or '')+' '+str(row.get('temporary_reason') or '')).lower()
    clean=[pattern for pattern in patterns if pattern in text]
    if re.search(r'(?<!\d)401(?!\d)',text):
        clean.append('401')
    row['error_message']=''
    row['temporary_reason']=' '.join(clean)
print(json.dumps(rows))
'''

def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def classify(row):
    """403, quota errors and access-token expiry timestamps are not proof."""
    primary = row.get('error_message', '') if row.get('status') == 'error' else ''
    text = (str(primary or '') + ' ' + str(row.get('temporary_reason') or '')).lower()
    for pattern, label in (
        ('refresh_token_reused', '刷新令牌已使用，需要重新授权'),
        ('token_revoked', '登录令牌已撤销'),
        ('token revoked', '登录令牌已撤销'),
        ('invalidated oauth token', '登录令牌已撤销'),
        ('invalid_grant', '刷新授权失效'),
        ('invalid_jwt', '登录令牌无效'),
        ('token_expired', '登录令牌过期，刷新未恢复'),
        ('authentication token has expired', '登录令牌过期，刷新未恢复'),
        ('authentication token is expired', '登录令牌过期，刷新未恢复'),
    ):
        if pattern in text:
            return label
    if re.search(r'(?<!\d)401(?!\d)', text):
        return '上游返回 401，登录授权失败'
    return None


def display_name(row):
    name = str(row.get('email') or row.get('name') or '未命名账号')
    # Never forward raw provider error bodies or arbitrary account-name markup.
    return re.sub(r'[^\w@.+\-\u3400-\u9fff ]', '', name)[:100]


def identity(row):
    account = str(row.get('account_id') or '').strip().lower()
    return 'upstream:' + account if account else 'email:' + display_name(row).lower()


def parse_time(value):
    try:
        return dt.datetime.fromisoformat(str(value).replace('Z', '+00:00')).timestamp()
    except (ValueError, TypeError, OverflowError):
        return None


def usage_label(source):
    value = parse_time(source.get('last_success'))
    if value is None:
        return '现有日志未见成功调用'
    date = dt.datetime.fromtimestamp(value, dt.timezone(dt.timedelta(hours=8))).strftime('%m-%d %H:%M')
    return '末次成功 ' + date + '，近7天 ' + str(source.get('requests_7d', 0)) + ' 次'


def collect_site(site, runner=subprocess.run):
    import shlex
    command = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
               '-o', 'ConnectionAttempts=1', '-o', 'ServerAliveInterval=5',
               '-o', 'ServerAliveCountMax=2', '-o', 'StrictHostKeyChecking=yes']
    if site.get('identity_file'):
        command += ['-i', os.path.expanduser(site['identity_file'])]
    command += [site['ssh'], ('sudo -n ' if site.get('sudo') else '') +
                'python3 -c ' + shlex.quote(REMOTE)]
    try:
        result = runner(command, input=json.dumps({
            'docker': ['docker'], 'sql': SQL,
        }), capture_output=True, text=True, timeout=45)
        if result.returncode:
            return {'ok': False, 'reason': 'SSH 或数据库查询失败'}
        rows = json.loads(result.stdout)
        if not isinstance(rows, list) or any(not isinstance(r, dict) or not isinstance(r.get('id'), int) for r in rows):
            raise ValueError('invalid metadata')
        return {'ok': True, 'rows': rows}
    except subprocess.TimeoutExpired:
        return {'ok': False, 'reason': 'SSH 查询超时'}
    except (OSError, ValueError):
        return {'ok': False, 'reason': '站点返回无效数据或无法执行查询'}


def empty_state():
    return {'version': SCHEMA, 'accounts': {}, 'sites': {}, 'rotation': {}, 'last_run_at': None}


def load_state(path):
    if not path.exists():
        return empty_state()
    state = json.loads(path.read_text())
    if state.get('version') != SCHEMA or not isinstance(state.get('accounts'), dict) or not isinstance(state.get('sites'), dict):
        raise ValueError('状态文件格式错误；保留原文件，未发送通知')
    return state


def atomic_write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix='.auth-alert-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as file:
            json.dump(value, file, ensure_ascii=False, indent=2)
            file.write('\n')
            file.flush()
            os.fsync(file.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def evaluate(previous, results, sites, now, confirmations=2, minimum_age=300,
             recent_use_days=7, ignored_accounts=()):
    """Unknown sites preserve incidents; recovery requires two spaced checks."""
    state = copy.deepcopy(previous)
    labels = {site['id']: site['name'] for site in sites}
    successful = {key for key, result in results.items() if result['ok']}
    rotation = state.setdefault('rotation', {})
    ignored = {str(item).strip().lower() for item in ignored_accounts}
    cutoff = now - recent_use_days * 86400
    facts = {}
    for site_id in successful:
        for row in results[site_id]['rows']:
            facts.setdefault(identity(row), []).append(row)
            if row.get('status') == 'active' and row.get('schedulable') is True and not classify(row):
                rotation[identity(row)] = now
    eligible = set()
    for key, rows in facts.items():
        if key in ignored or any(display_name(row).lower() in ignored for row in rows):
            continue
        if (any(row.get('schedulable') is True or (parse_time(row.get('last_success')) or 0) >= cutoff for row in rows)
                or rotation.get(key, 0) >= cutoff):
            eligible.add(key)
    observed = {}
    for site_id in successful:
        for row in results[site_id]['rows']:
            reason = classify(row)
            if reason and identity(row) in eligible:
                key = identity(row)
                source = site_id + ':' + str(row['id'])
                observed.setdefault(key, {})[source] = {
                    'site': site_id, 'id': row['id'], 'name': display_name(row), 'reason': reason,
                    'plan': row.get('plan'), 'status': row.get('status'),
                    'schedulable': row.get('schedulable'), 'last_success': row.get('last_success'),
                    'requests_7d': row.get('requests_7d', 0),
                }

    events = []
    for key in set(state['accounts']) | set(observed):
        incident = state['accounts'].setdefault(key, {'sources': {}, 'notified': False})
        sources = incident['sources']
        for source, old in list(sources.items()):
            if old['site'] in successful and source not in observed.get(key, {}):
                del sources[source]
        for source, record in observed.get(key, {}).items():
            old = sources.get(source)
            sources[source] = {**record, 'first_seen': old['first_seen'] if old else now,
                               'observations': old['observations'] + 1 if old else 1}
        if sources:
            incident.pop('healthy_since', None)
            incident.pop('healthy_observations', None)
            ready = any(source in observed.get(key, {}) and s['observations'] >= confirmations
                        and now - s['first_seen'] >= minimum_age for source, s in sources.items())
            if ready and not incident['notified'] and key in observed:
                events.append({'kind': 'auth', 'key': key, 'sources': copy.deepcopy(sources)})
        elif len(successful) == len(sites):
            incident.setdefault('healthy_since', now)
            incident['healthy_observations'] = incident.get('healthy_observations', 0) + 1
            if incident['healthy_observations'] >= 2 and now - incident['healthy_since'] >= minimum_age:
                del state['accounts'][key]

    for site in sites:
        key = site['id']
        info = state['sites'].setdefault(key, {'failures': 0, 'notified': False})
        result = results[key]
        if result['ok']:
            info.update(failures=0, notified=False, last_success=now)
            info.pop('first_failure', None)
        else:
            info.setdefault('first_failure', now)
            info['failures'] += 1
            if info['failures'] >= 3 and now - info['first_failure'] >= minimum_age * 2 and not info['notified']:
                events.append({'kind': 'site', 'key': key, 'name': labels[key], 'reason': result['reason']})
    state['last_run_at'] = now
    return state, sorted(events, key=lambda event: (event['kind'], event['key']))


def format_message(events, sites):
    labels = {site['id']: site['name'] for site in sites}
    lines = ['中转站 OAuth 授权告警', '检查时间：' + dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')]
    for event in events:
        if event['kind'] == 'site':
            lines.append('⚠ ' + event['name'] + '连续三轮无法检查：' + event['reason'] + '；账号状态未知。')
            continue
        sources = list(event['sources'].values())
        locations = '、'.join(labels[s['site']] + '#' + str(s['id']) for s in sources)
        reasons = '；'.join(sorted({s['reason'] for s in sources}))
        plans = '/'.join(sorted({str(s['plan']).upper() for s in sources if s.get('plan')})) or '未知'
        status = '仍配置参与调度' if any(s.get('schedulable') for s in sources) else '当前已停止调度'
        lines.append('• ' + sources[0]['name'] + '（登记 ' + plans + '；' + locations + '；' + status + '）')
        for source in sources:
            lines.append('  ' + labels[source['site']] + '#' + str(source['id']) + '：' + usage_label(source))
        lines.append('  授权错误：' + reasons)
    if any(e['kind'] == 'auth' for e in events):
        lines.append('仅提醒近期使用过或仍配置参与调度的账号；历史停用号不主动提醒。登记套餐可能过时，已停用不等于已确认弃用。')
        lines.append('以上为服务器记录的持续授权错误。需继续使用的账号可在 Cockpit 重新授权；额度与重置次数需恢复授权后实时查询。')
    return '\n'.join(lines)


def notify(message, config, runner=subprocess.run):
    command = [os.path.expanduser(config['feishu_ask']), 'notify', '-', '--from', '中转站 · 授权告警',
               '--session', config.get('notification_session', 'sub2api-account-auth-alerts')]
    result = runner(command, input=message, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise RuntimeError('飞书通知发送失败，保留待发送状态，下轮重试')
    return result.stdout.strip()[-200:]


def run(config, send=False, confirmations=None, minimum_age=None):
    state_path = Path(config['state_path']).expanduser()
    state_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = (state_path.parent / 'monitor.lock').open('a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        return {'skipped': '已有巡检正在运行'}
    try:
        previous = load_state(state_path)
        sites = config['sites']
        if not sites or len({s['id'] for s in sites}) != len(sites):
            raise ValueError('站点配置为空或 ID 重复')
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(sites)) as pool:
            results = dict(zip((s['id'] for s in sites), pool.map(collect_site, sites)))
        now = time.time()
        state, events = evaluate(previous, results, sites, now,
                                 confirmations if confirmations is not None else config.get('confirmations', 2),
                                 minimum_age if minimum_age is not None else config.get('minimum_failure_seconds', 300),
                                 config.get('recent_use_days', 7), config.get('ignored_accounts', []))
        deliveries = []
        failure = None
        if send:
            # One batch per 20 incidents, acknowledging only successful batches.
            for offset in range(0, len(events), 20):
                batch = events[offset:offset + 20]
                try:
                    delivery = notify(format_message(batch, sites), config)
                except (OSError, RuntimeError, subprocess.TimeoutExpired):
                    failure = '飞书发送失败；未确认的告警将在下轮重试'
                    break
                deliveries.append(delivery)
                for event in batch:
                    target = state['accounts'] if event['kind'] == 'auth' else state['sites']
                    target[event['key']]['notified'] = True
                    target[event['key']]['notified_at'] = now
                    target[event['key']]['delivery_receipt'] = delivery
            atomic_write(state_path, state)
        report = {'checked_at': utc_now(), 'send': send,
                  'sites': {key: {'ok': value['ok'], 'accounts': len(value.get('rows', [])), 'reason': value.get('reason')} for key, value in results.items()},
                  'pending_alerts': len(events), 'messages_sent': len(deliveries),
                  'auth_accounts': len(state['accounts']), 'delivery_error': failure}
        current_errors = {identity(row) for result in results.values() if result['ok']
                          for row in result['rows'] if classify(row)}
        alertable = {key for key, value in state['accounts'].items()
                     if value['sources'] and key in current_errors}
        report.update(observed_auth_accounts=len(current_errors),
                      alertable_auth_accounts=len(alertable),
                      excluded_auth_accounts=len(current_errors - alertable))
        if not send:
            report['preview'] = format_message(events, sites) if events else None
        else:
            atomic_write(state_path.parent / 'last-run.json', report)
        if failure:
            report['exit_code'] = 1
        return report
    finally:
        lock.close()


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--send', action='store_true', help='发送到期告警并写入去重状态；默认仅预览')
    parser.add_argument('--confirmations', type=int, choices=range(1, 10))
    parser.add_argument('--minimum-age', type=int)
    args = parser.parse_args()
    if args.minimum_age is not None and args.minimum_age < 0:
        parser.error('--minimum-age 不能为负数')
    try:
        config = json.loads(Path(args.config).expanduser().read_text())
        report = run(config, args.send, args.confirmations, args.minimum_age)
        print(json.dumps(report, ensure_ascii=False))
        return report.get('exit_code', 0)
    except Exception as error:
        # Never print remote stderr, raw provider messages, credentials or config.
        print(json.dumps({'error': type(error).__name__, 'message': '授权监控执行失败；检查配置、状态文件及 SSH 连通性'}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
