from pathlib import Path
import re,json,collections
from html.parser import HTMLParser
from urllib.parse import urljoin
ROOT=Path(__file__).resolve().parent;raw=ROOT/'原始材料'
class N:
 def __init__(self,tag='',attrs=(),parent=None):self.tag=tag;self.attrs=dict(attrs);self.parent=parent;self.children=[]
 def walk(self):
  yield self
  for c in self.children:
   if isinstance(c,N):yield from c.walk()
 def text(self):return re.sub(r'\s+',' ',''.join(c.text() if isinstance(c,N) else c for c in self.children)).strip()
 def has(self,cls):return cls in self.attrs.get('class','').split()
 def find(self,p):return next((n for n in self.walk() if p(n)),None)
class Parser(HTMLParser):
 def __init__(self):super().__init__();self.root=N();self.stack=[self.root]
 def handle_starttag(self,t,a):
  n=N(t,a,self.stack[-1]);self.stack[-1].children.append(n)
  if t not in ['area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr']:self.stack.append(n)
 def handle_endtag(self,t):
  for i in range(len(self.stack)-1,0,-1):
   if self.stack[i].tag==t:self.stack=self.stack[:i];break
 def handle_data(self,s):self.stack[-1].children.append(s)
p=Parser();p.feed((raw/'CDS_详细日程_2026-11-16.html').read_text());room='';sessions=[];items=[]
for node in p.root.walk():
 if node.tag=='h3' and node.has('program-item-date'):room=node.text()
 if not node.attrs.get('id','').startswith('session'):continue
 sid=node.attrs['id'];day=node.find(lambda n:n.has('kg-session-date'));name=node.find(lambda n:n.has('span-sessionname'));table=node.find(lambda n:n.tag=='table' and n.has('proram-item-table'))
 session={'session_id':sid,'date':day.text() if day else None,'room':room,'title':name.text() if name else None,'chairs':[]}
 for x in node.walk():
  if x.tag=='a' and (nm:=x.find(lambda n:n.has('pip-name'))):
   org=x.find(lambda n:n.has('pip-org'));session['chairs'].append({'name':nm.text(),'institution':org.text() if org else '', 'url':urljoin('https://cds26.tiemeeting.com',x.attrs.get('href',''))})
 sessions.append(session)
 if not table:continue
 tbody=next((n for n in table.children if isinstance(n,N) and n.tag=='tbody'),None)
 if not tbody:continue
 for row in tbody.children:
  if not isinstance(row,N) or row.tag!='tr':continue
  cells=[c for c in row.children if isinstance(c,N) and c.tag=='td']
  if len(cells)<4:continue
  people=[];authors=cells[-1].find(lambda n:n.has('childTable'))
  if authors:
   for tr in authors.walk():
    if tr.tag!='tr':continue
    tds=[n for n in tr.children if isinstance(n,N) and n.tag=='td'];links=[n for n in tr.walk() if n.tag=='a' and 'Speaker?' in n.attrs.get('href','')]
    if tds and links:people.append({'name':tds[0].text(),'institution':tds[1].text() if len(tds)>1 else '', 'profile_url':urljoin('https://cds26.tiemeeting.com',links[0].attrs['href'])})
  items.append({'code':cells[0].text(),'time':cells[1].text(),'kind':cells[2].text(),'title':cells[3].text(),'people':people,'date':session['date'],'room':room,'session':session['title'],'session_id':sid,'source_url':'https://cds26.tiemeeting.com/CN/Program/Details#'+sid,'evidence':'planned agenda; no results'})
(raw/'CDS_全日程结构化.json').write_text(json.dumps({'as_of':'2026-11-16','sessions':sessions,'items':items},ensure_ascii=False,indent=2)+'\n')
print('sessions',len(sessions),'rows',len(items),'numbered',sum(bool(re.fullmatch(r'(S_|OR_|PL_)\d+',x['code'])) for x in items));print(collections.Counter(x['kind'] for x in items))
