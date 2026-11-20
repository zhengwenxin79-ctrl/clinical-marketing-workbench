# Windows transfer edition: explicit UTF-8 and portable runtime.
"""Low-volume official-source calendar monitor. Every run writes a review draft only."""
import argparse
from portable_runtime import project_lock, curl_executable
import shutil
import copy
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date, timezone, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
ROOT = Path(__file__).resolve().parents[1]
TZ = timezone(timedelta(hours=8), 'Asia/Shanghai')
MONTHS = {m.lower(): i for i, m in enumerate(['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'], 1)}
TRACKED = ['start', 'end', 'location', 'abstract_deadline', 'registration_deadline', 'program_url']

def norm(s):
    return re.sub('\\s+', ' ', s).strip()

def digest(b):
    return hashlib.sha256(b).hexdigest()

def load(p):
    return json.loads(p.read_text(encoding='utf-8'))

def save(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(p)

class Page(HTMLParser):

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.links = []
        self.skip = 0
        self.anchor = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ['script', 'style', 'noscript', 'svg']:
            self.skip += 1
        if not self.skip:
            if tag in ['p', 'div', 'h1', 'h2', 'h3', 'li', 'br', 'section', 'tr']:
                self.parts.append('\n')
            if tag == 'a':
                self.anchor = {'url': a.get('href', ''), 'text': ''}

    def handle_endtag(self, tag):
        if tag in ['script', 'style', 'noscript', 'svg']:
            self.skip = max(0, self.skip - 1)
        if tag == 'a' and self.anchor:
            self.links.append(self.anchor)
            self.anchor = None

    def handle_data(self, s):
        if not self.skip:
            self.parts.append(s + ' ')
            if self.anchor:
                self.anchor['text'] += s + ' '

def fetch(source, run, previous):
    """HTTP errors, short dynamic shells and parse misses never count as no changes."""
    sid = source['id']
    body = run / (sid + '.html')
    headers = run / (sid + '.headers.txt')
    result = {'id': sid, 'source_id': source['source_id'], 'url': source['url'], 'fields': source['fields'], 'status': 'fetch_failed'}
    cmd = [curl_executable(), '--location', '--fail', '--silent', '--show-error', '--max-time', '30', '--connect-timeout', '10', '--max-filesize', '10000000', '--proto', '=https', '--proto-redir', '=https', '--user-agent', 'Wenxin-ConferenceMonitor/1.0 (weekly public conference calendar check)', '--dump-header', str(headers), '--output', str(body), '--write-out', '%{http_code}\n%{url_effective}\n%{content_type}', source['url']]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=35, encoding='utf-8', errors='replace')
        meta = r.stdout.splitlines()
        result.update(http_status=meta[0] if meta else None, final_url=meta[1] if len(meta) > 1 else source['url'])
        if r.returncode:
            raise ValueError(r.stderr.strip()[:300] or 'HTTP request failed')
        if urlparse(result['final_url']).hostname != urlparse(source['url']).hostname:
            raise ValueError('Cross-domain redirect requires source review')
        raw = body.read_bytes()
        charset = re.search(b'charset=["\\s]*([\\w-]+)', raw[:5000], re.I)
        encoding = charset[1].decode() if charset else 'utf-8'
        parser = Page()
        parser.feed(raw.decode(encoding, errors='replace'))
        text = norm(' '.join(parser.parts))
        links = []
        for l in parser.links:
            href = urljoin(result['final_url'], l['url'])
            label = norm(l['text'])
            if href.startswith('https://') and label:
                links.append({'label': label, 'url': href})
        text_path = run / (sid + '.txt')
        text_path.write_text(text + '\n', encoding='utf-8')
        if len(text) < 100 or re.search('^(Just a moment|Access denied|Verify you are human)', text, re.I):
            raise ValueError('Dynamic shell, access challenge or insufficient readable content')
        sha = digest(text.encode())
        result.update(status='fetched', text_file=text_path.name, raw_file=body.name, text_sha256=sha, page_changed=None if not previous else sha != previous.get('text_sha256'), links=links, text=text)
    except (ValueError, subprocess.TimeoutExpired, OSError, LookupError) as e:
        result['error'] = str(e)
    return result

