"""只读导出论文池、初分数量及作者角色线索；不采集、不发布。"""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import sqlite3,json,csv,hashlib
from 论文文献分类 import classify_document,CATEGORIES
ROOT=Path(__file__).resolve().parents[1]
def main():
 out=ROOT/'论文视图';out.mkdir(exist_ok=True);c=sqlite3.connect((ROOT/'数据库/marketing.db').as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON')
 papers=[dict(x) for x in c.execute('SELECT * FROM v_literature_pool ORDER BY publication_date DESC,paper_id')]
 authors={}
 for x in c.execute('SELECT * FROM literature_authors ORDER BY paper_id,ordinal'):
  a=dict(x);a['affiliations']=json.loads(a.pop('affiliations_json'));authors.setdefault(a['paper_id'],[]).append(a)
 links={}
 for x in c.execute('SELECT * FROM literature_author_links'):
  a=dict(x);links.setdefault(a['paper_id'],[]).append(a)
 highlights={x['paper_id']:dict(x) for x in c.execute('SELECT * FROM literature_highlights')}
 for p in papers:
  p.pop('abstract_json');p['authors']=authors.get(p['paper_id'],[]);p['team_links']=links.get(p['paper_id'],[]);p['highlight']=highlights.get(p['paper_id'])
 people=[dict(x) for x in c.execute('SELECT * FROM literature_people JOIN literature_person_roles USING(person_id)')]
 boards=[dict(x) for x in c.execute("SELECT topic_id AS board_id,name AS board_name FROM research_topics WHERE conference_id='CDS2026' AND node_type='board'")]
 counts=[dict(x) for x in c.execute('SELECT * FROM v_literature_board_counts ORDER BY paper_count DESC,board_id')]
 sources=[dict(x) for x in c.execute('SELECT * FROM literature_sources JOIN literature_source_checks USING(source_id)')]
 run=dict(c.execute('SELECT * FROM literature_runs ORDER BY collected_on DESC LIMIT 1').fetchone())
 issue_analysis=None
 if c.execute("SELECT 1 FROM sqlite_master WHERE name='literature_issue_versions'").fetchone():
  version=dict(c.execute('SELECT * FROM literature_issue_versions WHERE is_current=1').fetchone());vid=version['version_id']
  issues=[dict(x) for x in c.execute('SELECT * FROM v_literature_issue_counts ORDER BY paper_count DESC,issue_id')]
  issue_links=[dict(x) for x in c.execute('SELECT * FROM literature_issue_links WHERE version_id=?',(vid,))]
  reviews={x['paper_id']:dict(x) for x in c.execute('SELECT * FROM literature_issue_paper_reviews WHERE version_id=?',(vid,))}
  by_id={x['issue_id']:x for x in issues};by_paper={x['paper_id']:x for x in issue_links}
  for p in papers:
   r=reviews.get(p['paper_id']);link=by_paper.get(p['paper_id'])
   p['in_issue_counts']=bool(link and link['count_in_ranking'])
   if r and link:
    topic=by_id[link['issue_id']];p['issue_review']=dict(r,issue_id=topic['issue_id'],issue_name=topic['name'],board_id=topic['board_id'],board_name=topic['board_name'],relation=link['relation'],relation_basis=link['basis'])
   else:p['issue_review']=None
  new_boards=[]
  for b in boards:
   ts=[t for t in issues if t['board_id']==b['board_id']];new_boards.append(dict(b,paper_count=sum(t['paper_count'] for t in ts),issue_count=len(ts)))
  new_boards.sort(key=lambda x:(-x['paper_count'],x['board_id']))
  issue_analysis=dict(version=version,issues=issues,links=issue_links,boards=new_boards,ranked_papers=sum(x['count_in_ranking'] for x in issue_links),background_count=sum(x['relation']=='background' for x in issue_links),supporting_count=sum(x['relation']=='supporting' for x in issue_links))
 c.close()
 original={p['paper_id']:p for p in json.loads((ROOT/'原始资料/论文首轮_2026-11-17/论文结构化初稿.json').read_text())}
 for p in papers:p['document_classification']=classify_document(p,original.get(p['paper_id'],{}))
 document_counts={k:sum(p['document_classification']['category']==k for p in papers) for k in CATEGORIES}
 data=dict(meta=dict(generated_on=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds'),database_sha256=hashlib.sha256((ROOT/'数据库/marketing.db').read_bytes()).hexdigest(),read_only=True,published=False),run=run,papers=papers,people=people,boards=boards,board_counts=counts,sources=sources,issue_analysis=issue_analysis,document_categories=CATEGORIES,document_counts=document_counts)
 (out/'文献分类快照.json').write_text(json.dumps(dict(categories=CATEGORIES,counts=document_counts,records=[dict(paper_id=p['paper_id'],**p['document_classification']) for p in papers]),ensure_ascii=False,indent=2)+'\n')
 (out/'论文数据快照.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 fields=['论文ID','题名','期刊','发表日期','日期口径','时间状态','来源层','文章类型','研究板块','第一作者','末位作者线索','已核角色参与','团队归属状态','具体研究问题','主要发现','阅读层级','DOI','PMID','原始链接','归类依据','复核主议题','复核研究板块','复核文献类型','证据类型','参与议题榜计数','展示文献分类','展示分类依据']
 names={p['person_id']:p for p in people}
 with (out/'糖尿病文章基础表.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(fields)
  for p in papers:
   a=[x for x in p['authors'] if not x['is_collective']];h=p['highlight'] or {};review=p.get('issue_review') or {}
   verified=[names[x['person_id']]['display_name'] for x in p['team_links'] if x['identity_status']=='name_and_institution_checked']
   w.writerow([p['paper_id'],p['title'],p['journal'],p['publication_date'],p['date_basis'],p['window_status'],p['source_tier'],p['article_type'],p['board_name'],a[0]['name_original'] if a else '',a[-1]['name_original'] if a else '','; '.join(verified),'通讯作者/课题PI/团队归属待核',h.get('research_question') or review.get('issue_name',''),review.get('finding_summary') or h.get('finding_summary') or p.get('summary_curated') or ('摘要已存/发现待提炼' if p['reading_level']=='indexed_abstract' else '主要发现待提炼'),p['reading_level'],p['doi'],p['pmid'],p['source_url'],p['classification_basis'],review.get('issue_name',''),review.get('board_name',''),review.get('reviewed_type',''),review.get('evidence_kind',''),p.get('in_issue_counts',False),p['document_classification']['label'],p['document_classification']['basis']])
 src=out/'src';embedded=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
 html=(src/'template.html').read_text().replace('__STYLE__',(src/'style.css').read_text()+'\n'+(src/'issues.css').read_text()).replace('__DATA__',embedded).replace('__ISSUE_APP__',(src/'issues.js').read_text()).replace('__APP__',(src/'app.js').read_text());(out/'index.html').write_text(html)
 result=dict(result='generated',paper_count=len(papers),in_window=sum(p['window_status']=='in_window' for p in papers),legacy_core_candidates=sum(p['in_core_counts'] for p in papers),issue_ranked_papers=issue_analysis['ranked_papers'],issues=len(issue_analysis['issues']),highlights=len(highlights),author_records=sum(len(x) for x in authors.values()),source_count=len(sources),role_people=len(people),database_sha256=data['meta']['database_sha256'],html_sha256=hashlib.sha256(html.encode()).hexdigest(),published=False)
 (out/'生成记录.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
