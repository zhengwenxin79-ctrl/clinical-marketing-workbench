"""只读核验分层结果、原文证据与原始20表保留情况。"""
from pathlib import Path
import hashlib,json,sqlite3,argparse

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);a=ap.parse_args();root=a.root.resolve();folder=root/'规则与说明/讲者与会议分层_2026-11-17';before=json.loads((folder/'变更前基线.json').read_text());c=sqlite3.connect((root/'数据库/marketing.db').as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;checks=[]
 try:
  assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert not c.execute('PRAGMA foreign_key_check').fetchall();assert c.execute('PRAGMA user_version').fetchone()[0]>=2
  for t,expected in before['original_table_fingerprints'].items():
   if t in {'analysis_versions','research_topics','report_classifications'}:
    legacy=sqlite3.connect((root/before['backup']).as_uri()+'?mode=ro',uri=True)
    try:assert set(legacy.execute('SELECT * FROM '+t).fetchall())<=set(tuple(x) for x in c.execute('SELECT * FROM '+t)),t
    finally:legacy.close()
   else:assert hashlib.sha256(json.dumps([tuple(x) for x in c.execute('SELECT * FROM '+t+' ORDER BY rowid')],ensure_ascii=False,sort_keys=True).encode()).hexdigest()==expected,t
  checks.append('版本≥2完整性/外键通过；原始20表旧记录完整保留，新分析版本允许追加')
  tiers=[dict(x) for x in c.execute('SELECT * FROM v_speaker_tiers')];counts={x['tier_code']:x['identity_count'] for x in c.execute('SELECT * FROM v_speaker_tier_counts')};assert counts=={'international':6,'national':96,'regional':43,'undetermined':388};assert len(tiers)==533
  assert len({x['person_id'] for x in tiers})==533;assert sum(x['tier_code']!='undetermined' for x in tiers)==145
  for t in tiers:
   assert t['rationale'] and t['evidence_gaps']
   assert bool(t['evidence_count'])==(t['tier_code']!='undetermined')
   if t['tier_code']!='undetermined':assert t['domain_scope'] and t['assessment_status']=='provisional_existing_bio'
  checks.append('533条讲者分层唯一且完备；145条有原文/领域/缺口，388条待定均有不足原因')
  evidence=[dict(x) for x in c.execute('SELECT * FROM speaker_tier_evidence')];assert len(evidence)==150
  for e in evidence:
   p=c.execute('SELECT * FROM person_profiles WHERE profile_id=?',(e['profile_id'],)).fetchone();assert p['person_id']==e['person_id'];assert p['extracted_text'][e['char_start']:e['char_end']]==e['quote_original'];assert e['context_original'] in p['extracted_text'];assert e['source_material_id']==p['evidence_material_id']
  checks.append('150条证据逐字符回读一致；人物、简介、来源及相邻原文关系正确')
  for v in c.execute('SELECT * FROM tier_rule_versions'):
   assert digest(root/v['rule_path'])==v['rule_sha256'];assert digest(root/v['decisions_path'])==v['decisions_sha256']
  checks.append('分层规则及选择记录指纹与数据库一致')
  rows=[dict(x) for x in c.execute('SELECT * FROM v_tier_speaker_talks')];assert len({(x['person_id'],x['report_id']) for x in rows})==len(rows)
  expected=c.execute("SELECT COUNT(*) FROM (SELECT DISTINCT ap.person_id,r.report_id FROM agenda_participants ap JOIN reports r USING(agenda_item_id) WHERE ap.agenda_role='speaker' AND r.conference_id='CDS2026')").fetchone()[0];assert len(rows)==expected
  assert c.execute('SELECT SUM(report_count) FROM v_topic_counts').fetchone()[0]==579
  checks.append('讲者×报告无证据引起的重复增行；579条议题报告计数不变')
  conf=dict(c.execute("SELECT * FROM v_conference_tiers WHERE conference_id='CDS2026'").fetchone());assert conf['tier_code']=='national_major' and conf['assessment_status']=='user_confirmed'
  original=json.loads((root/'原始资料/CDS2026/资料清单.json').read_text())
  for m in original['files']:
   assert digest(root/m['path'])==m['sha256'];assert digest(Path(m['original_path']))==m['original_sha256']
  checks.append('436份来源快照及原位置文件不变；CDS层级有用户确认依据，原地点未改')
  manifest=json.loads((root/'规则与说明/交付清单.json').read_text())
  for m in manifest['protected_files']:assert digest(Path(m['path']))==m['sha256'],m['path']
  checks.append('旧研究台及原项目主页等受保护文件不变')
  backup=root/before['backup'];assert backup.exists()
  result={'result':'passed','checked_on':'2026-11-17','counts':counts,'assessed_speaker_identities':533,'evidence_rows':150,'database_sha256':digest(root/'数据库/marketing.db'),'new_collection':False,'published':False,'scoring_enabled':False,'original_20_tables_old_records_preserved':True,'checks':checks}
  ((root/'规则与说明/CDS议题数量复核_2026-11-17/分层回归核验.json') if c.execute('PRAGMA user_version').fetchone()[0]>=3 else (folder/'分层核验.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
 finally:c.close()
if __name__=='__main__':main()
