from pathlib import Path
from collections import Counter,defaultdict
import json,re,math,csv,hashlib
R=Path(__file__).resolve().parent;W=R/'会前重点议题榜_工作资料';A=R.parent/'原始材料/CDS_全日程结构化.json'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def key(p):return re.sub(r'\s+','',p['name'])+'|'+re.sub(r'\s+','',p['institution'])
def norm(x):return re.sub(r'\s+','',x)
def bio_of(doc):
 s=doc.get('text','').split('学术任务如下')[0]
 return s.split('简历：',1)[-1].strip() if '简历：' in s else ''
# Qualification rules reference academic roles only; no customer grade, funds totals or institutional fame.
NATIONAL=[r'国家基层糖尿病防治管理办公室主任',r'中华糖尿病学会候任主任委员',r'中国心血管代谢联盟共同主席',r'中国(?:科学|工程)院院士',r'中华医学会(?:糖尿病|内分泌)[^。；;\n，,、]{0,36}(?:主任委员|主委)',r'中国医师协会(?:内分泌|内分泌代谢)[^。；;\n，,、]{0,40}(?:会长|主任委员|主委)',r'国家[^。；;\n，,、]{0,35}首席(?:科学家|专家|项目负责人)',r'国家(?:代谢性|儿童少年健康与疾病)[^。；;\n]{0,25}临床医学研究中心主任',r'中国营养学会[^。；;\n，,、]{0,30}(?:理事长|分会主任委员)',r'中华护理学会[^。；;\n，,、]{0,25}(?:主任委员|主委)',r'国际糖尿病联盟[^。；;\n]{0,35}主席',r'牵头[^。；;\n]{0,15}全国[^。；;\n]{0,15}(?:共识|指南)',r'led major clinical trials']
REGIONAL=[r'(?:省|市|自治区|广西|新疆|重庆|北京|上海|天津|云南|四川|福建|全军)[^。；;\n，,、]{0,35}(?:糖尿病|内分泌|营养|代谢|运动)[^。；;\n，,、]{0,25}(?:主任委员|主委|会长)',r'(?:内分泌|内分泌代谢|糖尿病|临床营养|心力衰竭|心衰|神经|运动营养|代谢性疾病)[^。；;\n，,、]{0,18}(?:科主任(?!医师|护师)|科室主任|学科带头人|中心主任(?!医师|护师)|首席专家|所长)',r'(?:科室主任|内分泌主任(?!医师|护师)|内分泌科学术带头人|内分泌学科带头人)',r'国家杰青|国家杰出青年',r'代谢[^。；;\n]{0,20}实验室(?:主任|负责人)']
def qualify(doc):
 bio=bio_of(doc);lines=[x.strip() for x in bio.splitlines() if x.strip()]
 def matches(patterns):
  out=[]
  for l in lines:
   for pat in patterns:
    m=re.search(pat,norm(l),re.I)
    if m:
     # Quote only the office/leadership phrase, not complete biography paragraphs.
     phrase=m[0]
     if ('曾任' in l or '历任' in l) and not any(v in phrase for v in ['曾任','历任','前任']):phrase='简介含曾任/历任：'+phrase
     if phrase not in out:out.append(phrase)
  return out
 nat=matches(NATIONAL);reg=matches(REGIONAL)
 if re.search('国际糖尿病联盟.*主席',norm(doc.get('institution',''))):nat=[doc['institution']]+nat
 if doc.get('name')=='刘超' and '南京中医药' in doc.get('institution',''):return '区域/专科学术带头',2,['中华医学会内分泌学分会中青年委员会第8—11届主任委员（学组/委员会角色）']
 if doc.get('name')=='刘铭' and '天津' in doc.get('institution',''):return '全国/领域学术引领',3,['中华医学会内分泌分会副主任委员（会议简介原文跨逗号，已逐句核对）']
 if doc.get('name')=='姬秋和' and '西安' in doc.get('institution',''):return '全国/领域学术引领',3,['曾任中华医学会糖尿病分会第八、九届委员会副主任委员']
 if nat:return '全国/领域学术引领',3,nat[:2]
 if reg:return '区域/专科学术带头',2,reg[:2]
 return None,None,[]
