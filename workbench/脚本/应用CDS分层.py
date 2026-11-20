"""在已有数据库上追加可审计分层；不改原始表，无网络。相同版本重跑只读跳过。"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sqlite3

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def data(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);a=ap.parse_args();root=a.root.resolve();db=root/'数据库/marketing.db';folder=root/'规则与说明/讲者与会议分层_2026-11-17';rules=folder/'分层口径.md';selection=folder/'分层选择.tsv';version='CDS2026:ROLE-TIERS:20261117:v1';source=data(folder/'已有简介候选片段.json');before=data(folder/'变更前基线.json');decisions={}
 for line in selection.read_text(encoding='utf-8').splitlines():
  if not line or line.startswith('#'):continue
  idx,tier,scope,picks,tenure,note=line.split('|');s=source[int(idx)];assert s['person_id'] not in decisions
  evidence=[]
  for i in map(int,picks.split(',')):
   quote=s['fragments'][i];matches=[p for p in s['profiles'] if p.get('read_status')=='read' and quote in (p.get('extracted_text') or '').split('学术任务如下')[0]];assert matches,(s['name'],quote);p=matches[0];text=p['extracted_text'];start=text.index(quote);end=start+len(quote)
   context=text[max(text.rfind('。',0,start)+1,text.rfind('简历：',0,start)+3,0):min(len(text),end+150)].split('学术任务如下')[0]
   eid='TIER-EVIDENCE:'+hashlib.sha256((version+s['person_id']+quote).encode()).hexdigest()[:20]
   kind='national_guideline_or_multicentre' if int(idx)==10 else 'national_infrastructure' if int(idx) in {40,99,102,129} else 'academic_organization_leadership'
   evidence.append(dict(evidence_id=eid,profile_id=p['profile_id'],source_material_id=p['evidence_material_id'],source_locator=p['source_locator']+f'.text[{start}:{end}]',quote_original=quote,context_original=context,char_start=start,char_end=end,evidence_kind=kind))
  decisions[s['person_id']]=dict(tier_code=tier,domain_scope=scope,tenure_status=tenure,evidence=evidence,note=note)
 conn=sqlite3.connect(db);conn.row_factory=sqlite3.Row;conn.execute('PRAGMA foreign_keys=ON')
 try:
  if conn.execute("SELECT COUNT(*) FROM sqlite_schema WHERE name='tier_rule_versions'").fetchone()[0]:
   old=conn.execute('SELECT * FROM tier_rule_versions WHERE rule_version_id=?',(version,)).fetchone()
   if old:
    assert old['rule_sha256']==sha(rules) and old['decisions_sha256']==sha(selection),'同版本规则改变；请使用新版本，未覆盖'
    print(json.dumps({'result':'already_applied','rule_version':version},ensure_ascii=False));return
  assert sha(db)==before['database_sha256'],'数据库已变化，停止迁移以便复核'
  conn.executescript('BEGIN IMMEDIATE;\n'+(root/'规则与说明/002_讲者与会议分层.sql').read_text())
  def insert(table,**values):conn.execute(f"INSERT INTO {table} ({','.join(values)}) VALUES ({','.join('?' for _ in values)})",list(values.values()))
  insert('tier_rule_versions',rule_version_id=version,label='CDS讲者三级角色与会议覆盖范围 v1',assessed_on='2026-11-17',source_snapshot_date='2026-11-16',rule_path=str(rules.relative_to(root)),rule_sha256=sha(rules),decisions_path=str(selection.relative_to(root)),decisions_sha256=sha(selection),assessment_method='AI逐项复核已有简介原文；讲者层级暂定待人工确认；CDS会议层级为用户明确确认',current_snapshot=1,new_collection=0)
  speakers=[dict(x) for x in conn.execute("SELECT DISTINCT p.* FROM people p JOIN agenda_participants ap USING(person_id) JOIN reports r USING(agenda_item_id) WHERE r.conference_id='CDS2026' AND ap.agenda_role='speaker' ORDER BY p.person_id")]
  assert len(speakers)==533;assert set(decisions)<=set(p['person_id'] for p in speakers)
  labels={'international':'国际学术带头人','national':'全国学术带头人','regional':'区域／专科学术带头人','undetermined':'层级待定'}
  for p in speakers:
   d=decisions.get(p['person_id']);profiles=[dict(x) for x in conn.execute('SELECT * FROM person_profiles WHERE person_id=?',(p['person_id'],))]
   if d:
    note=d['note'];rationale='已有会议简介记载：'+'；'.join(x['quote_original'] for x in d['evidence'])+'。按本版规则暂列'+labels[d['tier_code']]+'，领域限“'+d['domain_scope']+'”。'
    gaps='角色任期及组织覆盖范围尚未独立核验；本轮为既有简介初步分层，待人工确认。'+note
    insert('speaker_tier_assignments',conference_id='CDS2026',person_id=p['person_id'],rule_version_id=version,tier_code=d['tier_code'],domain_scope=d['domain_scope'],assessment_status='provisional_existing_bio',tenure_status=d['tenure_status'],rationale=rationale,evidence_gaps=gaps)
    for e in d['evidence']:
     original=conn.execute('SELECT * FROM person_profiles WHERE profile_id=?',(e['profile_id'],)).fetchone();assert original['person_id']==p['person_id'];assert original['extracted_text'][e['char_start']:e['char_end']]==e['quote_original'];assert original['evidence_material_id']==e['source_material_id']
     insert('speaker_tier_evidence',conference_id='CDS2026',person_id=p['person_id'],rule_version_id=version,**e)
   else:
    if not profiles:reason='该来源身份尚无简介读取记录，无法依据姓名和单位判断学术覆盖层级。';gap='待补可定位的官方学术组织/研究协作角色、具体领域与任期依据。'
    elif not any(x['read_status']=='read' and x['has_substantive_bio'] for x in profiles):reason='已有简介未读成功或缺少实质履历，尚不足以定层。';gap='待补可读取的实质简介及其学术组织/研究协作角色。'
    else:reason='已复核现有简介，尚无符合本版覆盖层级规则的明确核心角色；一般委员、院内职务、人才称号或项目资助不单独定层。';gap='待补组织或研究协作的明确牵头角色、覆盖范围、具体领域与任期；不据此推断学术水平较低。'
    insert('speaker_tier_assignments',conference_id='CDS2026',person_id=p['person_id'],rule_version_id=version,tier_code='undetermined',domain_scope=None,assessment_status='insufficient_evidence',tenure_status='not_applicable',rationale=reason,evidence_gaps=gap)
  meta=conn.execute("SELECT metadata_material_id FROM conference_editions WHERE conference_id='CDS2026'").fetchone()
  insert('conference_tier_assignments',conference_id='CDS2026',rule_version_id=version,tier_code='national_major',scope_label='全国性学术覆盖；举办地点独立保存',assessment_status='user_confirmed',basis_type='user_instruction_with_existing_title_reference',basis_text='用户于2026-11-17在本轮对话明确确认：CDS属于国内全国性大型会议。既有官方日程保留大会全称，作为资料参考；不是本次新联网核验。',source_material_id=meta[0],source_locator='conference_editions.name_original；用户对话2026-11-17',evidence_gaps='会议层级已按用户业务口径确认；主办方、举办国与具体场馆等原有元数据缺口继续保留，不从层级反填地点。')
  for t,expected in before['original_table_fingerprints'].items():
   actual=hashlib.sha256(json.dumps([tuple(x) for x in conn.execute('SELECT * FROM '+t+' ORDER BY rowid')],ensure_ascii=False,sort_keys=True).encode()).hexdigest();assert actual==expected,t
  assert conn.execute("SELECT COUNT(*) FROM v_speaker_tiers WHERE tier_code<>'undetermined' AND evidence_count=0").fetchone()[0]==0
  assert not conn.execute('PRAGMA foreign_key_check').fetchall();assert conn.execute('PRAGMA integrity_check').fetchone()[0]=='ok';conn.commit()
  result={'result':'applied','rule_version':version,'counts':{x['tier_code']:x['identity_count'] for x in conn.execute('SELECT * FROM v_speaker_tier_counts')},'speaker_records':533,'evidence_rows':conn.execute('SELECT COUNT(*) FROM speaker_tier_evidence').fetchone()[0],'conference_tier':'国内全国性大型会议','original_20_tables_unchanged':True,'new_collection':False,'published':False,'database_sha256':sha(db)}
  (folder/'分层应用结果.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
 except BaseException:conn.rollback();raise
 finally:conn.close()
if __name__=='__main__':main()
