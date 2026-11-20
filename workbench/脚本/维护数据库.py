"""CDS本地维护：导入草稿 → 字段差异 → 事务确认 → 核验导出。

首版只更新现有CDS场次/日程的日期、时间、会场。内容、人物和结构变化
明确挂起，不能借日程更新覆盖人工分类。无网络请求，不执行上传文件。
"""
from pathlib import Path
from contextlib import contextmanager, redirect_stdout
from datetime import datetime, timezone
from collections import Counter
import argparse
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import sqlite3
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'cds-maintenance-1'
MAX_UPLOAD = 12 * 1024 * 1024
SOURCE_PATH = '原始资料/CDS2026/官方日程/CDS_全日程结构化.json'


class MaintenanceError(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with tmp.open('w', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def database(root):
    return Path(root) / '数据库/marketing.db'


def connect(root, writable=False):
    db = database(root)
    if not db.is_file():
        raise MaintenanceError('找不到已有数据库；维护台不会创建空业务库。')
    c = sqlite3.connect(str(db) if writable else db.as_uri() + '?mode=ro', uri=not writable, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    if not writable:
        c.execute('PRAGMA query_only=ON')
    return c


@contextmanager
def locked(root):
    """进程退出会释放锁；避免依赖可能残留的PID文件。"""
    folder = Path(root) / '维护记录'
    folder.mkdir(exist_ok=True)
    with (folder / '.write.lock').open('a+b') as f:
        if os.name == 'nt':
            import msvcrt
            f.seek(0)
            if not f.read(1):
                f.write(b'0'); f.flush()
            f.seek(0)
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as e:
                raise MaintenanceError('另一个维护操作正在执行，请稍后重试。') from e
        else:
            import fcntl
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as e:
                raise MaintenanceError('另一个维护操作正在执行，请稍后重试。') from e
        try:
            yield
        finally:
            if os.name == 'nt':
                f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f, fcntl.LOCK_UN)


def run_path(root, run_id):
    if not re.fullmatch(r'CDS-\d{8}T\d{6}-[0-9a-f]{8}', run_id):
        raise MaintenanceError('批次编号无效。')
    p = Path(root) / '维护记录/批次' / run_id
    if not p.is_dir():
        raise MaintenanceError('找不到这次导入记录。')
    return p


def event(folder, kind, details):
    p = folder / '操作记录.jsonl'
    previous = ''
    if p.exists():
        lines = p.read_text(encoding='utf-8').splitlines()
        if lines:
            previous = json.loads(lines[-1])['event_sha256']
    row = dict(at=now(), kind=kind, details=details, previous_sha256=previous)
    row['event_sha256'] = hashlib.sha256(encoded(row).encode()).hexdigest()
    with p.open('a', encoding='utf-8') as f:
        f.write(encoded(row) + '\n'); f.flush(); os.fsync(f.fileno())


def validate_chain(folder):
    previous = ''
    for line in (folder / '操作记录.jsonl').read_text(encoding='utf-8').splitlines():
        row = json.loads(line)
        digest = row.pop('event_sha256')
        if row['previous_sha256'] != previous or hashlib.sha256(encoded(row).encode()).hexdigest() != digest:
            raise MaintenanceError('操作记录指纹不一致，请停止更新并检查。')
        previous = digest


def item_key(item):
    if item.get('code'):
        return 'code:' + item['code']
    return 'event:' + encoded([item.get(k) for k in ('session_id', 'kind', 'title', 'people')])


def date_iso(text):
    try:
        return datetime.strptime(text, '%Y年%m月%d日').strftime('%Y-%m-%d')
    except (TypeError, ValueError) as e:
        raise MaintenanceError('日期须采用 2026年11月18日 这样的格式。') from e


def time_pair(text):
    if not isinstance(text, str) or not re.fullmatch(r'\d{2}:\d{2}-\d{2}:\d{2}', text):
        raise MaintenanceError('日程时间须采用 14:00-14:18 这样的格式。')
    start, end = text.split('-')
    try:
        datetime.strptime(start, '%H:%M'); datetime.strptime(end, '%H:%M')
    except ValueError as e:
        raise MaintenanceError('日程时间超出有效范围。') from e
    if end < start:
        raise MaintenanceError('首版不支持跨午夜日程，请单独复核。')
    return start, end


def parse_source(content):
    if not content or len(content) > MAX_UPLOAD:
        raise MaintenanceError('请选择不超过12MB的CDS结构化JSON。')
    try:
        data = json.loads(content.decode('utf-8-sig'))
    except (UnicodeError, ValueError) as e:
        raise MaintenanceError('文件不是有效UTF-8 JSON；HTML/PDF需先提取为CDS结构化资料。') from e
    if not isinstance(data, dict) or set(data) != {'as_of', 'sessions', 'items'}:
        raise MaintenanceError('需要包含as_of、sessions、items的CDS日程JSON。可先下载样例。')
    try:
        datetime.strptime(data['as_of'], '%Y-%m-%d')
    except (TypeError, ValueError) as e:
        raise MaintenanceError('as_of须为YYYY-MM-DD资料日期。') from e
    if not isinstance(data['sessions'], list) or not isinstance(data['items'], list) or not data['items'] or len(data['items']) > 15000 or len(data['sessions']) > 3000:
        raise MaintenanceError('sessions/items必须为非空日程数组，且不得超过首版处理范围。')
    for s in data['sessions']:
        if not isinstance(s, dict) or set(s) != {'session_id', 'date', 'room', 'title', 'chairs'}:
            raise MaintenanceError('场次字段缺失或有未知字段，请按样例整理。')
        if not all(isinstance(s[k], str) for k in ('session_id', 'date', 'room', 'title')) or not isinstance(s['chairs'], list):
            raise MaintenanceError('场次字段类型不正确。')
        date_iso(s['date'])
    expected = {'code', 'date', 'evidence', 'kind', 'people', 'room', 'session', 'session_id', 'source_url', 'time', 'title'}
    for item in data['items']:
        if not isinstance(item, dict) or set(item) != expected or not isinstance(item['people'], list) or not all(isinstance(item[k], str) for k in expected - {'people'}):
            raise MaintenanceError('日程字段缺失、类型错误或有未知字段，请按样例整理。')
        date_iso(item['date']); time_pair(item['time'])
        for p in item['people']:
            if not isinstance(p, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in p.items()):
                raise MaintenanceError('讲者字段格式不正确。')
        if item['source_url'] and not item['source_url'].startswith('https://cds26.tiemeeting.com/'):
            raise MaintenanceError('此入口只接收CDS2026官方日程来源；其他会议请另行接入。')
    return data


def build_diff(root, data):
    """重新按稳定报告编号比对；输入顺序变化不构成新增或覆盖。"""
    c = connect(root)
    try:
        before_hash = sha(database(root))
        old_items = [dict(r) for r in c.execute("SELECT * FROM agenda_items WHERE conference_id='CDS2026' ORDER BY source_order")]
        old_sessions = [dict(r) for r in c.execute("SELECT * FROM sessions WHERE conference_id='CDS2026'")]
        if not old_items:
            raise MaintenanceError('当前数据库没有CDS2026日程。')
        changes, blocked = [], []
        updates = []
        def add(entity, key, field, before, after, locator):
            if before != after:
                changes.append(dict(entity=entity, entity_id=key, field=field, before=before, after=after, source_locator=locator))
        def issue(message, entity_id='', field='', before=None, after=None):
            blocked.append(dict(message=message, entity_id=entity_id, field=field, before=before, after=after))
        # 场次主持人不丢弃；其变动需要独立身份核验。
        old_s = {s['source_session_id']: s for s in old_sessions}
        new_s = {s['session_id']: (i, s) for i, s in enumerate(data['sessions'])}
        if len(new_s) != len(data['sessions']):
            issue('新资料有重复场次编号，不能自动匹配。')
        for key in sorted(set(old_s) | set(new_s)):
            if key not in old_s or key not in new_s:
                issue('新增或缺少场次，需要补齐关联关系后再确认。', key); continue
            old = old_s[key]; index, new = new_s[key]; loc = f'$.sessions[{index}]'
            # 主持人原文从旧证据回读，不从已归一化姓名反推。
            material = c.execute('SELECT relative_path FROM source_materials WHERE material_id=?', (old['material_id'],)).fetchone()
            raw_source = read_json(Path(root) / material['relative_path'])
            match = re.fullmatch(r'\$\.sessions\[(\d+)\]', old['source_locator'])
            if not match:
                raise MaintenanceError('旧场次的原文定位无法回读。')
            raw_old = raw_source['sessions'][int(match.group(1))]
            for f in ('title', 'chairs'):
                if raw_old[f] != new[f]:
                    issue('场次主题/主持人变化需人工核验，首版不自动覆盖。', key, f, raw_old[f], new[f])
            values = {'date_original': new['date'], 'local_date': date_iso(new['date']), 'room_original': new['room']}
            for f, v in values.items():
                add('sessions', old['session_id'], f, old[f], v, loc)
            if any(old[f] != v for f, v in values.items()):
                updates.append(dict(entity='sessions', key=old['session_id'], values=values, locator=loc))
        old_map = {}
        for old in old_items:
            raw = json.loads(old['raw_json']); key = item_key(raw)
            if key in old_map:
                raise MaintenanceError('旧库有无法唯一匹配的日程，需要先核验。')
            old_map[key] = (old, raw)
        new_map = {}
        for index, item in enumerate(data['items']):
            key = item_key(item)
            if key in new_map:
                issue('新资料有重复报告编号或同一日程，不能自动匹配。', key)
            new_map[key] = (index, item)
        for key in sorted(set(old_map) | set(new_map)):
            if key not in old_map or key not in new_map:
                issue('新增、缺少或身份改变的日程，需补齐人物及分类关联。', key); continue
            old, raw = old_map[key]; index, new = new_map[key]; loc = f'$.items[{index}]'
            for f in sorted(set(raw) - {'date', 'time', 'room'}):
                if raw.get(f) != new.get(f):
                    issue('题名、讲者、归属或来源变化需另行复核，首版不自动覆盖。', old['agenda_item_id'], f, raw.get(f), new.get(f))
            values = {'date_original': new['date'], 'local_date': date_iso(new['date']), 'time_original': new['time'], 'start_time': time_pair(new['time'])[0], 'end_time': time_pair(new['time'])[1], 'room_original': new['room']}
            for f, v in values.items():
                add('agenda_items', old['agenda_item_id'], f, old[f], v, loc)
            if any(old[f] != v for f, v in values.items()):
                values['raw_json'] = encoded(new)
                updates.append(dict(entity='agenda_items', key=old['agenda_item_id'], values=values, locator=loc))
            s = new_s.get(new['session_id'])
            if not s or s[1]['room'] != new['room'] or s[1]['date'] != new['date'] or s[1]['title'] != new['session']:
                issue('日程与所属场次的日期、会场或名称不一致。', old['agenda_item_id'])
        conf = c.execute("SELECT start_date,end_date FROM conference_editions WHERE conference_id='CDS2026'").fetchone()
        if any(not conf['start_date'] <= date_iso(i['date']) <= conf['end_date'] for i in data['items']):
            issue('日程超出已有会议日期范围，需要先复核会议元数据。')
        if sha(database(root)) != before_hash:
            raise MaintenanceError('分析过程中数据库已被其他程序更新，请重新导入。')
        return dict(version=VERSION, conference_id='CDS2026', baseline_sha256=before_hash, source_observed_on=data['as_of'], summary=dict(sessions=len(data['sessions']), agenda_items=len(data['items']), changed_fields=len(changes), changed_records=len(updates), blocked=len(blocked)), changes=changes, blocked=blocked, updates=updates, can_confirm=not blocked, scope='只更新现有日程/场次的日期、时间、会场；不改讲者、议题分类、科研结论和评分。')
    finally:
        c.close()


def import_source(root, content, filename='CDS日程.json', note=''):
    root = Path(root).resolve()
    with locked(root):
        run_id = 'CDS-' + datetime.now().strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
        folder = root / '维护记录/批次' / run_id
        folder.mkdir(parents=True)
        # 即使不能解析，也先保留原始字节和失败记录；不覆盖原文件。
        raw = folder / '原始资料/上传原文件.json'
        raw.parent.mkdir(); raw.write_bytes(content)
        meta = dict(run_id=run_id, imported_at=now(), original_filename=Path(filename.replace('\\', '/')).name[:180], source_path=str(raw.relative_to(root)), source_sha256=sha(raw), byte_size=len(content), note=note[:2000], new_collection=False, status='importing')
        write_json(folder / '导入记录.json', meta)
        event(folder, 'imported', dict(source_sha256=meta['source_sha256'], original_filename=meta['original_filename']))
        try:
            data = parse_source(content)
            diff = build_diff(root, data)
            write_json(folder / '变化清单.json', diff)
            meta.update(status='blocked' if diff['blocked'] else 'awaiting_confirmation', diff_sha256=sha(folder / '变化清单.json'), source_observed_on=data['as_of'])
            write_json(folder / '导入记录.json', meta)
            event(folder, 'compared', dict(diff_sha256=meta['diff_sha256'], summary=diff['summary']))
        except (MaintenanceError, ValueError, KeyError, TypeError) as e:
            meta.update(status='invalid', error=str(e)); write_json(folder / '导入记录.json', meta)
            event(folder, 'import_failed', dict(error=str(e)))
        return get_run(root, run_id)


def get_run(root, run_id):
    folder = run_path(root, run_id)
    meta = read_json(folder / '导入记录.json')
    result = dict(meta=meta, diff=read_json(folder / '变化清单.json') if (folder / '变化清单.json').exists() else None, confirmation=None, verification=None)
    c = connect(root)
    try:
        if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='maintenance_runs'").fetchone():
            row = c.execute('SELECT * FROM maintenance_runs WHERE run_id=?', (run_id,)).fetchone()
            if row:
                result['confirmation'] = dict(row)
    finally:
        c.close()
    if (folder / '确认结果.json').exists():
        result['confirmation_file'] = read_json(folder / '确认结果.json')
    for name in ('最近核验.json',):
        if (folder / name).exists():
            result['verification'] = read_json(folder / name)
    result['record_url'] = '/records/' + run_id + '/'
    return result


def overview(root):
    root = Path(root).resolve()
    c = connect(root)
    try:
        counts = {t: c.execute('SELECT COUNT(*) FROM ' + t + (" WHERE conference_id='CDS2026'" if t != 'source_materials' else '')).fetchone()[0] for t in ('sessions', 'agenda_items', 'reports', 'source_materials')}
        counts['topics'] = c.execute('SELECT COUNT(*) FROM v_cds_quantity_topic_counts').fetchone()[0]
        counts['classified_reports'] = c.execute('SELECT SUM(report_count) FROM v_cds_quantity_topic_counts').fetchone()[0]
        counts['boards'] = c.execute('SELECT COUNT(*) FROM v_cds_quantity_board_counts').fetchone()[0]
    finally:
        c.close()
    runs = []
    base = root / '维护记录/批次'
    for folder in sorted(base.glob('CDS-*'), reverse=True) if base.exists() else []:
        if (folder / '导入记录.json').exists():
            run = get_run(root, folder.name)
            runs.append(dict(meta=run['meta'], summary=run['diff']['summary'] if run['diff'] else None, confirmed=bool(run['confirmation']), verification=run['verification']))
    return dict(title='数据库维护台', database='数据库/marketing.db', database_sha256=sha(database(root)), counts=counts, runs=runs[:50], version=VERSION)


def migration(c, root):
    # execute逐句而非executescript，确保DDL和数据更改处于同一事务。
    sql = (Path(root) / '规则与说明/004_维护记录.sql').read_text(encoding='utf-8')
    statement = ''
    for line in sql.splitlines(True):
        statement += line
        if sqlite3.complete_statement(statement):
            c.execute(statement); statement = ''
    if c.execute('PRAGMA user_version').fetchone()[0] < 4:
        c.execute('PRAGMA user_version=4')


def backup_database(root, target):
    source = connect(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    dest = sqlite3.connect(target)
    try:
        source.backup(dest)
        if dest.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise MaintenanceError('更新前备份未通过完整性检查。')
    finally:
        dest.close(); source.close()


def confirm(root, run_id, actor='本地使用者'):
    root = Path(root).resolve()
    with locked(root):
        folder = run_path(root, run_id)
        meta = read_json(folder / '导入记录.json')
        if meta['status'] == 'invalid':
            raise MaintenanceError('这批资料格式未通过，不能确认。')
        if sha(root / meta['source_path']) != meta['source_sha256'] or sha(folder / '变化清单.json') != meta['diff_sha256']:
            raise MaintenanceError('导入后原资料或差异清单发生变化，请重新导入。')
        validate_chain(folder)
        diff = read_json(folder / '变化清单.json')
        existing = get_run(root, run_id)['confirmation']
        if existing:
            if existing['diff_sha256'] != meta['diff_sha256']:
                raise MaintenanceError('已确认记录与当前草稿指纹不一致。')
            return dict(result='already_confirmed', run_id=run_id, confirmation=existing)
        if diff['blocked']:
            raise MaintenanceError('存在需要人工复核的变化；本批未写入业务库。请处理后重新导入。')
        if sha(database(root)) != diff['baseline_sha256']:
            raise MaintenanceError('数据库在导入后已经改变；请重新导入生成最新差异。')
        # 重算差异，保证执行的是当前解析器从原资料得到的更新，而非任意字段指令。
        fresh = build_diff(root, parse_source((root / meta['source_path']).read_bytes()))
        if encoded(fresh) != encoded(diff):
            raise MaintenanceError('重新核对的差异与已查看清单不一致，请重新导入。')
        backup = root / '备份/维护台' / (run_id + '-确认前.db')
        backup_database(root, backup)
        intent = dict(run_id=run_id, at=now(), backup=str(backup.relative_to(root)), backup_sha256=sha(backup), baseline_sha256=diff['baseline_sha256'], diff_sha256=meta['diff_sha256'])
        write_json(folder / '确认准备.json', intent)
        event(folder, 'confirm_started', intent)
        c = connect(root, writable=True)
        try:
            c.execute('BEGIN IMMEDIATE')
            if sha(database(root)) != diff['baseline_sha256']:
                raise MaintenanceError('取得写入锁前数据库已变化，请重新导入。')
            migration(c, root)
            material_id = None
            if diff['updates']:
                batch = 'MAINT:' + run_id
                material_id = 'MAT:' + hashlib.sha256((meta['source_path'] + '|' + meta['source_sha256']).encode()).hexdigest()[:20]
                c.execute('INSERT INTO import_batches VALUES (?,?,?,?,?,?,?,?,?)', (batch, meta['source_sha256'], now()[:10], now(), meta['source_observed_on'], str((folder / '导入记录.json').relative_to(root)), VERSION, 0, '本地导入CDS既有/人工提供资料；只更新已确认日程字段，不代表联网核验。'))
                c.execute('INSERT INTO source_materials VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', (material_id, batch, meta['source_path'], meta['source_sha256'], meta['byte_size'], 'structured_agenda_update', 'https://cds26.tiemeeting.com/CN/Program/Details', '结构化资料；来源真实性需人工确认', meta['source_observed_on'], meta['original_filename'], meta['source_sha256'], 0))
                for update in diff['updates']:
                    table = update['entity']; pk = 'session_id' if table == 'sessions' else 'agenda_item_id'
                    values = dict(update['values'], material_id=material_id, source_locator=update['locator'])
                    for field, after in values.items():
                        old = c.execute(f'SELECT {field} FROM {table} WHERE {pk}=?', (update['key'],)).fetchone()[0]
                        if field in {'material_id', 'source_locator', 'raw_json'} and old != after:
                            diff['changes'].append(dict(entity=table, entity_id=update['key'], field=field, before=old, after=after, source_locator=update['locator']))
                    c.execute(f'UPDATE {table} SET ' + ','.join(f'{f}=?' for f in values) + f' WHERE {pk}=?', (*values.values(), update['key']))
            status = 'confirmed_updated' if diff['updates'] else 'confirmed_no_change'
            timestamp = now()
            c.execute('INSERT INTO maintenance_runs VALUES (?,?,?,?,?,?,?,?,?,?)', (run_id, meta['source_sha256'], diff['baseline_sha256'], meta['diff_sha256'], str(folder.relative_to(root)), timestamp, actor[:200], fresh['summary']['changed_fields'], material_id, status))
            for i, change in enumerate(diff['changes']):
                c.execute('INSERT INTO maintenance_changes VALUES (?,?,?,?,?,?,?,?)', (run_id, i, change['entity'], change['entity_id'], change['field'], encoded(change['before']), encoded(change['after']), change['source_locator']))
            detail = dict(status=status, changed_fields=fresh['summary']['changed_fields'], backup=intent['backup'], backup_sha256=intent['backup_sha256'], business_changes=bool(diff['updates']))
            c.execute('INSERT INTO maintenance_events VALUES (?,?,?,?,?)', (uuid.uuid4().hex, run_id, timestamp, 'confirmed', encoded(detail)))
            if c.execute('PRAGMA foreign_key_check').fetchall():
                raise MaintenanceError('更新产生外键错误，整批已经回滚。')
            c.commit()
        except Exception as e:
            c.rollback(); event(folder, 'confirm_failed', dict(error=str(e))); raise
        finally:
            c.close()
        result = dict(result=status, run_id=run_id, confirmed_at=timestamp, confirmed_by=actor, changed_fields=fresh['summary']['changed_fields'], changed_records=fresh['summary']['changed_records'], database_sha256=sha(database(root)), **{'backup': intent['backup'], 'backup_sha256': intent['backup_sha256']})
        write_json(folder / '确认结果.json', result)
        event(folder, 'confirmed', result)
        return result


def verify_database(root):
    root = Path(root).resolve(); before = sha(database(root)); checks = []
    c = connect(root)
    try:
        if c.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or c.execute('PRAGMA foreign_key_check').fetchall():
            raise MaintenanceError('数据库完整性或外键检查失败。')
        checks.append('数据库完整性与外键通过')
        materials = {r['material_id']: dict(r) for r in c.execute('SELECT * FROM source_materials')}
        for m in materials.values():
            p = (root / m['relative_path']).resolve()
            if not p.is_relative_to(root) or not p.is_file() or sha(p) != m['sha256']:
                raise MaintenanceError('来源文件缺失或指纹改变：' + m['relative_path'])
        checks.append(f"{len(materials)}份数据库来源文件逐一核对SHA256")
        manifest = read_json(root / '原始资料/CDS2026/资料清单.json')
        for m in manifest['files']:
            if sha(root / m['path']) != m['sha256']:
                raise MaintenanceError('最初CDS资料被改变：' + m['path'])
        checks.append(f"最初{len(manifest['files'])}份CDS随包原始资料保持不变")
        cache = {}; item_count = 0; session_count = 0
        for table, array, fields in [('agenda_items', 'items', {'title': 'title_original', 'kind': 'format_original', 'date': 'date_original', 'time': 'time_original', 'room': 'room_original', 'source_url': 'source_url'}), ('sessions', 'sessions', {'title': 'title_original', 'date': 'date_original', 'room': 'room_original'})]:
            for row in c.execute("SELECT * FROM " + table + " WHERE conference_id='CDS2026'"):
                m = materials[row['material_id']]
                if m['relative_path'] not in cache:
                    cache[m['relative_path']] = read_json(root / m['relative_path'])
                match = re.fullmatch(r'\$\.' + array + r'\[(\d+)\]', row['source_locator'])
                if not match:
                    raise MaintenanceError('日程原文定位不正确。')
                raw = cache[m['relative_path']][array][int(match.group(1))]
                if any(raw[a] != row[b] for a, b in fields.items()) or date_iso(raw['date']) != row['local_date']:
                    raise MaintenanceError('日程字段与原文不一致：' + row[0])
                if table == 'agenda_items':
                    if json.loads(row['raw_json']) != raw or time_pair(raw['time']) != (row['start_time'], row['end_time']):
                        raise MaintenanceError('日程结构或时间与原文不一致。')
                    item_count += 1
                else:
                    session_count += 1
        checks.append(f'{item_count}条日程与{session_count}个场次逐条回读原资料一致')
        topics = [dict(r) for r in c.execute('SELECT * FROM v_cds_quantity_topic_counts')]
        boards = [dict(r) for r in c.execute('SELECT * FROM v_cds_quantity_board_counts')]
        total = sum(t['report_count'] for t in topics)
        if total != sum(b['report_count'] for b in boards):
            raise MaintenanceError('板块与细分议题总量不一致。')
        classified = c.execute("SELECT COUNT(*) FROM report_classifications rc JOIN analysis_versions av USING(analysis_version_id) WHERE av.analysis_kind='topic_quantity' AND av.is_current_snapshot=1 AND rc.eligible=1").fetchone()[0]
        if total != classified or any(t['denominator'] != total for t in topics):
            raise MaintenanceError('议题统计范围与当前分类不一致。')
        if c.execute("SELECT COUNT(*) FROM reports r JOIN agenda_items a USING(agenda_item_id) WHERE r.conference_id<>a.conference_id").fetchone()[0]:
            raise MaintenanceError('报告与会议归属不一致。')
        checks.append(f"{len(boards)}板块／{len(topics)}议题／{total}条分类报告范围一致")
        counts = dict(agenda_items=item_count, sessions=session_count, reports=c.execute("SELECT COUNT(*) FROM reports WHERE conference_id='CDS2026'").fetchone()[0], classified_reports=total, topics=len(topics), boards=len(boards), source_materials=len(materials))
        if sha(database(root)) != before:
            raise MaintenanceError('核验过程中数据库有变化，请重试。')
        return dict(result='passed', checked_at=now(), database_sha256=before, checks=checks, counts=counts)
    finally:
        c.close()


def verify_export(root, run_id):
    root = Path(root).resolve()
    with locked(root):
        folder = run_path(root, run_id)
        run = get_run(root, run_id)
        if not run['confirmation']:
            raise MaintenanceError('请先确认这一批更新，再核验导出。')
        validate_chain(folder)
        attempt = folder / '核验与导出' / (datetime.now().strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:6])
        attempt.mkdir(parents=True)
        event(folder, 'verify_started', dict(attempt=str(attempt.relative_to(root))))
        try:
            meta = run['meta']; confirmation = run['confirmation']
            if sha(root / meta['source_path']) != confirmation['source_sha256'] or sha(folder / '变化清单.json') != confirmation['diff_sha256']:
                raise MaintenanceError('本批归档原件或变化清单指纹改变，请检查后再导出。')
            check = connect(root)
            try:
                committed = json.loads(check.execute("SELECT detail_json FROM maintenance_events WHERE run_id=? AND event_kind='confirmed'", (run_id,)).fetchone()[0])
                if sha(root / committed['backup']) != committed['backup_sha256']:
                    raise MaintenanceError('本批确认前备份指纹改变，请检查后再导出。')
            finally:
                check.close()
            result = verify_database(root)
            result['checks'].insert(0, '本批归档原件、变化清单与确认前数据库备份指纹一致')
            spec = importlib.util.spec_from_file_location('meeting_export', root / '脚本/生成会议视图.py')
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            staging = attempt / '新导出'
            with redirect_stdout(io.StringIO()):
                module.generate(root, output=staging)
            payload = read_json(staging / '会议数据快照.json')
            manifest = read_json(staging / '生成记录.json')
            if manifest['database_sha256'] != result['database_sha256'] or sha(database(root)) != result['database_sha256']:
                raise MaintenanceError('导出期间数据库变化，保留旧网页；请重新核验导出。')
            if len(payload['reports']) != result['counts']['reports'] or len(payload['topics']) != result['counts']['topics'] or len(payload['boards']) != result['counts']['boards']:
                raise MaintenanceError('导出数量与已核验数据库不一致。')
            if sha(staging / 'index.html') != manifest['html_sha256'] or sha(staging / '会议数据快照.json') != manifest['snapshot_sha256']:
                raise MaintenanceError('导出文件指纹不一致。')
            result['checks'].append('网页、JSON导出数量及数据库/文件指纹一致')
            out = root / '会议视图'
            old = attempt / '导出前网页备份'; old.mkdir()
            names = ['index.html', '会议数据快照.json', '生成记录.json']
            for name in names:
                if (out / name).exists():
                    shutil.copy2(out / name, old / name)
            replaced = []
            try:
                for name in names:
                    # 保留本批新导出作为审计快照，复制后逐文件原子替换；失败则回退全部。
                    tmp = out / (name + '.' + uuid.uuid4().hex + '.tmp')
                    shutil.copy2(staging / name, tmp)
                    os.replace(tmp, out / name); replaced.append(name)
            except Exception:
                for name in replaced:
                    if (old / name).exists():
                        shutil.copy2(old / name, out / name)
                    else:
                        (out / name).unlink(missing_ok=True)
                raise
            result.update(run_id=run_id, exported=True, published=False, export_url='/meeting/', export_manifest=manifest, attempt=str(attempt.relative_to(root)), export_scope='当前已确认数据库；不是重放所选历史批次。')
            write_json(attempt / '核验结果.json', result)
            write_json(folder / '最近核验.json', result)
            event(folder, 'verified_exported', dict(attempt=result['attempt'], database_sha256=result['database_sha256'], html_sha256=manifest['html_sha256']))
            return result
        except Exception as e:
            result = dict(result='failed', checked_at=now(), run_id=run_id, exported=False, error=str(e), attempt=str(attempt.relative_to(root)))
            write_json(attempt / '核验结果.json', result); write_json(folder / '最近核验.json', result)
            event(folder, 'verify_failed', result)
            raise


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=ROOT)
    sub = ap.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    imp = sub.add_parser('import'); imp.add_argument('file', type=Path); imp.add_argument('--note', default='')
    sub.add_parser('import-sample')
    diff = sub.add_parser('diff'); diff.add_argument('run_id')
    conf = sub.add_parser('confirm'); conf.add_argument('run_id'); conf.add_argument('--actor', default='本地使用者')
    exp = sub.add_parser('verify-export'); exp.add_argument('run_id')
    a = ap.parse_args(); root = a.root.resolve()
    try:
        if a.command == 'status': result = overview(root)
        elif a.command == 'import': result = import_source(root, a.file.read_bytes(), a.file.name, a.note)
        elif a.command == 'import-sample': result = import_source(root, (root / SOURCE_PATH).read_bytes(), Path(SOURCE_PATH).name, '用既有CDS资料跑通维护流程；未新增联网采集。')
        elif a.command == 'diff': result = get_run(root, a.run_id)
        elif a.command == 'confirm': result = confirm(root, a.run_id, a.actor)
        else: result = verify_export(root, a.run_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (MaintenanceError, sqlite3.Error, OSError) as e:
        print(json.dumps(dict(result='failed', error=str(e)), ensure_ascii=False)); raise SystemExit(1)


if __name__ == '__main__':
    main()
