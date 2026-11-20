"""从现有SQLite只读生成三级会议目录；不修改数据库、不采集、不发布。"""
from pathlib import Path
from urllib.parse import quote,unquote
from datetime import datetime
from zoneinfo import ZoneInfo
import sqlite3,json,hashlib
from 领域热点数据 import build_hotspots
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 root=ROOT;out=root/'会议总入口';db=root/'数据库/marketing.db';before=sha(db);config=json.loads((out/'入口配置.json').read_text());c=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON');entries=[]
 try:
  for cid,route in config['routes'].items():
   rows=c.execute('SELECT v.*,s.abbreviation,s.name_original AS series_name,t.tier_code,t.tier_label,t.assessment_status AS tier_status,t.basis_text AS tier_basis,t.evidence_gaps AS tier_gaps FROM v_conference_inventory v JOIN conference_series s USING(series_id) JOIN v_conference_tiers t USING(conference_id) WHERE v.conference_id=?',(cid,)).fetchall();assert len(rows)==1,cid
   row=dict(rows[0]);assert row['tier_code'] in {t['id'] for t in config['tiers']};target=(out/unquote(route['path'])).resolve();target.relative_to(root);assert target.is_file(),target
   row['view_url']=quote(route['path'],safe='/');row['topic_url']=row['view_url']+'#topics';row['coverage_url']=row['view_url']+'#sources';row['domain_id']=config['domain']['id'];row['domain_label']=config['domain']['label']
   av=c.execute("SELECT analysis_version_id,analysis_kind,review_status FROM analysis_versions WHERE conference_id=? AND is_current_snapshot=1 AND analysis_kind IN('topic_quantity','ada_topic_quantity')",(cid,)).fetchall();assert len(av)==1;version=dict(av[0]);vid=version['analysis_version_id'];row['analysis_version']=version
   row['classified_report_count']=c.execute('SELECT COUNT(DISTINCT report_id) FROM report_classifications WHERE analysis_version_id=? AND eligible=1',(vid,)).fetchone()[0]
   row['topic_count']=c.execute('SELECT COUNT(DISTINCT primary_topic_id) FROM report_classifications WHERE analysis_version_id=? AND eligible=1',(vid,)).fetchone()[0]
   row['outside_topic_count']=row['academic_report_count']-row['classified_report_count'];row['report_formats']=[dict(x) for x in c.execute('SELECT report_format,COUNT(*) AS count FROM reports WHERE conference_id=? GROUP BY report_format',(cid,))];row['poster_report_count']=sum(x['count'] for x in row['report_formats'] if x['report_format'] in ['海报报告','晚期突破海报'])
   row['speaker_tiers']=[dict(x) for x in c.execute('SELECT tier_code,tier_label,identity_count FROM v_speaker_tier_counts WHERE conference_id=?',(cid,))]
   coverage=c.execute('SELECT * FROM conference_coverage WHERE conference_id=?',(cid,)).fetchone()
   if coverage:
    cv=dict(coverage);row['coverage_summary']=json.loads(cv['coverage_json']);row['source_snapshot_label']=cv['source_snapshot_label'];row['coverage_note']=cv['gaps'];row['classification_label']='规则辅助初分';row['scope_label']='会前程序已入库';row['outside_topic_label']='待归类';row['programme_pages']=row['coverage_summary']['programme_physical_pages']
   else:
    observed=c.execute('SELECT sm.source_observed_on FROM source_materials sm WHERE sm.material_id=?',(row['metadata_material_id'],)).fetchone()[0];row['source_snapshot_label']='日程资料快照 '+str(observed);row['coverage_note']='完整日程已入库，579条按题名复核归类；27条培训、方法与综合内容另列。尚未录入报告结果，归类与人物角色仍待校准。';row['classification_label']='题名复核归类';row['scope_label']='完整日程已入库';row['outside_topic_label']='另列内容';row['programme_pages']=None
   manifest=json.loads((root/route['manifest']).read_text());row['view_matches_database']=manifest['database_sha256']==before;row['view_manifest_path']=route['manifest'];row['date_label']=str(row['start_date'])+' — '+str(row['end_date']);row['location_label']=row['city'] or '地点待补';entries.append(row)
  hot_data=build_hotspots(c,entries,config.get('hotspot_admission',{}))
 finally:c.close()
 entries.sort(key=lambda x:(list(t['id'] for t in config['tiers']).index(x['tier_code']),x['series_id'],-x['year']))
 tiers=[]
 for tier in config['tiers']:
  es=[x for x in entries if x['tier_code']==tier['id']];groups=[]
  for sid in dict.fromkeys(x['series_id'] for x in es):
   editions=[x for x in es if x['series_id']==sid];groups.append(dict(series_id=sid,abbreviation=editions[0]['abbreviation'],name=editions[0]['series_name'],editions=editions))
  tiers.append(dict(tier,series_count=len(groups),edition_count=len(es),series=groups))
 payload=dict(meta=dict(title='临床科研会议总入口',generated_on=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds'),source_database='数据库/marketing.db',database_sha256=before,read_only=True,new_collection=False,published=False),domain=config['domain'],tiers=tiers,summary=dict(series_count=len({x['series_id'] for x in entries}),edition_count=len(entries),tier_count=3),entries=entries)
 hot_data['meta']=payload['meta']
 (out/'领域热点数据快照.json').write_text(json.dumps(hot_data,ensure_ascii=False,indent=2)+'\n')
 (out/'会议目录快照.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n');embedded=json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('</','<\\/');src=out/'src';html=(src/'template.html').read_text().replace('__STYLE__',(src/'style.css').read_text()+'\n'+(src/'hotspots.css').read_text()).replace('__DATA__',embedded).replace('__HOT_DATA__',json.dumps(hot_data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')).replace('__HOT_APP__',(src/'hotspots.js').read_text()).replace('__APP__',(src/'app.js').read_text());(out/'index.html').write_text(html)
 assert sha(db)==before
 manifest=dict(result='generated',database_sha256=before,directory_sha256=sha(out/'会议目录快照.json'),hotspots_sha256=sha(out/'领域热点数据快照.json'),html_sha256=sha(out/'index.html'),counts={t['id']:t['edition_count'] for t in tiers},hotspot_topics=len(hot_data['topics']),database_unchanged=True,new_collection=False,published=False)
 (out/'生成记录.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps(manifest,ensure_ascii=False))
if __name__=='__main__':main()
