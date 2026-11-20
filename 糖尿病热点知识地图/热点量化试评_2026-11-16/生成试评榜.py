from pathlib import Path
import json,math,csv,re,hashlib,xml.etree.ElementTree as ET
from decimal import Decimal,ROUND_HALF_UP
from collections import Counter
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent;RAW=ROOT/'原始材料'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def rounded(v):return float(Decimal(str(v)).quantize(Decimal('0.1'),rounding=ROUND_HALF_UP))
def csvwrite(path,fields,rows):
 with path.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def normalize_name(n):return re.sub(r'\s+','',n).casefold()
cds=read(ROOT/'CDS_逐报告分类.json');themes=read(ROOT/'主题分组.json');weights=[40,25,20,15];scorekeys=['PI会内角色代理','重点报告覆盖','口头摘要候选量','专题覆盖']
rolemap={};role_evidence={}
for r in cds['items']:
 tier={'大会报告':3,'专题报告':2,'论文发言':1}.get(r['kind'],0)
 if not tier:continue
 for p in r['people']:
  name=normalize_name(p['name'])
  if tier>rolemap.get(name,0):rolemap[name]=tier;role_evidence[name]={'tier':tier,'code':r['code'],'kind':r['kind'],'url':r['source_url']}
rows=[]
for t in themes:
 pool=[r for r in cds['items'] if r.get('theme_id')==t['id']];kinds=Counter(r['kind'] for r in pool);people={normalize_name(p['name']):p for r in pool for p in r['people']};top=sorted(people,key=lambda n:(-rolemap.get(n,0),n))[:3];unique_or={r['code'] for r in pool if r['kind']=='论文发言'};key_count=3*kinds['大会报告']+kinds['专题报告'];session_count=len({r['session_id'] for r in pool})
 r=dict(t);r.update(report_count=len(pool),kinds=dict(kinds),unique_or_count=len(unique_or),unique_speakers=len(people),key_weighted_count=key_count,session_count=session_count,top_people=[{**people[n],'role_basis':role_evidence[n]} for n in top],components_raw=[sum(rolemap[n] for n in top)/9,key_count,len(unique_or),session_count],report_codes=[x['code'] for x in pool],examples=sorted(pool,key=lambda x:({'大会报告':0,'专题报告':1,'论文发言':2}[x['kind']],x['code']))[:4]);rows.append(r)
for k in [1,2,3]:
 maximum=max(r['components_raw'][k] for r in rows)
 for r in rows:r['components_raw'][k]=math.log1p(r['components_raw'][k])/math.log1p(maximum) if maximum else 0
for r in rows:
 r['components']={name:rounded(weight*value) for name,weight,value in zip(scorekeys,weights,r['components_raw'])};r['score']=rounded(sum(w*x for w,x in zip(weights,r['components_raw'])));r['status']='会前关注度；PI角色代理，待导师校准';r['gaps']=['仅有标题和日程，暂无本届报告结果。','PI以本届报告角色代理；学术影响、基金、客户意向尚未核验。','口头摘要编号去重不等于确认独立研究，跨题同队列待核。']
rows.sort(key=lambda r:(-r['score'],r['id']))
for i,r in enumerate(rows,1):r['rank']=i
scenarios={'默认':[40,25,20,15],'等权':[25,25,25,25],'PI较低':[30,25,25,20],'PI较高':[50,20,15,15]}
for r in rows:r['scenario_ranks']={}
for name,w in scenarios.items():
 sortedrows=sorted(rows,key=lambda r:(-sum(a*b for a,b in zip(w,r['components_raw'])),r['id']))
 for i,r in enumerate(sortedrows,1):r['scenario_ranks'][name]=i
