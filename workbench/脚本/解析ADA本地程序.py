from pathlib import Path
import re,json,collections
ROOT=Path(__file__).resolve().parents[1]
text=(ROOT/'原始资料/ADA2026/官方程序/ADA2026_日程.txt').read_text();pages=text.split('\f');sessions=[];items=[];current=None;item=None;unparsed=[]
startpat=re.compile(r'^\s{0,10}(\d{1,2}:\d{2}\s*[ap]\.m\.)\s*-\s*(.*)$')
timerem=re.compile(r'^\s*(?:\d{1,2}:\d{2}\s*[ap]\.m\.\s*-\s*(?:\d{1,2}:\d{2}\s*(?:[ap]\.m\.)?)?|\d{1,2}:\d{2}\s*[ap]\.m\.|[ap]\.m\.)\s*')
creds=re.compile(r',\s*(?:MD|PhD|MB|MS|BS|MPH|MSc|BSc|RN|MM|Dr|DNP|DO|FR|DC|RD|PsyD|MP|MA|MEd|MLS|Pharm|BCh|DPhil|MBB|FRC|FNP|MBA|BA|MRes|Diabetes|Bachelor|Master|Doctor|Post|N/A|BSN|MHS|MCH|Candidate|MSN|Student|BSc|MPhil|Medical|MBBS|BMed|PG|Ph\.D|M\.D|PT|RDN|Epidemiology|BEng|DHSc|DSc|MPS|Dipl|BTech|Degree|Lic|MTech|DPT|M\.A\.|NBC|FMedSci)',re.I)
def finish():
 global item
 if not item:return
 body=[x['text'] for x in item['lines'] if x['text']];joined=' '.join(body);m=re.search(r'\b(\d{3,4}-(?:OR|P|LB))\s+',joined);speaker='';title='';code=m[1] if m else None
 if 'Presenting Author:' in joined:
  title,sp=joined.split('Presenting Author:',1);speaker=sp.strip()
  if code:title=re.sub(r'^.*?\b'+re.escape(code)+r'\s*','',title)
 elif body:
  if len(body)>1 and (creds.search(body[-1]) or body[-1] in ['Charles Henderson','Christine Limonte','Ania Jastreboff','Osagie Ebekozien','Chantal Mathieu','John Ussher','Carl Yang','Mazen Noureddin','Ralph DeFronzo','Laura Jacobsen','Qiancheng Zhao','Melissa Leonard','Katrina Nguyen','Ian Neeland','Hongying Shen','Orian Shirihai']):speaker=body[-1];title=' '.join(body[:-1])
  else:title=joined
 item.update(code=code,title=title.strip(),speaker_original=speaker,presenter_name=speaker.split(',')[0].strip() if speaker else '',raw_text='\n'.join(x['raw'] for x in item['lines']),pages=sorted(set(x['page'] for x in item['lines'])),time_original=' '.join(item['time_parts']))
 # A number may appear in a talk title without marking this report. Save candidates for audit.
 if code and not title:unparsed.append(item)
 items.append(item);item=None
for pn,page in enumerate(pages,1):
 if not page.strip():continue
 lines=[(n+1,l) for n,l in enumerate(page.splitlines()) if not re.search(r'abstractsonline.com/SR/Diabetes/FinalProgram.asp',l) and l.strip()]
 m=re.search(r'Session Number:\s*(\S+)',page)
 if not m and re.search(r'(?:FRIDAY|SATURDAY|SUNDAY|MONDAY), JUNE',page):
  finish();current=None;continue
 if m:
  finish();sid=m[1];j=next(i for i,(_,l) in enumerate(lines) if 'Session Number:' in l);roomidx=next(i for i,(_,l) in enumerate(lines[j+1:],j+1) if 'Room:' in l);date=next((l.strip() for _,l in lines[:j] if re.search(r'(?:FRIDAY|SATURDAY|SUNDAY|MONDAY),',l)),None);typ=next(l.strip() for _,l in reversed(lines[:j]) if 'Theme Area:' not in l and not re.search(r'\d+:\d+|DAY,',l));theme=re.search(r'Theme Area:\s*(.+)',page)
  current=dict(session_id=sid,title=' '.join(l.strip() for _,l in lines[j+1:roomidx]),type=typ,theme=theme[1].strip() if theme else None,date=date,room=lines[roomidx][1].split('Room:',1)[1].strip(),page=pn,chairs=[],source_text=page)
  for _,l in lines[roomidx+1:]:
   if 'Chair(s):' in l:current['chairs']=l.split('Chair(s):',1)[1].strip().split(';')
  sessions.append(current);lines=lines[roomidx+1:]
 for lineno,line in lines:
  if re.search('Chair\(s\):|Responsible Committee Member\(s\):',line):continue
  m=startpat.match(line)
  if m:
   finish();tail=m[2];end=re.match(r'(\d{1,2}:\d{2}(?:\s*[ap]\.m\.)?)',tail);timeparts=[m[1],'-'];
   if end:timeparts.append(end[1])
   clean=timerem.sub('',line).strip();item=dict(session_id=current['session_id'] if current else None,source_order=len(items),lines=[],time_parts=timeparts,start_time_text=m[1],page=pn)
   if clean:item['lines'].append(dict(text=clean,page=pn,line=lineno,raw=line))
  elif item and current:
   if re.match(r'^\s*(\d{1,2}:\d{2}\s*[ap]\.m\.|[ap]\.m\.)\s*',line):item['time_parts'].append(line.strip().split(' ',2)[0] if re.match(r'^\s*\d',line) else line.strip().split()[0])
   clean=timerem.sub('',line).strip();item['lines'].append(dict(text=clean,page=pn,line=lineno,raw=line))
finish()
for x in items:x['person_name']=x['presenter_name']
summary=dict(pages=385,sessions=len(sessions),items=len(items),codes=len({x['code'] for x in items if x['code']}),code_occurrences=sum(bool(x['code']) for x in items),with_speaker=sum(bool(x['presenter_name']) for x in items),empty_titles=sum(not x['title'] for x in items))
print(summary);print(collections.Counter(x['type'] for x in sessions));print('nonspeaker examples',[(x['page'],x['title'][:100]) for x in items if not x['presenter_name']][:25]);print('speaker issues',[(x['page'],x['speaker_original']) for x in items if len(x['presenter_name'])>70][:15]);print('code disagreements',set(re.findall(r'\b\d{3,4}-(?:OR|P|LB)\b',text))-{x['code'] for x in items if x['code']})
(ROOT/'原始资料/ADA2026/官方程序/ADA程序结构化.json').write_text(json.dumps(dict(sessions=sessions,items=items,summary=summary),ensure_ascii=False,indent=2))
