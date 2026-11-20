"""Validate read-only restructuring and conservation across the new domain taxonomy."""
from pathlib import Path
from collections import Counter
import json,hashlib,sqlite3
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(rel):return json.loads((ROOT/rel).read_text())
def main():
 baseline=load('规则与说明/领域框架整理_2026-11-18/变更前基线.json');assert sha(ROOT/'数据库/marketing.db')==baseline['database_sha256']
 D=load('领域工作台/领域数据快照.json');tax=D['taxonomy'];a=load('会议总入口/领域热点数据快照.json');p=load('论文视图/论文数据快照.json');bm=load('标志物视图/标志物数据快照.json')
 assert len(D['boards'])==12 and len(D['topics'])==66 and len(D['papers'])==618
 assert len(tax['mappings'])==109 and len({(m['source_kind'],m['source_id']) for m in tax['mappings']})==109
 assert {m['source_id'] for m in tax['mappings'] if m['source_kind']=='paper_issue'}=={x['issue_id'] for x in p['issue_analysis']['issues']}
 assert {m['source_id'] for m in tax['mappings'] if m['source_kind']=='conference_topic'}=={x['topic_id'] for x in a['topics']}
 reports=[id for t in D['topics'] for id in t['report_ids']];papers=[id for t in D['topics'] for id in t['paper_ids']]
 assert len(reports)==len(set(reports))==2628 and set(reports)=={x['report_id'] for x in a['reports']}
 assert len(papers)==len(set(papers))==160 and set(papers)=={x['paper_id'] for x in p['papers'] if x['in_issue_counts']}
 assert all(not t['report_ids'] and t['paper_ids'] for t in D['topics'] if t['origin']=='paper_directory_extension')
 assert sum(t['origin']=='paper_directory_extension' for t in D['topics'])==8
 assert len(D['biomarkers'])==len(bm['biomarkers'])==39 and sum(b['reference_endpoint'] for b in D['biomarkers'])==7
 for source in p['issue_analysis']['boards']:
  board='DM:'+source['board_id'].split(':')[-1];assert sum(len(t['paper_ids']) for t in D['topics'] if t['board_id']==board)==source['paper_count']
 assert D['summary']['known_role_records']==139 and len(D['experts'])==2277
 assert len({e['key'] for e in D['experts']})==2277
 assert all(e['source_kind']=='conference' or e['key'].startswith('paper|') for e in D['experts'])
 source_people={x['key']:x for x in a['people']}
 assert all(e['tier_code']==source_people[e['key']]['tier_code'] for e in D['experts'] if e['source_kind']=='conference')
 assert len(D['navigation']['modules'])==6 and [m['label'] for m in D['navigation']['modules']]==['领域热点','会议库','论文库','专家与团队','市场工作台','销售工作台']
 assert len(D['navigation']['domains'])==6 and sum(d['connected'] for d in D['navigation']['domains'])==1
 c=sqlite3.connect((ROOT/'数据库/marketing.db').as_uri()+'?mode=ro',uri=True);assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not c.execute('PRAGMA foreign_key_check').fetchall();c.close()
 for html,m in [('领域工作台/index.html','领域工作台/生成记录.json'),('会议总入口/index.html','会议总入口/生成记录.json'),('论文视图/index.html','论文视图/生成记录.json'),('标志物视图/index.html','标志物视图/生成记录.json'),('会议视图/index.html','会议视图/生成记录.json'),('会议视图/ada.html','会议视图/ADA生成记录.json')]:
  v=load(m);assert v['html_sha256']==sha(ROOT/html) and v['database_sha256']==baseline['database_sha256']
 for html in ['会议总入口/index.html','论文视图/index.html','标志物视图/index.html','会议视图/index.html','会议视图/ada.html']:
  s=(ROOT/html).read_text();start=s.index('<nav class="framework-nav"');end=s.index('</nav>',start);nav=s[start:end];assert nav.count('<a ')==4 and 'Biomarker热点' not in nav;assert all(word in nav for word in ['领域热点','会议库','论文库','专家与团队'])
 result=dict(result='passed',database_unchanged=True,boards=12,domain_topics=66,paper_extensions=8,mappings=109,conference_reports_preserved=2628,primary_papers_preserved=160,article_pool=618,biomarkers_preserved=39,source_identity_records=2277,known_role_records=139,roles_not_scored=True,new_collection=False,published=False)
 (ROOT/'规则与说明/领域框架整理_2026-11-18/数据核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
