"""只读旧分类与题名，生成逐项复核方案；所有分流均为显式报告编号，不靠词频或评分。"""
from pathlib import Path
from collections import Counter
import sqlite3,json
ROOT=Path(__file__).resolve().parents[1]
SPLITS={
'H01':[
 ('Q01A','糖尿病发生风险与代谢异常早期识别','哪些临床指标、影像或分子信号有助于识别糖尿病发生及代谢异常风险？','OR_089 OR_096 OR_097 OR_103 OR_122 OR_281 OR_282 OR_287 OR_313 OR_318 OR_322 OR_323 OR_332 OR_338','早期发生风险、筛查与异常识别；不把数据驱动的既有表型分型重复计入。'),
 ('Q01B','糖代谢与肥胖异质性分型','如何区分已有糖代谢异常、糖尿病前期或肥胖人群的不同表型？','OR_031 OR_105 OR_227 OR_230 OR_246 S_147','以异质性或亚型识别为主；兼有风险结局时只保留一个主议题。')],
'H03':[
 ('Q03A','T1D筛查、分型与人群特征','如何识别T1D风险、抗体谱和异质人群？','OR_087 OR_110 OR_329 OR_337 S_024 S_029 S_030 S_031','筛查、人群特征与异质性；不与管理模式同时计数。'),
 ('Q03B','T1D长期与过渡期管理','如何改善T1D儿童、家庭及过渡期的长期管理？','S_033 S_034 S_035 S_045 S_062 S_098 S_219','以长期管理为主；免疫治疗、闭环装置已有独立议题。')],
'H13':[
 ('Q13A','体重维持与减重反弹','减重后怎样维持体重、识别及处理反弹？','OR_193 OR_335 S_060 S_096','非手术为主的维持/反弹；术后路径只进入代谢手术议题。'),
 ('Q13B','代谢手术及术后管理','代谢手术、术后代谢变化和管理路径有哪些议程？','OR_187 OR_236 OR_255 OR_311 S_091 S_092 S_093 S_094','明确手术或术后情境，保留机制与临床报告。'),
 ('Q13C','肥胖综合管理与糖尿病缓解','会议如何讨论肥胖指南、综合管理和糖尿病缓解？','OR_121 S_017 S_019 S_022 S_059 S_149 S_226','综合题名保留宽度提示，不强行解释为具体减重技术。')],
'H22':[
 ('Q22A','糖尿病创面与皮肤损伤修复','哪些细胞、材料与微环境干预用于糖尿病创面和皮肤修复？','OR_001 OR_034 OR_036 OR_124 OR_125 OR_129 OR_131 OR_134 OR_137 OR_146 OR_163 OR_174 S_118 S_121 S_245','以创面修复/皮肤微环境为主，不与足病临床风险或感染管理重复。'),
 ('Q22B','糖尿病足风险与综合管理','怎样识别足溃疡、血管及自主神经相关风险并管理患者？','OR_058 OR_111 OR_126 OR_139 OR_152 OR_156 S_115 S_116 S_117 S_120 S_122','足病风险、预后、围术期与综合管理；创面机制单列。'),
 ('Q22C','糖尿病足感染管理','会议如何安排糖尿病足感染管理？','S_119','仅明确感染管理；菌群或代谢微环境不直接等同感染。')],
'H25':[
 ('Q25A','ASCVD与血管残余风险','如何识别并干预动脉粥样硬化、心血管事件及残余风险？','OR_038 OR_141 OR_157 OR_168 OR_179 OR_223 OR_242 OR_247 OR_264 OR_324 OR_339 OR_340 S_026 S_084 S_085 S_114 S_207 S_229','非明确卒中终点的ASCVD和血管风险；脑血管主题另列。'),
 ('Q25B','卒中风险与二级预防','糖代谢异常与卒中风险、脑血管结局及二级预防有何议程？','OR_109 OR_285 OR_336 PL_08 S_025 S_083','明确卒中/脑血管结局；认知和脑小血管影像主问题仍在脑健康议题。')],
'H32':[
 ('Q32A','甲状腺疾病与糖脂代谢','甲状腺疾病、相关安全性及糖脂代谢怎样相互影响？','OR_039 OR_218 OR_253 OR_297 S_107','明确甲状腺及相关眼病；不把整个内分泌共病并入。'),
 ('Q32B','肾上腺疾病与代谢异常','库欣、原醛和肾上腺相关诊断结局有哪些议程？','OR_104 OR_277 OR_299 S_109 S_110','明确肾上腺疾病及诊断；罕见基因病仍保留特殊病因主归类。'),
 ('Q32C','生殖内分泌与代谢异常','卵巢/性腺、辅助生殖和代谢环境有什么研究安排？','OR_195 OR_229 OR_283 OR_290 OR_302 S_073 S_108 S_150','明确生殖内分泌/性腺，与GDM及母婴编程分开。'),
 ('Q32D','高尿酸与代谢相关损伤','高尿酸及其相关肾损伤、治疗有哪些研究安排？','OR_201 OR_248 OR_254 S_227','明确高尿酸问题，避免隐含在甲状腺/肾上腺标题下。')],
'H33':[
 ('Q33A','糖尿病肌少症与肌肉健康','如何识别、解释及干预糖尿病肌少症和肌肉功能下降？','OR_041 OR_056 OR_127 OR_135 OR_151 OR_165 OR_176 OR_215 OR_266 OR_301 S_148 S_166 S_167 S_168 S_214 S_225 S_255','以肌肉为主的预测、机制和管理；骨终点另列。'),
 ('Q33B','糖尿病骨代谢与骨质疏松','如何理解并管理糖尿病相关骨损伤和骨量变化？','OR_185 OR_268 OR_272 OR_300 S_113 S_222','以骨终点为主，即使发生在减重治疗后也只计此处。'),
 ('Q33C','减重期间身体成分与肌骨保护','减重过程中怎样兼顾肌肉、骨及身体成分质量？','S_211 S_240','明确减重质量或同时讨论肌骨；单独肌少症/骨损伤不重复计入。')],
'H37':[
 ('Q37A','基层区域网络与共同照护','区域网络、医联体和协同服务如何组织糖尿病管理？','OR_060 OR_065 OR_067 OR_068 OR_069 OR_071 OR_072 OR_119 OR_123 S_158 S_160 S_162 S_163 S_165 S_232 S_241','主要问题是服务组织和共同照护，即使使用数字工具仍只计一次。'),
 ('Q37B','数字化自我管理与教育工具','数字工具、平台与教育如何支持糖尿病自我管理？','OR_057 OR_061 OR_070 OR_073 S_065 S_066 S_067 S_068 S_159 S_161','主要问题是数字平台、自我管理、教育工具；区域组织路径另列。')],
'H38':[
 ('Q38A','糖尿病心理行为与困扰干预','如何识别并干预糖尿病/肥胖相关心理问题与困扰？','OR_208 S_061 S_063 S_064 S_191 S_192 S_193','心理行为或困扰为主，不与一般护理教育重复计数。'),
 ('Q38B','糖尿病护理与特殊人群教育','护理、用药自我管理及特殊人群教育有哪些议程？','OR_064 OR_066 S_215 S_216 S_221','护理/教育主问题；即使包含心理支持也不重复进入心理议题。')]
}
BROAD={
'H02':'将单基因、罕见病与特殊病因汇在同一诊断问题下；逐个病例数量少，暂不按每个基因拆分。',
'H05':'同时包含细胞机制、功能评估与保护；同属胰岛/胰腺功能问题，缺少摘要不进一步拆分。',
'H06':'含胰岛再生、干细胞以及题名未明确胰岛终点的移植/囊泡报告；保留集合并逐条提示边界。',
'H09':'AI覆盖多个场景，保留技术综合议题，器官终点更明确者按主问题归类。',
'H11':'药物类型、综合获益和个体化应答同属肠促胰素类综合报告；题名不足以稳定区分，保留较宽提示。',
'H18':'多种细胞与代谢机制共同指向DKD损伤；不把每条分子通路单独建议题。',
'H19':'兼有临床药物结局和探索性干预；标题不能统一解释为成熟临床证据，保留范围提示。',
'H21':'同属糖网损伤机制及探索性治疗，样本为少量综合报告，暂不按治疗材料细拆。',
'H24':'心肌机制与心衰治疗存在临床阶段差异；以心肌损伤/心衰为共同问题保留，展示报告类型。',
'H27':'CKM/MLCK命名、风险和管理同属多器官共病综合问题，不能等同单个具体标志物方向。',
'H29':'含MASH免疫/纤维化机制及靶向治疗总览；部分报告内容重叠需全文核对。',
'H30':'GDM筛查分型与管理均有少量报告，先作为同一病程管理问题保留较宽提示。',
'H31':'母体产后结局、妊娠代偿和子代编程的生命历程跨度较大，保留母婴主题并提示综合范围。',
'H39':'流行趋势、环境与疾病负担属于宏观人群背景；不与单分子研究作同等宽度解读。',
'H40':'是中西医结合的综合年度/方法报告，仅2条，不按单一疗法推断研究重点。',
'H41':'原本是跨疾病、组学及遗传机制综合线索；缺少足够题名边界，不包装为单一具体机制。',
'H42':'包含多种肝脂代谢与细胞器机制，题名不足以稳定细分；保留较宽集合并明确其数量受宽度影响。',
'H44':'认知、低血糖脑效应和脑血管损伤同属脑健康但不完全同质；保留较宽提示。'
}
CROSS={
'OR_101':('Q01A','主要终点是肾移植术后新发糖尿病风险，不是DKD进展预测。'),
'OR_332':('Q39','主要终点为预防队列远期并发症与生命质量，归入人群长期负担背景。'),
'S_033':('Q32A','明确甲状腺共病，按共病对象进入甲状腺议题；T1D只保留交叉背景。'),
'OR_121':('Q33C','明确减重后身体成分变化及其代谢结局，进入减重质量问题。'),
'S_017':('Q33C','题名明确减重与肌肉流失的平衡，进入身体成分质量问题。'),
'S_149':('Q33C','体重管理质量与数量的取舍，暂按减重质量归类，具体组成指标待摘要核对。'),
'S_022':('Q39','肥胖流行病学属于人群分布背景，不计作体重维持/手术。'),
'OR_294':('Q33B','主要损伤终点是肝性骨营养不良，肝来源囊泡保留为机制背景。'),
'OR_308':('Q33B','明确糖尿病骨质疏松终点，菌群/代谢物为机制，不在两个主议题重复计数。'),
'S_248':('Q34','明确精准营养与大数据，不是运动干预。'),
'OR_190':('Q43','研究终点明确为MASLD肝内脂质，归入肝病生活方式干预，运动保留作交叉背景。'),
'OR_048':('Q18','研究明确运动改善DKD的肌肉代谢机制，按DKD损伤问题归类，运动不重复计数。'),
'OR_079':('Q41','是酮体代谢物对葡萄糖转运的机制题名，未说明饮食干预，不据此算作限时进食证据。')
}
SPECIAL_GAPS={
'S_172':'原题为线粒体胶囊移植与重大疾病，未明确糖尿病或胰岛替代终点；保留旧关系待核，不视为已确认胰岛再生证据。',
'OR_233':'题名明确肝来源蛋白和脂质稳态，但未明确靶组织；暂保留原主归类，待摘要确认是否应转肝脏机制。',
'OR_306':'题名为肝肠轴调控，未明确微生物参与；暂保留原关系并标出边界，不能直接推断微生态机制。',
'OR_337':'同时提及T1D发病特征、治疗及并发症；暂以人群特征为主，需摘要确认主要分析问题。',
'OR_227':'同时含肥胖表型异质性及早期预测；本版以表型为主，只计一次，待摘要确认。',
'S_149':'题名未说明质量包含哪些身体成分，当前按质量管理暂归，需报告摘要进一步核对。'
}
def main():
 c=sqlite3.connect((ROOT/'数据库/marketing.db').as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
 old=[dict(t) for t in c.execute('SELECT t.*,v.report_count FROM research_topics t JOIN v_topic_counts v USING(topic_id) ORDER BY t.legacy_topic_id')];assert len(old)==44
 reports=[dict(x) for x in c.execute("SELECT r.*,rc.primary_topic_id,rc.eligible,rc.scope_original,rc.classification_basis,rc.material_id AS classification_material_id,rc.source_locator AS classification_locator FROM v_report_detail r JOIN report_classifications rc USING(report_id) WHERE rc.analysis_version_id='CDS2026:TOPICS:20261116' ORDER BY r.source_report_code")]
 topics=[];decisions={};reviews=[]
 for t in old:
  code=t['legacy_topic_id'];items=[x for x in reports if x['primary_topic_id']==t['topic_id']]
  if code in SPLITS:
   parts=SPLITS[code];claimed=[]
   for q,name,question,codes,boundary in parts:
    codes=codes.split();claimed+=codes;topics.append(dict(code=q,name=name,question=question,parent_id=t['parent_topic_id'],origin=code,width_status='broad' if q=='Q13C' else 'focused',boundary=boundary,gaps='仅按既有题名划定边界，主要终点及证据阶段仍待摘要/报告核验。'))
    for code2 in codes:decisions[code2]=(q,boundary)
   assert set(claimed)==set(x['source_report_code'] for x in items),(code,claimed)
   assert len(claimed)==len(set(claimed))
   reviews.append(dict(old_topic_id=t['topic_id'],old_name=t['name'],old_report_count=t['report_count'],action='split',reason='原议题合并了可按题名明确区分的研究对象或服务问题，拆开后不再让一个组合题目同时覆盖这些问题。',gaps='不同议题仍可能有宽窄差异；拆分不是为了平均报告数。',new_codes=[p[0] for p in parts]))
  else:
   q='Q'+code[1:];wide=code in BROAD;boundary=BROAD.get(code,'保留同一主要疾病/功能/研究问题，已有题名可支持边界；技术方法和机制作为交叉信息，不重复建主议题。')
   topics.append(dict(code=q,name=t['name'],question=t['research_question'],parent_id=t['parent_topic_id'],origin=code,width_status='broad' if wide else 'focused',boundary=boundary,gaps='综合/较宽集合，其数量受主题范围影响；细分需要摘要或报告内容，当前不据题名推断更多。' if wide else '仅题名分类，主要终点、证据阶段和同一研究身份待核。'))
   for x in items:decisions[x['source_report_code']]=(q,boundary)
   reviews.append(dict(old_topic_id=t['topic_id'],old_name=t['name'],old_report_count=t['report_count'],action='retain_broad' if wide else 'retain',reason=boundary,gaps='不强行细拆为单个分子或技术，需后续人工校准。' if wide else '保留题名归类的暂定性质。',new_codes=[q]))
 assert len(topics)==58
 for code,(target,basis) in CROSS.items():assert code in decisions;decisions[code]=(target,basis)
 targetmap={x['code']:x for x in topics};ledger=[]
 for x in reports:
  oldcode=x['primary_topic_id'].split(':')[-1] if x['primary_topic_id'] else None
  target,basis=decisions[x['source_report_code']] if x['eligible'] else (None,x['classification_basis'])
  if target:assert target in targetmap
  decision='excluded' if not target else 'reassign' if x['source_report_code'] in CROSS else 'split_assignment' if oldcode in SPLITS else 'retain'
  ledger.append(dict(report_id=x['report_id'],code=x['source_report_code'],title=x['title_original'],old_topic_id=x['primary_topic_id'],new_code=target,eligible=x['eligible'],scope_original=x['scope_original'],decision=decision,basis=basis,gaps=SPECIAL_GAPS.get(x['source_report_code'],'仅有会前题名，暂无摘要/报告结果；归类需人工校准，不能推断研究独立性或临床成熟度。'),source_material_id=x['material_id'],source_locator=x['source_locator'],old_classification_material_id=x['classification_material_id'],old_classification_locator=x['classification_locator']))
 counts=Counter(x['new_code'] for x in ledger if x['eligible']);assert sum(counts.values())==579;assert set(counts)==set(targetmap)
 for t in topics:t['report_count']=counts[t['code']]
 for rv in reviews:
  rv['flows']=[{'new_code':q,'count':n} for q,n in Counter(x['new_code'] for x in ledger if x['old_topic_id']==rv['old_topic_id']).items()]
 plan=dict(version='CDS2026:TOPIC-QUANTITY:20261117:v1',source_version='CDS2026:TOPICS:20261116',source_snapshot='2026-11-16',reviewed_on='2026-11-17',review_method='AI对44个旧议题及579条已归类题名逐项复核；待人工校准',scoring_enabled=False,denominator=579,topics=topics,scope_reviews=reviews,report_decisions=ledger,summary=dict(original_topics=44,reviewed_topics=44,split_old_topics=len(SPLITS),new_topics=len(topics),reassigned_reports=len(CROSS),broad_topics=sum(t['width_status']=='broad' for t in topics),focused_topics=sum(t['width_status']=='focused' for t in topics)))
 out=ROOT/'规则与说明/CDS议题数量复核_2026-11-17';(out/'议题复核方案.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n');print(json.dumps(plan['summary'],ensure_ascii=False))
 c.close()
if __name__=='__main__':main()
