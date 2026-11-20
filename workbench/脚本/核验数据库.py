"""只读核验数据与本地证据。--check-originals 可核原机器的原文件保留情况。"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sqlite3

def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--database',type=Path);ap.add_argument('--check-originals',action='store_true');ap.add_argument('--report',type=Path);args=ap.parse_args();root=args.root.resolve();db=args.database.resolve() if args.database else root/'数据库/marketing.db';m=read(root/'原始资料/CDS2026/资料清单.json');checks=[];c=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
 try:
  assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert not c.execute('PRAGMA foreign_key_check').fetchall();checks.append('SQLite完整性与全部外键通过')
  counts={t:c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t, in c.execute("SELECT name FROM sqlite_schema WHERE type='table'")}
  assert counts['conference_editions']==1 and counts['sessions']==148 and counts['agenda_items']==797 and counts['reports']==606
  assert counts['source_materials']==len(m['files'])==436 and counts['person_profiles']==230
  checks.append('会议1届、148专题、797日程、606学术报告、230简介读取记录与436材料齐全')
  raw=read(root/'原始资料/CDS2026/官方日程/CDS_全日程结构化.json');classified=read(root/'原始资料/CDS2026/处理依据/逐报告归类与计分.json');reviewed=read(root/'原始资料/CDS2026/处理依据/CDS标志物逐报告复核台账.json')
  for row in c.execute('SELECT source_order,raw_json FROM agenda_items'):assert json.loads(row['raw_json'])==raw['items'][row['source_order']]
  assert c.execute('SELECT COUNT(*) FROM agenda_participants').fetchone()[0]==sum(len(x['people']) for x in raw['items'])
  assert c.execute('SELECT COUNT(*) FROM session_chairs').fetchone()[0]==sum(len(x['chairs']) for x in raw['sessions'])
  expected={a['code'] for a in raw['items'] if a['kind'] in ['大会报告','专题报告','论文发言']};assert {r[0] for r in c.execute('SELECT source_report_code FROM reports')}==expected
  assert c.execute('SELECT COUNT(*) FROM v_report_detail').fetchone()[0]==606
  checks.append('797条原始JSON逐条回读一致，人员/主持关系完整，报告视图无重复增行')
  assert c.execute('SELECT COUNT(*) FROM v_topic_counts').fetchone()[0]==44 and c.execute('SELECT COUNT(*) FROM v_board_counts').fetchone()[0]==12
  assert c.execute('SELECT SUM(report_count) FROM v_topic_counts').fetchone()[0]==579;assert c.execute('SELECT SUM(report_count) FROM v_board_counts').fetchone()[0]==579
  expected_counts=Counter(x['topic_id'] for x in classified if x['scope']=='入榜')
  for row in c.execute('SELECT legacy_topic_id,report_count,denominator,report_share_percent FROM v_topic_counts'):
   assert row['report_count']==expected_counts[row['legacy_topic_id']] and row['denominator']==579
   assert row['report_share_percent']==round(100*row['report_count']/579,2)
  assert c.execute('SELECT SUM(in_denominator) FROM biomarker_title_reviews').fetchone()[0]==80
  assert c.execute('SELECT COUNT(DISTINCT report_id) FROM legacy_marker_bindings').fetchone()[0]==7
  assert c.execute('SELECT COUNT(*) FROM biomarker_title_reviews WHERE in_denominator=1 AND report_id NOT IN(SELECT report_id FROM legacy_marker_bindings)').fetchone()[0]==73
  assert Counter({r['review_status']:r['report_count'] for r in c.execute('SELECT * FROM v_biomarker_title_scope')})==Counter(x['status'] for x in reviewed)
  checks.append('既有44议题/12板块复算579，标志物复核80=7已绑定+73待细分；两个分母分开')
  assert counts['studies']==0 and counts['report_study_links']==0
  assert c.execute('SELECT COUNT(*) FROM reports WHERE has_results<>0 OR result_text IS NOT NULL').fetchone()[0]==0
  assert c.execute('SELECT COUNT(*) FROM analysis_versions WHERE scoring_enabled<>0').fetchone()[0]==0
  assert c.execute('SELECT COUNT(DISTINCT person_id) FROM academic_role_claims').fetchone()[0]==126
  assert c.execute("SELECT COUNT(DISTINCT l.person_id) FROM v_leader_talks l JOIN report_classifications rc USING(report_id) WHERE rc.eligible=1").fetchone()[0]==115
  assert c.execute("SELECT COUNT(*) FROM person_profiles WHERE read_status='unavailable' AND raw_material_id IS NULL").fetchone()[0]==3
  assert c.execute('SELECT SUM(has_substantive_bio) FROM person_profiles').fetchone()[0]==196
  checks.append('未把606报告认定为独立研究；结果留空、评分未导入；126角色来源/115入榜关联角色与3失败简介保留')
  missing_originals=[]
  for f in m['files']:
   p=root/f['path'];assert p.is_file() and sha(p)==f['sha256'],f['path'];assert c.execute('SELECT sha256 FROM source_materials WHERE relative_path=?',(f['path'],)).fetchone()[0]==f['sha256']
   if args.check_originals:
    old=Path(f['original_path'])
    if not old.is_file():missing_originals.append(str(old))
    else:assert sha(old)==f['original_sha256'],str(old)
  if args.check_originals:assert not missing_originals,missing_originals
  checks.append('436份随包材料指纹一致、数据库路径均可回溯'+('；原机器原始文件指纹保持' if args.check_originals else ''))
  report=dict(result='passed',verified_on='2026-11-17',database=str(db),database_sha256=sha(db),source_observed_on='2026-11-16',counts=counts,checks=checks,new_collection=False,published=False)
  if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  print(json.dumps(report,ensure_ascii=False,indent=2))
 finally:c.close()
if __name__=='__main__':main()
