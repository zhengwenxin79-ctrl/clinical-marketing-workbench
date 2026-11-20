"""ADA资料入库与导出独立核验；核对原31表记录保留、编号覆盖及各范围去重。"""
from pathlib import Path
from collections import Counter
import sqlite3,json,re,hashlib
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 r=ROOT;f=r/'规则与说明/ADA入库_2026-11-17';base=json.loads((f/'变更前基线.json').read_text());c=sqlite3.connect((r/'数据库/marketing.db').as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;old=sqlite3.connect((r/base['backup_database']).as_uri()+'?mode=ro',uri=True);checks=[]
 try:
  assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert not c.execute('PRAGMA foreign_key_check').fetchall();assert c.execute('PRAGMA user_version').fetchone()[0]==5
  for t in base['tables']:
   cols=','.join(x[1] for x in old.execute('PRAGMA table_info('+t+')'));assert set(old.execute('SELECT '+cols+' FROM '+t))<=set(tuple(x) for x in c.execute('SELECT '+cols+' FROM '+t)),t
  checks.append('版本5完整性和外键通过；入库前31表全部旧记录保留，维护日志未改')
  raw=json.loads((r/'原始资料/ADA2026/官方程序/ADA程序结构化.json').read_text());dbraw=[dict(x) for x in c.execute("SELECT * FROM agenda_items WHERE conference_id='ADA2026' ORDER BY source_order")];assert len(dbraw)==2859
  for row in dbraw:assert json.loads(row['raw_json'])==raw['items'][row['source_order']];assert row['title_original']==raw['items'][row['source_order']]['title']
  text=(r/'原始资料/ADA2026/官方程序/ADA2026_日程.txt').read_text();codes=set(re.findall(r'\b\d{3,4}-(?:OR|P|LB)\b',text));rpts=[dict(x) for x in c.execute("SELECT * FROM v_report_detail WHERE conference_id='ADA2026'")];rcodes={x['source_report_code'] for x in rpts if not x['source_report_code'].startswith('TALK-')};assert codes==rcodes and len(codes)==2102
  assert len(rpts)==2539;occ=[dict(x) for x in c.execute('SELECT * FROM conference_program_occurrences')];assert len(occ)==2621;assert len(occ)-len(rpts)==82
  assert len({x['agenda_item_id'] for x in occ})==2621;assert sum(x['is_primary'] for x in occ)==2539;assert len(c.execute("SELECT * FROM sessions WHERE conference_id='ADA2026'").fetchall())==242
  checks.append('2859条结构化原题逐条回读；原程序2102个摘要编号全部捕获；2621次展示按同号去重为2539报告')
  cv=dict(c.execute("SELECT * FROM conference_coverage WHERE conference_id='ADA2026'").fetchone());assert sha(r/cv['rules_path'])==cv['rules_sha256'];assert sha(r/cv['plan_path'])==cv['plan_sha256']
  assert c.execute('SELECT COUNT(*) FROM conference_page_audit').fetchone()[0]==385;assert c.execute("SELECT COUNT(*) FROM conference_page_audit WHERE parse_status='unparsed_satellite_or_metadata'").fetchone()[0]==12
  topics=[dict(x) for x in c.execute('SELECT * FROM v_ada_quantity_topic_counts')];assert len(topics)==56 and sum(x['report_count'] for x in topics)==2049
  assert c.execute("SELECT COUNT(*) FROM report_classifications WHERE analysis_version_id=? AND eligible=0",(cv['analysis_version_id'],)).fetchone()[0]==490
  assert len(c.execute('SELECT * FROM v_ada_quantity_board_counts').fetchall())==12;assert c.execute('SELECT SUM(report_count) FROM v_ada_quantity_board_counts').fetchone()[0]==2049
  checks.append('385页逐页覆盖记录；12页卫星/活动留缺口；56议题2049初分+490待归类=2539')
  for t in topics:
   ids={x[0] for x in c.execute('SELECT report_id FROM report_classifications WHERE analysis_version_id=? AND primary_topic_id=?',(t['analysis_version_id'],t['topic_id']))};assert len(ids)==t['report_count'];assert t['report_share_percent']==round(100*len(ids)/2049,2)
   fct=dict(c.execute('SELECT * FROM v_ada_quantity_topic_facts WHERE topic_id=?',(t['topic_id'],)).fetchone());fmts=Counter(x['report_format'] for x in rpts if x['report_id'] in ids)
   assert [fct['plenary_count'],fct['invited_count'],fct['oral_count'],fct['poster_count'],fct['late_poster_count']]==[fmts[k] for k in ['大会报告','专题报告','论文发言','海报报告','晚期突破海报']]
   pids={x[0] for rid in ids for x in c.execute("SELECT ap.person_id FROM conference_program_occurrences o JOIN agenda_participants ap USING(agenda_item_id) WHERE o.report_id=? AND ap.agenda_role='speaker'",(rid,))};layers=Counter(c.execute("SELECT tier_code FROM v_speaker_tiers WHERE conference_id='ADA2026' AND person_id=?",(pid,)).fetchone()[0] for pid in pids)
   assert fct['speaker_identity_count']==len(pids);assert [fct['international_count'],fct['national_count'],fct['regional_count'],fct['undetermined_count']]==[layers[k] for k in ['international','national','regional','undetermined']]
   sessions={x[0] for rid in ids for x in c.execute('SELECT a.session_id FROM conference_program_occurrences o JOIN agenda_items a USING(agenda_item_id) WHERE o.report_id=?',(rid,))};assert len(sessions)==fct['session_count']
  talks=c.execute('SELECT topic_id,person_id,report_id FROM v_ada_quantity_speaker_talks').fetchall();assert len(talks)==len(set(tuple(x) for x in talks))
  checks.append('56议题独立回算数量、报告类型、全部出现专题、三级+待定讲者去重；多展示/多角色未重复加人')
  layers={x['tier_code']:x['identity_count'] for x in c.execute("SELECT * FROM v_speaker_tier_counts WHERE conference_id='ADA2026'")};assert layers=={'national':2,'undetermined':2094}
  for e in c.execute("SELECT * FROM speaker_tier_evidence WHERE conference_id='ADA2026'"):
   pr=c.execute('SELECT * FROM person_profiles WHERE profile_id=?',(e['profile_id'],)).fetchone();assert pr['person_id']==e['person_id'] and pr['has_substantive_bio']==0;assert pr['extracted_text'][e['char_start']:e['char_end']]==e['quote_original']
  checks.append('2096条程序姓名身份：2条程序角色暂定、2094待定；角色摘录可回读且不计为完整简介')
  snapshot=json.loads((r/'会议视图/ADA会议数据快照.json').read_text());assert snapshot['meta']['database_sha256']==sha(r/'数据库/marketing.db')
  for k,co in snapshot['quantity']['cohorts'].items():
   expected=[x for x in snapshot['reports'] if not co['formats'] or x['report_format'] in co['formats']];assert co['all_reports']==len(expected)
   den=sum(bool(x['classification']['eligible']) for x in expected);assert den==co['denominator'];seen=[]
   for t in co['topics']:
    selected=[x for x in expected if x['classification']['primary_topic_id']==t['topic_id']];assert {x['report_id'] for x in selected}==set(t['report_ids']);assert len(selected)==t['report_count'];assert t['report_share_percent']==round(100*len(selected)/den,2);seen.extend(t['report_ids'])
   assert len(seen)==len(set(seen))==den
  checks.append('全部/口头专题大会/海报三种范围独立核算：2049/677/1372条初分，分母及去重匹配')
  assert c.execute("SELECT COUNT(*) FROM curated_research_records WHERE conference_id='ADA2026'").fetchone()[0]==27;assert c.execute('SELECT COUNT(*) FROM related_paper_abstracts').fetchone()[0]==14
  assert c.execute("SELECT COUNT(*) FROM reports WHERE conference_id='ADA2026' AND has_results<>0").fetchone()[0]==0
  connect=next(x for x in snapshot['reports'] if x['source_report_code']=='1170-OR');assert connect['participants'][0]['name_original'].startswith('Tom Martens');assert connect['research_records'][0]['papers'][0]['first_author']=='Tamara K Oser'
  checks.append('27精选记录与14论文摘要独立保存；CONNECT程序讲者Tom Martens与论文第一作者分开；未将论文结果变为程序结果')
  for x in c.execute("SELECT * FROM source_materials WHERE import_id LIKE 'ADA2026%'"):assert sha(r/x['relative_path'])==x['sha256'];assert sha(Path(x['original_path']))==x['original_sha256']
  for x in json.loads((r/'原始资料/CDS2026/资料清单.json').read_text())['files']:assert sha(r/x['path'])==x['sha256'];assert sha(Path(x['original_path']))==x['original_sha256']
  for x in json.loads((r/'规则与说明/交付清单.json').read_text())['protected_files']:assert sha(Path(x['path']))==x['sha256']
  assert c.execute('SELECT SUM(report_count) FROM v_cds_quantity_topic_counts').fetchone()[0]==579;assert c.execute('SELECT COUNT(*) FROM v_cds_quantity_topic_counts').fetchone()[0]==58
  checks.append('ADA原件及CDS436份原件/旧研究台未改；CDS58议题579报告保留')
  result=dict(result='passed',checked_on='2026-11-17',database_sha256=sha(r/'数据库/marketing.db'),summary=json.loads(cv['coverage_json']),speaker_tiers=layers,checks=checks,new_collection=False,published=False,scoring_enabled=False,old_records_preserved=True);(r/'规则与说明/ADA入库_2026-11-17/ADA入库核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
 finally:c.close();old.close()
if __name__=='__main__':main()