def iso(y, m, d):
    return date(int(y), MONTHS.get(str(m).lower(), int(m) if str(m).isdigit() else 0), int(d)).isoformat()

def extract(source, result, checked):
    t = result['text']
    adapter = source['adapter']
    sid = source['source_id']
    evidence = []
    values = {}

    def match(pattern, flags=re.I):
        m = re.search(pattern, t, flags)
        if not m:
            raise ValueError('Calendar grammar changed or concrete dates unavailable; manual review needed')
        evidence.append(m.group(0))
        return m
    if adapter == 'links':
        return None
    if adapter == 'cds':
        m = match('将于(20\\d{2})年(\\d{1,2})月(\\d{1,2})[-—–至](\\d{1,2})日在([^。]{1,35})举行')
        y, mo, a, b, city = m.groups()
        start, end = (iso(y, mo, a), iso(y, mo, b))
        location = city
        for key, pat in [('abstract_deadline', '征文截稿日期\\s*[：:]\\s*(20\\d{2})年(\\d{1,2})月(\\d{1,2})日'), ('registration_deadline', '注册优惠截止日期\\s*[：:]\\s*(20\\d{2})年(\\d{1,2})月(\\d{1,2})日')]:
            d = re.search(pat, t)
            if d:
                values[key] = iso(*d.groups())
                evidence.append(d.group(0))
    elif adapter == 'cse':
        m = match('将于(20\\d{2})年(\\d{1,2})月(\\d{1,2})[-—–至](\\d{1,2})日在([^。]{1,45})召开')
        y, mo, a, b, location = m.groups()
        start, end = (iso(y, mo, a), iso(y, mo, b))
    elif adapter == 'ada':
        m = match('Save the date for the (20\\d{2}) Scientific Sessions.{0,130}?in (.{1,50}?), (\\w+) (\\d{1,2})[–—-](\\d{1,2}), (20\\d{2}) at (.{1,120}?Convention Cent(?:er|re))')
        edition, city, mo, a, b, y, venue = m.groups()
        if edition != y:
            raise ValueError('Conflicting ADA edition and date')
        start, end = (iso(y, mo, a), iso(y, mo, b))
        location = city + ' · ' + venue
        d = re.search('Submissions will be accepted until (?:\\w+, )?(\\w+) (\\d{1,2}), (20\\d{2})(.{0,35}?)(?:\\. |$)', t, re.I)
        if d:
            mo, day, yr, _ = d.groups()
            values['abstract_deadline'] = iso(yr, mo, day)
            values['abstract_deadline_note'] = d.group(0)
            evidence.append(d.group(0))
    elif adapter == 'easd':
        m = match('(?:take place|be held) from (?:\\w+, )?(\\d{1,2}) (\\w+) to (?:\\w+, )?(\\d{1,2}) (\\w+) (20\\d{2})\\s*,? at (.{1,130}?) in (.{1,50}?)(?:\\. |$)')
        a, mo, b, mo2, y, venue, city = m.groups()
        start, end = (iso(y, mo, a), iso(y, mo2, b))
        location = city + ' · ' + venue
    elif adapter == 'idf':
        m = match('Congress (20\\d{2}) will be held in (.{1,45}?) from (\\d{1,2}) to (\\d{1,2}) (\\w+),? (20\\d{2})')
        edition, location, a, b, mo, y = m.groups()
        if edition != y:
            raise ValueError('Conflicting IDF edition and date')
        start, end = (iso(y, mo, a), iso(y, mo, b))
    elif adapter == 'attd':
        m = match('ATTD (20\\d{2}) SAVE THE DATE FOR THE NEXT EDITION IN ([A-Z -]+?) (\\d{1,2})[-–—](\\d{1,2}) (\\w+) (20\\d{2})')
        edition, location, a, b, mo, y = m.groups()
        if edition != y:
            raise ValueError('Conflicting ATTD edition and date')
        start, end = (iso(y, mo, a), iso(y, mo, b))
    else:
        raise ValueError('Unknown adapter')
    year = start[:4]
    names = {'CDS': 'CDS 全国糖尿病学术会议', 'CSE': 'CSE 全国内分泌学学术会议', 'ADA': 'ADA Scientific Sessions', 'EASD': 'EASD Annual Meeting', 'IDF': 'IDF World Diabetes Congress', 'ATTD': 'ATTD 糖尿病先进技术与治疗会议'}
    program = next((l['url'] for l in result['links'] if re.search('^(会议日程|日程安排|Program Information|Programme|Scientific Programme)$', l['label'], re.I)), None)
    if program:
        values.update(program_url=program, program_url_note='官方页面给出的入口，目标页可访问性待核；不代表完整日程新发布。')
    return dict(id=sid.lower() + '-' + year, source_id=sid, name=names[sid] + ' ' + year, fields=source['fields'], region=source['region'], start=start, end=end, location=norm(location), checked_at=checked, source_url=result['final_url'], evidence=[{'source_url': result['final_url'], 'snapshot': result['text_file'], 'quote': q} for q in evidence], **values)

