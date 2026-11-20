"""维护流程回归测试。所有修改都发生在临时副本，不改正式数据库。"""
from pathlib import Path
import json
import shutil
import sqlite3
import tempfile
import unittest
from 维护数据库 import (ROOT, SOURCE_PATH, MaintenanceError, sha, import_source,
                     confirm, verify_export, get_run, read_json, migration)


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cds-maint-test-')
        self.root = Path(self.temp.name) / 'center'
        self.root.mkdir()
        for name in ('数据库', '原始资料', '脚本'):
            shutil.copytree(ROOT / name, self.root / name, ignore=shutil.ignore_patterns('__pycache__'))
        (self.root / '规则与说明').mkdir()
        shutil.copy2(ROOT / '规则与说明/004_维护记录.sql', self.root / '规则与说明/004_维护记录.sql')
        shutil.copytree(ROOT / '会议视图/src', self.root / '会议视图/src')
        self.source = read_json(self.root / SOURCE_PATH)

    def tearDown(self):
        self.temp.cleanup()

    def imp(self, data=None):
        content = (self.root / SOURCE_PATH).read_bytes() if data is None else json.dumps(data, ensure_ascii=False).encode()
        return import_source(self.root, content, '隔离测试CDS.json')

    def dbsha(self):
        return sha(self.root / '数据库/marketing.db')

    def test_no_change_full_workflow_and_idempotence(self):
        c = sqlite3.connect(self.root / '数据库/marketing.db')
        tables = [x[0] for x in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'maintenance_%'")]
        before = {t: c.execute('SELECT * FROM '+t+' ORDER BY rowid').fetchall() for t in tables}; c.close()
        result = self.imp(); rid = result['meta']['run_id']
        self.assertEqual(result['diff']['summary']['changed_fields'], 0)
        self.assertEqual(confirm(self.root, rid)['result'], 'confirmed_no_change')
        after_confirm = self.dbsha()
        self.assertEqual(confirm(self.root, rid)['result'], 'already_confirmed')
        self.assertEqual(after_confirm, self.dbsha())
        report = verify_export(self.root, rid)
        self.assertEqual(report['result'], 'passed')
        self.assertEqual(report['counts']['reports'], 606)
        self.assertEqual(report['counts']['topics'], 58)
        self.assertEqual(after_confirm, self.dbsha())
        c = sqlite3.connect(self.root / '数据库/marketing.db')
        self.assertEqual(before, {t: c.execute('SELECT * FROM '+t+' ORDER BY rowid').fetchall() for t in tables}); c.close()
        second = self.imp()
        self.assertEqual(second['diff']['summary']['changed_fields'], 0)

    def test_real_field_update_source_and_export(self):
        self.source['items'][0]['time'] = '14:01-14:18'
        draft = self.imp(self.source); rid = draft['meta']['run_id']
        self.assertEqual(draft['diff']['summary']['changed_records'], 1)
        self.assertEqual(confirm(self.root, rid)['result'], 'confirmed_updated')
        c = sqlite3.connect(self.root / '数据库/marketing.db')
        row = c.execute("SELECT time_original,material_id FROM agenda_items WHERE agenda_item_id='CDS2026:AGENDA:0001'").fetchone()
        self.assertEqual(row[0], '14:01-14:18')
        source = c.execute('SELECT relative_path FROM source_materials WHERE material_id=?', (row[1],)).fetchone()[0]
        self.assertTrue(source.startswith('维护记录/批次/'))
        self.assertGreater(c.execute('SELECT COUNT(*) FROM maintenance_changes WHERE run_id=?', (rid,)).fetchone()[0], 2)
        c.close()
        self.assertEqual(verify_export(self.root, rid)['result'], 'passed')
        snapshot = read_json(self.root / '会议视图/会议数据快照.json')
        self.assertTrue(any(r['time_original'] == '14:01-14:18' for r in snapshot['reports']))

    def test_title_change_blocks_whole_batch(self):
        self.source['items'][0]['title'] += '【仅测试】'
        draft = self.imp(self.source); before = self.dbsha()
        self.assertGreater(draft['diff']['summary']['blocked'], 0)
        with self.assertRaises(MaintenanceError): confirm(self.root, draft['meta']['run_id'])
        self.assertEqual(before, self.dbsha())

    def test_stale_draft_does_not_overwrite(self):
        a = self.imp(); b = self.imp()
        confirm(self.root, a['meta']['run_id']); before = self.dbsha()
        with self.assertRaisesRegex(MaintenanceError, '已经改变'): confirm(self.root, b['meta']['run_id'])
        self.assertEqual(before, self.dbsha())

    def test_tampered_source_rejected(self):
        draft = self.imp(); before = self.dbsha()
        with (self.root / draft['meta']['source_path']).open('ab') as f: f.write(b' ')
        with self.assertRaisesRegex(MaintenanceError, '发生变化'): confirm(self.root, draft['meta']['run_id'])
        self.assertEqual(before, self.dbsha())

    def test_failed_update_rolls_back_atomically(self):
        c = sqlite3.connect(self.root / '数据库/marketing.db')
        c.execute("CREATE TRIGGER test_reject BEFORE UPDATE ON agenda_items BEGIN SELECT RAISE(ABORT,'injected failure'); END")
        c.commit(); c.close()
        self.source['items'][0]['time'] = '14:01-14:18'
        draft = self.imp(self.source); before = self.dbsha()
        with self.assertRaises(sqlite3.IntegrityError): confirm(self.root, draft['meta']['run_id'])
        self.assertEqual(before, self.dbsha())
        self.assertIsNone(get_run(self.root, draft['meta']['run_id'])['confirmation'])

    def test_failed_verification_keeps_old_export(self):
        draft = self.imp(); rid = draft['meta']['run_id']; confirm(self.root, rid)
        old = self.root / '会议视图/index.html'; old.write_text('old exported page')
        p = self.root / SOURCE_PATH
        with p.open('ab') as f: f.write(b' ')
        with self.assertRaisesRegex(MaintenanceError, '指纹改变'): verify_export(self.root, rid)
        self.assertEqual(old.read_text(), 'old exported page')
        self.assertEqual(get_run(self.root, rid)['verification']['result'], 'failed')

    def test_reordered_input_is_not_a_change(self):
        self.source['items'].reverse(); self.source['sessions'].reverse()
        draft = self.imp(self.source)
        self.assertEqual(draft['diff']['summary']['changed_records'], 0)
        self.assertEqual(draft['diff']['summary']['blocked'], 0)

    def test_confirmed_no_change_archive_is_still_verified(self):
        draft = self.imp(); rid = draft['meta']['run_id']; confirm(self.root, rid)
        with (self.root / draft['meta']['source_path']).open('ab') as f: f.write(b' ')
        with self.assertRaisesRegex(MaintenanceError, '本批归档原件'): verify_export(self.root, rid)
        self.assertFalse(get_run(self.root, rid)['verification']['exported'])

    def test_invalid_import_preserves_bytes(self):
        raw = b'{bad json'
        draft = import_source(self.root, raw, 'invalid.json')
        self.assertEqual(draft['meta']['status'], 'invalid')
        self.assertEqual((self.root / draft['meta']['source_path']).read_bytes(), raw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
