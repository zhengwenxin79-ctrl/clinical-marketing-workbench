# Windows transfer edition: explicit UTF-8 and portable runtime.
"""WorkBuddy entry point: preflight, one draft run, and evidence verification."""
import argparse
import os
import contextlib
import hashlib
import importlib.util
import io
import json
import re
import shutil
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
sys.dont_write_bytecode = True
from portable_runtime import project_lock, curl_executable
SKILL = Path(__file__).resolve().parents[1]
VALID_STATUSES = {'checked', 'page_only', 'parse_gap', 'fetch_failed', 'conflict'}

class ValidationError(Exception):
    pass

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def ensure(ok, msg):
    if not ok:
        raise ValidationError(msg)

def norm(text):
    return re.sub('\\s+', ' ', text).strip()

def contained(path, root):
    return path.resolve().is_relative_to(root.resolve())

def inside(path, root):
    ensure(contained(path, root), 'Path leaves the selected project: ' + str(path))
    return path

def integrity():
    manifest = load(SKILL / 'package-manifest.json')
    for name, expected in manifest['files'].items():
        p = SKILL / name
        ensure(contained(p, SKILL) and p.is_file(), 'Missing package file: ' + name)
        ensure(sha(p) == expected, 'Skill package file changed; restore the verified package: ' + name)
    return manifest

def preflight(root):
    ensure(sys.version_info >= (3, 9), 'Python 3.9 or later required')
    ensure(sys.platform in ['win32', 'darwin', 'linux'], 'Supported runtime: Windows/macOS/Linux')
    ensure(curl_executable() is not None, 'curl.exe/curl is not installed or not in PATH')
    manifest = integrity()
    ensure(root.is_dir(), 'Project directory does not exist')
    for name in ['build.py', 'README.md', 'src/data.snapshot.json', 'src/weekly-meetings.json', 'monitoring/sources.json']:
        p = inside(root / name, root)
        ensure(p.is_file(), 'Missing project file: ' + name)
    ensure(sha(root / 'build.py') == manifest['project_build_sha256'], 'Project build script differs from the tested integration; update/revalidate the Skill package before running')
    expected = load(SKILL / 'references/sources.json')
    actual = load(root / 'monitoring/sources.json')
    ensure(actual.get('field') == 'diabetes', 'This version supports the diabetes pilot only')
    ensure(actual.get('sources') == expected['sources'], 'Source configuration differs from the packaged eight-source scope; review and repackage first')
    for name in ['runs', '待复核', 'state.json', 'latest.json', '.collector.lock.d']:
        inside(root / 'monitoring' / name, root)
    for folder in [root / 'monitoring/runs', root / 'monitoring/待复核']:
        if folder.exists():
            for p in folder.rglob('*'):
                if p.is_symlink():
                    inside(p, root)
    baseline = load(root / 'src/weekly-meetings.json')
    ensure(baseline.get('meetings') is not None and baseline.get('update_events') is not None, 'Formal calendar has an unsupported schema')
    return {'mode': 'check', 'result': 'ready', 'field': 'diabetes', 'sources_total': len(actual['sources']), 'network_requests': 0, 'schedule_created': False, 'project_root': str(root)}

def protected_hashes(root):
    names = ['build.py', 'README.md', 'index.html', 'dist/index.html', '会议与论文研究台_v2_分享包.zip', 'monitoring/sources.json', 'monitoring/collect.py', 'monitoring/promote.py', 'monitoring/schedule-status.json']
    result = {name: sha(root / name) if (root / name).is_file() else None for name in names}
    result.update({str(p.relative_to(root)): sha(p) for p in (root / 'src').rglob('*') if p.is_file()})
    return result

