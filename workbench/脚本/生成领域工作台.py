"""Read-only domain workbench: join existing source classifications; never collect or score PI identity."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
from urllib.parse import quote
import json,hashlib,sqlite3
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(rel):return json.loads((ROOT/rel).read_text(encoding='utf-8'))
def main():
 dbhash=sha(ROOT/'数据库/marketing.db');nav=load('框架配置/研究领域与导航.json');tax=load('框架配置/糖尿病统一议题映射.json')
 conf=load('会议总入口/领域热点数据快照.json');catalog=load('会议总入口/会议目录快照.json');lit=load('论文视图/论文数据快照.json');bm=load('标志物视图/标志物数据快照.json')
 assert all(x['meta']['database_sha256']==dbhash for x in [conf,catalog,lit,bm]),'Regenerate source exports first'
 mapping={(x['source_kind'],x['source_id']):x for x in tax['mappings']};topics={x['topic_id']:dict(x,report_ids=[],paper_ids=[],supporting_paper_ids=[],biomarker_ids=[],expert_keys=[]) for x in tax['topics']};boards={x['board_id']:dict(x,topic_ids=[]) for x in tax['boards']}
 for t in topics.values():boards[t['board_id']]['topic_ids'].append(t['topic_id'])
 reports=[]
 for r in conf['reports']:
  tid=mapping['conference_topic',r['topic_id']]['topic_id'];report=dict(r,source_topic_id=r['topic_id'],topic_id=tid);reports.append(report);topics[tid]['report_ids'].append(r['report_id'])
 report_map={r['report_id']:r for r in reports};papers=[]
 for p in lit['papers']:
  issue=p.get('issue_review');target=mapping.get(('paper_issue',issue['issue_id'])) if issue else None;tid=target['topic_id'] if target else None
  row={k:p.get(k) for k in ['paper_id','pmid','doi','title','journal','publication_date','window_status','source_tier','reading_level']}
  row.update(topic_id=tid,source_issue_id=issue['issue_id'] if issue else None,source_issue_name=issue['issue_name'] if issue else None,primary_counted=bool(p.get('in_issue_counts')),type=p['document_classification']['category'],type_label=p['document_classification']['label'],finding=issue.get('finding_summary') if issue else (p.get('highlight') or {}).get('finding_summary'),authors=[a['name_original'] for a in p['authors']],expert_keys=['paper|'+x['person_id'] for x in p['team_links']],detail_url='../论文视图/index.html#paper/'+quote(p['paper_id'],safe=''),source_url=p['source_url'])
  papers.append(row)
  if tid:topics[tid]['paper_ids' if row['primary_counted'] else 'supporting_paper_ids'].append(p['paper_id'])
 paper_map={p['paper_id']:p for p in papers};experts={}
 for p in conf['people']:
  related=[r for r in reports if p['key'] in r['speaker_keys']]
  experts[p['key']]=dict(p,source_kind='conference',source_label=p['conference_id'],report_ids=[r['report_id'] for r in related],paper_ids=[],topic_ids=sorted({r['topic_id'] for r in related}),role_scope=p.get('domain_scope') or '领域依据待补',pi_status='课题PI身份未由讲者身份推定',identity_status='source_record',role_basis=p.get('rationale') or '',source_url=None)
 for p in lit['people']:
  key='paper|'+p['person_id'];related=[x for x in papers if key in x['expert_keys']]
  experts[key]=dict(key=key,person_id=p['person_id'],display_name=p['display_name'],institution_source='单位见原始论文及身份依据',tier_code=p['tier_code'],tier_label={'international':'国际学术角色','national':'全国学术角色','regional':'区域/专科学术角色','undetermined':'角色待定'}[p['tier_code']],role_scope=p['domain_scope'],domain_scope=p['domain_scope'],tenure_status=p['tenure_note'],role_basis=p['role_basis'],source_kind='paper',source_label='论文身份线索',report_ids=[],paper_ids=[x['paper_id'] for x in related],topic_ids=sorted({x['topic_id'] for x in related if x['topic_id']}),source_url=p['source_url'],detail_url='../论文视图/index.html#teams',identity_status=p['identity_status'],pi_status='署名参与，通讯/课题PI关系待核' if p['identity_status']=='name_and_institution_checked' else '同名/跨语言作者身份待核；通讯/课题PI关系未确认',evidence_gaps='仅姓名与单位匹配通过者可确认论文参与；不推断牵头关系。')
 for t in topics.values():
  t['expert_keys']=sorted({k for rid in t['report_ids'] for k in report_map[rid]['speaker_keys']}|{k for pid in t['paper_ids'] for k in paper_map[pid]['expert_keys']})
 markers=[]
 for b in bm['biomarkers']:
  cs=[x for x in bm['contexts'] if x['biomarker_id']==b['biomarker_id']];ids={x['context_id'] for x in cs};es=[x for x in bm['evidence'] if x['context_id'] in ids]
  tids={report_map[e['report_id']]['topic_id'] for e in es if e['report_id'] in report_map}|{paper_map[e['paper_id']]['topic_id'] for e in es if e['paper_id'] in paper_map and paper_map[e['paper_id']]['topic_id']}
  row=dict(biomarker_id=b['biomarker_id'],name=b['name_zh'],standard_name=b['standard_name'],reference_endpoint=b['reference_endpoint'],topic_ids=sorted(tids),context_ids=sorted(ids),has_results=any(e['has_result_evidence'] for e in es),purposes=sorted({x['category'] for x in cs}),detail_url='../标志物视图/index.html#research?bm='+quote(b['biomarker_id'],safe='')+('&refs=include' if b['reference_endpoint'] else ''),association_basis='沿用该指标证据所连接的原报告/论文主议题；无来源分类时保留待归类。')
  markers.append(row)
  if not b['reference_endpoint']:
   for tid in tids:topics[tid]['biomarker_ids'].append(b['biomarker_id'])
 c=sqlite3.connect((ROOT/'数据库/marketing.db').as_uri()+'?mode=ro',uri=True);assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok';c.close()
 assert sum(len(t['report_ids']) for t in topics.values())==2628
 assert sum(len(t['paper_ids']) for t in topics.values())==160
 assert len(topics)==66 and len(boards)==12
 out=ROOT/'领域工作台';data=dict(meta=dict(generated_on=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),database_sha256=dbhash,read_only=True,new_collection=False,published=False,scope='框架与现有分类整理；采集由WorkBuddy执行'),navigation=nav,taxonomy=tax,boards=list(boards.values()),topics=list(topics.values()),reports=reports,papers=papers,experts=list(experts.values()),biomarkers=markers,conferences=conf['conferences'],catalog=catalog,weekly=dict(timezone='Asia/Shanghai',change_log=load('框架配置/会议更新记录.json')),sales=load('框架配置/销售协作原型.json'),pi_ratings=load('框架配置/PI已有评级.json'),summary=dict(boards=len(boards),topics=len(topics),conference_topics=58,paper_extensions=8,papers=618,primary_papers=160,reports=2628,talk_reports=sum(r['cohort']=='talks' for r in reports),expert_records=len(experts),known_role_records=sum(p['tier_code']!='undetermined' for p in experts.values()),biomarkers=len(markers),unclassified_biomarkers=sum(not b['topic_ids'] for b in markers),reference_biomarkers=sum(b['reference_endpoint'] for b in markers)),method=dict(meeting=conf['method'],paper='领域议题数量沿用核心四刊、窗口内、已复核主池160篇；其它资料可检索或作为补充，不自动加进主池。',mapping='已有12板块，58会议工作议题与51论文议题整理为66领域议题；8项缺少准确会议对应，单列论文补充议题。所有对应是分类草案，不是同研究或因果认定。',people='人物按来源身份保留，跨来源不按姓名自动合并；学术角色、论文署名和课题PI是不同字段，不加进关注度。',roles='我们维护框架、分类和展示；WorkBuddy采集资料、保留原文并按约定提交待审核增量。'))
 demo=data['sales']['demo_recommendation'];assert demo['topic_id'] in topics
 for item in demo['links']:assert item['id'] in (report_map if item['kind']=='report' else paper_map)
 assert set(demo['capability_ids'])<=set(x['id'] for x in data['sales']['capabilities'])
 snapshot=json.dumps(data,ensure_ascii=False,indent=2)+'\n';(out/'领域数据快照.json').write_text(snapshot,encoding='utf-8')
 pending=dict(paper_extensions=[dict(topic_id=t['topic_id'],name=t['name'],source_issue_ids=[m['source_id'] for m in tax['mappings'] if m['topic_id']==t['topic_id']],status='保留论文独立议题，会议对应待核') for t in topics.values() if t['origin']=='paper_directory_extension'],biomarkers=[dict(biomarker_id=b['biomarker_id'],name=b['name'],context_ids=b['context_ids'],status='来源尚未建立准确主议题关联；待分类') for b in markers if not b['topic_ids']],owner='分类结构由我们维护；具体来源与信息增量由WorkBuddy提交，保留证据后复核。')
 (out/'分类待办.json').write_text(json.dumps(pending,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 src=out/'src';embed=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c');html=(src/'template.html').read_text(encoding='utf-8').replace('__STYLE__',((src/'style.css').read_text(encoding='utf-8')+'\n'+(src/'weekly.css').read_text(encoding='utf-8')+'\n'+(src/'sales.css').read_text(encoding='utf-8')+'\n'+(src/'pi-recommendations.css').read_text(encoding='utf-8')+'\n'+(src/'recommendation-feedback.css').read_text(encoding='utf-8'))).replace('__DATA__',embed).replace('__DOMAIN_FRAMEWORKS__',(src/'domain-frameworks.js').read_text(encoding='utf-8')).replace('__WEEK_APP__',(src/'weekly.js').read_text(encoding='utf-8')).replace('__PI_APP__',(src/'pi-recommendations.js').read_text(encoding='utf-8')).replace('__QUALITY_APP__',(src/'recommendation-feedback.js').read_text(encoding='utf-8')).replace('__SALES_APP__',(src/'sales.js').read_text(encoding='utf-8')).replace('__OVERVIEW_APP__',(src/'overview.js').read_text(encoding='utf-8')).replace('__APP__',(src/'app.js').read_text(encoding='utf-8'));(out/'index.html').write_text(html,encoding='utf-8')
 roothtml='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=领域工作台/index.html"><title>临床科研热点工作台</title><a href="领域工作台/index.html">进入临床科研热点工作台</a></html>'
 (ROOT/'index.html').write_text(roothtml,encoding='utf-8')
 assert sha(ROOT/'数据库/marketing.db')==dbhash
 result=dict(result='generated',database_sha256=dbhash,html_sha256=sha(out/'index.html'),snapshot_sha256=sha(out/'领域数据快照.json'),counts=data['summary'],database_unchanged=True,new_collection=False,published=False)
 (out/'生成记录.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