write(ROOT/'CDS_重点议题榜.json',{'as_of':'2026-11-16','meeting':'CDS 2026','view':'会前关注度','weights':dict(zip(scorekeys,weights)),'scope':{'sessions':len(cds['sessions']),'rows':len(cds['items']),'numbered_rows':sum(bool(re.fullmatch(r'(S_|OR_|PL_)\d+',r['code'])) for r in cds['items']),'academic_rows':606,'classified_rows':sum(r['report_count'] for r in rows),'unclassified':3,'education_excluded':3,'other_format_numbered_excluded':93,'independent_study_count':None},'rows':rows,'expert_review':'pending'})
csvwrite(ROOT/'CDS_重点议题榜.csv',['名次','议题','总分','PI角色代理_40','重点报告_25','口头摘要量_20','专题覆盖_15','大会报告','专题报告','口头摘要','不同讲者','不同专题','权重情景名次范围','业务参与建议','状态'],[{'名次':r['rank'],'议题':r['name'],'总分':r['score'],'PI角色代理_40':r['components'][scorekeys[0]],'重点报告_25':r['components'][scorekeys[1]],'口头摘要量_20':r['components'][scorekeys[2]],'专题覆盖_15':r['components'][scorekeys[3]],'大会报告':r['kinds'].get('大会报告',0),'专题报告':r['kinds'].get('专题报告',0),'口头摘要':r['unique_or_count'],'不同讲者':r['unique_speakers'],'不同专题':r['session_count'],'权重情景名次范围':f"{min(r['scenario_ranks'].values())}—{max(r['scenario_ranks'].values())}",'业务参与建议':r['participation'],'状态':r['status']} for r in rows])
csvwrite(ROOT/'CDS_报告分类明细.csv',['编号','标题','类型','日期','主题ID','次要主题','分类依据','讲者','专题','来源'],[{'编号':r['code'],'标题':r['title'],'类型':r['kind'],'日期':r['date'],'主题ID':r.get('theme_id',''),'次要主题':','.join(r.get('secondary_theme_ids',[])),'分类依据':r.get('classification_basis',r.get('excluded_reason','未分类/不计分')),'讲者':'；'.join(p['name'] for p in r['people']),'专题':r['session'],'来源':r['source_url']} for r in cds['items']])
# Primary paper abstracts, deduped by PMID and trial identity. No outcome inference from programs.
records={r['id']:r for r in read(PROJECT/'会议与论文研究台_v2/src/data.snapshot.json')['ada']};papers={}
for file in ['ADA_论文摘要批量.xml','ADA_A01关联论文.xml']:
 xml=ET.fromstring((RAW/file).read_bytes())
 for node in xml.findall('PubmedArticle'):
  a=node.find('./MedlineCitation/Article');pmid=node.findtext('./MedlineCitation/PMID');abstracts=[{'section':t.get('Label',''),'text':''.join(t.itertext())} for t in a.findall('./Abstract/AbstractText')];ids={t.get('IdType'):t.text for t in node.findall('./PubmedData/ArticleIdList/ArticleId')};ncts=sorted(set(re.findall(r'NCT\d+',str(abstracts))));dates=['-'.join(d.findtext(k,'?') for k in ['Year','Month','Day']) for d in a.findall('ArticleDate')];corrections=[{'type':c.get('RefType'),'pmid':c.findtext('PMID'),'source':c.findtext('RefSource')} for c in node.findall('./MedlineCitation/CommentsCorrectionsList/CommentsCorrections')];first=a.find('./AuthorList/Author');author=' '.join(first.findtext(k,'') for k in ['ForeName','LastName']) if first is not None else ''
  papers[pmid]={'pmid':pmid,'doi':ids.get('doi'),'title':''.join(a.find('ArticleTitle').itertext()),'abstract':abstracts,'trial_ids':ncts,'online_dates':dates,'corrections':corrections,'first_author':author,'journal':a.findtext('./Journal/Title'),'source_file':file,'url':'https://pubmed.ncbi.nlm.nih.gov/'+pmid+'/','reading_level':'原始论文摘要；未全文精读'}
programme=(PROJECT/'来源/ADA2026_日程.txt').read_text().split('\f');ada=[];ratings=read(ROOT/'ADA编辑评分.json');aw=[30,35,25,10];ak=['新颖性','临床科研价值','证据成熟度','多研究支持']
for t in ratings:
 r=dict(t);evidence=[]
 for rid in t['records']:
  rec=records[rid];pmid='42709505' if rid=='A01' else rec['url'].strip('/').split('/')[-1];p=papers[pmid];code=rec['code'];terms=[code] if re.match(r'\d+-',code) else [code.replace('-',' '),code];pages=[i+1 for i,page in enumerate(programme) if any(term.casefold() in page.casefold() for term in terms)]
  evidence.append({'record_id':rid,'program_code_or_trial':code,'program_physical_pages':pages,**p})
  if rid=='A01':evidence[-1]['version_note']='A01与R03同研究，合并计一次。'
 r['evidence']=evidence;r['study_count']=len(evidence);r['components']={k:rounded(w*s/4) for k,w,s in zip(ak,aw,t['scores'])};r['score']=rounded(sum(w*s/4 for w,s in zip(aw,t['scores'])));r['status']='原始摘要试评；待专业/业务复核';r['raw_scale_max']=4
 if r.get('correction_pmids'):r['score_if_correction_resolved']=rounded(sum(w*s/4 for w,s in zip(aw,t['scores']))+25/4)
 r['scenario_ranks']={};ada.append(r)
ada.sort(key=lambda r:(-r['score'],r['id']))
for i,r in enumerate(ada,1):r['rank']=i
for name,w in {'默认':aw,'等权':[25,25,25,25],'偏临床':[20,45,25,10],'偏证据':[25,30,35,10]}.items():
 for i,r in enumerate(sorted(ada,key=lambda r:(-sum(a*b/4 for a,b in zip(w,r['scores'])),r['id'])),1):r['scenario_ranks'][name]=i
