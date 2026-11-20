"""只读本地程序与既有CDS分类定义，显式划定ADA解析范围并规则辅助初分。"""
from pathlib import Path
from collections import Counter,defaultdict
import re,json,sqlite3
ROOT=Path(__file__).resolve().parents[1]
RULES=[
('Q02',r'\bMODY\b|monogenic|neonatal diabetes|rare diabetes|Wolfram|lipodystrophy'),
('Q32A',r'thyroid|thyrotropin'),('Q32B',r'cushing|aldosteronism|pheochromocytoma|adrenal'),('Q32C',r'polycystic|PCOS|ovarian|reproduct|testosterone|gonadal'),('Q32D',r'uric acid|hyperuric|\bgout\b'),
('Q30',r'gestational|\bGDM\b|pregnan'),('Q31',r'offspring|maternal|in utero|placenta|intergenerational'),
('Q22C',r'(?:diabet|foot|wound).{0,35}infection|infect.{0,30}(?:foot|ulcer)'),('Q22A',r'wound|ulcer.{0,30}healing|skin repair|diabetic skin'),('Q22B',r'diabetic foot|foot ulcer|foot care|lower.extremity.{0,25}(?:ulcer|amput|arter|wound)|amputat|peripheral arter'),
('Q20',r'retinopath.{0,40}(?:screen|predict|risk|biomarker|detect)|(?:screen|predict|risk).{0,45}retinopath|fundus|retinal imaging'),('Q21',r'retinopath|retina|macular|vision loss|ocular'),
('Q25B',r'\bstroke\b|cerebrovascular'),('Q44',r'cogniti|dementia|alzheimer|brain injury|brain health|hippocamp'),('Q23',r'neuropath|neuropathy|neuropathic pain|nerve injury|autonomic|gastroparesis'),
('Q17',r'(?:kidney|renal|nephropa|\bCKD\b|\bDKD\b).{0,55}(?:predict|risk|screen|diagnos|trajectory|phenotyp)|(?:predict|screen|biomarker).{0,55}(?:kidney|renal|nephropa)'),('Q19',r'(?:kidney|renal|nephropa|\bCKD\b|\bDKD\b).{0,100}(?:trial|finerenone|SGLT|semaglutide|tirzepatide)|(?:finerenone|SGLT|dapagliflozin|empagliflozin).{0,100}(?:renal|kidney|CKD|DKD)'),('Q18',r'kidney|renal|nephropa|\bDKD\b|\bCKD\b|podocyte|glomerul|tubular'),
('Q24',r'heart failure|cardiomyopath|myocard|cardiac fibrosis|ventricular'),('Q27',r'cardiovascular.kidney.metabolic|\bCKM\b|multimorbid|multiorgan|multi.organ'),('Q25A',r'atherosclero|cardiovascular|coronary|\bMACE\b|vascular endotheli|endothelial|infarction'),('Q26',r'lipoprotein|LDL|HDL|cholesterol|dyslipid|triglyceride'),
('Q43',r'(?:MASLD|MASH|MAFLD|NAFLD|NASH|fatty liver|steatohepatitis).{0,100}(?:diet|exercise|microbio|microbiota|fasting)|(?:diet|exercise|microbio|microbiota).{0,100}(?:MASLD|MASH|MAFLD|NAFLD|NASH|fatty liver)'),('Q28',r'(?:liver|hepatic|MASLD|MASH|MAFLD|NAFLD|NASH).{0,50}(?:predict|risk|detect|diagnos|biomarker|stratif|imaging|MRI|elastograph)'),('Q29',r'(?:MASH|NASH|liver|hepatic).{0,75}(?:fibrosis|macrophage|stellate|immune|inflamm|target)'),('Q42',r'MASLD|MAFLD|NAFLD|MASH|NASH|steatohepat|fatty liver|hepatic|liver'),
('Q33B',r'osteopor|osteoblast|osteocyte|bone density|bone loss|bone health|fracture|bone metabolism'),('Q33C',r'lean.{0,20}(?:mass|loss)|body composition|weight.loss.{0,40}muscle|muscle.{0,40}weight.loss'),('Q33A',r'sarcopen|muscle atrophy|muscle loss|muscle health|muscle strength'),
('Q38A',r'depress|diabetes distress|mental health|mindful|psycholog|anxiety|eating disorder'),('Q38B',r'nurs.{0,15}(?:led|care|interven)|caregiv|care partner|medication self.management'),
('Q06',r'islet.{0,30}transplant|stem.cell|organoid|cell replacement|islet graft|islet replacement|beta.cell.{0,30}regener|β.cell.{0,30}regener|neo.islet'),('Q04',r'immunotherap|immune toler|teplizumab|anti.CD3|autoimmune|autoreactive|\bT[ -]cell|\bB[ -]cell|\bTreg\b|\bCD8|\bCD4|\bNK cell'),
('Q08',r'closed.loop|artificial pancreas|automated insulin|\bAID\b|insulin pump'),('Q03A',r'autoantibod|islet antibod|type 1.{0,35}(?:screen|heterogen|subtyp)|T1D.{0,35}(?:screen|heterogen|subtyp)'),('Q03B',r'(?:type 1|T1D).{0,40}(?:transition|family|management|adolescen)'),
('Q07',r'\bCGM\b|continuous glucose|time.in.range|glyc.emic variab|glucose monitoring|glucose sensor'),('Q10',r'noninvasive|non.invasive|breath sensor|optical glucose'),
('Q13B',r'bariatric|metabolic surgery|gastric bypass|\bRYGB\b|sleeve gastrectomy'),('Q13A',r'weight regain|weight.maintenance|weight.loss maintenance|weight cycling|weight rebound'),
('Q11',r'GLP.?1|GIP|incretin|orforglipron|retatrutide|tirzepatide|semaglutide|amylin|cagri|survodutide|elecoglipron'),('Q12',r'SGLT.?2|DPP.?4|metformin|insulin glargine|insulin degludec|efsitora|icodec|insulin therap|insulin analog|basal insulin|imeglimin'),
('Q34',r'nutrition|dietary|diet |intermittent fasting|prolonged fast|meal|food |carbohydrate.restric|low.carbo|caloric|calorie|time.restricted'),('Q35',r'exercise|physical activ|sedentary|resistance training|aerobic|step count'),
('Q36',r'microbiom|microbiota|gut bacteria|short.chain fatty acid'),('Q14',r'brown adip|beige adip|adipogen|thermogen|adipose|adipocyt|energy expenditure'),('Q15',r'brain|hypothalam|interorgan|organ crosstalk|skeletal muscle|muscle metabolism'),
('Q16',r'insulin resistance|lipotox|metabolic inflamm|cGAS|STING'),
('Q01B',r'heterogen|subtyp|cluster.{0,25}(?:diabet|metabol)|phenotyp'),('Q01A',r'incident type 2|incident diabet|diabetes risk|predict.{0,45}diabet|diabet.{0,45}predict|early detect|prediabet|screening'),
('Q37B',r'self.management|education|digital|telehealth|remote care|mobile health'),('Q09',r'artificial intelligence|machine.learning|deep.learning|foundation model|language model|\bAI\b'),
('Q41',r'genom|GWAS|epigen|genetic|proteom|metabolom|transcriptom|single.cell'),('Q05',r'islet|beta.cell|β.cell|ß.cell|alpha.cell|α.cell|insulin secret|pancrea'),
('Q39',r'epidemiol|prevalence|incidence|mortality|population|social determinant|health equit|disparit|health policy|disease burden|prevention|public health'),('Q13C',r'obes|weight management|diabetes remission')]
def main():
 r=ROOT;folder=r/'规则与说明/ADA入库_2026-11-17';d=json.loads((r/'原始资料/ADA2026/官方程序/ADA程序结构化.json').read_text());sm={x['session_id']:x for x in d['sessions']};c=sqlite3.connect((r/'数据库/marketing.db').as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
 defs={x['legacy_topic_id']:dict(x) for x in c.execute('SELECT t.*,v.width_status,v.boundary_text,v.scope_gaps FROM research_topics t JOIN v_cds_quantity_topic_counts v USING(topic_id)')};boards=[dict(x) for x in c.execute("SELECT * FROM research_topics WHERE conference_id='CDS2026' AND node_type='board'")];c.close()
 bykey=defaultdict(list);academic=[];excluded=[]
 nonacademic=re.compile(r'^(?:Introduction|Question|Closing|Welcome|ADA Chief|Panel Discussion$|Networking|Saturday General|Sunday General|Monday General|Session Break|Discussion$|Rebuttal$)',re.I)
 types={'Oral Presentations','Symposium','Debate','Panel Discussion','Special Lectures and Addresses','General Poster Session','Late Breaking Poster Session','ePoster Theater','Ask the Expert'}
 for x in d['items']:
  ss=sm[x['session_id']];x['eligible_academic']=bool(x['code']) or (ss['type'] in types and not nonacademic.search(x['title']) and x['title']!='Pathway Symposium: TBD')
  if x['eligible_academic']:
   key=x['code'] or f"TALK-{x['source_order']+1:04d}";bykey[key].append(x)
  else:excluded.append(x['source_order'])
 reports=[]
 for key,occ in bykey.items():
  # 同号海报优先保留普通海报原始记录，电子海报展示作为发生记录附存。
  primary=min(occ,key=lambda x:(sm[x['session_id']]['type']=='ePoster Theater',x['source_order']));title=primary['title'];session=sm[primary['session_id']];assigned=None;basis=None;method='title_rule';matches=[]
  for code,pat in RULES:
   if re.search(pat,title,re.I):matches.append(code)
  if matches:assigned=matches[0];basis=f'题名命中“{defs[assigned]["name"]}”规则；按器官/主要问题优先，只保留一个主议题。'
  if 'Embrace the Possible: Transforming' in title:assigned='Q37B';method='manual_title_review';basis='题名明确糖尿病照护与教育的未来，暂归教育/自我管理主题；不是对具体数字技术的效果证明。'
  if title.startswith('From Mechanism to Milieu:'):assigned='Q39';method='manual_title_review';basis='题名明确生物医学与社会决定因素的综合议题，暂归公共卫生与人群背景。'
  if not assigned:
   context=session['title'];cm=[code for code,pat in RULES if re.search(pat,context,re.I)]
   if cm:assigned=cm[0];method='session_context_rule';basis=f'题名本身不足；暂按专题“{context}”辅助归入“{defs[assigned]["name"]}”，待逐条校准。'
  if not assigned:basis='题名和所在专题未支持当前规则明确归类，保留待归类，不强行填入综合主题。';method='unclassified'
  fmt='论文发言' if key.endswith('-OR') else '海报报告' if key.endswith('-P') else '晚期突破海报' if key.endswith('-LB') else '大会报告' if session['type']=='Special Lectures and Addresses' else '专题报告'
  gap='仅有2026-04-24页眉版本会前程序；未核最终/实际报告及本条完整结果。规则辅助初分，待人工复核，不作独立研究或领域热度判断。'
  if method=='session_context_rule':gap+=' 本条依赖专题背景，尤其需要核对归类。'
  if len(set(matches))>1:gap+=' 题名同时关联多个方向，其他命中保留交叉标签，不重复计数。'
  if len(occ)>1:gap+=' 同一摘要编号在不同展示场景重复，合并计一次，全部出现位置保留。'
  reports.append(dict(key=key,primary_order=primary['source_order'],occurrence_orders=[x['source_order'] for x in occ],format=fmt,topic_code=assigned,classification_method=method,basis=basis,gaps=gap,cross_tags=list(dict.fromkeys(matches[1:])),title=title))
 counts=Counter(x['topic_code'] for x in reports if x['topic_code']);topics=[]
 for code,n in sorted(counts.items()):
  t=defs[code];topics.append(dict(code=code,name=t['name'],question=t['research_question'],parent_code=t['parent_topic_id'].split(':')[1],width_status=t['width_status'],boundary=t['boundary_text'],gaps='沿用CDS同层次问题边界作ADA初分；会场技术与生物学议题宽窄仍可能不同，跨会议不直接比排名。',report_count=n))
 pages=(r/'原始资料/ADA2026/官方程序/ADA2026_日程.txt').read_text().split('\f');audit=[]
 for i,p in enumerate(pages,1):
  if not p.strip():continue
  status='numbered_session' if re.search('Session Number:',p) else 'unparsed_satellite_or_metadata' if re.search(r'(?:FRIDAY|SATURDAY|SUNDAY|MONDAY), JUNE',p) else 'programme_continuation' if any(i in x['pages'] for x in d['items']) else 'cover_or_other'
  audit.append(dict(page=i,status=status,code_occurrences=len(re.findall(r'\b\d{3,4}-(?:OR|P|LB)\b',p))))
 summary=dict(programme_physical_pages=385,sessions=len(d['sessions']),raw_agenda_items=len(d['items']),academic_occurrences=sum(len(v) for v in bykey.values()),distinct_reports=len(reports),duplicate_occurrences=sum(len(v)-1 for v in bykey.values()),classified_reports=sum(counts.values()),unclassified_reports=sum(not x['topic_code'] for x in reports),nonacademic_agenda_items=len(excluded),coded_reports=len({x['code'] for x in d['items'] if x['code']}),topics=len(topics),formats=dict(Counter(x['format'] for x in reports)),classification_methods=dict(Counter(x['classification_method'] for x in reports)),page_statuses=dict(Counter(x['status'] for x in audit)))
 plan=dict(conference_id='ADA2026',analysis_version='ADA2026:TOPIC-QUANTITY:20261117:v1',source_version='2026-04-24 programme snapshot',summary=summary,reports=reports,topics=topics,boards=boards,page_audit=audit,excluded_orders=excluded,classification_rules=[dict(topic=code,pattern=pat) for code,pat in RULES],scoring_enabled=False,new_collection=False)
 (folder/'ADA入库方案.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
