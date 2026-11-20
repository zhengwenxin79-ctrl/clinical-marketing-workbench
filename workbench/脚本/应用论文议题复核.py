"""将已有摘要复核及议题归并追加为新版本，不改旧论文/会议记录。"""
from pathlib import Path
import json,sqlite3,hashlib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'规则与说明/论文议题复核_2026-11-17'
def digest(c,t):
 rows=[list(r) for r in c.execute('SELECT * FROM "'+t+'" ORDER BY rowid')]
 return dict(count=len(rows),sha256=hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()).hexdigest())
def main():
 definition=json.loads((OUT/'议题定义与归并.json').read_text());reviews=json.loads((OUT/'逐篇研究问题与结果复核.json').read_text());backup=Path((OUT/'本轮备份位置.txt').read_text().strip());old=json.loads((backup/'原表指纹.json').read_text());vid=definition['version_id'];c=sqlite3.connect(ROOT/'数据库/marketing.db');c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
 assert all(digest(c,t)==f for t,f in old.items())
 assert hashlib.sha256((OUT/'复核输入快照.json').read_bytes()).hexdigest()==definition['input_sha256']
 try:
  c.executescript('BEGIN IMMEDIATE;\n'+(ROOT/'规则与说明/007_论文议题.sql').read_text())
  c.execute('UPDATE literature_issue_versions SET is_current=0 WHERE version_id<>?',(vid,))
  c.execute('INSERT OR IGNORE INTO literature_issue_versions VALUES(?,?,?,?,?,?,?)',(vid,'2026-11-17',definition['input_sha256'],definition['review_scope'],len(reviews),1,str((OUT/'议题定义与归并.json').relative_to(ROOT))))
  for t in definition['topics']:
   c.execute('INSERT OR IGNORE INTO literature_issues VALUES(?,?,?,?,?,?,?,?)',(t['issue_id'],vid,t['board_id'],t['name'],t['boundary_text'],t['progress_summary'],t['limits_text'],t['width_status']))
   for pid in t['paper_ids']:c.execute('INSERT OR IGNORE INTO literature_issue_links VALUES(?,?,?,?,?,?)',(vid,t['issue_id'],pid,'primary',1,'按本轮题名和摘要方法/结论复核，只进入一个主议题'))
  for x in definition['exclusions']:c.execute('INSERT OR IGNORE INTO literature_issue_links VALUES(?,?,?,?,?,?)',(vid,x['related_issue_id'],x['paper_id'],'background',0,x['reason']))
  for x in definition['supporting']:c.execute('INSERT OR IGNORE INTO literature_issue_links VALUES(?,?,?,?,?,?)',(vid,x['issue_id'],x['paper_id'],'supporting',0,'沿用已有重点进展摘要，来源覆盖不同，不进入四刊主榜数量'))
  for r in reviews:
   board=c.execute('SELECT board_id FROM literature_classifications WHERE paper_id=?',(r['paper_id'],)).fetchone()[0]
   c.execute('INSERT OR IGNORE INTO literature_issue_paper_reviews VALUES(?,?,?,?,?,?,?,?,?,?,?)',(vid,r['paper_id'],r['reviewed_type'],r['evidence_kind'],r['finding_summary'],r['method_excerpt'],r['result_excerpt'],r['review_basis'],board,'ai_excerpt_review_pending_mentor',str((OUT/'逐篇研究问题与结果复核.json').relative_to(ROOT))))
  for x in definition['supporting']:
   h=c.execute('SELECT * FROM literature_highlights WHERE paper_id=?',(x['paper_id'],)).fetchone();board=c.execute('SELECT board_id FROM literature_classifications WHERE paper_id=?',(x['paper_id'],)).fetchone()[0]
   c.execute('INSERT OR IGNORE INTO literature_issue_paper_reviews VALUES(?,?,?,?,?,?,?,?,?,?,?)',(vid,x['paper_id'],'original_abstract_reviewed','人体干预／试验分析',h['finding_summary'],'沿用已有摘要复核','','已有重点进展，未新增采集',board,'existing_highlight_summary',h['raw_path']))
  assert all(digest(c,t)==f for t,f in old.items());assert not c.execute('PRAGMA foreign_key_check').fetchall();assert c.execute('SELECT COUNT(*) FROM literature_issue_links WHERE version_id=? AND count_in_ranking=1',(vid,)).fetchone()[0]==160
  c.execute('PRAGMA user_version=7');c.commit()
 except BaseException:c.rollback();raise
 result=dict(result='applied',reviewed_core=162,issues=51,ranked_papers=160,background=2,supplement=1,old_tables_preserved=len(old),new_collection=False,published=False);c.close();(OUT/'应用记录.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
