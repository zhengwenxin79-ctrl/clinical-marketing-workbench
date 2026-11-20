"""仅从SQLite只读查询生成独立会议网页，不读取旧网页/JSON作回退。"""
from pathlib import Path
from urllib.parse import quote
import argparse,hashlib,json,sqlite3

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def generate(root,output=None):
 root=root.resolve();db=root/'数据库/marketing.db';before=digest(db);out=Path(output) if output is not None else root/'会议视图';out.mkdir(parents=True,exist_ok=True);c=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON')
 try:
  def rows(sql,params=()):return [dict(r) for r in c.execute(sql,params)]
  batch=rows("SELECT * FROM import_batches WHERE import_id LIKE 'CDS2026%'")[0];conf=rows("SELECT * FROM v_conference_inventory WHERE conference_id='CDS2026'")[0];cid=conf['conference_id'];conf['tier']=rows('SELECT * FROM v_conference_tiers WHERE conference_id=?',(cid,))[0]
  materials=rows("SELECT * FROM source_materials WHERE import_id NOT LIKE 'ADA2026%' ORDER BY relative_path")
  for m in materials:
   p=root/m['relative_path'];assert p.is_file(),m['relative_path'];m['local_url']='../'+quote(m['relative_path'],safe='/')
  sessions=rows('SELECT * FROM sessions WHERE conference_id=? ORDER BY local_date,source_session_id',(cid,))
  chairs=rows('SELECT sc.* FROM session_chairs sc JOIN sessions s USING(session_id) WHERE s.conference_id=? ORDER BY sc.session_id,sc.ordinal',(cid,));cm={}
  for x in chairs:cm.setdefault(x['session_id'],[]).append(x)
  for x in sessions:x['chairs']=cm.get(x['session_id'],[])
  reports=rows('SELECT r.*,a.source_order,a.raw_json FROM v_report_detail r JOIN agenda_items a USING(agenda_item_id) WHERE r.conference_id=? ORDER BY a.source_order',(cid,))
  participants=rows("SELECT ap.* FROM agenda_participants ap JOIN reports r USING(agenda_item_id) WHERE r.conference_id=? AND ap.agenda_role='speaker' ORDER BY ap.agenda_item_id,ap.ordinal",(cid,));ppm={}
  for p in participants:ppm.setdefault(p['agenda_item_id'],[]).append(p)
  classifications=rows('SELECT rc.* FROM report_classifications rc JOIN analysis_versions av USING(analysis_version_id) WHERE av.is_current_snapshot=1 AND av.analysis_kind=?',('topic_quantity',));rc={x['report_id']:x for x in classifications}
  reviewed=rows('SELECT b.* FROM biomarker_title_reviews b JOIN analysis_versions av USING(analysis_version_id) WHERE av.is_current_snapshot=1');bm={x['report_id']:x for x in reviewed};tags={}
  for t in rows('SELECT rt.* FROM report_tags rt JOIN analysis_versions av USING(analysis_version_id) WHERE av.is_current_snapshot=1'):tags.setdefault(t['report_id'],[]).append(t['tag'])
  topic_notes={x['report_id']:x for x in rows("SELECT n.* FROM report_topic_review_notes n JOIN analysis_versions av USING(analysis_version_id) WHERE av.analysis_kind='topic_quantity' AND av.is_current_snapshot=1")}
  for r in reports:
   r['participants']=ppm.get(r['agenda_item_id'],[]);r['speaker_ids']=list(dict.fromkeys(p['person_id'] for p in r['participants']));r['classification']=rc.get(r['report_id']);r['topic_review']=topic_notes.get(r['report_id']);r['title_review']=bm.get(r['report_id']);r['tags']=tags.get(r['report_id'],[]);r['raw_record']=json.loads(r.pop('raw_json'))
  people=rows("SELECT * FROM people WHERE mapping_material_id IN(SELECT material_id FROM source_materials WHERE import_id NOT LIKE 'ADA2026%') ORDER BY display_name,person_id");profiles=rows("SELECT * FROM person_profiles WHERE import_id NOT LIKE 'ADA2026%'");profilemap={}
  for p in profiles:profilemap.setdefault(p['person_id'],[]).append(p)
  tiers={t['person_id']:t for t in rows('SELECT * FROM v_speaker_tiers WHERE conference_id=?',(cid,))};tier_evidence={}
  for e in rows('SELECT e.* FROM speaker_tier_evidence e JOIN tier_rule_versions v USING(rule_version_id) WHERE v.current_snapshot=1 AND e.conference_id=?',(cid,)):tier_evidence.setdefault(e['person_id'],[]).append(e)
  for pid,t in tiers.items():t['evidence']=tier_evidence.get(pid,[])
  roles=rows('SELECT * FROM academic_role_claims');rolemap={}
  for p in roles:rolemap.setdefault(p['person_id'],[]).append(p)
  for p in people:
   p['tier']=tiers.get(p['person_id']);p['profiles']=profilemap.get(p['person_id'],[]);p['roles']=rolemap.get(p['person_id'],[]);p['report_ids']=[r['report_id'] for r in reports if p['person_id'] in r['speaker_ids']]
  topics=rows('SELECT t.*,v.report_count,v.denominator,v.report_share_percent,v.quantity_rank,v.width_status,v.boundary_text,v.scope_gaps,v.definition_origin_id FROM research_topics t JOIN v_cds_quantity_topic_counts v USING(topic_id) ORDER BY v.report_count DESC,t.legacy_topic_id')
  facts={x['topic_id']:x for x in rows('SELECT * FROM v_cds_quantity_topic_facts')}
  for t in topics:t['facts']=facts[t['topic_id']];t['report_ids']=[r['report_id'] for r in reports if r['classification'] and r['classification']['primary_topic_id']==t['topic_id']]
  boards=rows('SELECT * FROM v_cds_quantity_board_counts ORDER BY report_count DESC,legacy_topic_id')
  main_html=next(m['material_id'] for m in materials if m['material_kind']=='official_agenda_html')
  versions=rows("SELECT * FROM analysis_versions WHERE conference_id='CDS2026'");source_rows=rows("SELECT format_original,COUNT(*) AS count FROM agenda_items WHERE conference_id='CDS2026' GROUP BY format_original");academic_count=rows("SELECT report_format,COUNT(*) AS count FROM reports WHERE conference_id='CDS2026' GROUP BY report_format");excluded=rows("SELECT rc.scope_original,COUNT(*) AS count FROM report_classifications rc JOIN analysis_versions av USING(analysis_version_id) WHERE av.analysis_kind='topic_quantity' AND av.is_current_snapshot=1 AND rc.eligible=0 GROUP BY scope_original")
  quant=rows("SELECT q.* FROM quantity_rule_versions q JOIN analysis_versions av USING(analysis_version_id) WHERE av.analysis_kind='topic_quantity' AND av.is_current_snapshot=1")[0]
  scope_reviews=rows('SELECT s.*,t.name AS old_name FROM topic_scope_reviews s JOIN research_topics t ON t.topic_id=s.old_topic_id WHERE s.analysis_version_id=? ORDER BY t.legacy_topic_id',(quant['analysis_version_id'],))
  for rv in scope_reviews:
   rv['flows']=rows('SELECT rc.primary_topic_id AS topic_id,t.name,COUNT(*) AS report_count FROM report_topic_review_notes n JOIN report_classifications rc ON rc.report_id=n.report_id AND rc.analysis_version_id=n.analysis_version_id JOIN research_topics t ON t.topic_id=rc.primary_topic_id WHERE n.analysis_version_id=? AND n.previous_topic_id=? GROUP BY rc.primary_topic_id ORDER BY report_count DESC',(quant['analysis_version_id'],rv['old_topic_id']))
  quant['scope_reviews']=scope_reviews;quant['speaker_talks']=rows('SELECT * FROM v_cds_quantity_speaker_talks');quant['summary']=dict(original_topics=len(scope_reviews),split_old_topics=sum(x['action']=='split' for x in scope_reviews),new_topics=len(topics),broad_topics=sum(t['width_status']=='broad' for t in topics),focused_topics=sum(t['width_status']=='focused' for t in topics),reassigned_reports=sum(n['decision_code']=='reassign' for n in topic_notes.values()))
  payload=dict(meta=dict(title='CDS会议视图',source_database='数据库/marketing.db',database_sha256=before,source_observed_on=batch['source_observed_on'],imported_on=batch['imported_on'],generated_from='SQLite只读查询；未使用旧网页数据回退',import_id=batch['import_id'],new_collection=False,published=False,agenda_html_material_id=main_html),conference=conf,quantity=quant,sessions=sessions,reports=reports,people=people,topics=topics,boards=boards,materials=materials,analysis_versions=versions,stats=dict(academic_speakers=sum(bool(p['report_ids']) for p in people),speakers_with_role=sum(bool(p['roles']) and bool(p['report_ids']) for p in people),ranked_reports=sum(t['report_count'] for t in topics),raw_formats=source_rows,report_formats=academic_count,excluded=excluded,tier_counts=rows('SELECT * FROM v_speaker_tier_counts WHERE conference_id=?',(cid,)),profiles_total=len(profiles),profiles_read=sum(p['read_status']=='read' for p in profiles),profiles_with_bio=sum(p['has_substantive_bio'] for p in profiles),biomarker_scope=rows('SELECT * FROM v_biomarker_title_scope')))
  assert len(reports)==606 and len(topics)==58 and len(boards)==12;assert payload['stats']['ranked_reports']==579 and payload['stats']['academic_speakers']==533
 finally:c.close()
 snapshot=out/'会议数据快照.json';snapshot.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');embedded=json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
 src=root/'会议视图/src';template=(src/'template.html').read_text(encoding='utf-8');html=template.replace('__STYLE__',(src/'style.css').read_text(encoding='utf-8')).replace('__DATA__',embedded).replace('__APP__',(src/'app.js').read_text(encoding='utf-8'));(out/'index.html').write_text(html,encoding='utf-8')
 assert digest(db)==before
 manifest=dict(result='generated',database_sha256=before,tier_rule_version=conf['tier']['rule_version_id'],topic_quantity_version=quant['analysis_version_id'],scoring_enabled=False,snapshot_sha256=digest(snapshot),html_sha256=digest(out/'index.html'),record_counts=dict(reports=len(reports),topics=len(topics),boards=len(boards),speakers=payload['stats']['academic_speakers']),database_unchanged=True,new_collection=False,published=False,source_database='数据库/marketing.db')
 (out/'生成记录.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(manifest,ensure_ascii=False))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);generate(ap.parse_args().root)
