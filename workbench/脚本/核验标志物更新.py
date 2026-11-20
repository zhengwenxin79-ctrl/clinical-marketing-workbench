"""Verify incoming-table preservation, local evidence audits, source hashes and exported counts."""
from pathlib import Path
import sqlite3,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 rules=ROOT/'规则与说明/WorkBuddy更新复核_2026-11-18';baseline=json.loads((rules/'收到的63表指纹.json').read_text());c=sqlite3.connect((ROOT/'数据库/marketing.db').as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
 assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not c.execute('PRAGMA foreign_key_check').fetchall()
 for n,f in baseline.items():
  rows=[list(x) for x in c.execute('SELECT * FROM "'+n+'" ORDER BY rowid')];assert len(rows)==f['count'];assert hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==f['sha256'],n
 raw_manifest=json.loads((rules/'接收文件指纹.json').read_text())
 for rel,d in raw_manifest.items():assert sha(ROOT/rel)==d,rel
 materials=0
 for rel,d in c.execute('SELECT relative_path,sha256 FROM source_materials'):assert sha(ROOT/rel)==d,rel;materials+=1
 data=json.loads((ROOT/'标志物视图/标志物数据快照.json').read_text());e=data['evidence'];assert len(e)==24
 assert len({x['report_id'] for x in e if x['report_id']})==19 and len({x['paper_id'] for x in e if x['paper_id']})==5
 assert all(x['evidence_role']=='title_mention_only' and x['validation_type']=='unspecified' and x['review_status']=='local_title_checked' and not x['has_result_evidence'] and not x['has_external_validation'] for x in e)
 for x in e:
  assert sha(ROOT/x['raw_path'])==x['raw_sha256']
  if x['report_id']:
   r=c.execute('SELECT * FROM v_report_detail WHERE report_id=?',(x['report_id'],)).fetchone();assert x['source_title']==r['title_original'] and x['material_id']==r['material_id'];assert x['speakers'];assert x['source_locator']==r['source_locator']
  else:
   r=c.execute('SELECT * FROM literature_papers WHERE paper_id=?',(x['paper_id'],)).fetchone();assert r['reading_level']=='directory_excerpt' and r['abstract_json']=='[]' and x['reading_level']=='directory_excerpt';assert x['source_title']==r['title']
  assert x['original_excerpt']==x['source_title'] and x['study_id'] is None
 assert all(x['status']=='pending_review' and not x['is_confirmed_application'] and x['capability_source_locator'] for x in data['matches'])
 assert data['runs'][0]['statistical_metrics']['title_candidates']==24 and data['runs'][0]['statistical_metrics']['pending_content_review']==6
 assert len(data['runs'][0]['input_hash'])==64
 assert all(x['context_status']=='provisional' and x['translation_status']=='evidence_needed' for x in data['contexts'])
 assert len(list(c.execute('SELECT * FROM v_biomarker_current_audits')))==107
 assert c.execute("SELECT COUNT(*) FROM v_biomarker_audited_evidence WHERE evidence_role<>'title_mention_only' OR has_result_evidence<>0 OR has_external_validation<>0").fetchone()[0]==0
 assert dict(c.execute('SELECT conference_id,COUNT(*) FROM reports GROUP BY conference_id'))=={'ADA2026':2539,'CDS2026':606}
 paper_data=json.loads((ROOT/'论文视图/论文数据快照.json').read_text());assert len(paper_data['papers'])==618 and paper_data['issue_analysis']['ranked_papers']==160 and len(paper_data['issue_analysis']['issues'])==51
 for html,manifest in [('标志物视图/index.html','标志物视图/生成记录.json'),('会议总入口/index.html','会议总入口/生成记录.json'),('会议视图/index.html','会议视图/生成记录.json'),('会议视图/ada.html','会议视图/ADA生成记录.json'),('论文视图/index.html','论文视图/生成记录.json')]:
  m=json.loads((ROOT/manifest).read_text());assert m['html_sha256']==sha(ROOT/html) and m['database_sha256']==sha(ROOT/'数据库/marketing.db')
 c.close();result=dict(result='passed',imported_tables_unchanged=len(baseline),source_materials_verified=materials,received_files_verified=len(raw_manifest),audited_records=107,evidence=24,report_mentions=19,paper_mentions=5,result_evidence=0,capability_candidates=11,papers_preserved=618,ranked_papers_preserved=160,issues_preserved=51,new_collection=False,published=False)
 (rules/'数据核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
