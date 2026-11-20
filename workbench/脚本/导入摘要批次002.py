"""Append the curated ten-abstract batch transactionally; retain the entire previous audit version."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import sqlite3,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
VERSION='BM:LOCAL-ABSTRACT-AUDIT:20261118:v2';PREVIOUS='BM:LOCAL-SOURCE-AUDIT:20261118:v1';RUN='RUN:P03:EXISTING-ABSTRACTS-002'
def enc(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def digest(x):return hashlib.sha256(enc(x).encode()).hexdigest()
def main():
 proof=ROOT/'原始资料/标志物摘要复核_2026-11-18/批次002_结构化证据.json';batch=json.loads(proof.read_text());payload_hash=digest(batch)
 c=sqlite3.connect(ROOT/'数据库/marketing.db');c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
 current=c.execute('SELECT version_id FROM biomarker_review_versions WHERE is_current=1').fetchone()[0]
 old=c.execute('SELECT input_sha256 FROM biomarker_review_versions WHERE version_id=?',(VERSION,)).fetchone()
 if old:
  assert old[0]==payload_hash,'Curated input changed: create another version'
  assert current==VERSION,'A later audit is current; do not replay an older version'
  print(json.dumps(dict(result='already_imported',version=VERSION,new_collection=False,published=False)));c.close();return
 assert current==PREVIOUS,'Unexpected predecessor'
 for p in batch['papers']:assert hashlib.sha256((ROOT/p['raw_path']).read_bytes()).hexdigest()==p['raw_sha256']
 now=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds');today=now[:10];added=[];materials={}
 def addrow(table,row):
  keys=list(row);c.execute('INSERT INTO '+table+' ('+','.join(keys)+') VALUES ('+','.join('?' for _ in keys)+')',[row[k] for k in keys]);return row
 def audit(kind,id,row,review,basis):added.append((VERSION,kind,id,digest(row),enc(review),basis))
 try:
  c.execute('BEGIN IMMEDIATE')
  c.execute('''CREATE TABLE IF NOT EXISTS biomarker_components (biomarker_id TEXT NOT NULL REFERENCES biomarkers(biomarker_id),paper_id TEXT NOT NULL REFERENCES literature_papers(paper_id),component_label TEXT NOT NULL,component_kind TEXT NOT NULL,definition_status TEXT NOT NULL,source_locator TEXT NOT NULL,PRIMARY KEY(biomarker_id,paper_id,component_label))''')
  iid='BM-ABSTRACTS-002:'+payload_hash[:16]
  addrow('import_batches',dict(import_id=iid,fingerprint=payload_hash,imported_on=today,imported_at=now,source_observed_on='2026-11-17',source_manifest=str(proof.relative_to(ROOT)),importer_version='biomarker-abstracts-002:v1',new_collection=0,notes='对已有PubMed XML做10篇摘要复核；没有联网。原始文件保留，结果不等于全文或外部验证。'))
  for p in batch['papers']:
   rel=p['raw_path']
   if rel in materials:continue
   file=ROOT/rel;oldmat=c.execute('SELECT material_id,sha256 FROM source_materials WHERE relative_path=?',(rel,)).fetchone()
   if oldmat:assert oldmat['sha256']==p['raw_sha256'];materials[rel]=oldmat['material_id'];continue
   mid='MAT:BM2:XML:'+p['raw_sha256'][:20]
   addrow('source_materials',dict(material_id=mid,import_id=iid,relative_path=rel,sha256=p['raw_sha256'],byte_size=file.stat().st_size,material_kind='existing_pubmed_xml',source_url='https://pubmed.ncbi.nlm.nih.gov/',reading_level='本地PubMed XML中的原始摘要；未全文精读',source_observed_on='2026-11-17',original_path=str(file),original_sha256=p['raw_sha256'],is_derived=0));materials[rel]=mid
  proofsha=hashlib.sha256(proof.read_bytes()).hexdigest();proofid='MAT:BM2:PROOF:'+proofsha[:20]
  addrow('source_materials',dict(material_id=proofid,import_id=iid,relative_path=str(proof.relative_to(ROOT)),sha256=proofsha,byte_size=proof.stat().st_size,material_kind='derived_abstract_curation',source_url=None,reading_level='本地摘要人工可复核的AI结构化提炼；非新采集',source_observed_on=today,original_path=str(proof),original_sha256=proofsha,is_derived=1))
  # Clone all prior reviewed projections; the original 107 rows under v1 are untouched.
  addrow('biomarker_review_versions',dict(version_id=VERSION,created_at=now,input_sha256=payload_hash,rule_text='继承v1题名审核，新增10篇原始摘要。按报告/论文ID去重，常规终点单列；未核独立性不计独立研究；验证不明不升为外部验证。',is_current=0))
  c.execute('INSERT INTO biomarker_record_audits SELECT ?,record_kind,record_id,original_row_sha256,reviewed_json,basis FROM biomarker_record_audits WHERE version_id=?',(VERSION,PREVIOUS))
  entities={};contexts=[];evidence=[];review_ids=[]
  for p in batch['papers']:
   pmid=p['pmid'];mid=materials[p['raw_path']];ev_ids=[]
   for r in p['records']:
    bid=r['biomarker_id'];suffix=bid.split(':',1)[1]
    if bid not in entities:
     b=addrow('biomarkers',dict(biomarker_id=bid,standard_name=r['standard_name'],biomarker_type=r['biomarker_type'],is_member_defined=r['is_member_defined'],review_status='candidate',created_at=now,notes=r['entity_note']));entities[bid]=b
     addrow('biomarker_aliases',dict(alias_id='AL:B2:'+suffix,biomarker_id=bid,alias_name=r['name_zh'],language='zh',source='本地摘要复核批次002',review_status='unverified'))
     audit('entity',bid,b,dict(name_zh=r['name_zh'],standard_name=r['standard_name'],biomarker_type=r['biomarker_type'],is_member_defined=r['is_member_defined'],review_status='candidate',notes=r['entity_note'],entity_note=r['entity_note'],reference_endpoint=r['reference_endpoint'],source_batch=batch['batch_id']), '名称及研究用途按本地原始摘要核对；常规参照、组合定义完整度分别标注。')
    for comp in r['components']:
     addrow('biomarker_components',dict(biomarker_id=bid,paper_id=p['paper_id'],component_label=comp,component_kind='gene-associated locus label',definition_status='基因对应位点名称已给；具体CpG坐标和权重待核',source_locator=p['source_locator']+f'/AbstractText[{r["excerpt_segment"]}]'))
    cid='CTX:B2:'+pmid+':'+suffix
    ctx=addrow('biomarker_contexts',dict(context_id=cid,biomarker_id=bid,domain='内分泌代谢',disease_or_complication=r['disease_or_complication'],target_population=r['target_population'],sample_or_fraction=r['sample_or_fraction'],clinical_use=r['clinical_use'],target_outcome=p['clinical_increment'],time_point='依摘要研究设计；详见证据',context_status='provisional'));contexts.append(ctx)
    patch=dict(ctx,category=r['category'],scope_label='摘要支持的研究用途；临床适用性仍需独立确认',translation_status=p['translation_status'],priority_reason=p['priority_reason'],evidence_needed=p['limitations'],result_state='abstract_results',validation_label=p['validation_label'],validation_kind=p['validation_kind'],validation_detail=p['validation_detail'],clinical_increment=p['clinical_increment'],reference_endpoint=r['reference_endpoint'],source_batch=batch['batch_id'])
    audit('context',cid,ctx,patch,'按摘要区分疾病、人群、样本、用途及验证阶段；没有继承其他指标的临床标签。')
    eid='EV:B2:'+pmid+':'+suffix;locator=p['source_locator']+f'/AbstractText[{r["excerpt_segment"]}] ({r["excerpt_label"] or "UNLABELLED"})'
    ev=addrow('biomarker_evidence',dict(evidence_id=eid,context_id=cid,report_id=None,paper_id=p['paper_id'],study_id=None,evidence_role='background_reference' if r['reference_endpoint'] else 'primary_finding',reading_level='abstract_only',method=r['method'],sample_size_or_cohort=p['sample_size'],result_text=r['result_text'],original_excerpt=r['original_excerpt'],direction=r['direction'],validation_type=p['validation_type'],metric_value_or_interval=enc(r['metrics']),comparison_method=p['clinical_increment'],material_id=mid,source_locator=locator,review_version=VERSION,review_status='auto_extracted',reviewed_on=today));evidence.append(ev);ev_ids.append(eid)
    patch=dict(ev,review_status='abstract_checked',reviewer_kind='AI逐篇本地摘要复核；未取得全文或人工签核',has_result_evidence=True,has_external_validation=False,source_kind='paper',source_title=p['title'],source_url=p['source_url'],raw_path=p['raw_path'],raw_sha256=p['raw_sha256'],source_locator=locator,independence_status='not_established',validation_label=p['validation_label'],validation_kind=p['validation_kind'],validation_detail=p['validation_detail'],external_validation_status=p['external_validation_status'],metrics=r['metrics'],method_excerpt=r['method_excerpt'],paper_summary=p['summary'],paper_limitations=p['limitations'],study_design=p['study_design'],cohort_name=p['cohort_name'],reference_endpoint=r['reference_endpoint'],source_batch=batch['batch_id'],normalized_abstract_sha256=p['normalized_abstract_sha256'],excerpt_label=r['excerpt_label'],excerpt_segment=r['excerpt_segment'])
    audit('evidence',eid,ev,patch,'结果摘录逐一对照本地PubMed XML；只反映摘要层证据，不补全文、未指明的效应或验证独立性。')
   rid='REV:B2:'+pmid
   rev=addrow('biomarker_extraction_reviews',dict(review_id=rid,run_id=RUN,source_kind='paper',source_id=p['paper_id'],outcome_status='positive',basis_detail='已有英文摘要已逐篇提取；'+('常规参照/终点研究单列。' if all(r['reference_endpoint'] for r in p['records']) else '指标及用途已核，验证按摘要明示记录。'),rule_version=VERSION,batch_id=batch['batch_id'],created_at=now));review_ids.append(rid)
   assessment={k:p[k] for k in ['paper_id','title','study_design','sample_size','cohort_name','method','summary','validation_type','validation_kind','validation_label','validation_detail','external_validation_status','clinical_increment','limitations','translation_status','priority_reason','raw_path','source_locator','raw_sha256','normalized_abstract_sha256']}
   assessment.update(evidence_ids=ev_ids,reference_only=all(r['reference_endpoint'] for r in p['records']),other_outcomes=p.get('other_outcomes'))
   audit('extraction',rid,rev,dict(outcome_status='abstract_results',reading_level='abstract_only',review_status='abstract_checked',basis_detail=rev['basis_detail'],paper_assessment=assessment), '完成10篇中一篇的原始摘要复核，保留逐篇恢复点。')
  run=addrow('biomarker_analysis_runs',dict(run_id=RUN,source_manifest_or_version=str(proof.relative_to(ROOT)),analysis_window='既有2026-08-17至2026-11-17论文池内10篇选定样本；非全面采集',inclusion_rules='逐篇原始摘要；常规终点单列；未核外部验证/独立研究不升级',processed_denominator=10,gaps_count=10,input_hash=payload_hash,generated_at=now,statistical_metrics=enc(dict(papers=10,new_entities=len(entities),new_contexts=len(contexts),new_evidence=len(evidence),reference_entities=sum(r['notes'].startswith('常规') for r in entities.values()),external_validation_confirmed=0))))
  audit('run',RUN,run,dict(run,statistical_metrics=dict(papers=10,new_entities=len(entities),new_contexts=len(contexts),new_evidence=len(evidence),reference_entities=7,external_validation_confirmed=0,full_text_read=0)),'真实批次统计；验证未明者不补0研究效果，外部验证仅表示当前未确认。')
  c.executemany('INSERT INTO biomarker_record_audits VALUES(?,?,?,?,?,?)',added)
  assert len(entities)==20 and len(contexts)==21 and len(evidence)==21
  c.execute('UPDATE biomarker_review_versions SET is_current=0 WHERE version_id=?',(PREVIOUS,));c.execute('UPDATE biomarker_review_versions SET is_current=1 WHERE version_id=?',(VERSION,))
  assert not c.execute('PRAGMA foreign_key_check').fetchall()
  c.commit()
 except BaseException:c.rollback();raise
 result=dict(result='imported',version=VERSION,papers=10,entities_added=len(entities),contexts_added=len(contexts),evidence_added=len(evidence),audit_records_added=len(added),source_materials_added=5,new_collection=False,published=False,source_batch=batch['batch_id'])
 out=ROOT/'规则与说明/标志物摘要批次002_2026-11-18';(out/'导入记录.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');c.close();print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
