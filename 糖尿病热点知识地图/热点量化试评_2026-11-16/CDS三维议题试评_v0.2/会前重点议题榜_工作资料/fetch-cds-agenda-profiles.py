from pathlib import Path
from html.parser import HTMLParser
from urllib.request import urlopen,Request
from concurrent.futures import ThreadPoolExecutor,as_completed
import json,time,hashlib,re
R=Path('/Users/zwx/Documents/文献阅读/BrainHao-Study/wenxin/糖尿病热点知识地图/热点量化试评_2026-11-16/CDS三维议题试评_v0.2');W=R/'会前重点议题榜_工作资料';O=W/'讲者简介原始页';O.mkdir(exist_ok=True)
people=json.loads((W/'讲者入口.json').read_text());old=json.loads((R/'联网补证_2026-11-16/讲者官方简介.json').read_text());known={x['url']:x for x in old if x.get('status')=='read'}
class T(HTMLParser):
 def __init__(self):super().__init__();self.skip=0;self.parts=[]
 def handle_starttag(self,t,a):
  if t in ['script','style']:self.skip+=1
  if t in ['p','div','li','h1','h2','br','td']:self.parts.append('\n')
 def handle_endtag(self,t):
  if t in ['script','style']:self.skip-=1
 def handle_data(self,s):
  if not self.skip:self.parts.append(s)
def fetch(p):
 rec=dict(p);url=p['url'];key=hashlib.sha256(url.encode()).hexdigest()[:12];f=O/(key+'.html')
 try:
  if url in known:rec.update(text=known[url]['text'],status='read',origin='复用本轮已存官方简介');return rec
  if f.exists():data=f.read_bytes();rec['origin']='复用本地官方页缓存'
  else:
   data=urlopen(Request(url,headers={'User-Agent':'Wenxin-CDS-AgendaReview/1.0'}),timeout=14).read();f.write_bytes(data);rec['origin']='读取原日程所附CDS官方讲者页；未扩展其他会议/论文'
  a=T();a.feed(data.decode('utf-8',errors='strict'));text='\n'.join(' '.join(s.split()) for s in ''.join(a.parts).splitlines() if s.strip());(O/(key+'.txt')).write_text(text)
  rec.update(text=text,status='read',raw_file=f.name)
 except Exception as e:rec.update(status='unavailable',error=str(e))
 return rec
out=[]
with ThreadPoolExecutor(max_workers=4) as ex:
 futures=[ex.submit(fetch,p) for p in people]
 for i,fu in enumerate(as_completed(futures),1):
  out.append(fu.result())
  if i%25==0:print('已处理',i,'/',len(people),flush=True)
  if i%25==0:(W/'讲者简介核查.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
out.sort(key=lambda p:p['key']);(W/'讲者简介核查.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('完成',len(out),'读取成功',sum(x['status']=='read' for x in out),'待补',sum(x['status']!='read' for x in out),flush=True)