def run_folder(root, rid):
    ensure(bool(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]*', rid or '')), 'A valid run ID is required')
    run = inside(root / 'monitoring/runs' / rid, root)
    ensure(run.is_dir(), 'Run directory not found: ' + rid)
    return run

def verify(root, rid):
    run = run_folder(root, rid)
    required = ['manifest.json', 'fetch-report.json', 'observations.json', 'weekly-meetings.proposed.json', '复核报告.md', 'preview/index.html', 'preview/dist/index.html', 'preview/会议与论文研究台_v2_分享包.zip']
    for name in required:
        ensure(inside(run / name, root).is_file(), 'Run artifact missing: ' + name)
    m = load(run / 'manifest.json')
    report = load(run / 'fetch-report.json')
    proposed = load(run / 'weekly-meetings.proposed.json')
    observations = load(run / 'observations.json')
    cfg = load(SKILL / 'references/sources.json')
    sources = {s['id']: s for s in cfg['sources']}
    ensure(m['run_id'] == rid and m['status'] == 'awaiting_review', 'Run is not an unapplied review draft')
    ensure(sha(root / 'src/weekly-meetings.json') == m['formal_sha256'], 'Formal data changed since the run; rerun before reviewing')
    ensure(sha(run / 'weekly-meetings.proposed.json') == m['proposed_sha256'], 'Proposed calendar hash mismatch')
    rows = report['sources']
    ensure(len(rows) == len(sources) and {r['id'] for r in rows} == set(sources), 'Source coverage differs from configured scope')
    ensure(all((r['status'] in VALID_STATUSES for r in rows)), 'Unknown source status')
    good = [r for r in rows if r['status'] == 'checked']
    issues = [r for r in rows if r['status'] != 'checked']
    expected_status = 'complete' if not issues else 'partial' if good else 'failed'
    ensure(report['run_status'] == m['run_status'] == proposed['monitoring']['run_status'] == expected_status, 'Run status conflicts with actual source results')
    ensure(proposed['monitoring']['status'] == 'review_draft' and proposed['monitoring']['mode'] == 'draft_only', 'Only review-draft outputs are supported')
    ensure(proposed['monitoring']['sources_checked'] == len(good) and proposed['monitoring']['sources_total'] == len(rows), 'Source counts do not match the report')
    ensure(proposed['monitoring']['last_checked_at'] == report['checked_at'] == m['checked_at'], 'Check timestamps conflict')
    checked_on = datetime.fromisoformat(report['checked_at']).date().isoformat()
    ids = [o['id'] for o in observations]
    ensure(len(ids) == len(set(ids)), 'Conflicting or duplicate edition observations')

    def evidence(ev):
        ensure(ev['source_url'].startswith('https://'), 'Evidence must use an HTTPS official source')
        ensure(Path(ev['snapshot']).name == ev['snapshot'], 'Snapshot must be a local file name')
        snapshot = inside(run / ev['snapshot'], root)
        ensure(snapshot.is_file(), 'Evidence snapshot missing')
        source = next((r for r in rows if r.get('text_file') == ev['snapshot'] and r.get('final_url') == ev['source_url'] and (r['status'] == 'checked')), None)
        ensure(source is not None, 'Evidence is not linked to a successfully checked source')
        ensure(hashlib.sha256(norm(snapshot.read_text(encoding='utf-8')).encode()).hexdigest() == source.get('text_sha256'), 'Saved source text hash mismatch')
        ensure(norm(ev['quote']) in norm(snapshot.read_text(encoding='utf-8')), 'Evidence quote is absent from the saved source')
    for o in observations:
        ensure(o['fields'] == ['diabetes'], 'Unexpected field assignment')
        start, end = (date.fromisoformat(o['start']), date.fromisoformat(o['end']))
        ensure(start <= end, 'Invalid conference date range')
        ensure(o['id'] == o['source_id'].lower() + '-' + str(start.year), 'Conference ID does not match edition year')
        ensure(o.get('location') and o.get('evidence'), 'Meeting location or evidence missing')
        for ev in o['evidence']:
            evidence(ev)
    mids = [v['id'] for v in proposed['meetings']]
    ensure(len(mids) == len(set(mids)), 'Duplicate meetings in proposed calendar')
    events = proposed['update_events']
    ensure(len({e['id'] for e in events}) == len(events), 'Duplicate update events')
    this_run = [e for e in events if e.get('run_id') == rid]
    ensure(len(this_run) == m['events_this_run'], 'New event count does not match manifest')
    for e in this_run:
        ensure(e['meeting_id'] in mids and e['recorded_on'] == checked_on, 'Update identity or first-observed date mismatch')
        ensure(e.get('evidence') and e.get('changes'), 'Update lacks evidence or field-level changes')
        for ev in e['evidence']:
            evidence(ev)
    ensure((run / 'preview/index.html').read_bytes() == (run / 'preview/dist/index.html').read_bytes(), 'Preview HTML and dist differ')
    import zipfile
    with zipfile.ZipFile(run / 'preview/会议与论文研究台_v2_分享包.zip') as z:
        ensure(set(z.namelist()) == {'research-workbench-v2/index.html', 'research-workbench-v2/README.md'}, 'Unexpected files in preview share ZIP')
        ensure(z.read('research-workbench-v2/index.html') == (run / 'preview/index.html').read_bytes(), 'Preview ZIP contains different HTML')
    return {'mode': 'verify', 'result': 'verified', 'run_id': rid, 'run_status': expected_status, 'checked': len(good), 'total': len(rows), 'events_this_run': len(this_run), 'issues': [{'id': r['id'], 'status': r['status'], 'note': r.get('error', r.get('gap', ''))} for r in issues], 'report': str(run / '复核报告.md'), 'preview': str(run / 'preview/index.html'), 'latest_preview': str(root / 'monitoring/待复核/index.html'), 'schedule_created': False}

def execute(root, mode, rid=None):
    check = preflight(root)
    if mode == 'check':
        return check
    before = protected_hashes(root)
    if mode == 'verify':
        return verify(root, rid)
    if mode == 'replay':
        run_folder(root, rid)
    spec = importlib.util.spec_from_file_location('workbuddy_conference_collector', SKILL / 'scripts/collector_core.py')
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    with project_lock(root):
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                run = core.collect(root=root, replay=rid if mode == 'replay' else None)
        finally:
            ensure(protected_hashes(root) == before, 'Protected project files changed during execution; stop and inspect before using outputs')
    result = verify(root, run.name)
    result['mode'] = mode
    result['network_requests'] = 0 if mode == 'replay' else 'See fetch-report.json'
    result['protected_files_unchanged'] = True
    (run / 'skill-execution.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', required=True, type=Path)
    parser.add_argument('--mode', choices=['check', 'collect', 'replay', 'verify'], default='check')
    parser.add_argument('--run-id')
    args = parser.parse_args()
    try:
        ensure(args.mode in ['replay', 'verify'] or not args.run_id, '--run-id is only valid with replay or verify')
        result = execute(args.project_root.expanduser().resolve(), args.mode, args.run_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 3 if result.get('run_status') == 'failed' else 0
    except (ValidationError, OSError, ValueError, KeyError, ImportError, subprocess.SubprocessError) as e:
        print(json.dumps({'result': 'failed', 'error': str(e), 'schedule_created': False}, ensure_ascii=False), file=sys.stderr)
        return 2
if __name__ == '__main__':
    for stream in [sys.stdout, sys.stderr]:
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    os.environ['PYTHONUTF8'] = '1'
    raise SystemExit(main())
