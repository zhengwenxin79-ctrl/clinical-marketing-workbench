"""Read-only initial handoff verification; reports go outside workbench."""
from pathlib import Path
import argparse,hashlib,json,sqlite3,sys
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[1]
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--check-manifest',action='store_true');ap.add_argument('--report',type=Path);a=ap.parse_args();w=ROOT/'workbench';base=read(ROOT/'handoff/baseline.json');checks=[];errors=[]
 def check(name,condition,detail=None):
  checks.append({'name':name,'passed':bool(condition),'detail':detail})
  if not condition:errors.append(name)
 check('Python 3.11+',sys.version_info>=(3,11),sys.version.split()[0])
 for rel,expected in base['source_files'].items():check('baseline '+rel,(w/rel).is_file() and digest(w/rel)==expected)
 c=sqlite3.connect((w/'数据库/marketing.db').as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
 check('SQLite integrity',c.execute('pragma integrity_check').fetchone()[0]=='ok');check('foreign keys',not c.execute('pragma foreign_key_check').fetchall())
 tables=c.execute("select count(*) from sqlite_master where type='table' and name not like 'sqlite_%'").fetchone()[0];views=c.execute("select count(*) from sqlite_master where type='view'").fetchone()[0];check('66 tables / 25 views',(tables,views)==(base['tables'],base['views']))
 materials=list(c.execute('select material_id,relative_path,sha256 from source_materials'));bad=[]
 for m in materials:
  p=(w/m['relative_path']).resolve()
  if not p.is_relative_to(w.resolve()) or not p.is_file() or digest(p)!=m['sha256']:bad.append(m['material_id'])
 check('all registered source materials',len(materials)==base['materials'] and not bad,{'count':len(materials),'bad':bad});check('independent studies not invented',c.execute('select count(*) from studies').fetchone()[0]==0);c.close()
 d=read(w/'领域工作台/领域数据快照.json');check('research data conservation',d['summary']==base['summary']);check('six entries',[m['id'] for m in d['navigation']['modules']]==base['modules']);check('six domains one connected',len(d['navigation']['domains'])==6 and sum(x['connected'] for x in d['navigation']['domains'])==1)
 reports=[x for t in d['topics'] for x in t['report_ids']];papers=[x for t in d['topics'] for x in t['paper_ids']];check('unique primary report/paper counts',len(reports)==len(set(reports))==2628 and len(papers)==len(set(papers))==160)
 rs=d['pi_ratings']['ratings'];complete=[r for r in rs if r['total_score'] is not None];check('existing ratings only',len(rs)==14 and len(complete)==5 and all(sum(x['score'] for x in r['dimensions'])==r['total_score'] for r in complete))
 check('truthful prototype status',not d['sales']['auto_recommendation']['model_connected'] and d['weekly']['change_log']['connection_status']=='not_connected')
 missing=[];local_count=0
 def walk(x,folder):
  nonlocal local_count
  if isinstance(x,dict):
   for k,v in x.items():
    if isinstance(v,str) and k.endswith('_url') and v.startswith(('../','./')):
     rel=unquote(v.split('#',1)[0].split('?',1)[0]);p=(folder/rel).resolve();local_count+=1
     if not p.is_relative_to(ROOT.resolve()) or not p.is_file():missing.append({'value':v,'base':str(folder.relative_to(ROOT))})
    elif isinstance(v,(dict,list)):walk(v,folder)
  elif isinstance(x,list):
   for v in x:walk(v,folder)
 for rel in ['领域工作台/领域数据快照.json','标志物视图/标志物数据快照.json','论文视图/论文数据快照.json','会议总入口/会议目录快照.json']:
  p=w/rel;walk(read(p),p.parent)
 check('runtime local source links',not missing,{'checked':local_count,'missing':missing})
 for rel,manifest in [('领域工作台/index.html','领域工作台/生成记录.json'),('会议总入口/index.html','会议总入口/生成记录.json'),('会议视图/index.html','会议视图/生成记录.json'),('会议视图/ada.html','会议视图/ADA生成记录.json'),('论文视图/index.html','论文视图/生成记录.json'),('标志物视图/index.html','标志物视图/生成记录.json')]:
  m=read(w/manifest);check('export '+rel,digest(w/rel)==m['html_sha256'] and m['database_sha256']==base['database_sha256'])
 if a.check_manifest:
  m=read(ROOT/'PACKAGE_MANIFEST.json');bad=[]
  for item in m['files']:
   p=ROOT/item['path']
   if not p.is_file() or digest(p)!=item['sha256']:bad.append(item['path'])
  check('ZIP payload manifest',not bad,{'checked':len(m['files']),'bad':bad})
 result={'result':'passed' if not errors else 'failed','checks':checks,'errors':errors,'database_unchanged':digest(w/'数据库/marketing.db')==base['database_sha256'],'new_collection':False,'published':False}
 out=a.report or ROOT/'handoff/acceptance/P00/offline.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'result':result['result'],'checks':len(checks),'errors':errors,'materials':len(materials),'local_links':local_count,'report':str(out.relative_to(ROOT)) if out.is_relative_to(ROOT) else str(out)},ensure_ascii=False));sys.exit(bool(errors))
if __name__=='__main__':main()
