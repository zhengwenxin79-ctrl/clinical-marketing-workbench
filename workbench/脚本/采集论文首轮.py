from pathlib import Path
from urllib.request import urlopen,Request
from urllib.parse import urlencode
from datetime import datetime
import time,json,xml.etree.ElementTree as ET,hashlib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'原始资料/论文首轮_2026-11-17';OUT.mkdir(exist_ok=True)
END='2026/11/17';START='2026/08/17';UA='ClinicalResearchWorkbench/0.1 (local noncommercial literature indexing)'
log=json.loads((OUT/'请求记录.json').read_text()) if (OUT/'请求记录.json').exists() else []
def request(name,endpoint,params):
 target=OUT/name
 if target.exists():return target.read_bytes()
 url='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'+endpoint+'?'+urlencode(params)
 for attempt in range(3):
  try:
   time.sleep(.42);b=urlopen(Request(url,headers={'User-Agent':UA}),timeout=35).read();target.write_bytes(b);log.append({'name':name,'url':url,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'status':'saved'});(OUT/'请求记录.json').write_text(json.dumps(log,ensure_ascii=False,indent=2));return b
  except Exception as e:
   if attempt==2:log.append({'name':name,'url':url,'status':'failed','error':str(e)});(OUT/'请求记录.json').write_text(json.dumps(log,ensure_ascii=False,indent=2));raise
   time.sleep(1+attempt)
core_terms={'care':'"Diabetes Care"[Journal]','diabetes':'"Diabetes"[Journal]','diabetologia':'"Diabetologia"[Journal]','landia':'"Lancet Diabetes Endocrinol"[Journal]'}
core_ids=set();checks=[]
for name,term in core_terms.items():
 q=f'({term}) AND ("{START}"[DP] : "{END}"[DP])';d=json.loads(request('检索_核心_'+name+'.json','esearch.fcgi',dict(db='pubmed',term=q,retmode='json',retmax=9999)))['esearchresult'];assert len(d['idlist'])==int(d['count']);core_ids.update(d['idlist']);checks.append(dict(id=name,query=q,count=int(d['count']),ids=d['idlist'],source='PubMed',status='indexed_metadata_complete_publisher_directory_unverified'));print(name,d['count'],flush=True)
theme_ids=set()
for i,(a,b) in enumerate([('2026/08/17','2026/08/31'),('2026/09/01','2026/09/30'),('2026/10/01','2026/10/31'),('2026/11/01',END)]):
 q=f'("Diabetes Mellitus"[MeSH Terms] OR diabet*[Title/Abstract]) AND ("{a}"[DP] : "{b}"[DP])';d=json.loads(request('检索_主题_'+str(i)+'.json','esearch.fcgi',dict(db='pubmed',term=q,retmode='json',retmax=9999)))['esearchresult'];assert len(d['idlist'])==int(d['count']);theme_ids.update(d['idlist']);checks.append(dict(id='theme-'+str(i),query=q,count=int(d['count']),source='PubMed',status='discovery_candidates'));print('theme',i,d['count'],flush=True)
# 先完整读取核心池，补漏候选另存编号，避免把未经审阅的广检索命中混入热点榜。
core=sorted(core_ids,key=int);parsed=0
for i in range(0,len(core),150):
 b=request('PubMed核心_'+str(i//150+1)+'.xml','efetch.fcgi',dict(db='pubmed',id=','.join(core[i:i+150]),retmode='xml'));x=ET.fromstring(b);parsed+=len(x.findall('PubmedArticle'));print('core metadata',parsed,flush=True)
assert parsed==len(core)
# 广检索所有编号留档；首轮补漏选择与临床/转化直接相关的可界定子集，保留检索式和命中差额。
extra_query=f'("Diabetes Mellitus"[MeSH Terms] OR diabet*[Title/Abstract]) AND ("{START}"[DP] : "{END}"[DP]) AND ("N Engl J Med"[Journal] OR "Lancet"[Journal] OR "JAMA"[Journal] OR "Nat Med"[Journal] OR "Nat Metab"[Journal] OR "Cell Metab"[Journal] OR "Kidney Int"[Journal] OR "J Am Soc Nephrol"[Journal] OR "Circulation"[Journal] OR "J Am Coll Cardiol"[Journal])'
d=json.loads(request('检索_补漏重点期刊.json','esearch.fcgi',dict(db='pubmed',term=extra_query,retmode='json',retmax=9999)))['esearchresult'];assert len(d['idlist'])==int(d['count']);extra=sorted(set(d['idlist'])-core_ids,key=int)
for i in range(0,len(extra),150):
 b=request('PubMed补漏_'+str(i//150+1)+'.xml','efetch.fcgi',dict(db='pubmed',id=','.join(extra[i:i+150]),retmode='xml'));ET.fromstring(b);print('supplement metadata',min(i+150,len(extra)),flush=True)
checks.append(dict(id='theme-priority-journals',query=extra_query,count=int(d['count']),source='PubMed',status='bounded_supplement_not_exhaustive_theme_review'))
manifest=dict(start=START,end=END,core_ids=core,core_count=len(core),broad_candidate_ids=sorted(theme_ids,key=int),broad_candidate_count=len(theme_ids),supplement_ids=extra,supplement_count=len(extra),checks=checks,scope_note='核心4刊PubMed窗口命中全量元数据；广检索全编号留档，首轮补漏读取指定10本综合/转化/并发症期刊。未读取其余广检索候选，不能宣称全领域无遗漏。出版社目录与中文2刊另行核查。',collected_on='2026-11-17',published=False)
(OUT/'采集清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));print('DONE',manifest['core_count'],manifest['broad_candidate_count'],manifest['supplement_count'],flush=True)
