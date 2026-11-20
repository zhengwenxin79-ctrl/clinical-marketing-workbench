"""仅从已有本地ADA材料追加入库；迁移扩展报告类型，保留旧表全部记录。"""
from pathlib import Path
from collections import defaultdict,Counter
from datetime import datetime,timezone
import sqlite3,json,hashlib,re,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def jid(prefix,text):return prefix+hashlib.sha256(text.encode()).hexdigest()[:20]
def main():
 r=ROOT;folder=r/'规则与说明/ADA入库_2026-11-17';plan=read(folder/'ADA入库方案.json');raw=read(r/'原始资料/ADA2026/官方程序/ADA程序结构化.json');rules=folder/'ADA数量榜口径.md';baseline=read(folder/'变更前基线.json');db=globals().get('DATABASE_OVERRIDE',r/'数据库/marketing.db');c=sqlite3.connect(db);c.row_factory=sqlite3.Row
 if c.execute("SELECT 1 FROM conference_editions WHERE conference_id='ADA2026'").fetchone():
  row=c.execute("SELECT * FROM conference_coverage WHERE conference_id='ADA2026'").fetchone();assert row['plan_sha256']==sha(folder/'ADA入库方案.json') and row['rules_sha256']==sha(rules);print('already_imported ADA2026');c.close();return
 assert sha(db) in {baseline['database_sha256'],sha(r/baseline['backup_database'])},'数据库有新变化，已停止，避免覆盖并行修改'
 c.execute('PRAGMA foreign_keys=OFF');c.execute('PRAGMA legacy_alter_table=ON')
 try:
  c.execute('BEGIN IMMEDIATE')
  # 扩展已有CHECK枚举，不删改旧记录，不改依赖表/视图的引用名称。
  for table,needle,replacement in [
   ('reports',"('大会报告','专题报告','论文发言')","('大会报告','专题报告','论文发言','海报报告','晚期突破海报')"),
   ('speaker_tier_assignments',"('provisional_existing_bio','insufficient_evidence')","('provisional_existing_bio','provisional_program_role','insufficient_evidence')")]:
   sql=c.execute('SELECT sql FROM sqlite_schema WHERE name=?',(table,)).fetchone()[0];assert needle in sql;sql=sql.replace('CREATE TABLE '+table+' (','CREATE TABLE '+table+'_new (',1).replace(needle,replacement)
   if table=='speaker_tier_assignments':sql=sql.replace("assessment_status='provisional_existing_bio'","assessment_status IN('provisional_existing_bio','provisional_program_role')")
   c.execute(sql);c.execute('INSERT INTO '+table+'_new SELECT * FROM '+table);c.execute('DROP TABLE '+table);c.execute('ALTER TABLE '+table+'_new RENAME TO '+table)
  c.execute('DROP INDEX one_current_tier_rule');c.execute('CREATE INDEX tier_current_versions ON tier_rule_versions(current_snapshot)')
  # 逐句执行增量结构，保持一个事务。
  statement=''
  for line in (r/'规则与说明/005_ADA入库.sql').read_text().splitlines(True):
   statement+=line
   if sqlite3.complete_statement(statement):c.execute(statement);statement=''
  def ins(table,**v):c.execute(f"INSERT INTO {table} ({','.join(v)}) VALUES ({','.join('?' for _ in v)})",list(v.values()))
  batch='ADA2026-LOCAL-20261117-v1';cid='ADA2026';vid=plan['analysis_version'];source=read(folder/'本地来源清单.json')
  for p,kind in [(r/'原始资料/ADA2026/官方程序/ADA程序结构化.json','structured_programme_derived'),(folder/'ADA入库方案.json','ada_import_decisions'),(rules,'ada_quantity_rules')]:source.append(dict(original_path=str(p),relative_path=str(p.relative_to(r)),sha256=sha(p),byte_size=p.stat().st_size,kind=kind,source_observed_on='2026-11-17'))
  fingerprint=hashlib.sha256(json.dumps(source,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
  ins('import_batches',import_id=batch,fingerprint=fingerprint,imported_on='2026-11-17',imported_at=datetime.now(timezone.utc).isoformat(),source_observed_on='2026-11-16',source_manifest=str((folder/'本地来源清单.json').relative_to(r)),importer_version='ADA-1.0.0',new_collection=0,notes='既有385页程序与精选记录/论文摘要；仅解析入库，不新联网，不导入旧评分。')
  mids={}
  for x in source:
   assert sha(r/x['relative_path'])==x['sha256'];mid=jid('MAT:',x['relative_path']+'|'+x['sha256']);mids[x['relative_path']]=mid
   derived=x['kind'] in ['structured_programme_derived','ada_import_decisions','ada_quantity_rules'];url='https://www.abstractsonline.com/SR/Diabetes/FinalProgram.asp' if x['kind'].startswith('official_program') else None
   ins('source_materials',material_id=mid,import_id=batch,relative_path=x['relative_path'],sha256=x['sha256'],byte_size=x['byte_size'],material_kind=x['kind'],source_url=url,reading_level='本地程序原文；非最终现场核验' if x['kind'].startswith('official_program') else '本次本地派生/规则' if derived else '保留的既有研究记录/论文材料，非新采集',source_observed_on=x['source_observed_on'],original_path=x['original_path'],original_sha256=x['sha256'],is_derived=int(derived))
  pdfmid=mids['原始资料/ADA2026/官方程序/ADA2026_日程.pdf'];textmid=mids['原始资料/ADA2026/官方程序/ADA2026_日程.txt'];structmid=mids['原始资料/ADA2026/官方程序/ADA程序结构化.json'];planmid=mids[str((folder/'ADA入库方案.json').relative_to(r))];rulemid=mids[str(rules.relative_to(r))]
  ins('conference_series',series_id='ADA',abbreviation='ADA',name_original='American Diabetes Association Scientific Sessions',evidence_material_id=pdfmid)
  ins('conference_editions',conference_id=cid,series_id='ADA',year=2026,edition_label=None,name_original='ADA 2026 Scientific Sessions',organizer='American Diabetes Association',region='international',country=None,city='New Orleans, LA',format=None,start_date='2026-06-05',end_date='2026-06-08',local_timezone='America/Chicago',timezone_basis='按程序封面New Orleans, LA理解当地时区；原程序未显式标注',official_url='https://www.abstractsonline.com/SR/Diabetes/FinalProgram.asp',metadata_status='existing_programme_snapshot_not_rechecked',metadata_material_id=pdfmid,source_locator='PDF物理第1—2页；页眉2026-04-24',metadata_gaps='仅会前程序版本，未核最终日程/现场报告；举办国/具体场馆未从本包单独核实，城市按封面保留。')
  def date(s):return '2026-06-'+re.search(r'JUNE (\d+)',s)[1].zfill(2)
  sessionmap={s['session_id']:s for s in raw['sessions']}
  for i,s in enumerate(raw['sessions']):ins('sessions',session_id=cid+':'+s['session_id'],conference_id=cid,source_session_id=s['session_id'],title_original=s['title'],date_original=s['date'],local_date=date(s['date']),room_original=s['room'],material_id=structmid,source_locator=f'$.sessions[{i}]；PDF物理第{s["page"]}页')
  people={}
  def person(name):
   key=re.sub(r'\s+',' ',name).strip();identity=cid+'|programme-name|'+key.casefold()
   if identity not in people:
    pid=jid('PERSON:',identity);people[identity]=pid
    ins('people',person_id=pid,source_identity_key=identity,display_name=key,institution_source='',identity_status='programme_name_only_unverified',legacy_person_id=None,mapping_material_id=structmid,identity_note='ADA程序姓名来源身份；程序未提供单位，不与CDS或论文作者按同名自动合并，同名不同人和缩写尚未完全消歧。')
   return people[identity]
  amap={};itemmap={x['source_order']:x for x in raw['items']};reportplan={x['primary_order']:x for x in plan['reports']};occmap={i:x for x in plan['reports'] for i in x['occurrence_orders']}
  for s in raw['sessions']:
   for j,name in enumerate(s['chairs']):
    nm=name.split(',')[0].strip()
    if nm:ins('session_chairs',session_id=cid+':'+s['session_id'],ordinal=j,person_id=person(nm),name_original=name.strip(),institution_original='',profile_url=None)
  for i,x in enumerate(raw['items']):
   aid=cid+':AGENDA:'+f'{i+1:04d}';amap[i]=aid;s=sessionmap[x['session_id']];isreport=i in occmap;fmt=occmap[i]['format'] if isreport else '活动/讨论/引介';begin=re.search(r'(\d+:\d+)\s*([ap])',x['start_time_text']);bh,bm=map(int,begin[1].split(':'));bh=bh%12+(12 if begin[2]=='p' else 0);start=f'{bh:02d}:{bm:02d}';end=None
   ins('agenda_items',agenda_item_id=aid,conference_id=cid,session_id=cid+':'+x['session_id'],source_code=None,source_order=i,title_original=x['title'],format_original=fmt,date_original=s['date'],local_date=date(s['date']),time_original=x['time_original'],start_time=start,end_time=end,room_original=s['room'],source_url='https://www.abstractsonline.com/SR/Diabetes/FinalProgram.asp',evidence_level='planned_agenda',material_id=structmid,source_locator=f'$.items[{i}]；PDF物理页'+','.join(map(str,x['pages'])),raw_json=json.dumps(x,ensure_ascii=False,sort_keys=True))
   if x['person_name']:ins('agenda_participants',agenda_item_id=aid,ordinal=0,person_id=person(x['person_name']),agenda_role='speaker' if isreport else 'listed_person',name_original=x['speaker_original'],institution_original='',profile_url=None,role_basis='程序Presenting Author或该定时讲题下的列名；非论文作者推断；主持独立保存。')
  for x in plan['reports']:
   rid=cid+':'+x['key'];ins('reports',report_id=rid,agenda_item_id=amap[x['primary_order']],conference_id=cid,source_report_code=x['key'],legacy_report_id=x['key'],legacy_evidence_id=cid+':EVIDENCE:'+x['key'],report_format=x['format'],evidence_status='agenda_only',has_results=0,result_text=None,independent_study_status='not_established')
   for i in x['occurrence_orders']:ins('conference_program_occurrences',report_id=rid,agenda_item_id=amap[i],programme_pages=json.dumps(itemmap[i]['pages']),is_primary=int(i==x['primary_order']))
  ins('analysis_versions',analysis_version_id=vid,conference_id=cid,analysis_kind='ada_topic_quantity',rule_label='ADA既有程序题名数量榜：规则辅助初分',review_status='rule_assisted_title_review_pending',is_current_snapshot=1,scoring_enabled=0,material_id=planmid,method_note='仅基于既有程序；2049条初分，490条待归类。人物/会议级别不加权，海报重复展示按同编号去重。')
  usedboards={t['parent_code'] for t in plan['topics']}
  for b in plan['boards']:
   if b['legacy_topic_id'] in usedboards:ins('research_topics',topic_id=cid+':'+b['legacy_topic_id'],conference_id=cid,legacy_topic_id=b['legacy_topic_id'],parent_topic_id=None,node_type='board',name=b['name'],research_question=None,taxonomy_status='working_classification',material_id=planmid)
  for t in plan['topics']:
   tid=cid+':'+t['code'];ins('research_topics',topic_id=tid,conference_id=cid,legacy_topic_id=t['code'],parent_topic_id=cid+':'+t['parent_code'],node_type='topic',name=t['name'],research_question=t['question'],taxonomy_status='working_classification',material_id=planmid)
   ins('conference_topic_scope',topic_id=tid,analysis_version_id=vid,template_topic_id='CDS2026:'+t['code'],width_status=t['width_status'],boundary_text=t['boundary'],evidence_gaps=t['gaps'])
  for x in plan['reports']:
   rid=cid+':'+x['key'];primary=itemmap[x['primary_order']];topic=x['topic_code'];ins('report_classifications',report_id=rid,analysis_version_id=vid,primary_topic_id=cid+':'+topic if topic else None,scope_original='规则辅助初分' if topic else '待归类',eligible=int(bool(topic)),classification_basis=x['basis'],material_id=structmid,source_locator=f'$.items[{x["primary_order"]}]')
   ins('conference_report_notes',report_id=rid,analysis_version_id=vid,classification_method=x['classification_method'],classification_basis=x['basis'],evidence_gaps=x['gaps'],cross_tags_json=json.dumps(x['cross_tags']))
  for x in plan['page_audit']:ins('conference_page_audit',conference_id=cid,physical_page=x['page'],parse_status=x['status'],code_occurrences=x['code_occurrences'])
  ins('conference_coverage',conference_id=cid,analysis_version_id=vid,programme_material_id=pdfmid,programme_text_material_id=textmid,source_snapshot_label='页眉2026-04-24的会前程序；PDF物理385页',original_observed_on='2026-11-11',coverage_json=json.dumps(plan['summary'],ensure_ascii=False),rules_path=str(rules.relative_to(r)),rules_sha256=sha(rules),plan_path=str((folder/'ADA入库方案.json').relative_to(r)),plan_sha256=sha(folder/'ADA入库方案.json'),gaps='不是最终实际报告清单；12页无编号卫星会/活动未逐报告解析，490条待归类，140条依赖专题背景。程序未含完整简介与研究结果；14篇为论文摘要。',new_collection=0)
  tr='ADA2026:ROLE-TIERS:20261117:v1';ins('tier_rule_versions',rule_version_id=tr,label='ADA既有程序角色：三级＋待定',assessed_on='2026-11-17',source_snapshot_date='2026-04-24',rule_path=str(rules.relative_to(r)),rule_sha256=sha(rules),decisions_path=str((folder/'ADA入库方案.json').relative_to(r)),decisions_sha256=sha(folder/'ADA入库方案.json'),assessment_method='仅原程序明确角色及致辞位置，非完整个人简介或实时任职核验',current_snapshot=1,new_collection=0)
  ins('conference_tier_assignments',conference_id=cid,rule_version_id=tr,tier_code='international_core',scope_label='国际性学术覆盖，与举办城市分开',assessment_status='provisional',basis_type='existing_official_programme',basis_text='原程序物理第2页记载Scientific Sessions为大型糖尿病会议，来自115多个国家的参与者；按业务规则暂列国际核心会议。',source_material_id=pdfmid,source_locator='PDF物理第1—2页',evidence_gaps='基于已有程序定位，不是本次新联网核验；不把会议国际层级传递给所有讲者。')
  speakerids={x[0] for x in c.execute("SELECT DISTINCT ap.person_id FROM conference_program_occurrences o JOIN reports rp USING(report_id) JOIN agenda_participants ap ON ap.agenda_item_id=o.agenda_item_id WHERE rp.conference_id='ADA2026' AND ap.agenda_role='speaker'")}
  roles={'Amy Hess-Fischl':('HCE-01','美国ADA·糖尿病照护与教育','President, Health Care & Education Address'), 'A. Enrique Caballero':('MSB-01','美国ADA·糖尿病医学与科学','President, Medicine & Science Address')}
  for pid in sorted(speakerids):
   name=c.execute('SELECT display_name FROM people WHERE person_id=?',(pid,)).fetchone()[0];role=roles.get(name)
   if not role:ins('speaker_tier_assignments',conference_id=cid,person_id=pid,rule_version_id=tr,tier_code='undetermined',domain_scope=None,assessment_status='insufficient_evidence',tenure_status='not_applicable',rationale='程序能确认列名讲者，未提供足够核心学术组织/研究协作角色。国际会议报告或主持、论文作者/获奖不单独决定层级。',evidence_gaps='待补可定位的个人官方简介、组织角色范围和任期；不因待定减少报告数。');continue
   sid,domain,quote=role;ss=sessionmap[sid];profileid=jid('PROFILE:',cid+'|programmerole|'+pid);context=ss['source_text'];pos=context.index(quote)
   ins('person_profiles',profile_id=profileid,person_id=pid,import_id=batch,profile_url='https://www.abstractsonline.com/SR/Diabetes/FinalProgram.asp',read_status='read',has_substantive_bio=0,extracted_text=context,fetch_error=None,raw_material_id=pdfmid,evidence_material_id=pdfmid,source_locator=f'PDF物理第{ss["page"]}页',source_observed_on='2026-04-24')
   ins('speaker_tier_assignments',conference_id=cid,person_id=pid,rule_version_id=tr,tier_code='national',domain_scope=domain,assessment_status='provisional_program_role',tenure_status='term_unverified',rationale='按原程序专题标题及致辞先后次序，暂关联该讲者与ADA主席相应专业职务；范围限美国全国性组织角色，不认定全球带头人。',evidence_gaps='程序角色关联为暂定；未取得完整简介，个人任期、该角色与致辞者的对应仍待官方履历独立核验。')
   ins('speaker_tier_evidence',evidence_id=jid('TIER-EVIDENCE:',tr+pid),conference_id=cid,person_id=pid,rule_version_id=tr,profile_id=profileid,source_material_id=pdfmid,source_locator=f'PDF物理第{ss["page"]}页；专题标题与列名顺序',quote_original=quote,context_original=context,char_start=pos,char_end=pos+len(quote),evidence_kind='programme_role_and_order_pending')
  curated=read(r/'原始资料/ADA2026/研究记录/ADA2026_研究动向.json')['items'];curmid=mids['原始资料/ADA2026/研究记录/ADA2026_研究动向.json'];paperfile='原始资料/ADA2026/关联论文/ADA_14篇原始论文摘要结构化.json';papers=read(r/paperfile)
  for i,p in enumerate(papers):ins('related_paper_abstracts',paper_id='PMID:'+p['pmid'],pmid=p['pmid'],doi=p.get('doi'),title_original=p['title'],journal=p.get('journal'),first_author=p.get('first_author'),source_url=p['url'],reading_level=p['reading_level'],source_material_id=mids[paperfile],source_locator=f'$[{i}]',raw_json=json.dumps(p,ensure_ascii=False))
  rkeys={x['key']:x for x in plan['reports']}
  for i,x in enumerate(curated):
   record=cid+':'+x['id'];ins('curated_research_records',record_id=record,conference_id=cid,legacy_id=x['id'],code_original=x['code'],title_curated=x['title'],evidence_level=x['evidence_level'],reading_level=x['reading_level'],source_date=x.get('source_date'),source_material_id=curmid,source_locator=f'$.items[{i}]',raw_json=json.dumps(x,ensure_ascii=False))
   if x['code'] in rkeys:matches=[rkeys[x['code']]];relation='exact_programme_abstract_number'
   else:
    trial=x['code'].replace(' ','[- ]?');matches=[p for p in plan['reports'] if not p['key'].endswith(('-P','-LB')) and re.search(trial,p['title'],re.I)];relation='matching_trial_name_pending_version_check'
   for p in matches:ins('curated_report_links',record_id=record,report_id=cid+':'+p['key'],relation_type=relation,basis='按既有编号精确关联' if relation.startswith('exact') else '程序原题包含同一试验名；仅做阅读关联，不据此确认论文/报告版本或独立研究身份')
   if x.get('paper') and any(p['pmid']==x['paper']['pmid'] for p in papers):ins('related_paper_links',record_id=record,paper_id='PMID:'+x['paper']['pmid'],relation_type='existing_curated_paper_link',basis='沿用既有研究记录中的论文关联；不追加会议报告计数，不以第一作者替代程序讲者。')
  # 旧记录保留校验，在提交前独立比对入库前数据库。
  previous=sqlite3.connect((r/baseline['backup_database']).as_uri()+'?mode=ro',uri=True)
  for t in baseline['tables']:
   cols=[x[1] for x in previous.execute('PRAGMA table_info('+t+')')];fields=','.join(cols);assert set(previous.execute('SELECT '+fields+' FROM '+t))<=set(tuple(x) for x in c.execute('SELECT '+fields+' FROM '+t)),t
  previous.close();assert not c.execute('PRAGMA foreign_key_check').fetchall();assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert c.execute("SELECT SUM(report_count) FROM v_cds_quantity_topic_counts").fetchone()[0]==579;assert c.execute('SELECT SUM(report_count) FROM v_ada_quantity_topic_counts').fetchone()[0]==2049
  assert not c.execute('SELECT conference_id,person_id,COUNT(*) FROM v_speaker_tiers GROUP BY conference_id,person_id HAVING COUNT(*)>1').fetchall()
  c.commit();c.execute('PRAGMA foreign_keys=ON');c.execute('PRAGMA legacy_alter_table=OFF')
  result=dict(result='imported',conference='ADA2026',summary=plan['summary'],speaker_identities=len(speakerids),speaker_tier_counts={x['tier_code']:x['identity_count'] for x in c.execute("SELECT * FROM v_speaker_tier_counts WHERE conference_id='ADA2026'")},source_materials=len(source),old_records_preserved=True,new_collection=False,published=False,database_sha256=sha(db));(folder/'ADA入库结果.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
 except BaseException:c.rollback();raise
 finally:c.close()
if __name__=='__main__':main()
