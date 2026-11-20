"""Read-only Biomarker page generator. Uses the current audited projection, never imported claims directly."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
from urllib.parse import quote
import json,sqlite3,hashlib
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 db=ROOT/'数据库/marketing.db';before=sha(db);c=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON')
 def rows(t):return [dict(x) for x in c.execute('SELECT * FROM '+t+' ORDER BY rowid')]
 audits={(x['record_kind'],x['record_id']):json.loads(x['reviewed_json']) for x in c.execute('SELECT * FROM v_biomarker_current_audits')}
 def project(kind,x,id):
  patch=audits.get((kind,x[id]));assert patch is not None,(kind,x[id])
  return dict(x,**patch,imported_claim=x)
 entities=[project('entity',x,'biomarker_id') for x in rows('biomarkers')]
 components=rows('biomarker_components') if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='biomarker_components'").fetchone() else []
 for b in entities:
  b.setdefault('reference_endpoint',False);b['components']=[x for x in components if x['biomarker_id']==b['biomarker_id']]
 contexts=[project('context',x,'context_id') for x in rows('biomarker_contexts')]
 evidence=[project('evidence',x,'evidence_id') for x in rows('biomarker_evidence')]
 for e in evidence:
  if e['report_id']:
   r=dict(c.execute('SELECT * FROM v_report_detail WHERE report_id=?',(e['report_id'],)).fetchone());conf=dict(c.execute('SELECT * FROM conference_editions WHERE conference_id=?',(r['conference_id'],)).fetchone())
   e.update(conference_id=r['conference_id'],region=conf['region'],conference_name=conf['name_original'],date=r['local_date'],report_format=r['report_format'],internal_url='../会议视图/'+('index.html' if r['conference_id']=='CDS2026' else 'ada.html')+'#report/'+quote(e['report_id'],safe=''))
   speakers=[]
   for p in c.execute("SELECT * FROM agenda_participants WHERE agenda_item_id=? AND agenda_role='speaker' ORDER BY ordinal",(r['agenda_item_id'],)):
    p=dict(p);tier=c.execute('SELECT * FROM v_speaker_tiers WHERE conference_id=? AND person_id=?',(r['conference_id'],p['person_id'])).fetchone();p['tier']=dict(tier) if tier else None;speakers.append(p)
   e['speakers']=speakers
  else:
   p=dict(c.execute('SELECT * FROM literature_papers WHERE paper_id=?',(e['paper_id'],)).fetchone());e.update(journal=p['journal'],date=p['publication_date'],date_basis=p['date_basis'],paper_type=p['article_type'],region=None,internal_url='../论文视图/index.html#paper/'+quote(p['paper_id'],safe=''),speakers=[])
  e['local_source_url']='../'+quote(e['raw_path'],safe='/')
  e['authors']=[dict(x) for x in c.execute('SELECT ordinal,name_original,is_collective FROM literature_authors WHERE paper_id=? ORDER BY ordinal',(e['paper_id'],))] if e['paper_id'] else []
 matches=[project('match',x,'match_id') for x in rows('biomarker_capability_matches')]
 for m in matches:m['capability_source_url']='../'+quote(m['capability_source_path'],safe='/')
 reviews=[project('extraction',x,'review_id') for x in rows('biomarker_extraction_reviews')]
 runs=[project('run',x,'run_id') for x in rows('biomarker_analysis_runs')]
 conferences=[dict(x) for x in c.execute('SELECT conference_id,name_original,region FROM conference_editions ORDER BY conference_id')]
 for conf in conferences:
  conf['total_reports']=c.execute('SELECT COUNT(*) FROM reports WHERE conference_id=?',(conf['conference_id'],)).fetchone()[0]
  conf['reviewed_reports']=c.execute("SELECT COUNT(DISTINCT r.source_id) FROM biomarker_extraction_reviews r JOIN reports p ON p.report_id=r.source_id WHERE r.source_kind='report' AND p.conference_id=?",(conf['conference_id'],)).fetchone()[0]
 version=dict(c.execute('SELECT * FROM biomarker_review_versions WHERE is_current=1').fetchone())
 source_key=lambda e:('report',e['report_id']) if e['report_id'] else ('paper',e['paper_id'])
 result_papers={e['paper_id'] for e in evidence if e['paper_id'] and e['has_result_evidence']}
 reference_papers={e['paper_id'] for e in evidence if e['paper_id'] and e['has_result_evidence'] and e.get('reference_endpoint')}
 counts=dict(biomarkers=len(entities),contexts=len(contexts),evidence=len(evidence),report_mentions=len({e['report_id'] for e in evidence if e['report_id']}),paper_mentions=len({e['paper_id'] for e in evidence if e['paper_id']}),result_evidence=sum(bool(e['has_result_evidence']) for e in evidence),result_papers=len(result_papers),research_result_papers=len(result_papers-reference_papers),reference_result_papers=len(reference_papers),reference_entities=sum(bool(b['reference_endpoint']) for b in entities),external_validation=len({source_key(e) for e in evidence if e['has_external_validation']}),confirmed_studies=len({e['study_id'] for e in evidence if e.get('study_id') and e.get('independence_status')=='confirmed'}),unresolved_study_sources=len({source_key(e) for e in evidence if e.get('independence_status')!='confirmed'}),capability_candidates=len(matches),clinical_priority_confirmed=sum(c.get('translation_status')=='confirmed_clinical' for c in contexts),reviewed_sources=len({(r['source_kind'],r['source_id']) for r in reviews}),reviewed_reports=len({r['source_id'] for r in reviews if r['source_kind']=='report'}),reviewed_papers=len({r['source_id'] for r in reviews if r['source_kind']=='paper'}),pending_content=len({(r['source_kind'],r['source_id']) for r in reviews if r['outcome_status']=='pending_content_review'}),paper_pool=c.execute('SELECT COUNT(*) FROM literature_papers').fetchone()[0],paper_in_window=c.execute("SELECT COUNT(*) FROM literature_papers WHERE window_status='in_window'").fetchone()[0])
 assessments=[r['paper_assessment'] for r in reviews if r.get('paper_assessment')]
 c.close();assert sha(db)==before
 data=dict(meta=dict(title='Biomarker研究线索与转化证据',generated_on=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),database_sha256=before,audit_version=version['version_id'],read_only=True,new_collection=False,published=False,sample_only=True),counts=counts,biomarkers=entities,contexts=contexts,evidence=evidence,matches=matches,reviews=reviews,runs=runs,conferences=conferences,paper_assessments=assessments)
 out=ROOT/'标志物视图';src=out/'src';snapshot=json.dumps(data,ensure_ascii=False,indent=2)+'\n';(out/'标志物数据快照.json').write_text(snapshot,encoding='utf-8')
 embed=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
 html=(src/'template.html').read_text(encoding='utf-8').replace('__STYLE__',(src/'style.css').read_text(encoding='utf-8')).replace('__DATA__',embed).replace('__APP__',(src/'app.js').read_text(encoding='utf-8'));(out/'index.html').write_text(html,encoding='utf-8')
 result=dict(result='generated',database_sha256=before,snapshot_sha256=sha(out/'标志物数据快照.json'),html_sha256=sha(out/'index.html'),counts=counts,audit_version=version['version_id'],database_unchanged=True,new_collection=False,published=False)
 (out/'生成记录.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
