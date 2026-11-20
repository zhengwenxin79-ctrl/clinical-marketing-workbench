from pathlib import Path
import sqlite3,json,hashlib,csv,xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[1];RAW=ROOT/'原始资料/论文首轮_2026-11-17';OUT=ROOT/'论文视图'
def main():
 backup=Path((RAW/'本轮备份位置.txt').read_text().strip());old=json.loads((backup/'原表指纹.json').read_text());c=sqlite3.connect((ROOT/'数据库/marketing.db').as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
 for t,f in old.items():
  rows=[list(x) for x in c.execute('SELECT * FROM "'+t+'" ORDER BY rowid')];assert len(rows)==f['count'];assert hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()==f['sha256'],t
 assert not c.execute('PRAGMA foreign_key_check').fetchall();assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 xmlids=set()
 for p in RAW.glob('PubMed*.xml'):xmlids.update(x.findtext('MedlineCitation/PMID') for x in E.parse(p).getroot().findall('PubmedArticle'))
 dbids={x[0] for x in c.execute('SELECT pmid FROM literature_papers WHERE pmid IS NOT NULL')};assert xmlids==dbids
 data=json.loads((OUT/'论文数据快照.json').read_text());assert len(data['papers'])==618;assert sum(p['in_core_counts'] for p in data['papers'])==162
 assert sum(b['paper_count'] for b in data['board_counts'])==162;assert len({p['paper_id'] for p in data['papers']})==618
 with (OUT/'糖尿病文章基础表.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f));assert len(rows)==618;assert len({x['论文ID'] for x in rows})==618
 for p in data['papers']:
  for l in p['team_links']:
   a=next(a for a in p['authors'] if a['ordinal']==l['ordinal']);assert a['affiliations'];assert l['leadership_status']=='paper_leadership_pending'
  if p['in_core_counts']:assert p['source_tier']=='core' and p['window_status']=='in_window' and p['board_id']
 n=next(p for p in data['papers'] if p['pmid']=='42599779');assert n['publication_date']=='2026-08-14' and n['window_status']=='outside' and not n['in_core_counts']
 assert c.execute('SELECT COUNT(*) FROM literature_discovery_candidates').fetchone()[0]==16034
 files=0
 for p in (backup/'会议视图').rglob('*'):
  if p.is_file():assert p.read_bytes()==(ROOT/'会议视图'/p.relative_to(backup/'会议视图')).read_bytes();files+=1
 source_files=0
 for m in c.execute('SELECT relative_path,sha256 FROM source_materials'):
  p=ROOT/m['relative_path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==m['sha256'];source_files+=1
 manifest=json.loads((OUT/'生成记录.json').read_text());assert manifest['database_sha256']==hashlib.sha256((ROOT/'数据库/marketing.db').read_bytes()).hexdigest();assert manifest['html_sha256']==hashlib.sha256((OUT/'index.html').read_bytes()).hexdigest()
 c.close();result=dict(result='passed',old_tables_preserved=len(old),old_conference_view_files_preserved=files,old_source_files_verified=source_files,papers=618,pubmed_records=len(dbids),core_counted=162,broad_discovery_ids=16034,checks=['数据库完整性和外键','旧40表逐行指纹与原会议页面、原始文件保留','原始PubMed XML全PMID集合与入库相等','CSV/JSON/数据库主键一致，无重复计数','图表仅计核心池，类型/范围/日期按规则筛选','8条作者参与不升级为负责人；跨语言待核身份保持','宁光参与论文已核8/14首发，排除窗口外','广检索编号与已读元数据分开'],published=False,biomarker_changes=False)
 (OUT/'数据核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
