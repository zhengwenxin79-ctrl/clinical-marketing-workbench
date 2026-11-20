"""仅重组本地既有证据；不联网、不写正式站。"""
from pathlib import Path
from collections import Counter
from datetime import date,timedelta
import json,math,hashlib
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent.parent
WORK=ROOT/'领域与Biomarker_工作资料'
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
PM={'R01':'H01','R02':'H11','R03':'F45','R04':'H03','R05':'H04','R06':'H07','R07':'H03','R08':'H12','R09':'H05','R10':'H05','R11':'H17','R12':'H31','R13':'H04','R14':'H37','R15':'H34','R16':'H30','R17':'H17'}
AM={'A01':'F45','A02':'H18','A03':'H07','A04':'H11','A05':'H08','A06':'H06','A07':'H11','A08':'H11','A09':'H11','A10':'H11','A11':'H11','A12':'H11','A13':'H11','A14':'H11','A15':'H11','A16':'H11','A17':'H29','A18':'H08','A19':'H04','A20':'H03','A21':'H04','A22':'H21','A23':'H30','A24':'H30','A25':'H30','A26':'H34','A27':'H04'}
# 同研究版本、可能重叠样本与同队列不同分析，保守合并用于线索组统计。
FAMILIES={'A01':'R03','A05':'AID-待核同源','A18':'AID-待核同源','A21':'免疫分群-待核重叠','R13':'免疫分群-待核重叠','A24':'GDM-同队列','A25':'GDM-同队列'}
NOTES={'R03':'A01与R03为同一研究的会议/论文版本，合并计一组。','AID-待核同源':'A05与A18可能来自同一AIDING研究；保守合并，待核注册号与样本。','免疫分群-待核重叠':'A21与R13团队/研究框架相关；保守合并，不宣称已证实同一研究。','GDM-同队列':'A24/A25为共享队列不同分析；线索组计一，不作为两次独立验证。'}
STAGES={
'rna35':('V3','有人体外部验证记录','优先复核','已有外部验证AUC 0.73，可先评估临床基线模型上的增益。','补35基因成员、外部验证样本量、独立中心、校准与临床基线增益；补检测重复性及标准化流程。'),
'malat1':('V3','有人体独立验证记录','优先复核','尿液细胞MALAT1有独立验证，适合围绕DKD/NDKD鉴别复核。','补独立验证人数、跨中心设计、检测阈值及相对现有临床路径的增益；先确认尿液细胞输入。'),
'pvt1':('V2','人体候选比较','常规跟踪','有明确候选分子，可比较不同尿液输入的检测表现。','独立验证中PVT1的具体结果和性能待核；不沿用MALAT1结果。'),
'tnfr':('V2','人体风险关联','优先复核','聚焦常规白蛋白尿未覆盖的早期肾风险，临床问题明确。','补TNFR1/2各自效应、检测方法、外部验证及eGFR/UACR之上的增量。'),
'kim1':('V2','人体风险关联','优先复核','面向正常白蛋白尿T2D的肾功能下降风险。','补样本输入与方法、外部验证及相对eGFR/UACR增量。'),
'mmp7':('V2','人体风险关联','优先复核','面向正常白蛋白尿T2D的肾功能下降风险。','补样本输入与方法、阈值、外部验证及相对eGFR/UACR增量。'),
'longitudinal-proteins':('V2','人体纵向队列','常规跟踪','大队列和重复采样可支持动态风险研究。','补明确候选蛋白、可复现模型和外部验证；A01/R03只计一组。'),
'metabolite15':('V2','人体内部建模','常规跟踪','免疫治疗应答分层有具体临床用途。','补15个成员、外部验证、稳定性和相对基础临床指标增益。'),
'bile-acids':('V2','人体分群关联','常规跟踪','可研究免疫代谢与治疗应答的联系。','补具体分子、外部验证及与R13样本重叠情况。'),
'scfa':('V2','人体阴性结果','阴性证据','保留阴性证据，帮助评估指标适用范围。','现有ENDIA研究未支持目标关联；后续研究需解释人群、时窗或检测差异。'),
'glp1r-r131q':('V2','人体观察与功能研究','优先复核','变异明确并关联GLP-1RA应答，适合复核应答分层价值。','补跨族群验证、预设分层试验和临床决策增益；公司基因检测流程待核。'),
'pgs':('V2','长期队列关联','常规跟踪','GDM后长期风险分层用途明确。','补人群外验证、模型校准与临床增益；T1D/T2D适用范围分别判断。'),
'induced-transcript':('V2','人体关联与验证差异','常规跟踪','可追踪免疫反应分群及其临床关联。','独立验证的临床关联未复现；使用血浆刺激报告细胞后测转录，需复核可重复性。'),
'c-peptide':('V2','已用临床指标的研究用途','常规跟踪','作为T1D进展与治疗应答研究的临床比较基准。','区分既有指标与新用途；补新增模型效益及不同研究/队列的独立性。'),
'islet-autoantibodies':('V2','临床风险分层研究','常规跟踪','可用于识别T1D高风险人群并设计分层研究。','补具体抗体、阈值、随访终点及新模型增益。'),
'postmeal-glucose':('V2','人体风险预测','常规跟踪','常规诊断前的GDM风险研究用途明确。','补外部验证、时间窗和相对临床基础模型增益。'),
'mage':('V2','人体诊断模型','常规跟踪','可研究血糖波动指标辅助GDM识别。','补外部验证、阈值与OGTT比较；A24/A25共享队列。'),
'ffa':('V2','人体预测模型','常规跟踪','可用于GDM代谢风险分层的候选指标。','补外部验证、阈值与常规危险因素增益；A24/A25共享队列。'),
'triglycerides':('V2','人体预测模型','常规跟踪','可作为GDM风险模型的候选比较指标。','补外部验证、阈值与临床基础模型增益；常规生化与代谢组流程分别确认。'),
'ev-proteins':('V0','仅取得研究方法','先补结果','EV蛋白可提出T1D部分缓解相关标志物研究问题。','补候选蛋白清单、结果、样本量、验证设计与EV分离/蛋白检测方法。'),
'hgf':('V1','机制研究','机制观察','可从周细胞HGF与β细胞功能寻找后续候选靶点。','以机制证据为主，补人体体液可测性、临床关联与验证。'),
'glutamate':('V1','机制研究','机制观察','可研究成纤维细胞-β细胞代谢互作并寻找候选信号。','补人体体液可测性、来源特异性、临床风险关联与验证。'),
'cytokines':('V0','会前题名线索','先补结果','可跟踪生活方式干预的应答预测研究。','补具体因子、样本、方法、结果及独立验证。'),
'retina-panel':('V0','会前题名线索','先补结果','可跟踪糖网风险预警模型的指标组合。','补组合成员、输入样本、研究结果及独立验证。'),
'cardiometabolic-markers':('V0','会前题名线索','先补结果','可跟踪早期CKM结局风险指标。','补具体标志物、研究结果、随访终点及独立验证。'),
'sarcopenia-metabolites':('V0','会前题名线索','先补结果','可从肌少症代谢表型中寻找候选分子。','补代谢物成员、结果、肌少症定义及独立验证。'),
'hba1c':('REF','常规参照/结局','参照指标','用于解释新模型是否增加已有临床指标之外的信息。','多次作为结局出现，不累计为新Biomarker发现热度。'),
'tir':('REF','常规参照/结局','参照指标','用于解释监测和干预的临床结局。','多次作为结局出现，不累计为新Biomarker发现热度；A05/A18同源待核。')}
def build(base):
 WORK.mkdir(exist_ok=True)
 sp=PROJECT/'会议与论文研究台_v2/src/data.snapshot.json';bp=sp.with_name('biomarkers.catalog.json');ap=ROOT.parent/'ADA_重点议题榜.json'
 old=read(sp);bio=read(bp);adaextra={e['record_id']:e for row in read(ap)['rows'] for e in row.get('evidence',[])}
 records=[];cutoff=date(2026,11,16);start=cutoff-timedelta(days=89)
 people={p['key']:p for p in base['people']}
 for c in base['reports']:
  primary='F45' if c['code']=='OR_318' else c['topic_id']
  records.append(dict(id='C-'+c['code'],original_id=c['code'],source='CDS2026',line='会议',region='国内',title=c['title'],field_id=primary,field_basis='按既有CDS题名归类；OR_318在领域目录细分为循环蛋白风险，原CDS榜归属保留。' if c['code']=='OR_318' else c['classification_basis'],date=None,date_label=c['date']+'（计划）',date_basis='日程安排；不作为研究结果发表时间',team='；'.join(p['name'].replace(' ','')+' · '+p['institution'] for p in c['people']),people_ids=[people[k]['id'] for k in c['people_keys']],leader_ids=[people[k]['id'] for k in c['people_keys'] if people[k]['leader_weight']],study_group=None,has_results=False,level='计划日程题名',url=c['source_url'],scope=c['scope'],design='',result='',limits='研究结果、具体样本及独立研究身份待补。',narrative=None,product_links=[],version_note='',known_date=False))
 for source,key,mapping,prefix in [('论文','papers',PM,'P-'),('会议','ada',AM,'A-')]:
  for x in old[key]:
   ispaper=source=='论文';extra=adaextra.get(x['id'],{});dated=x.get('online_date');basis='原论文在线日期' if ispaper else x.get('date_basis','日期依据待核')
   if '待核' in basis or basis.startswith('官方报道'):dated=None
   oid=x['id'];family=FAMILIES.get(oid,oid);url=('https://pubmed.ncbi.nlm.nih.gov/'+str(x['pmid'])+'/') if ispaper else x['url']
   result=x.get('result','');hasresults=bool(result) if ispaper else bool(x.get('has_results'))
   records.append(dict(id=prefix+oid,original_id=oid,source=x.get('journal','论文') if ispaper else 'ADA2026',line=source,region='国际',title=x.get('title_cn') or x.get('title'),field_id=mapping[oid],field_basis='AI按临床问题及用途映射至统一议题；待mentor校准。',date=dated,date_label=x.get('date') if ispaper else x.get('source_date'),date_basis=basis,team=x.get('team','团队待核'),people_ids=[],leader_ids=[],study_group=family if (hasresults and oid!='A18') else None,has_results=hasresults,level=x.get('reading_level','已存摘要'),url=url,scope='研究记录' if ispaper else '会议关联研究（部分含会后论文）',design=x.get('design',''),result=result,limits=x.get('limits',''),narrative=x.get('narrative'),product_links=x.get('product_relation',{}).get('links',[]),version_note=NOTES.get(family,''),known_date=bool(dated),doi=extra.get('doi') or x.get('doi'),pmid=extra.get('pmid') or x.get('pmid'),paper_url=('https://pubmed.ncbi.nlm.nih.gov/'+str(extra['pmid'])+'/') if extra.get('pmid') else None))
 rm={r['id']:r for r in records};om={r['original_id']:r for r in records if r['line']=='论文' or r['source']=='ADA2026'}
 # 共同目录与当前资料覆盖榜；未满足全量比较条件不伪造领域总热度。
 fields=[dict(id=t['id'],name=t['name'],parent=t['parent'],parent_id=t['parent_id'],question=t['question'],participation=t['participation'],cds_topic_id=t['id']) for t in base['topics']]
 fields.append(dict(id='F45',name='循环蛋白特征与糖尿病发病风险',parent='风险识别与疾病分型',parent_id='new',question='循环蛋白及其纵向变化能否补充糖尿病发病风险判断？',participation='可开展候选蛋白筛选、纵向采样与临床模型增益研究；蛋白检测流程待技术核实。',cds_topic_id=None))
 for f in fields:
  rs=[r for r in records if r['field_id']==f['id']];studies={r['study_group'] for r in rs if r['study_group']};recent={r['study_group'] for r in rs if r['study_group'] and r['date'] and start<=date.fromisoformat(r['date'])<=cutoff};unknown=[r['id'] for r in rs if r['study_group'] and not r['known_date']];leaders={p for r in rs for p in r['leader_ids']};cs=[r for r in rs if r['source']=='CDS2026'];ads=[r for r in rs if r['source']=='ADA2026'];ps=[r for r in rs if r['line']=='论文']
  f.update(record_ids=[r['id'] for r in rs],cds_count=len(cs),ada_count=len(ads),paper_count=len(ps),conference_count=int(bool(cs))+int(bool(ads)),study_groups=sorted(studies),study_count=len(studies),recent_count=len(recent),recent_ids=[r['id'] for r in rs if r['study_group'] in recent],unknown_date_ids=unknown,leader_ids=sorted(leaders),leader_count=len(leaders),team_lines=sorted({r['team'] for r in rs if r['source']!='CDS2026'}),status='跨会议线索' if cs and ads else '候选议题',gaps=['ADA仅27条定向资料，全会覆盖分母待补。','CDS为计划日程，研究身份及结果待补；同题报告不等于独立研究。','ADA/论文作者的带头角色尚未按CDS规则全量核实；跨会同人消歧待补。']+(['部分研究首发日期待核，近期项暂不计总分。'] if unknown else []),biomarker_ids=[])
 # 每项以全目录最大原始量log1p归一；分母不完备项保留null，分项仅在现有资料内解释。
 maxima={k:max(f[k] for f in fields) for k in ['study_count','leader_count','recent_count']}
 for f in fields:
  components=[dict(name='会议覆盖',weight=30,raw=f['conference_count'],score=None,reason='已见CDS/ADA会议数；ADA覆盖不全，跨会标准化分母待补。')]
  for key,name,w in [('study_count','有结果的研究线索组',30),('leader_count','有依据的学术带头角色',20),('recent_count','近90天研究更新',20)]:
   valid=f[key]>0 if key!='recent_count' else bool(f['study_count']) and not f['unknown_date_ids']
   val=round(w*math.log1p(f[key])/math.log1p(maxima[key]),1) if valid and maxima[key] else None
   components.append(dict(name=name,weight=w,raw=f[key],maximum=maxima[key],score=val,reason='仅现有资料的覆盖下限；去重线索组不等于已确认的独立验证。' if key=='study_count' else '仅CDS官方简介已存角色；ADA角色待核。' if key=='leader_count' else f'{start}—{cutoff}，按首发日期；未知日期保留待核。'))
  f['components']=components;f['score']=None;f['observed_subtotal']=round(sum(c['score'] for c in components if c['score'] is not None),1);f['available_weight']=sum(c['weight'] for c in components if c['score'] is not None)
 fields.sort(key=lambda f:(-f['conference_count'],-f['study_count'],-f['leader_count'],f['id']))
 for i,f in enumerate(fields):f['coverage_order']=i+1
 markers=[]
 for b0 in bio['entries']:
  b=dict(b0);bindings=[]
  for x in b.get('bindings',[]):
   rr=om[x['record_id']];bindings.append(dict(x,evidence_id=rr['id']))
  agenda=[dict(x,evidence_id='C-'+x['code']) for x in b.get('agendas',[]) if 'C-'+x['code'] in rm]
  active=[x for x in bindings if x['role'] in ['research','mechanism']];active_ids=[x['evidence_id'] for x in active];rs=[rm[x] for x in active_ids];groups={r['study_group'] for r in rs if r['study_group']};cats=sorted({c for x in active+agenda for c in x.get('categories',[])})
  if not cats:cats=sorted({c for x in bindings for c in x.get('categories',[])})
  stage,stage_label,priority,reason,gap=STAGES[b['id']];group_count=len(groups);status='候选线索'
  if stage=='REF':status='参照指标'
  elif b['id']=='scfa':status='阴性证据'
  elif group_count>=2:status='多研究线索·独立性待核'
  # 暂未完成多团队独立性与跨届历史核验；不把重复出现直接升级为热点。
  item=dict(b,bindings=bindings,agendas=agenda,categories=cats,research_ids=active_ids,record_ids=list(dict.fromkeys([x['evidence_id'] for x in bindings+agenda])),field_ids=sorted({rm[x]['field_id'] for x in active_ids+[a['evidence_id'] for a in agenda] if rm[x]['field_id']}),study_groups=sorted(groups),study_count=group_count,agenda_count=len(agenda),stage=stage,stage_label=stage_label,priority=priority,priority_reason=reason,gap=gap,status=status,heat_eligible=False,heat_basis=f'有结果研究线索组{group_count}组；会前题名{len(agenda)}条。尚缺多团队独立复现与可比时间序列。',reference=stage=='REF',sample_notes=list(dict.fromkeys(x.get('sample','输入待补') for x in active)),heat_gaps=['核对样本/队列与团队独立性。','补可比会议/时间窗口，才能判断上升或持续。'])
  markers.append(item)
 from Biomarker三视角 import review
 biomarker_views=review(markers,records,base['people'],start,cutoff)
 for f in fields:f['biomarker_ids']=[b['id'] for b in markers if f['id'] in b['field_ids'] and not b['reference']]
 sources=[dict(id='CDS2026',name='CDS 2026',line='会议',region='国内',count=606,coverage='已存完整日程；579条进入原榜',denominator=606,results=False,url='https://cds26.tiemeeting.com/CN/Program/Details',gap='题名级资料；结果与独立研究身份待补。'),dict(id='ADA2026',name='ADA 2026',line='会议',region='国际',count=27,coverage='定向收录27条；不是全大会',denominator=None,results=True,url='https://professional.diabetes.org/scientific-sessions',gap='未遍历全会；部分关联记录为会后论文更新。')]
 for journal,n in Counter(x['journal'] for x in old['papers']).items():sources.append(dict(id=journal,name=journal,line='论文',region='国际',count=n,coverage='已有定向样本',denominator=None,results=True,url={'Diabetes Care':'https://diabetesjournals.org/care','Diabetes':'https://diabetesjournals.org/diabetes','Diabetologia':'https://link.springer.com/journal/125','Lancet Diabetes Endocrinol':'https://www.thelancet.com/journals/landia/home','Epigenetics':'https://www.tandfonline.com/journals/kepi20','BMJ Open Diabetes Research & Care':'https://drc.bmj.com/'}.get(journal,'https://pubmed.ncbi.nlm.nih.gov/'),gap='未系统检索或建立同期全量分母；逐篇原文入口见记录。'))
 payload=dict(biomarker_views=biomarker_views,version='0.1',as_of=str(cutoff),window_start=str(start),new_collection=False,records=records,fields=fields,biomarkers=markers,categories=bio['categories'],technologies=old['product_map']['technologies'],sources=sources,dedup_notes=NOTES,score_weights={'会议覆盖':30,'有结果的研究线索组':30,'有依据的学术带头角色':20,'近90天研究更新':20},scoring_note='跨会分母不全，总热度暂不出分；分项在现有资料内试算。领域列表按已见会议数→有结果线索组数→有依据角色数排序，同值按ID；不是领域全量热度榜。',intake=['登记会议/论文来源与采集覆盖范围。','保存原题、团队、日期依据、样本输入、研究设计、结果和原始链接。','按主要临床问题映射稳定议题ID；新问题先加入候选目录。','核对DOI、注册号、队列及会议/论文版本，标注同源或待核。','绑定明确Biomarker及其输入、用途和技术；技术名独立作为筛选标签。','复核后重新生成本地页面；补齐可比覆盖范围后再启用领域总热度。'],source_files=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in [sp,bp,ap]])
 save(WORK/'统一领域与Biomarker数据.json',payload)
 save(WORK/'Biomarker三视角复核.json',dict(rules=biomarker_views,rows=markers))
 save(WORK/'议题映射与去重规则.json',dict(papers=PM,ada=AM,cds_field_overrides={'OR_318':'F45'},families=FAMILIES,notes=NOTES,review='本轮AI按已有资料映射；待mentor校准',protected='原CDS会前榜分组与分值不变'))
 save(WORK/'Biomarker验证与优先理由.json',markers)
 return payload