ranked_records={rid for t in ada for rid in t['records']};pending=[]
for rid,rec in records.items():
 if rid not in ranked_records:pending.append({'id':rid,'name':rec.get('topic',rec['title']),'code':rec['code'],'reading_level':rec['reading_level'],'official_url':rec['url'],'reason':'原始完整结果本轮未取得；旧索引或官方报道可作线索，不以缺失当0分','next':'获取原始摘要/海报/关联论文，并核同研究版本后再评分'})
write(ROOT/'ADA_重点议题榜.json',{'as_of':'2026-11-16','meeting':'ADA 2026','view':'会议关联研究进展重要性；含会前及会后论文版本','weights':dict(zip(ak,aw)),'scope':{'candidate_records':len(records),'scored_records':len(ranked_records),'primary_paper_abstracts':len(papers),'pending_records':len(pending),'conference_universe':'未系统遍历全大会结果，榜单仅覆盖当前候选池','full_text_reviewed':0},'rows':ada,'pending':pending,'expert_review':'pending'})
write(RAW/'ADA_14篇原始摘要结构化.json',list(papers.values()))
csvwrite(ROOT/'ADA_重点议题榜.csv',['名次','议题','总分','新颖性_30','临床价值_35','证据_25','多研究_10','研究数量','原始记录','权重情景名次范围','勘误核清后情景分','主要发现','缺口','业务关系'],[{'名次':r['rank'],'议题':r['name'],'总分':r['score'],'新颖性_30':r['components'][ak[0]],'临床价值_35':r['components'][ak[1]],'证据_25':r['components'][ak[2]],'多研究_10':r['components'][ak[3]],'研究数量':r['study_count'],'原始记录':','.join(r['records']),'权重情景名次范围':f"{min(r['scenario_ranks'].values())}—{max(r['scenario_ranks'].values())}",'勘误核清后情景分':r.get('score_if_correction_resolved',''),'主要发现':r['summary'],'缺口':r['gap'],'业务关系':r['business']} for r in ada])
csvwrite(ROOT/'ADA_待评估记录.csv',['ID','题目','原读取层次','缺口','来源'],[{'ID':r['id'],'题目':r['name'],'原读取层次':r['reading_level'],'缺口':r['reason'],'来源':r['official_url']} for r in pending])
source_audit={'as_of':'2026-11-16','CDS':{'url':'https://cds26.tiemeeting.com/CN/Program/Details','raw_file':'原始材料/CDS_详细日程_2026-11-16.html','sha256':hashlib.sha256((RAW/'CDS_详细日程_2026-11-16.html').read_bytes()).hexdigest(),'sessions':148,'rows':797,'numbered':699,'parsed_previous_2026_11_11':{'rows':798,'numbered':700},'difference':'原日程OR_219本次不再出现；仅记录条目变化，不推断主办方撤稿原因','reports_result_read':0},'ADA':{'program_url':'https://professional.diabetes.org/sites/dpro/files/2026-04/SS26_Program_Final_Digital.pdf','program_version':'2026-04-24导出；复用11/11存档，抽样核对物理第294页','source_papers':len(papers),'read_level':'PubMed保存的原始论文完整摘要；未全文精读','candidate_pool':27,'eligible_records':14,'unranked':13,'blocked_examples':['https://diabetesjournals.org/diabetes/article/75/Supplement_1/1024-OR/167746/1024-OR-Immunologically-Distinct-Type-1-Diabetes','https://diabetesjournals.org/diabetes/article/75/Supplement_1/1113-OR/168085/1113-OR-ADA-Presidents-Select-Abstract-Single-Cell'],'blocked_status':'原站直访403；检索线索未替代本轮完整原始结果','correction_gaps':[{'pmid':'42251859','erratum_pmid':'42320507','doi':'10.1016/S2213-8587(26)00157-9','status':'勘误存在已核，内容待取'},{'pmid':'42252333','erratum_pmid':'42642663','doi':'10.1038/s41591-026-04650-w','status':'勘误存在已核，内容待取'}],'publication_timing_note':'A08会议前已发表，A03/A15为会后论文更新；会议关联不代表本届首次披露。'},'company_fit':{'basis_date':'2026-11-10','source':'吉因加临床科研能力表','status':'仅研究问题匹配，未重新核对产品目录或当前交付'},'ranking_version':'v0.1 AI试评，待导师人工校准','formal_website_changed':False,'new_schedule_created':False}
write(ROOT/'来源覆盖与缺口.json',source_audit)
print('CDS:',[(r['rank'],r['name'],r['score']) for r in rows[:5]])
print('ADA:',[(r['rank'],r['name'],r['score']) for r in ada]);print('Published original source datasets unchanged.')
