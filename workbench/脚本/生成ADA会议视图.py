"""从数据库只读导出ADA会前程序数量视图；三种报告类型范围均独立计数。"""
from pathlib import Path
from collections import defaultdict
from urllib.parse import quote
import json,sqlite3,hashlib
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 r=ROOT;db=r/'数据库/marketing.db';before=sha(db);c=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON')
 def rows(s,p=()):return [dict(x) for x in c.execute(s,p)]
 conf=rows("SELECT * FROM v_conference_inventory WHERE conference_id='ADA2026'")[0];conf['tier']=rows("SELECT * FROM v_conference_tiers WHERE conference_id='ADA2026'")[0];coverage=rows("SELECT * FROM conference_coverage WHERE conference_id='ADA2026'")[0];coverage['summary']=json.loads(coverage.pop('coverage_json'));coverage['page_audit']=rows("SELECT * FROM conference_page_audit WHERE conference_id='ADA2026' ORDER BY physical_page")
 materials=rows("SELECT * FROM source_materials WHERE import_id LIKE 'ADA2026%' ORDER BY relative_path")
 for m in materials:assert (r/m['relative_path']).is_file();m['local_url']='../'+quote(m['relative_path'],safe='/')
 sessions=rows("SELECT * FROM sessions WHERE conference_id='ADA2026' ORDER BY local_date,source_session_id")
 for s in sessions:s['chairs']=rows('SELECT * FROM session_chairs WHERE session_id=? ORDER BY ordinal',(s['session_id'],))
 reports=rows("SELECT r.*,a.source_order,a.raw_json FROM v_report_detail r JOIN agenda_items a USING(agenda_item_id) WHERE r.conference_id='ADA2026' ORDER BY a.source_order");peoplemap=defaultdict(set)
 for x in reports:
  rid=x['report_id'];x['raw_record']=json.loads(x.pop('raw_json'));x['classification']=rows('SELECT * FROM report_classifications WHERE report_id=? AND analysis_version_id=?',(rid,coverage['analysis_version_id']))[0];x['topic_review']=rows('SELECT * FROM conference_report_notes WHERE report_id=? AND analysis_version_id=?',(rid,coverage['analysis_version_id']))[0]
  x['occurrences']=rows('SELECT o.*,a.session_id,a.title_original,a.local_date,a.time_original,a.source_locator,s.title_original AS session_title FROM conference_program_occurrences o JOIN agenda_items a USING(agenda_item_id) JOIN sessions s USING(session_id) WHERE o.report_id=? ORDER BY a.source_order',(rid,))
  persons=[]
  for o in x['occurrences']:
   o['pages']=json.loads(o['programme_pages']);o['participants']=rows("SELECT * FROM agenda_participants WHERE agenda_item_id=? AND agenda_role='speaker'",(o['agenda_item_id'],));persons.extend(o['participants'])
  unique={p['person_id']:p for p in persons};x['participants']=list(unique.values());x['speaker_ids']=list(unique);x['primary_page']=next(o['pages'][0] for o in x['occurrences'] if o['is_primary']);x['tags']=json.loads(x['topic_review']['cross_tags_json']);x['title_review']=None
  for pid in unique:peoplemap[pid].add(rid)
  x['research_records']=rows('SELECT rr.*,l.relation_type,l.basis AS link_basis FROM curated_report_links l JOIN curated_research_records rr USING(record_id) WHERE l.report_id=?',(rid,))
  for rr in x['research_records']:
   rr['data']=json.loads(rr.pop('raw_json'));rr['papers']=rows('SELECT p.*,l.relation_type FROM related_paper_links l JOIN related_paper_abstracts p USING(paper_id) WHERE l.record_id=?',(rr['record_id'],))
   for p in rr['papers']:p['data']=json.loads(p.pop('raw_json'))
 people=rows("SELECT * FROM people WHERE mapping_material_id IN(SELECT material_id FROM source_materials WHERE import_id LIKE 'ADA2026%') ORDER BY display_name")
 for p in people:
  pid=p['person_id'];p['report_ids']=sorted(peoplemap.get(pid,[]));p['roles']=[];p['profiles']=rows('SELECT * FROM person_profiles WHERE person_id=?',(pid,));ts=rows("SELECT * FROM v_speaker_tiers WHERE conference_id='ADA2026' AND person_id=?",(pid,));p['tier']=ts[0] if ts else None
  if p['tier']:p['tier']['evidence']=rows('SELECT * FROM speaker_tier_evidence WHERE conference_id=? AND person_id=?',('ADA2026',pid))
 topics=rows('SELECT t.*,v.report_count,v.denominator,v.report_share_percent,v.quantity_rank,v.width_status,v.boundary_text,v.scope_gaps FROM research_topics t JOIN v_ada_quantity_topic_counts v USING(topic_id) ORDER BY report_count DESC,legacy_topic_id');facts={f['topic_id']:f for f in rows('SELECT * FROM v_ada_quantity_topic_facts')}
 cohorts={}
 for kind,formats in [('all',None),('talks',['大会报告','专题报告','论文发言']),('posters',['海报报告','晚期突破海报'])]:
  if formats:
   sql=c.execute("SELECT sql FROM sqlite_schema WHERE name='v_ada_quantity_topic_facts'").fetchone()[0].split(' AS',1)[1];clause='AND rc.eligible=1 AND r.report_format IN('+','.join("'"+f+"'" for f in formats)+')';sql=sql.replace('AND rc.eligible=1',clause,1);ff={f['topic_id']:f for f in rows(sql)}
  else:ff=facts
  den=sum(x['report_count'] for x in ff.values());rank={n:i+1 for i,n in enumerate(sorted({f['report_count'] for f in ff.values()},reverse=True))};tt=[]
  for t in topics:
   if t['topic_id'] not in ff:continue
   f=ff[t['topic_id']];new=dict(t);new.update(facts=f,report_count=f['report_count'],denominator=den,report_share_percent=round(100*f['report_count']/den,2),quantity_rank=rank[f['report_count']],report_ids=[x['report_id'] for x in reports if x['classification']['primary_topic_id']==t['topic_id'] and (not formats or x['report_format'] in formats)]);tt.append(new)
  tt.sort(key=lambda t:(-t['report_count'],t['legacy_topic_id']));cohorts[kind]=dict(topics=tt,denominator=den,all_reports=sum(not formats or x['report_format'] in formats for x in reports),formats=formats)
 payload=dict(meta=dict(title='ADA会议视图',source_database='数据库/marketing.db',database_sha256=before,source_observed_on='2026-11-11',imported_on='2026-11-17',new_collection=False,published=False),conference=conf,coverage=coverage,materials=materials,sessions=sessions,reports=reports,people=people,topics=cohorts['all']['topics'],boards=rows('SELECT * FROM v_ada_quantity_board_counts ORDER BY report_count DESC'),quantity=dict(cohorts=cohorts,speaker_talks=rows('SELECT * FROM v_ada_quantity_speaker_talks')),stats=dict(tier_counts=rows("SELECT * FROM v_speaker_tier_counts WHERE conference_id='ADA2026'"),academic_speakers=len(peoplemap),report_formats=rows("SELECT report_format,COUNT(*) AS count FROM reports WHERE conference_id='ADA2026' GROUP BY report_format"),curated_records=rows("SELECT COUNT(*) AS n FROM curated_research_records WHERE conference_id='ADA2026'")[0]['n'],paper_abstracts=rows('SELECT COUNT(*) AS n FROM related_paper_abstracts')[0]['n']))
 c.close();assert sha(db)==before
 out=r/'会议视图';(out/'ADA会议数据快照.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n');embedded=json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('</','<\\/');src=out/'src';template=(src/'template.html').read_text().replace('CDS 2026 · 本地会议视图','ADA 2026 · 本地会议视图').replace('<title>CDS会议视图','<title>ADA会议视图').replace('>CDS会议总览</a>','>ADA会议总览</a>').replace('<option value="index.html" selected>','<option value="index.html">').replace('<option value="ada.html">','<option value="ada.html" selected>');html=template.replace('__STYLE__',(src/'style.css').read_text()).replace('__DATA__',embedded).replace('__APP__',(src/'ada-app.js').read_text());(out/'ada.html').write_text(html)
 manifest=dict(result='generated',database_sha256=before,html_sha256=sha(out/'ada.html'),snapshot_sha256=sha(out/'ADA会议数据快照.json'),counts=dict(reports=len(reports),topics=len(topics),classified=coverage['summary']['classified_reports'],speakers=len(peoplemap)),cohorts={k:dict(denominator=v['denominator'],all_reports=v['all_reports']) for k,v in cohorts.items()},database_unchanged_during_export=True,new_collection=False,published=False,scoring_enabled=False);(out/'ADA生成记录.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps(manifest,ensure_ascii=False))
if __name__=='__main__':main()
