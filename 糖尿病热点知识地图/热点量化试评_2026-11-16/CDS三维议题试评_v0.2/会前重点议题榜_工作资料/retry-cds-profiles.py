from pathlib import Path
import json,concurrent.futures,urllib.request,hashlib,sys
sys.path.insert(0,'/tmp/clinical-ranking-verify')
# Reuse parser without running collection loop.
s=Path('/tmp/clinical-ranking-verify/fetch-cds-agenda-profiles.py').read_text();a=s.index('class T(');b=s.index('def fetch(',a);ns={};exec(s[a:b],{'HTMLParser':__import__('html.parser',fromlist=['HTMLParser']).HTMLParser},ns);T=ns['T']
W=Path('/Users/zwx/Documents/文献阅读/BrainHao-Study/wenxin/糖尿病热点知识地图/热点量化试评_2026-11-16/CDS三维议题试评_v0.2/会前重点议题榜_工作资料');ds=json.loads((W/'讲者简介核查.json').read_text());failed=[d for d in ds if d['status']!='read'];print('重试',len(failed),flush=True)
def f(d):
 try:
  data=urllib.request.urlopen(urllib.request.Request(d['url'],headers={'User-Agent':'Mozilla/5.0'}),timeout=18).read();name=hashlib.sha256(d['url'].encode()).hexdigest()[:12];(W/'讲者简介原始页'/(name+'.html')).write_bytes(data);p=T();p.feed(data.decode('utf-8'));text='\n'.join(' '.join(l.split()) for l in ''.join(p.parts).splitlines() if l.strip());(W/'讲者简介原始页'/(name+'.txt')).write_text(text);d.update(status='read',text=text,raw_file=name+'.html',origin='日程原附官方讲者页连接重试成功');d.pop('error',None);return d
 except Exception as e:d['retry_error']=str(e);return d
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
 out={d['key']:d for d in ex.map(f,failed)}
for i,d in enumerate(ds):
 if d['key'] in out:ds[i]=out[d['key']]
(W/'讲者简介核查.json').write_text(json.dumps(ds,ensure_ascii=False,indent=2)+'\n');print('重试后读取',sum(d['status']=='read' for d in ds),'/',len(ds),flush=True)
