"""给已绑定的Biomarker计算本地资料关注分，不推断全领域热度。"""
import math
from datetime import date
from collections import defaultdict

def quantify(markers,records,people,start,cutoff):
 rm={r['id']:r for r in records};pm={p['id']:p for p in people};raw={}
 for b in markers:
  ids=list(dict.fromkeys(b['research_ids']+[a['evidence_id'] for a in b['agendas']]))
  rs=[rm[i] for i in ids];conference_ids=sorted({r['source'] for r in rs if r['line']=='会议'})
  result_rs=[r for r in rs if r['study_group']]
  recent={r['study_group'] for r in result_rs if r['date'] and start<=date.fromisoformat(r['date'])<=cutoff}
  unknown_dates=[r['id'] for r in result_rs if not r['date'] and r['study_group'] not in recent]
  leader_ids=sorted({p for r in rs for p in r['leader_ids']})
  unknown_roles=[r['id'] for r in rs if r['source']!='CDS2026' or any(not pm[p]['leader_weight'] for p in r['people_ids'])]
  pending_results=[r['id'] for r in rs if not r['has_results']]
  raw[b['id']]=dict(conference_ids=conference_ids,conference_count=len(conference_ids),study_count=b['study_count'],study_ids=sorted({r['study_group'] for r in result_rs}),leader_count=len(leader_ids),leader_ids=leader_ids,recent_count=len(recent),recent_ids=[r['id'] for r in result_rs if r['study_group'] in recent],unknown_date_ids=unknown_dates,unknown_role_ids=unknown_roles,pending_result_ids=pending_results,evidence_ids=ids,record_count=len(rs),date_label=f'{start}—{cutoff}')
 nonrefs=[raw[b['id']] for b in markers if not b['reference']]
 maxima={k:max([r[k] for r in nonrefs]+[1]) for k in ['study_count','leader_count','recent_count']}
 def logscore(n,w,m):return w*math.log1p(n)/math.log1p(m)
 for b in markers:
  r=raw[b['id']]
  if b['reference']:
   b['quantification']=dict(r,score=None,rank=None,components=[],pending_count=0,ceiling=None,reference=True)
   continue
  cs=[]
  spec=[('conference_count','会议提及',30,2,r['conference_count']*15,False,'当前CDS、ADA两场，每见一场明确绑定资料记15分；同一场多条不重复加分。'),('study_count','去重研究线索组',30,maxima['study_count'],logscore(r['study_count'],30,maxima['study_count']),bool(r['pending_result_ids']),'同研究会议/论文合并；疑似重叠保守计组，不等同经核独立研究。'),('leader_count','已核学术带头人',20,maxima['leader_count'],logscore(r['leader_count'],20,maxima['leader_count']),bool(r['unknown_role_ids']),'仅本指标直接绑定报告中有角色依据的主讲人；不继承整个领域的专家人数。'),('recent_count','近90天更新',20,maxima['recent_count'],logscore(r['recent_count'],20,maxima['recent_count']),bool(r['unknown_date_ids']),'按已读结果的可核首发日期计去重研究组；计划日、卷期日和发现日不代替首发。')]
  for key,name,w,m,s,pending,reason in spec:
   # 已见量达到当前归一化上限时，未知资料仍留缺口，但不会再增加该分项。
   pending=pending and s<w-1e-8
   evidence=[i for i in r['evidence_ids'] if rm[i]['line']=='会议'] if key=='conference_count' else [i for i in r['evidence_ids'] if rm[i]['study_group']] if key=='study_count' else [i for i in r['evidence_ids'] if rm[i]['leader_ids']] if key=='leader_count' else r['recent_ids']
   gaps=[]
   if key=='conference_count':gaps=['ADA为定向样本，仅反映当前资料的已见覆盖，不推断全会或全领域缺席。']
   elif key=='study_count':gaps=['独立队列、团队与样本重叠仍需核实。']+(['部分记录只取得题名或方法，结果待补。'] if r['pending_result_ids'] else [])
   elif key=='leader_count' and r['unknown_role_ids']:gaps=[f"{len(r['unknown_role_ids'])}条绑定记录的作者/主讲角色仍待核。"]
   elif key=='recent_count' and r['unknown_date_ids']:gaps=[f"{len(r['unknown_date_ids'])}条有结果记录的首发日期待核。"]
   cs.append(dict(key=key,name=name,weight=w,raw=r[key],maximum=m,score=round(s,2) if not pending else None,observed_points=round(s,2),pending=pending,basis=reason,gaps=gaps,evidence_ids=evidence))
  score=round(sum(v[4] for v in spec),1)
  ceiling=round(sum(c['weight'] if c['pending'] else c['observed_points'] for c in cs),1)
  b['quantification']=dict(r,score=score,ceiling=ceiling,rank=None,components=cs,pending_count=sum(c['pending'] for c in cs),reference=False)
 for b in markers:
  q=b['quantification']
  if q['score'] is not None:q['rank']=1+sum(o['quantification']['score'] is not None and o['quantification']['score']>q['score'] for o in markers)
 return dict(version='0.1',label='本地资料关注分',weights={'会议提及':30,'去重研究线索组':30,'已核学术带头人':20,'近90天更新':20},conference_denominator=2,maxima=maxima,window=f'{start}—{cutoff}',normalization='会议项＝15×已见会议数（当前登记CDS、ADA两场）。其余项＝权重×ln(1+已见量)/ln(1+本轮非参照指标最大已见量)，分项不超过其权重；总分用未舍入分项相加后保留1位小数。',missing='缺项分值显示待核，已核关注分仅累计已有证据分，是资料内关注下限；可补分上限只表示按本轮规则仍可补的分，不是置信区间。',ranking='按已核关注分降序，同分并列，次序按词条ID。未知角色或日期补齐可能改变排序；筛选不重算归一化分母。',cloud='词云字号=18+12×已核关注分/100（像素，保留1位小数）；参照指标固定18px。',scope='只计指标直接绑定的现有CDS/ADA/论文记录；不从领域话题继承专家和会议，不将参照用途计入新指标关注。分数用于当前资料池内比较，不代表领域总体热度、研究正确性或临床成熟度。',trial_status='试行口径，待mentor校准；热点等级与验证阶段继续单独判断。')