def merge(base, observations, checked, run_id):
    out = copy.deepcopy(base)
    by_id = {m['id']: m for m in out['meetings']}
    events = out.setdefault('update_events', [])
    for obs in observations:
        existing = by_id.get(obs['id'])
        changes = {}
        if existing:
            for k in TRACKED:
                if k in obs and obs[k] != existing.get(k):
                    if k == 'location' and str(obs[k]).removesuffix('市') == str(existing.get(k, '')).removesuffix('市'):
                        continue
                    changes[k] = {'before': existing.get(k), 'after': obs[k]}
            kind = ('字段变化（待复核）' if any((v['before'] is not None for v in changes.values())) else '资料补充（待复核）') if changes else None
            existing.update({k: v for k, v in obs.items() if k not in ['name', 'fields', 'region', 'source_id']})
            existing['date_basis'] = '官方页面核对于' + checked[:10]
            existing['basis_ref'] = '采集快照 ' + run_id
            existing['links'] = [{'label': '本轮官方依据', 'url': obs['source_url']}] + [l for l in existing.get('links', []) if l['url'] != obs['source_url']]
            existing['gaps'] = [g for g in existing.get('gaps', []) if '未复查官方安排' not in g]
        else:
            m = copy.deepcopy(obs)
            m.update(date_basis='官方页面核对于' + checked[:10], basis_ref='采集快照 ' + run_id, links=[{'label': '官方会议来源', 'url': obs['source_url']}], material='已核会议基本信息；具体议题与研究内容待采集。', priority='待业务筛选', priority_reason='既有会议目录中的核心来源；已核举办日期，议题与转化价值待评估。', priority_basis='来源相关性，尚未进行热点或产品评分', gaps=['本轮仅核会议基本信息，议题、团队和研究结果未采集。', '截止日以官方当地时区为准；缺失项保持待核。'])
            out['meetings'].append(m)
            by_id[m['id']] = m
            kind = '首次发现（待复核）'
            changes = {k: {'before': None, 'after': obs[k]} for k in TRACKED if k in obs}
        if kind:
            fingerprint = digest(json.dumps([obs['id'], changes], sort_keys=True, ensure_ascii=False).encode())[:20]
            if not any((e.get('id') == fingerprint for e in events)):
                events.append(dict(id=fingerprint, meeting_id=obs['id'], recorded_on=checked[:10], kind=kind, summary='已收录本届会议的举办日期、地点及官方入口。' if not existing else '补充／核对：' + '、'.join(({'start': '开始日期', 'end': '结束日期', 'location': '地点', 'abstract_deadline': '摘要截止', 'registration_deadline': '优惠注册截止', 'program_url': '日程入口'}.get(k, k) for k in changes)) + '。', changes=changes, evidence=obs['evidence'], run_id=run_id))
    return out