def generate():
 a=read(A);defs=read(W/'议题定义.json');topics=defs['topics'];direct={c:t['id'] for t in topics for c in t['explicit_codes']};excluded=defs['exclusions'];topicmap={t['id']:t for t in topics};docs=read(W/'讲者简介核查.json');docmap={d['key']:d for d in docs}
 ledger=[];people={};allacademic=[r for r in a['items'] if r['kind'] in ['大会报告','专题报告','论文发言']];assert len(allacademic)==606
 for i,r0 in enumerate(allacademic):
  r=dict(r0);r['id']=r['code'];r['people_keys']=[key(p) for p in r['people']]
  if r['code'] in excluded:r.update(topic_id=None,scope=excluded[r['code']]['status'],classification_basis=excluded[r['code']]['reason'])
  else:
   assert r['code'] in direct,('必须逐条明确归属',r['code'],r['title'])
   t=topicmap[direct[r['code']]];r.update(topic_id=t['id'],scope='入榜',classification_basis='AI按题名中的研究对象、临床用途或主要研究问题逐条归类：'+t['question']+'；方法/药物跨题标签不额外计分。')
  tags=[]
  for label,pat in [('单细胞/空间','单细胞|空间转录'),('RNA/表观遗传','RNA|转录|甲基化|染色质|表观|乳酸化|m6A|m⁶A'),('蛋白/代谢组','蛋白组|代谢组|多组学|组学'),('标志物/预测','标志物|预测|模型|分型|分层|早期识别|异质'),('临床试验/队列','队列|随机|对照|随访|真实世界'),('肠促胰素','GLP|肠促胰素|格鲁肽|替尔泊肽|玛仕度肽')]:
   if re.search(pat,r['title'],re.I):tags.append(label)
  r['cross_tags']=tags;ledger.append(r)
  for p0 in r['people']:
   k=key(p0)
   if k not in people:
    doc=docmap.get(k,{});bio=bio_of(doc);level,weight,evidence=qualify(doc);pid='E'+str(len(people)+1).zfill(3)
    name=p0['name'].strip() if re.search('[A-Za-z]',p0['name']) else norm(p0['name'])
    people[k]=dict(id=pid,key=k,name=name,institution=p0['institution'],profile_url=p0['profile_url'],profile_status=doc.get('status','本轮未读取简介'),profile_origin=doc.get('origin','未新增个人履历调查'),profile_has_bio=bool(bio),leader_level=level,leader_weight=weight,leader_basis=evidence,source_note='CDS官方会议简介自报角色；含历任，任期未独立核查；不推断多位同职务者同时在任',reports=[],topic_ids=[],kind_counts={},is_plenary=False)
   p=people[k];p['reports'].append(r['code']);p['is_plenary']|=r['kind']=='大会报告'
   if r['topic_id'] and r['topic_id'] not in p['topic_ids']:p['topic_ids'].append(r['topic_id'])
 for p in people.values():p['kind_counts']=dict(Counter(r['kind'] for r in ledger if p['key'] in r['people_keys']))
 # Identity key includes institution; never transfer roles to same-name authors at another institution.
 for p in people.values():
  if any(q['name']==p['name'] and q['key']!=p['key'] for q in people.values()):p['same_name_note']='存在同名/不同单位条目，各条独立保存，未自动合并任职。'
 rows=[]
 for t0 in topics:
  t={k:v for k,v in t0.items() if k not in ['pattern','explicit_codes']};rs=[r for r in ledger if r['topic_id']==t['id']];assert rs,t['id'];ps=[p for p in people.values() if t['id'] in p['topic_ids']];leaders=[p for p in ps if p['leader_weight'] is not None];leaders.sort(key=lambda p:(-p['leader_weight'],-p['kind_counts'].get('大会报告',0),p['name']))
  ks=[p for p in ps if any(r['kind'] in ['大会报告','专题报告'] and p['key'] in r['people_keys'] for r in rs)]
  nr=len(rs);nk=3*sum(r['kind']=='大会报告' for r in rs)+sum(r['kind']=='专题报告' for r in rs);unknown=[p for p in ks if not p['profile_has_bio']]
  t.update(report_codes=[r['code'] for r in rs],report_count=nr,kind_counts=dict(Counter(r['kind'] for r in rs)),session_count=len({r['session_id'] for r in rs}),people_ids=[p['id'] for p in ps],leader_ids=[p['id'] for p in leaders],leader_count=len(leaders),leader_units=sum(p['leader_weight'] for p in leaders),key_units=nk,key_people=len(ks),key_bios_read=sum(p['profile_has_bio'] for p in ks),key_bio_missing_ids=[p['id'] for p in unknown],featured_codes=[r['code'] for r in sorted(rs,key=lambda r:({'大会报告':0,'专题报告':1,'论文发言':2}[r['kind']],r['code']))[:4]],gap='题名和会议角色可核；尚未取得本届报告结果或摘要全文。领导角色依据官方简介，待独立交叉核查；未识别到角色不等于该人没有学术影响。')
  rows.append(t)
 labels=['相关报告量','学术带头人覆盖','跨专题覆盖','大会及专题重点报告'];keys=['report_count','leader_units','session_count','key_units'];weights=[40,30,20,10];maxima={k:max(t[k] for t in rows) for k in keys}
 for t in rows:
  t['components']=[dict(name=label,raw=t[k],maximum=maxima[k],weight=w,score=round(w*math.log1p(t[k])/math.log1p(maxima[k]),2)) for label,k,w in zip(labels,keys,weights)]
  t['score']=round(sum(w*math.log1p(t[k])/math.log1p(maxima[k]) for k,w in zip(keys,weights)),1)
  t['agenda_only_score']=round(sum(w*math.log1p(t[k])/math.log1p(maxima[k]) for k,w in zip(keys,weights) if k!='leader_units')/0.7,1)
 for t in rows:
  t['rank']=1+sum(q['score']>t['score'] for q in rows);t['agenda_only_rank']=1+sum(q['agenda_only_score']>t['agenda_only_score'] for q in rows)
 rows.sort(key=lambda t:(-t['score'],t['id']))
 parents=[]
 for pid,name in defs['parents'].items():
  ts=[t for t in rows if t['parent_id']==pid];parents.append(dict(id=pid,name=name,topics=[t['id'] for t in ts],report_count=sum(t['report_count'] for t in ts),leader_count=len({p for t in ts for p in t['leader_ids']})))
 meta=dict(as_of='2026-11-16',title='CDS 2026 会前重点议题榜',status='AI归类与试行权重；待mentor校准',agenda_date='2026年11月18—21日',weights=dict(zip(labels,weights)),normalization='每项=权重×ln(1+原始量)/ln(1+本轮全部入榜议题最大量)；总分以未舍入分项相加后保留1位小数。同一议题同一人只计一次。',leader_rule='有官方会议简介依据的全国/领域学术引领角色记3单位，区域/专科学术带头角色记2单位；同人同题取一次。不按客户等级、医院名气、发言次数或主持席位认定学术地位。',key_rule='重点报告量=3×大会报告+1×专题报告；论文发言在报告总量中计数。主持、致辞、企业专题会发言不计。',scope=dict(total_source_rows=len(a['items']),all_academic=len(ledger),ranked_reports=sum(t['report_count'] for t in rows),excluded_counts=dict(Counter(r['scope'] for r in ledger if r['scope']!='入榜')),all_speakers=len(people),topic_count=len(rows),parent_count=len(parents),profiles_requested=len(docs),profiles_read=sum(d['status']=='read' for d in docs),profiles_with_bio=sum(bool(bio_of(d)) for d in docs),recognized_leaders=sum(p['leader_weight'] is not None for p in people.values()),ranked_leaders=sum(p['leader_weight'] is not None and bool(p['topic_ids']) for p in people.values()),plenary_reports=sum(r['kind']=='大会报告' for r in ledger),all_key_reports=sum(r['kind'] in ['大会报告','专题报告'] for r in ledger)),notes=['使用已有完整日程；仅核对日程自带官方讲者页，没有扩展其他会议或论文结果。','同一报告仅一个主议题，跨题方法/产品标签不重复计报告量；议题归并均为AI题名级初稿。','机构按日程分开保留；同名者不合并，不把单位/科室所有成果归个人。','专家覆盖是当前已找到依据的下限，简介缺失不记成无影响。新增核对可能改变此项和名次；同时提供去专家项的日程排序。','报告量、分会数与重点报告可能相关，不视为四条独立科学证据；没有跨年数据，不判断上升趋势。','议题边界与宽窄不同，总分是本届当前分组下的会前相对关注度，不是研究质量、临床成熟度或客户意向。','大庆随访、GDM预测、药物或机制题名不代表本届已报告结果；不得从题名补写研究结论。'],source_files=[dict(path=str(A),sha256=hashlib.sha256(A.read_bytes()).hexdigest()),dict(path=str(W/'议题定义.json'),sha256=hashlib.sha256((W/'议题定义.json').read_bytes()).hexdigest()),dict(path=str(W/'讲者简介核查.json'),sha256=hashlib.sha256((W/'讲者简介核查.json').read_bytes()).hexdigest())],protected='本地试评页更新；未发布原有框架汇总、正式站或GitHub；客户资料留在改版前存档。')
 payload=dict(meta=meta,topics=rows,parents=parents,people=list(people.values()),reports=ledger,comprehensive_codes=[r['code'] for r in ledger if r['scope']=='综合题目待细分'])
 from 构建领域与Biomarker数据 import build
 payload['research']=build(payload)
 write(R/'会前重点议题数据.json',payload);write(W/'逐报告归类与计分.json',ledger);write(W/'学术带头人依据.json',[p for p in people.values() if p['leader_weight'] is not None]);write(W/'专家识别规则.json',dict(national=NATIONAL,regional=REGIONAL,notes=meta['leader_rule'],confidence='自动抽取角色后AI审阅；单一官方简介，并非履历全量审计。'))
 with (W/'会前重点议题榜.csv').open('w',encoding='utf-8-sig',newline='') as f:
  fields=['排名','议题ID','研究主题','具体议题','会前关注度','报告数','学术带头人数','专家覆盖单位','专题数','大会','专题报告','论文发言','不含专家项排名','分项分数'];out=csv.DictWriter(f,fieldnames=fields);out.writeheader()
  for t in rows:out.writerow(dict(zip(fields,[t['rank'],t['id'],t['parent'],t['name'],t['score'],t['report_count'],t['leader_count'],t['leader_units'],t['session_count'],t['kind_counts'].get('大会报告',0),t['kind_counts'].get('专题报告',0),t['kind_counts'].get('论文发言',0),t['agenda_only_rank'],'；'.join(c['name']+':'+str(c['score']) for c in t['components'])])))
 template=R/'会前重点议题模板.html'
 if template.exists():(R/'index.html').write_text(template.read_text().replace('__DATA__',json.dumps(payload,ensure_ascii=False).replace('</','<\\/')).replace('__RESEARCH_UI__',(R/'领域与Biomarker_工作资料/扩展界面.js').read_text()))
 print(json.dumps(meta['scope'],ensure_ascii=False));print('Top',[(t['id'],t['name'],t['score'],t['leader_count']) for t in rows[:8]])
if __name__=='__main__':generate()
