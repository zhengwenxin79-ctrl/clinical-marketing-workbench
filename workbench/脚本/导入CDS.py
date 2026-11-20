"""从随包本地快照导入SQLite。无网络；首次原子建库，同源重复导入只读跳过。"""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,re,sqlite3,tempfile,os
VERSION='1.0.0'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def jid(prefix,x):return prefix+hashlib.sha256(x.encode('utf-8')).hexdigest()[:20]
def norm(x):return re.sub(r'\s+','',x or '')
def clean_name(n):return re.sub(r'^(?:主持人|主持|致辞|讨论|总结)\s*','',n).strip()
def identity(n,u):return norm(clean_name(n))+'|'+norm(u)
def localdate(s):
 m=re.fullmatch(r'(\d{4})年(\d{1,2})月(\d{1,2})日',s or '')
 return f'{int(m[1]):04d}-{int(m[2]):02d}-{int(m[3]):02d}' if m else None
def times(s):
 m=re.fullmatch(r'\s*(\d{1,2}:\d{2})\s*[-–—~至]\s*(\d{1,2}:\d{2})\s*',s or '')
 return (m[1].zfill(5),m[2].zfill(5)) if m else (None,None)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--output',type=Path);args=ap.parse_args();root=args.root.resolve();out=args.output.resolve() if args.output else root/'数据库/marketing.db';folder=root/'原始资料/CDS2026';manifest=read(folder/'资料清单.json')
 assert manifest['new_collection'] is False
 for f in manifest['files']:
  path=(root/f['path']).resolve();path.relative_to(root)
  if not path.is_file() or digest(path)!=f['sha256']:raise SystemExit('快照缺失或指纹不符：'+f['path'])
 batch='CDS2026-'+manifest['fingerprint'][:16]
 if out.exists():
  con=sqlite3.connect(out.as_uri()+'?mode=ro',uri=True)
  try:row=con.execute('SELECT fingerprint FROM import_batches WHERE import_id=?',(batch,)).fetchone()
  finally:con.close()
  if row and row[0]==manifest['fingerprint']:
   print(json.dumps(dict(status='already_imported',import_id=batch,database=str(out)),ensure_ascii=False));return
  raise SystemExit('目标数据库已存在且不是本批快照；已停止，不覆盖、不擅自执行增量迁移。')
 raw=read(folder/'官方日程/CDS_全日程结构化.json');mapping=read(folder/'处理依据/CDS_导入映射快照.json');defs=read(folder/'处理依据/议题定义.json');ledger=read(folder/'处理依据/逐报告归类与计分.json');profiles=read(folder/'处理依据/讲者简介核查.json');reviews=read(folder/'处理依据/CDS标志物逐报告复核台账.json');assert len(ledger)==606
 schema=(root/'规则与说明/schema.sql').read_text(encoding='utf-8');out.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(prefix='.cds_import_',suffix='.db',dir=str(out.parent));os.close(fd);tmp=Path(tmp);con=None
 try:
  con=sqlite3.connect(tmp);con.execute('PRAGMA foreign_keys=ON');con.execute('PRAGMA journal_mode=DELETE');con.executescript(schema);con.execute('BEGIN')
  def insert(table,**values):
   cols=','.join(values);q=','.join('?' for _ in values);con.execute(f'INSERT INTO {table} ({cols}) VALUES ({q})',list(values.values()))
  insert('import_batches',import_id=batch,fingerprint=manifest['fingerprint'],imported_on='2026-11-17',imported_at=datetime.now(timezone.utc).isoformat(),source_observed_on=raw['as_of'],source_manifest='原始资料/CDS2026/资料清单.json',importer_version=VERSION,new_collection=0,notes='仅CDS已有快照；旧归类与角色提取作为待复核分析保留，不导入旧评分；没有把报告造为独立研究。')
  mids={}
  for f in manifest['files']:
   mid=jid('MAT:',f['path']+'|'+f['sha256']);mids[f['path']]=mid
   insert('source_materials',material_id=mid,import_id=batch,relative_path=f['path'],sha256=f['sha256'],byte_size=f['bytes'],material_kind=f['kind'],source_url=f['source_url'],reading_level=f['reading_level'],source_observed_on=f['source_observed_on'],original_path=f['original_path'],original_sha256=f['original_sha256'],is_derived=int(f['generated']))
  def mat(rel):return mids['原始资料/CDS2026/'+rel]
  agenda_mat=mat('官方日程/CDS_全日程结构化.json');html_mat=mat('官方日程/CDS_详细日程_2026-11-16.html');map_mat=mat('处理依据/CDS_导入映射快照.json');prof_mat=mat('处理依据/讲者简介核查.json');defs_mat=mat('处理依据/议题定义.json');ledger_mat=mat('处理依据/逐报告归类与计分.json');review_mat=mat('处理依据/CDS标志物逐报告复核台账.json');rules_mat=mat('处理依据/CDS标志物题名复核.json')
  html=(folder/'官方日程/CDS_详细日程_2026-11-16.html').read_text(encoding='utf-8');title=re.search(r'<title>(.*?)</title>',html,re.S)[1].split('大会日程-',1)[-1];calendar=mapping['conference_calendar_record'];cid='CDS2026'
  insert('conference_series',series_id='CDS',abbreviation='CDS',name_original='中华医学会糖尿病学术会议',evidence_material_id=html_mat)
  insert('conference_editions',conference_id=cid,series_id='CDS',year=2026,edition_label='第二十八次',name_original=title,organizer=None,region=calendar.get('region'),country=None,city=calendar.get('location'),format=None,start_date=calendar['start'],end_date=calendar['end'],local_timezone='Asia/Shanghai',timezone_basis='按既有地点厦门解释本地日程；原始日程未显式标时区',official_url='https://cds26.tiemeeting.com/CN',metadata_status='existing_source_snapshot_not_rechecked',metadata_material_id=map_mat,source_locator='$.conference_calendar_record；官方标题另见官方日程HTML<title>',metadata_gaps='主办方/举办国/具体场馆/形式未在本包元数据中独立核清；日期地点沿用既有CDS日历依据，不代表本次联网核验。')
  for i,s in enumerate(raw['sessions']):insert('sessions',session_id=cid+':'+s['session_id'],conference_id=cid,source_session_id=s['session_id'],title_original=s['title'],date_original=s['date'],local_date=localdate(s['date']),room_original=s['room'],material_id=agenda_mat,source_locator=f'$.sessions[{i}]')
  # 人名+原文单位只作来源身份条目；跨单位同名不自动消歧，原始写法保留在关系表。
  known={p['key']:p for p in mapping['people']};people={}
  def person(n,u):
   k=identity(n,u)
   if k not in people:
    p=known.get(k);pid=jid('PERSON:',k);people[k]=pid
    name=p['name'] if p else clean_name(n)
    if not re.search('[A-Za-z]',name):name=norm(name)
    insert('people',person_id=pid,source_identity_key=k,display_name=name,institution_source=p['institution'] if p else u,identity_status='source_name_institution_entry_unverified',legacy_person_id=(cid+':'+p['id']) if p else None,mapping_material_id=map_mat if p else agenda_mat,identity_note='按姓名与原文单位去空格匹配；不是经过完整消歧的自然人主档。原文单位可能含角色，不自动确认为标准机构。')
   return people[k]
  for p in mapping['people']:person(p['name'],p['institution'])
  for s in raw['sessions']:
   for i,p in enumerate(s['chairs']):insert('session_chairs',session_id=cid+':'+s['session_id'],ordinal=i,person_id=person(p['name'],p['institution']),name_original=p['name'],institution_original=p['institution'],profile_url=p.get('url'))
  by_code={};academic={'大会报告','专题报告','论文发言'}
  for i,a in enumerate(raw['items']):
   aid=cid+':AGENDA:'+str(i+1).zfill(4);begin,end=times(a['time']);code=a.get('code') or None
   insert('agenda_items',agenda_item_id=aid,conference_id=cid,session_id=cid+':'+a['session_id'],source_code=code,source_order=i,title_original=a['title'],format_original=a['kind'],date_original=a['date'],local_date=localdate(a['date']),time_original=a['time'],start_time=begin,end_time=end,room_original=a['room'],source_url=a['source_url'],evidence_level='planned_agenda',material_id=agenda_mat,source_locator=f'$.items[{i}]',raw_json=json.dumps(a,ensure_ascii=False,sort_keys=True))
   for j,p in enumerate(a['people']):
    role='speaker' if a['kind'] in academic else {'致辞':'address','讨论':'discussant','总结':'summary','专题会发言':'session_talk'}.get(a['kind'],'listed_person')
    insert('agenda_participants',agenda_item_id=aid,ordinal=j,person_id=person(p['name'],p['institution']),agenda_role=role,name_original=p['name'],institution_original=p['institution'],profile_url=p.get('profile_url'),role_basis='原日程条目列名；按发言类型区别角色，主持另见session_chairs，不混入报告讲者计数。')
   if a['kind'] in academic:
    assert code;rid=cid+':'+code;by_code[code]=rid
    insert('reports',report_id=rid,agenda_item_id=aid,conference_id=cid,source_report_code=code,legacy_report_id=code,legacy_evidence_id='C-'+code,report_format=a['kind'],evidence_status='agenda_only',has_results=0,result_text=None,independent_study_status='not_established')
  prof_ids={}
  for i,p in enumerate(profiles):
   pid=person(p['name'],p['institution']);profileid=jid('PROFILE:',p['key']+'|'+p['url']+'|'+batch);prof_ids[p['key']]=profileid;legacy=known.get(p['key'],{});rawmid=mids.get('原始资料/CDS2026/官方简介/'+p.get('raw_file',''))
   insert('person_profiles',profile_id=profileid,person_id=pid,import_id=batch,profile_url=p['url'],read_status=p['status'],has_substantive_bio=int(bool(legacy.get('profile_has_bio'))),extracted_text=p.get('text'),fetch_error=json.dumps({k:p[k] for k in ['error','retry_error'] if k in p},ensure_ascii=False) or None,raw_material_id=rawmid,evidence_material_id=prof_mat,source_locator=f'$[{i}]',source_observed_on=raw['as_of'])
  for i,p in enumerate(mapping['people']):
   for j,phrase in enumerate(p['leader_basis']):
    insert('academic_role_claims',claim_id=jid('ROLE:',p['key']+'|'+phrase),person_id=people[p['key']],profile_id=prof_ids.get(p['key']),role_phrase=phrase,role_level=p['leader_level'],tenure_status='historical_mentioned' if re.search('曾任|历任|前任',phrase) else 'not_independently_verified',source_material_id=map_mat,source_locator=f'$.people[{i}].leader_basis[{j}]',source_note=p['source_note'],verification_status='conference_bio_claim')
  tv='CDS2026:TOPICS:20261116';bv='CDS2026:BIOMARKER-TITLES:20261116'
  insert('analysis_versions',analysis_version_id=tv,conference_id=cid,analysis_kind='primary_topic',rule_label='既有12板块/44议题主归类',review_status='pending_method_review',is_current_snapshot=1,scoring_enabled=0,material_id=defs_mat,method_note='仅复现既有归类和排除范围；评分重复计量问题待讨论，不导入任何旧综合分或角色权重。')
  insert('analysis_versions',analysis_version_id=bv,conference_id=cid,analysis_kind='biomarker_title_scope',rule_label='既有CDS606题名复核',review_status='ai_title_review_pending_mentor',is_current_snapshot=1,scoring_enabled=0,material_id=rules_mat,method_note='80条标志物相关题名；不等于80个已验证Biomarker，成员/用途/输入和结果待核。')
  for key,name in defs['parents'].items():insert('research_topics',topic_id=cid+':'+key,conference_id=cid,legacy_topic_id=key,parent_topic_id=None,node_type='board',name=name,research_question=None,taxonomy_status='working_classification',material_id=defs_mat)
  for t in defs['topics']:insert('research_topics',topic_id=cid+':'+t['id'],conference_id=cid,legacy_topic_id=t['id'],parent_topic_id=cid+':'+t['parent_id'],node_type='topic',name=t['name'],research_question=t['question'],taxonomy_status='working_classification',material_id=defs_mat)
  for i,r in enumerate(ledger):
   rid=by_code[r['code']]
   insert('report_classifications',report_id=rid,analysis_version_id=tv,primary_topic_id=cid+':'+r['topic_id'] if r['topic_id'] else None,scope_original=r['scope'],eligible=int(r['scope']=='入榜'),classification_basis=r['classification_basis'],material_id=ledger_mat,source_locator=f'$[{i}]')
   for tag in r['cross_tags']:insert('report_tags',report_id=rid,analysis_version_id=tv,tag=tag,material_id=ledger_mat)
  for i,r in enumerate(reviews):
   rid=by_code[r['code']];insert('biomarker_title_reviews',report_id=rid,analysis_version_id=bv,review_status=r['status'],in_denominator=int(r['in_denominator']),target_text=r['target'],use_text=r['use'],indicator_kind=r['kind'],basis=r['basis'],review_level=r['review_level'],material_id=review_mat,source_locator=f'$[{i}]')
   for key in r['bound_marker_ids']:insert('legacy_marker_bindings',report_id=rid,analysis_version_id=bv,legacy_marker_id=key,evidence_id_original=r['evidence_id'],binding_status='existing_title_binding_pending_review',material_id=review_mat,source_locator=f'$[{i}].bound_marker_ids')
  assert len(by_code)==606;assert con.execute('SELECT SUM(report_count) FROM v_topic_counts').fetchone()[0]==579
  assert con.execute('SELECT COUNT(*) FROM biomarker_title_reviews WHERE in_denominator=1').fetchone()[0]==80
  assert not con.execute('PRAGMA foreign_key_check').fetchall();assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  con.commit();con.close();con=None;os.replace(tmp,out)
  print(json.dumps(dict(status='imported',database=str(out),import_id=batch,source_observed_on=raw['as_of'],imported_on='2026-11-17',new_collection=False),ensure_ascii=False))
 finally:
  if con is not None:con.close()
  if tmp.exists():tmp.unlink()
if __name__=='__main__':main()