def collect(root=ROOT, replay=None):
    cfg = load(root / 'monitoring/sources.json')
    now = datetime.now(TZ)
    checked = now.isoformat(timespec='seconds')
    run_id = now.strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:6]
    run = root / 'monitoring/runs' / run_id
    run.mkdir(parents=True)
    state_path = root / 'monitoring/state.json'
    old = load(state_path) if state_path.exists() else {'sources': {}}
    base = load(root / 'src/weekly-meetings.json')
    if old.get('latest_run'):
        prior = root / 'monitoring/runs' / old['latest_run'] / 'weekly-meetings.proposed.json'
        if prior.exists() and load(prior.parent / 'manifest.json').get('formal_sha256') == digest((root / 'src/weekly-meetings.json').read_bytes()):
            previous = load(prior)
            known = {m['id'] for m in previous['meetings']}
            previous['meetings'] += [m for m in base['meetings'] if m['id'] not in known]
            base = previous
    if replay:
        if Path(replay).name != replay:
            raise ValueError('Expected a run ID, not a path')
        origin = root / 'monitoring/runs' / replay
        report = load(origin / 'fetch-report.json')
        checked = report['checked_at']
        results = report['sources']
        for r in results:
            for key in ['text_file', 'raw_file']:
                if r.get(key):
                    shutil.copy2(origin / r[key], run / r[key])
            if r.get('text_file'):
                r['text'] = (run / r['text_file']).read_text(encoding='utf-8')
                r['status'] = 'fetched'
        save(run / 'replay.json', {'from_run': replay, 'original_checked_at': checked, 'note': 'Reparsed saved snapshots without new HTTP checks.'})
    else:
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(lambda s: fetch(s, run, old['sources'].get(s['id'])), cfg['sources']))
    observations = []
    for s, r in zip(cfg['sources'], results):
        if r['status'] == 'fetched':
            try:
                obs = extract(s, r, checked)
                if obs:
                    observations.append(obs)
                r['status'] = 'checked' if obs else 'page_only'
                if not obs:
                    r['gap'] = '仅取得日程页面；未解析完整议程，也不推断已发布。'
            except (ValueError, KeyError) as e:
                r.update(status='parse_gap', error=str(e))
    grouped = {}
    for obs in observations:
        grouped.setdefault(obs['id'], []).append(obs)
    conflicts = {mid for mid, group in grouped.items() if any((any((a.get(k) != b.get(k) for k in ['start', 'end', 'location'])) for a in group for b in group))}
    if conflicts:
        observations = [o for o in observations if o['id'] not in conflicts]
        for r in results:
            if r['status'] == 'checked' and any((o['source_url'] == r.get('final_url') for mid in conflicts for o in grouped[mid])):
                r.update(status='conflict', error='Official observations conflict for the same edition; retained prior calendar pending review')
    proposed = merge(base, observations, checked, run_id)
    successful = [r for r in results if r['status'] == 'checked']
    gaps = [r for r in results if r['status'] != 'checked']
    run_status = 'complete' if not gaps else 'partial' if successful else 'failed'
    proposed['source_cutoff'] = checked[:10]
    proposed['monitoring'] = {'status': 'review_draft', 'run_status': run_status, 'last_checked_at': checked, 'run_id': run_id, 'mode': 'draft_only', 'field': 'diabetes', 'sources_total': len(results), 'sources_checked': len(successful), 'issues': [{'id': r['id'], 'status': r['status'], 'note': r.get('error', r.get('gap', ''))} for r in gaps], 'checks': base.get('monitoring', {}).get('checks', []) + [{'checked_at': checked, 'fields': ['diabetes'], 'status': run_status, 'run_id': run_id, 'sources_checked': len(successful), 'sources_total': len(results)}]}
    clean = [{k: v for k, v in r.items() if k != 'text'} for r in results]
    save(run / 'fetch-report.json', {'checked_at': checked, 'run_status': run_status, 'sources': clean})
    save(run / 'observations.json', observations)
    save(run / 'weekly-meetings.proposed.json', proposed)
    new_state = {'latest_run': run_id, 'sources': {r['id']: {k: r[k] for k in ['text_sha256', 'final_url', 'status'] if k in r} for r in results}}
    new_events = [e for e in proposed['update_events'] if e.get('run_id') == run_id]
    save(run / 'manifest.json', {'run_id': run_id, 'checked_at': checked, 'status': 'awaiting_review', 'run_status': run_status, 'formal_sha256': digest((root / 'src/weekly-meetings.json').read_bytes()), 'proposed_sha256': digest((run / 'weekly-meetings.proposed.json').read_bytes()), 'events_this_run': len(new_events)})
    lines = ['# 每周会议检查｜待复核', f'\n检查时间：{checked}。正式网站未覆盖。', f'\n共{len(results)}个入口，{len(successful)}个解析出会议信息；其余{len(gaps)}个待核。', f'\n本轮产生{len(new_events)}条首次发现或资料补充候选，均不是主办方发布日期。', '\n## 来源状态', '\n|来源|状态|说明|', '|---|---|---|']
    for r in results:
        lines.append(f"|[{r['id']}]({r['url']})|{r['status']}|{r.get('error', r.get('gap', '已保存页面与日期依据')).replace('|', '/')}|")
    lines += ['\n## 本轮候选'] + [f"- {o['name']}：{o['start']}—{o['end']}，{o['location']}。" for o in observations] + ['\n## 边界与缺口', '- 首轮建立抓取基线，不能还原过去哪天发布或变更。截止日缺失保留待核；不把报名按钮当作报名开放。', '- 固定届次／旧公告不能覆盖未来所有会议；需逐轮检查官方新届次链接，网站改版或解析失败不算无变化。', '- 候选网页：preview/index.html。变化、原文证据分别见JSON与本地快照。', '- 本轮未采集研究结果，不更新Biomarker、研究热度或产品匹配评分。']
    (run / '复核报告.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    subprocess.run([sys.executable, str(root / 'build.py'), '--weekly-data', str(run / 'weekly-meetings.proposed.json'), '--output-dir', str(run / 'preview')], check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
    stable = root / 'monitoring/待复核'
    stable.mkdir(exist_ok=True)
    (stable / 'dist').mkdir(exist_ok=True)
    for name in ['index.html', 'dist/index.html', '会议与论文研究台_v2_分享包.zip', 'README.md']:
        source = run / 'preview' / name
        if source.exists():
            dest = stable / name
            tmp = dest.with_suffix(dest.suffix + '.tmp')
            shutil.copy2(source, tmp)
            tmp.replace(dest)
    save(state_path, new_state)
    save(root / 'monitoring/latest.json', {'run_id': run_id, 'report': str((run / '复核报告.md').relative_to(root)), 'preview': str((run / 'preview/index.html').relative_to(root)), 'run_status': run_status})
    print(json.dumps({'run_id': run_id, 'checked': len(successful), 'total': len(results), 'events': len(new_events), 'status': run_status, 'report': str(run / '复核报告.md'), 'preview': str(run / 'preview/index.html')}, ensure_ascii=False))
    return run
if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--replay', help='Reparse stored snapshots; preserves original check timestamp.')
    args = ap.parse_args()
    with project_lock(ROOT):
        collect(replay=args.replay)
