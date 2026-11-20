"""将已留档论文及角色证据增量入库。保留旧40表记录，不采集、不发布。"""
from pathlib import Path
import sqlite3,json,re,hashlib
ROOT=Path(__file__).resolve().parents[1];RAW=ROOT/'原始资料/论文首轮_2026-11-17';RUN='LITERATURE-20261117-v1'
def dump(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def digest(c,t):
 rows=c.execute('SELECT * FROM "'+t+'" ORDER BY rowid').fetchall()
 return dict(count=len(rows),sha256=hashlib.sha256(dump([list(x) for x in rows]).encode()).hexdigest())
PATTERNS={
 'M10':r'gestational|pregnan|perinatal|postpartum|maternal|offspring|\bbone\b|skeletal|sarcopen|muscle loss|妊娠|产后|家系|肌少|骨质',
 'M05':r'kidney|renal|nephro|albuminuri|egfr|肾脏|肾病|肾小球',
 'M06':r'retina|retinopathy|diabetic foot|neuropath|cognit|brain|认知|糖尿病足|视网膜|神经病变',
 'M08':r'\bmash\b|\bmasld\b|\bnafld\b|fatty liver|hepatic|肝病|脂肪肝|糖肝',
 'M07':r'cardiovas|cardiac|heart|stroke|\bmace\b|cardiorenal|心血管|心房|卒中|动脉粥样',
 'M03':r'continuous glucose|automated insulin|closed.loop|artificial intelligence|machine learning|wearable|cgm|人工智能|血糖监测|机器学习',
 'M04':r'glp.1|gip|tirzepatide|semaglutide|survodutide|retatrutide|orforglipron|htd1801|icos[e]?ma|weight loss|weight management|obesity|obese|dapagliflozin|empagliflozin|司美格鲁肽|替尔泊肽|达格列净|减重|肥胖',
 'M01':r'phenotyp|subtyp|cluster|predict|risk score|screen|proteomic|methylat|分型|亚型|筛查|预测|胰岛素抵抗',
 'M02':r'type 1|islet|beta.cell|β.cell|stem.cell|transplant|autoimmun|insulin secret|胰岛|1型糖尿病|干细胞',
 'M09':r'diet|nutrition|exercise|physical activity|gut microbio|food|olive oil|膳食|营养|运动|饮食|肠道',
 'M11':r'prevalence|incidence|epidemio|population|health service|cost|burden|education|care delivery|hospitalization|trends|流行|患病率|成本|医疗费用|管理模式',
 'M12':r'molecular|mitochond|signalling|signaling|autophagy|thermogen|adipose|macrophage|metabol|分子|信号|小胶质|铁死亡|脂代谢'
}
def classify(p,highlights):
 title=p['title'];full=' '.join(x['text'] for x in p['abstract']);s=title.lower()
 if re.search(r'diabet|glyc[ae]m|glucose|insulin|islet|β.cell|beta.cell|hypoglyc|glp.1|gip|糖尿病|血糖|胰岛',s):scope='direct'
 elif re.search(r'obes|adipos|weight|metabol|肥胖|代谢|减重',s) and p['source_tier']=='core':scope='related_metabolic'
 elif re.search(r'diabet|糖尿病',full,re.I):scope='abstract_related_pending'
 else:scope='scope_pending'
 hit=[(b,m.group(0)) for b,pat in PATTERNS.items() if (m:=re.search(pat,title,re.I))]
 board='CDS2026:'+hit[0][0] if hit else None
 basis='题名关键词初分：'+('; '.join(b+':'+word for b,word in hit)) if hit else '题名未稳定匹配，待人工归类'
 if p['paper_id'] in highlights:
  board='CDS2026:'+highlights[p['paper_id']]['board'];basis='已读摘要后复核研究问题；重点进展人工初分（AI）'
 if not hit and scope=='direct':basis+='；未强行填入其他板块'
 return board,scope,basis
def main():
 papers=json.loads((RAW/'论文结构化初稿.json').read_text());manifest=json.loads((RAW/'采集清单.json').read_text());cur=json.loads((RAW/'人工核对与进展摘要.json').read_text());backup=Path((RAW/'本轮备份位置.txt').read_text().strip());old=json.loads((backup/'原表指纹.json').read_text())
 c=sqlite3.connect(ROOT/'数据库/marketing.db');c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
 assert all(digest(c,t)==v for t,v in old.items())
 try:
  c.executescript('BEGIN IMMEDIATE;\n'+(ROOT/'规则与说明/006_论文热点.sql').read_text())
  c.execute('INSERT OR IGNORE INTO literature_runs VALUES(?,?,?,?,?,?,?)',(RUN,'2026-08-17','2026-11-17','2026-11-17',str((RAW/'采集清单.json').relative_to(ROOT)),hashlib.sha256((RAW/'采集清单.json').read_bytes()).hexdigest(),manifest['scope_note']))
  for code,label,url in [('care','Diabetes Care','https://diabetesjournals.org/care'),('diabetes','Diabetes','https://diabetesjournals.org/diabetes'),('diabetologia','Diabetologia','https://diabetologia-journal.org/'),('landia','The Lancet Diabetes & Endocrinology','https://www.thelancet.com/journals/landia/home')]:
   check=next(x for x in manifest['checks'] if x['id']==code);note='已读取时间窗口PubMed全部命中；不等于出版社完整目录。按电子发表日期优先，刊期命中较早在线论文另列。'
   c.execute('INSERT OR IGNORE INTO literature_sources VALUES(?,?,?,?,?,?)',(code,label,'core_journal',url,'pubmed_index_complete',note))
   c.execute('INSERT OR IGNORE INTO literature_source_checks VALUES(?,?,?,?,?,?,?)',(RUN,code,check['query'],check['count'],'indexed_metadata_read','出版社在线优先/目录未全部独立校验；收录可能滞后',str((RAW/('检索_核心_'+code+'.json')).relative_to(ROOT))))
  for code,label,url in [('cndm','中华糖尿病杂志','https://cs.medjournals.cn/cn/zhtnbzz/current'),('cnendo','中华内分泌代谢杂志','https://cs.medjournals.cn/cn/zhnfmdxzz/current')]:
   count=sum(p['journal']==label for p in papers);note='官方目录/索引部分读取；动态空壳、历史目录及优先出版完整性待核。只作补充，不混入核心数量榜。'
   c.execute('INSERT OR IGNORE INTO literature_sources VALUES(?,?,?,?,?,?)',(code,label,'core_journal',url,'partial_directory',note))
   c.execute('INSERT OR IGNORE INTO literature_source_checks VALUES(?,?,?,?,?,?,?)',(RUN,code,None,count,'partial_directory','未取得近三个月全部期次与每篇独立摘要；不能认定未读期次无文章。','原始资料/论文首轮_2026-11-17/中文目录_索引全文读取记录.txt'))
  c.execute('INSERT OR IGNORE INTO literature_sources VALUES(?,?,?,?,?,?)',('pubmed-theme','PubMed主题补漏','discovery','https://pubmed.ncbi.nlm.nih.gov/','bounded_supplement',manifest['scope_note']))
  c.execute('INSERT OR IGNORE INTO literature_source_checks VALUES(?,?,?,?,?,?,?)',(RUN,'pubmed-theme',next(x['query'] for x in manifest['checks'] if x['id']=='theme-priority-journals'),manifest['broad_candidate_count'],'id_index_and_bounded_metadata','广检索共16034个去重编号，仅补漏重点10刊114篇读取元数据；其余编号不作文章或热点计数。','原始资料/论文首轮_2026-11-17/采集清单.json'))
  related={x['pmid']:x['paper_id'] for x in c.execute('SELECT paper_id,pmid FROM related_paper_abstracts') if x['pmid']}
  cols=['paper_id','pmid','doi','pmcid','title','journal','journal_abbr','publication_date','date_precision','date_basis','online_date','issue_date','window_status','source_tier','article_type','type_basis','reading_level','abstract_json','summary_curated','source_url','publisher_url','raw_path','source_locator','existing_abstract_id','run_id']
  for p in papers:
   if p['paper_id'] in cur['highlights']:p['article_type']='original_reviewed';p['type_basis']='已读摘要的明确研究设计，AI复核原创；未全文精读'
   p['abstract_json']=dump(p['abstract']);p['existing_abstract_id']=related.get(p['pmid']);p['run_id']=RUN
   c.execute('INSERT INTO literature_papers('+','.join(cols)+') VALUES('+','.join('?' for _ in cols)+') ON CONFLICT(paper_id) DO UPDATE SET '+','.join(k+'=excluded.'+k for k in cols if k!='paper_id'),tuple(p.get(k) for k in cols))
   for a in p['authors']:c.execute('INSERT OR IGNORE INTO literature_authors VALUES(?,?,?,?,?,?,?)',(p['paper_id'],a['ordinal'],a['name'],dump(a['affiliations']),a['orcid'],int(a['collective']),a['corresponding_status']))
   b,scope,basis=classify(p,cur['highlights']);c.execute('INSERT INTO literature_classifications VALUES(?,?,?,?,?) ON CONFLICT(paper_id) DO UPDATE SET board_id=excluded.board_id,scope_status=excluded.scope_status,classification_basis=excluded.classification_basis,review_status=excluded.review_status',(p['paper_id'],b,scope,basis,'ai_initial_pending_review'))
  for p in cur['role_seeds']:
   identity='cross_language_identity_pending' if p['person_id'].endswith('ning-guang') else 'name_and_institution_checked'
   c.execute('INSERT OR IGNORE INTO literature_people VALUES(?,?,?,?)',(p['person_id'],p['display_name'],p['domain'],identity))
   c.execute('INSERT OR IGNORE INTO literature_person_roles VALUES(?,?,?,?,?,?,?,?)',(p['person_id'],p['tier'],p['academy_kind'],p['role_basis'],p['role_source_url'],p['tenure'],'原始资料/论文首轮_2026-11-17/团队身份_官方读取记录.txt','2026-11-17'))
   for paper in papers:
    for a in paper['authors']:
     aff=' '.join(a['affiliations'])
     if a['name'] in p['author_names'] and any(term.lower() in aff.lower() for term in p['affiliation_terms']):
      c.execute('INSERT OR IGNORE INTO literature_author_links VALUES(?,?,?,?,?,?,?)',(paper['paper_id'],a['ordinal'],p['person_id'],identity,'first_author' if a['ordinal']==1 else 'coauthor','paper_leadership_pending','原始作者全名及其明确关联单位匹配；作者序不替代通讯作者或课题PI证据'))
  for pid,h in cur['highlights'].items():
   c.execute('INSERT OR IGNORE INTO literature_highlights VALUES(?,?,?,?,?,?,?)',(pid,h['question'],h['summary'],h['reason'],h['limit'],'abstract_reviewed_ai_pending_mentor','原始资料/论文首轮_2026-11-17/人工核对与进展摘要.json'))
  read={p['pmid'] for p in papers if p['pmid']}
  c.executemany('INSERT OR IGNORE INTO literature_discovery_candidates VALUES(?,?,?)',[(RUN,pid,'metadata_read' if pid in read else 'id_only_not_read') for pid in manifest['broad_candidate_ids']])
  assert all(digest(c,t)==v for t,v in old.items());assert not c.execute('PRAGMA foreign_key_check').fetchall();c.execute('PRAGMA user_version=6');c.commit()
 except BaseException:c.rollback();raise
 result=dict(result='imported',papers=c.execute('SELECT COUNT(*) FROM literature_papers').fetchone()[0],authors=c.execute('SELECT COUNT(*) FROM literature_authors').fetchone()[0],core_counted=c.execute('SELECT COUNT(*) FROM v_literature_pool WHERE in_core_counts=1').fetchone()[0],source_checks=c.execute('SELECT COUNT(*) FROM literature_source_checks').fetchone()[0],old_tables_preserved=len(old),team_links=c.execute('SELECT COUNT(*) FROM literature_author_links').fetchone()[0],biomarker_changes=False,published=False)
 c.close();(RAW/'入库核验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(dump(result))
if __name__=='__main__':main()
