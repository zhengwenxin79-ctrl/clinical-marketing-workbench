from pathlib import Path
import json,sqlite3,hashlib,csv
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'规则与说明/论文议题复核_2026-11-17';WEB=ROOT/'论文视图'
def main():
 b=Path((OUT/'本轮备份位置.txt').read_text().strip());old=json.loads((b/'原表指纹.json').read_text());c=sqlite3.connect((ROOT/'数据库/marketing.db').as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
 for t,f in old.items():
  rows=[list(x) for x in c.execute('SELECT * FROM "'+t+'" ORDER BY rowid')];assert len(rows)==f['count'];assert hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==f['sha256'],t
 assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not c.execute('PRAGMA foreign_key_check').fetchall()
 data=json.loads((WEB/'论文数据快照.json').read_text());analysis=data['issue_analysis'];assert len(analysis['issues'])==51;assert len(analysis['boards'])==12;assert analysis['ranked_papers']==160
 assert sum(t['paper_count'] for t in analysis['issues'])==sum(b['paper_count'] for b in analysis['boards'])==160
 primary=[x for x in analysis['links'] if x['count_in_ranking']];assert len(primary)==len({x['paper_id'] for x in primary})==160
 assert {x['paper_id'] for x in primary}<={p['paper_id'] for p in data['papers'] if p['in_core_counts']}
 assert c.execute('SELECT COUNT(*) FROM literature_issue_paper_reviews').fetchone()[0]==163
 assert sum(p['in_issue_counts'] for p in data['papers'])==160 and len(data['papers'])==618
 P={p['paper_id']:p for p in data['papers']};assert not P['PMID:42627353']['in_issue_counts'] and P['PMID:42627353']['issue_review']['reviewed_type']=='review_or_guideline';assert not P['PMID:42961127']['in_issue_counts']
 assert len([p for p in data['papers'] if p['highlight'] and p['issue_review']])==7
 assert P['PMID:42820639']['issue_review']['relation']=='supporting' and not P['PMID:42820639']['in_issue_counts']
 assert all(p['issue_review']['finding_summary'] for p in data['papers'] if p['in_issue_counts'])
 assert all(l['leadership_status']=='paper_leadership_pending' for p in data['papers'] for l in p['team_links'])
 with (WEB/'糖尿病文章基础表.csv').open(encoding='utf-8-sig',newline='') as f:csvrows=list(csv.DictReader(f))
 assert len(csvrows)==618 and sum(x['参与议题榜计数']=='True' for x in csvrows)==160
 changed_boards=c.execute('SELECT COUNT(*) FROM literature_issue_links l JOIN literature_issues i USING(issue_id) JOIN literature_classifications old USING(paper_id) WHERE l.count_in_ranking=1 AND i.board_id<>old.board_id').fetchone()[0]
 kept=0
 for folder in ['会议总入口','会议视图']:
  for p in (b/folder).rglob('*'):
   if p.is_file():assert p.read_bytes()==(ROOT/folder/p.relative_to(b/folder)).read_bytes(),str(p);kept+=1
 source_files=0
 for m in c.execute('SELECT relative_path,sha256 FROM source_materials'):assert hashlib.sha256((ROOT/m['relative_path']).read_bytes()).hexdigest()==m['sha256'];source_files+=1
 c.close();m=json.loads((WEB/'生成记录.json').read_text());assert m['html_sha256']==hashlib.sha256((WEB/'index.html').read_bytes()).hexdigest();assert m['database_sha256']==hashlib.sha256((ROOT/'数据库/marketing.db').read_bytes()).hexdigest()
 result=dict(result='passed',old_tables_preserved=len(old),reviewed_core=162,ranked=160,issues=51,reassigned_board_count=changed_boards,background=2,existing_supplement=1,highlights_linked=7,old_meeting_files_preserved=kept,source_files_verified=source_files,new_collection=False,published=False)
 (WEB/'议题数据核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
