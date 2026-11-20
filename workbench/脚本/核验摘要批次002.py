"""Verify the ten-abstract append, original-text provenance and preservation of previous rows."""
from pathlib import Path
from collections import Counter
import sqlite3,json,hashlib,re,xml.etree.ElementTree as ET,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];VERSION='BM:LOCAL-ABSTRACT-AUDIT:20261118:v2'
def norm(x):return re.sub(r'\s+',' ',x).strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rowhash(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
 out=ROOT/'规则与说明/标志物摘要批次002_2026-11-18';base=json.loads((out/'变更前表指纹.json').read_text());c=sqlite3.connect((ROOT/'数据库/marketing.db').as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
 assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not c.execute('PRAGMA foreign_key_check').fetchall()
 old_rows=0
 for n,b in base.items():
  assert c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?",(n,)).fetchone()[0]==b['schema'],n
  current=[dict(x) for x in c.execute('SELECT * FROM "'+n+'" ORDER BY rowid')]
  if n=='biomarker_review_versions':
   before_db=Path((out/'变更前备份位置.txt').read_text().strip())/'数据库/marketing.db';oldc=sqlite3.connect(before_db.as_uri()+'?mode=ro',uri=True);oldc.row_factory=sqlite3.Row
   old=[dict(x) for x in oldc.execute('SELECT * FROM biomarker_review_versions')];oldc.close()
   now={x['version_id']:x for x in current}
   for r in old:
    assert all(now[r['version_id']][k]==v for k,v in r.items() if k!='is_current');assert now[r['version_id']]['is_current']==0
  else:assert not (Counter(b['row_hashes'])-Counter(rowhash(x) for x in current)),n
  old_rows+=b['count']
 data=json.loads((ROOT/'标志物视图/标志物数据快照.json').read_text());counts=data['counts'];assert counts['biomarkers']==39 and counts['contexts']==43 and counts['evidence']==45
 assert counts['result_papers']==10 and counts['result_evidence']==21 and counts['reference_entities']==7 and counts['reference_result_papers']==2
 assert counts['paper_mentions']==15 and counts['report_mentions']==19 and counts['confirmed_studies']==0 and counts['external_validation']==0
 assert len(data['paper_assessments'])==10 and len({p['paper_id'] for p in data['paper_assessments']})==10
 batch=json.loads((ROOT/'原始资料/标志物摘要复核_2026-11-18/批次002_结构化证据.json').read_text());assert len(batch['papers'])==10
 E={e['evidence_id']:e for e in data['evidence']};source_count=0
 for p in batch['papers']:
  assert sha(ROOT/p['raw_path'])==p['raw_sha256'];raw=next(a for a in ET.parse(ROOT/p['raw_path']).getroot().findall('PubmedArticle') if a.findtext('./MedlineCitation/PMID')==p['pmid'])
  segments=[dict(label=x.get('Label',''),text=''.join(x.itertext())) for x in raw.findall('./MedlineCitation/Article/Abstract/AbstractText')]
  assert segments==p['abstract_segments']
  for r in p['records']:
   assert norm(r['original_excerpt']) in norm(segments[r['excerpt_segment']-1]['text'])
   e=E['EV:B2:'+p['pmid']+':'+r['biomarker_id'].split(':',1)[1]]
   assert e['paper_id']==p['paper_id'] and e['reading_level']=='abstract_only' and e['has_result_evidence'] and not e['has_external_validation'] and e['study_id'] is None
   assert e['review_status']=='abstract_checked' and e['material_id'] and e['original_excerpt']==r['original_excerpt']
   assert 'human' not in e['review_status'] and e['raw_sha256']==p['raw_sha256']
   source_count+=1
 assert source_count==21
 for e in data['evidence']:
  if not e['evidence_id'].startswith('EV:B2:'):assert e['evidence_role']=='title_mention_only' and not e['has_result_evidence']
 assert E['EV:B2:42821458:DKD_METH4']['validation_kind']=='validation_reported_unspecified'
 assert E['EV:B2:42461785:MACE_DNAM']['validation_kind']=='random_holdout_internal_test'
 assert E['EV:B2:42709505:MESA_PROTEINS']['validation_kind']=='longitudinal_discovery_cross_cohort_comparison'
 assert E['EV:B2:42423517:PANCREATIC_PVAT']['validation_kind']=='internal_imaging_assessment'
 assert E['EV:B2:42988924:CPEPTIDE6']['direction']=='inconclusive'
 assert E['EV:B2:42663510:HBA1C']['metrics'][0]['unit']=='个百分点'
 ctx={x['context_id']:x for x in data['contexts']}
 assert ctx[E['EV:B2:42969688:FE1']['context_id']]['sample_or_fraction'].startswith('粪便')
 assert ctx[E['EV:B2:42969688:IRT']['context_id']]['sample_or_fraction'].startswith('血清')
 components=[dict(x) for x in c.execute('SELECT * FROM biomarker_components')];assert {x['component_label'] for x in components}=={'SLC4A4','FSTL4','ICA1','PTK2'}
 assert c.execute("SELECT COUNT(*) FROM v_biomarker_audited_evidence WHERE has_result_evidence=1").fetchone()[0]==21
 assert c.execute("SELECT COUNT(*) FROM v_biomarker_audited_evidence WHERE has_external_validation=1").fetchone()[0]==0
 assert c.execute('SELECT COUNT(*) FROM v_biomarker_current_audits').fetchone()[0]==180
 assert c.execute("SELECT COUNT(*) FROM biomarker_record_audits WHERE version_id='BM:LOCAL-SOURCE-AUDIT:20261118:v1'").fetchone()[0]==107
 materials=0
 for rel,digest in c.execute('SELECT relative_path,sha256 FROM source_materials'):assert sha(ROOT/rel)==digest;materials+=1
 assert materials==453
 assert dict(c.execute('SELECT conference_id,COUNT(*) FROM reports GROUP BY conference_id'))=={'ADA2026':2539,'CDS2026':606}
 assert c.execute('SELECT COUNT(*) FROM literature_papers').fetchone()[0]==618
 papers=json.loads((ROOT/'论文视图/论文数据快照.json').read_text());assert papers['issue_analysis']['ranked_papers']==160 and len(papers['issue_analysis']['issues'])==51
 for html,manifest in [('标志物视图/index.html','标志物视图/生成记录.json'),('会议总入口/index.html','会议总入口/生成记录.json'),('会议视图/index.html','会议视图/生成记录.json'),('会议视图/ada.html','会议视图/ADA生成记录.json'),('论文视图/index.html','论文视图/生成记录.json')]:
  m=json.loads((ROOT/manifest).read_text());assert m['html_sha256']==sha(ROOT/html) and m['database_sha256']==sha(ROOT/'数据库/marketing.db')
 c.close();before=sha(ROOT/'数据库/marketing.db');cp=subprocess.run([sys.executable,str(ROOT/'脚本/导入摘要批次002.py')],capture_output=True,text=True);assert cp.returncode==0 and 'already_imported' in cp.stdout and before==sha(ROOT/'数据库/marketing.db')
 result=dict(result='passed',old_tables_preserved=len(base),old_rows_preserved=old_rows,old_review_versions_preserved=True,papers_processed=10,biomarker_result_evidence=21,raw_excerpt_checks=source_count,components=4,source_materials_verified=materials,reference_entities=7,independent_external_validation_not_overstated=True,idempotent_import=True,core_papers=618,ranked_papers=160,issues=51,new_collection=False,published=False)
 (out/'数据核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
