"""复核本地资料并输出会议关注、研究跟进、转化优先；不计算综合分。"""
from pathlib import Path
from datetime import date
from collections import Counter
import json
ROOT=Path(__file__).resolve().parent
WORK=ROOT/'领域与Biomarker_工作资料'

def review(markers,records,people,start,cutoff):
 spec=json.loads((WORK/'CDS标志物题名复核.json').read_text());focus=spec['focus'];rm={r['id']:r for r in records};pm={p['id']:p for p in people};cds=[r for r in records if r['source']=='CDS2026'];assert len(cds)==606
 assert set(focus)<=set(r['original_id'] for r in cds)
 ledger=[]
 for r in cds:
  c=r['original_id'];f=focus.get(c)
  if f:status='标志物相关题名';reason='题名明确可测特征及临床用途/关联；仅识别讨论方向，结果与用途验证待补。'
  elif c in spec['pending_inputs']:status='输入或指标待明确';reason='有分型、风险或模型方向，但具体生物特征/输入未明，不计入当前明确题名分母。'
  elif c in spec['mechanism_context']:status='机制/来源参考';reason='题名为机制、靶点或发现来源；尚未明确对应的临床检测用途。'
  elif c in spec['reference_context']:status='常规指标/方法背景';reason='指标主要为治疗结局、常规比较或参数关系，不计新标志物关注。'
  elif r['scope']!='入榜':status='培训/方法/综合背景';reason='原CDS榜已单列，保留原题及链接。'
  else:status='其他研究/临床背景';reason='本轮题名规则下以治疗、机制、管理或一般危险因素为主；摘要补充后可复核。'
  ledger.append(dict(evidence_id=r['id'],code=c,title=r['title'],status=status,in_denominator=bool(f),target=f[0] if f else None,use=f[1] if f else None,kind=f[2] if f else None,basis=reason,review_level='AI题名复核；待mentor校准',url=r['url'],people_ids=r['people_ids'],leader_ids=r['leader_ids'],bound_marker_ids=[]))
 lm={r['code']:r for r in ledger};denom=len(focus)
 for b in markers:
  # 保留旧源文件不变，只修正本次输出的用途角色。
  for x in b['bindings']:
   x['original_role']=x['role']
   if b['id']=='islet-autoantibodies' and x['record_id']=='R04':
    x['role']='population';x['review_note']='抗体阳性定义入组人群；本文主要分析代谢表型，不计为抗体新检测性能验证。'
   if b['id']=='c-peptide' and x['record_id']=='A19':x['role']='endpoint_method';x['review_note']='C肽阈值用于免疫治疗终点方法评价，与R04进展风险用途分开。'
  existing={a['code'] for a in b['agendas']}
  for a in spec['binding_additions'].get(b['id'],[]):
   if a['code'] not in existing:b['agendas'].append(dict(a,evidence_id='C-'+a['code']))
  if b['id']=='islet-autoantibodies':
   b['stage']='V0';b['stage_label']='会前检测/筛查议题；具体新用途待核';b['notes']='R04中抗体用于定义入组人群。CDS原题已明确IA-2A与ZnT8等成员，但不同抗体及组合性能应分别核实。';b['gap']='补各抗体/组合的检测输入、阈值及结果；区分异质性、抗体谱协同与亲属筛查用途。'
  active=[x for x in b['bindings'] if x['role'] in ['research','mechanism','endpoint_method']]
  research_rs=[rm[x['evidence_id']] for x in active];result_rs=[r for r in research_rs if r['study_group']];groups=sorted({r['study_group'] for r in result_rs});recent={r['study_group'] for r in result_rs if r['date'] and start<=date.fromisoformat(r['date'])<=cutoff}
  conference_ids=list(dict.fromkeys([r['id'] for r in research_rs if r['line']=='会议']+[a['evidence_id'] for a in b['agendas']]))
  if b['reference']:conference_ids=list(dict.fromkeys(x['evidence_id'] for x in b['bindings'] if rm[x['evidence_id']]['line']=='会议'))
  panels=[]
  for source,total in [('CDS2026',606),('ADA2026',None)]:
   rs=[rm[i] for i in conference_ids if rm[i]['source']==source];ids=[r['id'] for r in rs];cds_focus_count=sum(r['original_id'] in focus for r in rs) if source=='CDS2026' else None
   leaders=sorted({p for r in rs for p in r['leader_ids']});speakers=sorted({p for r in rs for p in r['people_ids']});unknown=[p for p in speakers if not pm[p]['leader_weight']]
   panels.append(dict(source=source,record_ids=ids,count=len(ids),focus_count=cds_focus_count,share=round(100*cds_focus_count/denom,2) if total else None,denominator=denom if total else None,total_reviewed=total,leader_ids=leaders,people_ids=speakers,unknown_role_ids=unknown,unresolved_team_record_ids=[r['id'] for r in rs if not r['people_ids']],coverage='完整606条学术题名，按本轮规则复核' if total else '27条定向关联记录；不是全会',reading='计划题名' if total else '会议摘要/方法及关联论文更新'))
  cases=[]
  for x in b['bindings']:
   r=rm[x['evidence_id']];cases.append(dict(id=b['id']+'-'+r['id'],evidence_id=r['id'],role=x['role'],sample=x.get('sample','待补'),use=x.get('use','待补'),basis=x['basis'],review_note=x.get('review_note',''),signal=x.get('signal',''),source=r['source'],study_group=r['study_group'],has_results=r['has_results']))
  for a in b['agendas']:
   r=rm[a['evidence_id']];f=focus.get(a['code']);cases.append(dict(id=b['id']+'-'+r['id'],evidence_id=r['id'],role='agenda',sample=a.get('sample','输入/测量方法待摘要核实'),use=a.get('use') or (f[1] if f else '具体用途待核'),basis=a['basis'],review_note='会前题名，具体研究结果待补。',signal='计划议题',source='CDS2026',study_group=None,has_results=False))
   if a['code'] in lm:lm[a['code']]['bound_marker_ids'].append(b['id'])
  if b['reference']:priority='参照用途'
  elif b['id']=='scfa' or b['stage'] in ['V0','V1']:priority='方向观察'
  elif b['priority']=='优先复核':priority='优先复核'
  else:priority='继续验证'
  reason=b['priority_reason']
  if b['id'] in ['ffa','triglycerides']:reason='现有GDM队列加入这些指标后未见预测增益；先核适用人群、方法与重复验证。'
  elif b['id']=='mage':reason='现有诊断性能未支持替代OGTT；可复核其辅助用途与外部验证。'
  elif b['id']=='induced-transcript':reason='有免疫分群线索，但部分临床关联在验证队列未复现，优先核重复性。'
  elif b['id']=='islet-autoantibodies':reason='先取得CDS各具体抗体与用途的结果；R04入组筛查条件不作为新抗体检测发现。'
  validation_ids=['P-R16'] if b['id']=='rna35' else ['P-R17'] if b['id']=='malat1' else []
  negative=b['id'] in ['scfa','ffa','triglycerides','mage']
  human='有人体研究记录' if b['stage'] in ['V2','V3'] else '题名/方法待结果' if b['stage']=='V0' else '机制为主；人体标志物用途待核' if b['stage']=='V1' else '常规参照'
  gain='未见预测增益' if b['id'] in ['ffa','triglycerides'] else '未支持替代OGTT' if b['id']=='mage' else '目标关联未获支持' if b['id']=='scfa' else 'T1D有补充记录，T2D增益较小；待复核' if b['id']=='pgs' else '部分临床关联未复现' if b['id']=='induced-transcript' else '相对现行临床模型/路径的增益待补'
  teams=[]
  for g in groups:teams.append(dict(study_group=g,team_labels=sorted({r['team'] for r in result_rs if r['study_group']==g}),evidence_ids=[r['id'] for r in result_rs if r['study_group']==g]))
  label='常规参照' if b['reference'] else '机制观察' if b['stage']=='V1' else '候选线索'
  attention_checks=[dict(label='候选线索',status='已记录' if not b['reference'] else '参照用途',basis='有明确指标/类别及对应原始记录，按用途与输入分别保留。'),dict(label='会议集中讨论',status='待同用途复核',basis='类别下不同检测、筛查、组合不合并为同一具体指标热点。'),dict(label='多团队跟进',status='待核',basis='研究组去重与外部验证记录，不直接证明独立团队复现。'),dict(label='持续关注',status='待可比窗口',basis='当前无相同覆盖规则的连续会议/时间窗口。')]
  b.update(priority=priority,priority_reason=reason,study_groups=groups,study_count=len(groups),research_ids=[x['evidence_id'] for x in active],record_ids=list(dict.fromkeys([x['evidence_id'] for x in b['bindings']]+[a['evidence_id'] for a in b['agendas']])),field_ids=sorted({rm[i]['field_id'] for i in conference_ids+[x['evidence_id'] for x in b['bindings']] if rm[i]['field_id']}),agenda_count=len(b['agendas']),status=label,heat_eligible=False,heat_basis='按会议、研究和转化分别列证据；无综合分和跨资料池排名。')
  b['review']=dict(conferences=panels,study_count=len(groups),study_groups=groups,teams=teams,confirmed_independent_studies=None,confirmed_independent_teams=None,independence_note='跨研究队列/样本与团队独立性尚未完成核查；不以不同作者字符串或单位数替代。',recent_count=len(recent),recent_ids=[r['id'] for r in result_rs if r['study_group'] in recent],latest_known_date=max([r['date'] for r in result_rs if r['date']],default=None),unknown_date_ids=[r['id'] for r in result_rs if not r['date']],validation_ids=validation_ids,validation_study_count=len({rm[i]['study_group'] for i in validation_ids}),paper_ids=[r['id'] for r in research_rs if r['line']=='论文'],population_ids=[x['evidence_id'] for x in b['bindings'] if x['role']=='population'],cases=cases,attention_checks=attention_checks,negative=negative,translation=dict(priority=priority,reason=reason,stage=b['stage'],stage_label=b['stage_label'],gap=b['gap'],checks=[dict(name='人体证据',status=human),dict(name='独立/外部验证',status='有原研究验证记录，细节待复核' if validation_ids else '未核实，待补'),dict(name='临床增益',status=gain),dict(name='检测与交付适配',status='有研究技术关联，样本/平台/参数待技术确认' if b['matches'] else '对应检测流程待技术确认')]))
 # 完整题名复核名单可复算分母，未绑定现有词条的题名原样单列，不挤入近似指标。
 for b in markers:
  assert all(a['code'] in focus for a in b['agendas'])
 meta=dict(version='0.2',as_of=str(cutoff),window_start=str(start),scoring_enabled=False,new_collection=False,cloud_mode='uniform',cloud_font_px=20,definition=spec['definition'],reviewer=spec['reviewer'],cds_total=606,cds_focus_count=denom,cds_bound_focus_count=sum(bool(r['bound_marker_ids']) for r in ledger if r['in_denominator']),cds_unbound_focus_count=sum(not r['bound_marker_ids'] for r in ledger if r['in_denominator']),cds_scope_counts=dict(Counter(r['status'] for r in ledger)),ada_count=27,ada_denominator=None,ledger=ledger,non_equivalences=spec['non_equivalences'],role_labels={'research':'指标研究','mechanism':'机制来源','endpoint_method':'终点方法','population':'入组/筛查条件','reference':'参照/结局','agenda':'会前题名'},notes=['只使用本地已存资料；CDS为题名级复核，不补写结果。','CDS占比=本词条明确绑定的相关报告数÷本轮标志物相关题名数；一个报告可涉及多个指标，占比不要求相加100%。','ADA为定向样本，不计算全会占比，不与CDS按收录数量排共同榜。','词云统一20px用于导航；没有综合关注分，也没有按分数生成字号或热点标签。','同指标不同样本、用途及角色分别列为证据单元；类别、组合与具体分子分别筛选。','多团队跟进与持续关注需补独立性和可比历史；未核不是0。'])
 (WORK/'CDS标志物逐报告复核台账.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n')
 return meta
