"""Audit the supplied Biomarker batch against existing local source titles. No collection.
Imported tables are preserved; reviewed projections live in two additive audit tables.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import sqlite3,json,hashlib,re
ROOT=Path(__file__).resolve().parents[1]
VERSION='BM:LOCAL-SOURCE-AUDIT:20261118:v1'
def encoded(x):return json.dumps(x,ensure_ascii=False,separators=(',',':'),sort_keys=True)
def digest(x):return hashlib.sha256(encoded(x).encode()).hexdigest()
# Only summarize what the stored titles explicitly support. All unconfirmed details remain in imported rows.
CONTEXTS={
'CTX_ISLET_T1D_DIFF':('分型与预测','1型糖尿病','中国1型糖尿病人群；细分人群待核','题名未给出样本基质','异质性与抗体检测；IA-2A/ZnT8协同价值'),
'CTX_ISLET_T1D_REL':('早期识别','1型糖尿病','T1D患者一级亲属','题名未给出样本基质','基于胰岛自身抗体的亲属筛查'),
'CTX_RETINA_DR':('分型与预测','糖尿病视网膜病变','题名未限定病程和具体人群','题名未列出标志物及样本','多维度标志物风险预警模型'),
'CTX_SARCO_T2D':('早期识别','糖尿病肌少症','糖尿病肌少症患者','血清（题名明示）','血清代谢组学特征与代谢物筛选'),
'CTX_CYTO_LIFESTYLE':('分型与预测','糖代谢异常','不同糖代谢人群','血清（题名明示）','细胞因子表达与生活方式干预后的转归'),
'CTX_CKM_EARLY':('分型与预测','心血管-肾脏-代谢综合征','早期CKM 0–2期人群','循环标志物；具体基质待核','心肾代谢结局风险研究'),
'CTX_OSTEO_DKD':('其他','糖尿病肾病','题名未限定人群细节','题名未说明基质','骨钙素人群关联与肾保护潜力探索'),
'CTX_PPP1_SGLT2I':('分型与预测','达格列净肾脏获益','题名未限定人群或实验模型','题名未说明组织/PBMC等样本','Ppp1r3g机制与获益差异预测模型'),
'CTX_DRDKD_METAB':('分型与预测','糖尿病视网膜与肾脏病变','题名未限定人群细节','代谢物；基质待核','病变发生发展异质性的纵向关联'),
'CTX_BETA_MORTALITY':('分型与预测','糖代谢与长期死亡','全国代表性队列（题名明示）','空腹与负荷后指标；基质待核','胰岛素抵抗/β细胞功能与死因别死亡'),
'CTX_BETA_DRUG_RESP':('分型与预测','2型糖尿病','中国不同β细胞功能分层患者','β细胞功能测量方式待核','Soli-D疗效安全性结果解读'),
'CTX_CUMGLY_GDM':('分型与预测','妊娠与产后糖代谢','中国孕妇队列（题名明示）','妊娠期累积血糖；计算方式待核','母亲产后4–7年糖代谢结局关联'),
'CTX_LIPID_SARCO':('分型与预测','肌少症','中国老年2型糖尿病人群','非HDL-C/HDL-C；采样条件待核','比值对肌少症的预测研究'),
'CTX_1HPG_SCREEN':('早期识别','糖尿病','年轻肥胖中国成人','1小时血糖；负荷/餐后条件待核','1小时血糖标准的早期筛查研究'),
'CTX_GCK_GDM':('分型与预测','GCK-MODY与妊娠期糖尿病','GDM女性；另有GCK/FOXP3家系报道','题名未说明测序方法/样本','筛选标准与识别模型；遗传变异家系线索'),
'CTX_TYG_DKD':('分型与预测','糖尿病肾脏病','题名未限定人群细节','TyG；计算公式与采样条件待核','TyG指数相关性研究'),
'CTX_TYG_PTDM':('分型与预测','肾移植术后糖尿病','肾移植术后人群','TyG；采样时间待核','早期发病风险预测研究'),
'CTX_VFA_UHR_T2D':('分型与预测','2型糖尿病','非肥胖人群；BMI阈值待核','CT内脏脂肪面积联合UHR','联合预测与风险分层研究'),
'CTX_ABSI_T2D':('分型与预测','2型糖尿病','NHANES/CHARLS人群；细分条件待核','TyG-ABSI；具体算法待核','横断面及前瞻性队列关联研究'),
'CTX_MASLD_LIVER':('其他','代谢功能障碍相关脂肪性肝病','小鼠（题名明示）','肝脏小分子代谢物（题名明示）','司美格鲁肽与替尔泊肽干预比较'),
'CTX_APPL1_MODY':('分型与预测','青少年起病的成人型糖尿病14型','1例病例（题名明示）','APPL1变异；变异位点/方法待核','基因突变病例报道'),
'CTX_PRED_EGFR':('分型与预测','糖尿病前期','糖尿病前期人群；队列细节待核','聚类输入指标与算法待核','亚型划分与肾小球滤过功能损害关联'),
}
ENTITY_OVERRIDES={
'BM_1H_PG':dict(name_zh='1小时血糖指标',standard_name='1-hour glucose (sampling condition pending)',entity_note='题名仅称1小时血糖，尚未确认负荷试验或餐后采样，暂不沿用餐后/OGTT断言。'),
'BM_HOMA_BETA':dict(name_zh='β细胞功能与胰岛素抵抗指标',standard_name='Beta-cell function / insulin resistance measures',entity_note='指标族线索；题名未给出HOMA公式，不能认定两个来源使用同一指标或固定面板。',biomarker_type='family',is_member_defined=0),
'BM_GCK_MODY_GENETICS':dict(name_zh='GCK-MODY相关遗传与识别线索',entity_note='识别模型与遗传变异来源分开计数；具体变异位点及模型成员待核。'),
'BM_APPL1_GENETICS':dict(name_zh='APPL1变异线索（位点待核）',entity_note='题名仅说明基因突变病例，具体位点、功能及治疗反应待原文。'),
'BM_ISLET_AB':dict(entity_note='抗体指标族；不同报告涉及的抗体组合未核齐，不按同一固定panel或同一检测产品理解。',biomarker_type='family',is_member_defined=0),
}
MATCH_RELATIONS={
'MATCH_01':'method_candidate','MATCH_02':'new_research_hypothesis','MATCH_03':'method_candidate',
'MATCH_04':'new_research_hypothesis','MATCH_05':'new_research_hypothesis','MATCH_06':'method_candidate',
'MATCH_07':'method_candidate','MATCH_08':'method_candidate','MATCH_09':'method_candidate',
'MATCH_10':'method_candidate','MATCH_11':'new_research_hypothesis'}

def main():
 c=sqlite3.connect(ROOT/'数据库/marketing.db');c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
 tables=['biomarkers','biomarker_aliases','biomarker_contexts','biomarker_evidence','biomarker_capability_matches','biomarker_extraction_reviews','biomarker_analysis_runs']
 incoming={t:[dict(x) for x in c.execute('SELECT * FROM '+t+' ORDER BY rowid')] for t in tables}
 raw_hash=digest(incoming);records=[]
 def add(kind,id,original,reviewed,basis):records.append((VERSION,kind,id,digest(original),encoded(reviewed),basis))
 for e in incoming['biomarker_evidence']:
  if e['report_id']:
   source=dict(c.execute('SELECT * FROM v_report_detail WHERE report_id=?',(e['report_id'],)).fetchone());title=source['title_original'];path=source['material_path'];loc=source['source_locator'];mat=source['material_id'];url=source['source_url'];reading='title_only';kind='report'
  else:
   source=dict(c.execute('SELECT * FROM literature_papers WHERE paper_id=?',(e['paper_id'],)).fetchone());title=source['title'];path=source['raw_path'];loc=source['source_locator'];matrow=c.execute('SELECT material_id FROM source_materials WHERE relative_path=?',(path,)).fetchone();mat=matrow[0] if matrow else None;url=source['source_url'];reading='directory_excerpt';kind='paper'
   assert source['reading_level']=='directory_excerpt' and json.loads(source['abstract_json'])==[]
  path_obj=ROOT/path;assert path_obj.is_file(),path
  r=dict(evidence_role='title_mention_only',reading_level=reading,method='方法待原始摘要/全文确认',sample_size_or_cohort=None,result_text='研究题名：'+title,original_excerpt=title,direction='inconclusive',validation_type='unspecified',metric_value_or_interval=None,comparison_method=None,review_status='local_title_checked',reviewer_kind='AI本地题名对照；未取得人工复核记录',has_result_evidence=False,has_external_validation=False,source_kind=kind,source_title=title,source_url=url,raw_path=path,source_locator=loc,material_id=mat,raw_sha256=hashlib.sha256(path_obj.read_bytes()).hexdigest(),study_id=None,independence_status='not_established',unsupported_fields=['原填研究结果','检测平台和测量方法','验证类型','关联方向','性能或效应数字','人工复核状态'])
  add('evidence',e['evidence_id'],e,r,'原始资料仅有题名/目录，不能支撑结果、验证和检测方法；用原始题名及真实定位替代扩写。')
 for b in incoming['biomarkers']:
  zh=next((a['alias_name'] for a in incoming['biomarker_aliases'] if a['biomarker_id']==b['biomarker_id'] and a['language']=='zh'),b['standard_name'])
  r=dict(name_zh=zh,standard_name=b['standard_name'],biomarker_type=b['biomarker_type'],is_member_defined=b['is_member_defined'],review_status='candidate',notes='已对照本地题名的候选指标/研究方向，结果和验证证据待补。',entity_note='组合/特征集的具体成员需回查原文。' if not b['is_member_defined'] else '名称出现不等于用途、采样条件和性能已经验证。')
  r.update(ENTITY_OVERRIDES.get(b['biomarker_id'],{}));add('entity',b['biomarker_id'],b,r,'仅按题名保留名称线索，不继承已复核/临床成熟标签。')
 for x in incoming['biomarker_contexts']:
  category,disease,pop,sample,use=CONTEXTS[x['context_id']]
  r=dict(domain='内分泌代谢',category=category,disease_or_complication=disease,target_population=pop,sample_or_fraction=sample,clinical_use=use,target_outcome='具体终点与性能待原文核对',time_point=None,context_status='provisional',scope_label='题名归纳的研究用途；不是已经验证的临床适应证',translation_status='evidence_needed',priority_reason='先取得可定位的研究结果，再判断验证阶段和临床增益。',evidence_needed=['原始摘要或全文及结果','具体指标/面板成员、样本和检测方法','验证设计及相对现有方法的增益','当前公司交付范围与适配条件'])
  add('context',x['context_id'],x,r,'删除题名未支撑的BMI/病程阈值、样本和队列限定；应用场景保留为研究用途。')
 capability_path='原始资料/WorkBuddy更新_2026-11-18/公司能力底表_2026-11-10.md';text=(ROOT/capability_path).read_text();lines=text.splitlines()
 for m in incoming['biomarker_capability_matches']:
  capid=re.match(r'(T\d+|P\d+)',m['capability_reference'])[1];line_no=next(i+1 for i,line in enumerate(lines) if line.startswith('| '+capid+' |'));line=lines[line_no-1];cells=[x.strip() for x in line.split('|')[1:-1]]
  relation=MATCH_RELATIONS[m['match_id']];confirmed='已确认' in cells[2]
  r=dict(capability_id=capid,capability_reference=cells[1],capability_status=cells[2].replace('**',''),status='pending_review',relation=relation,participating_stage=m['participating_stage'],sample_or_method_fit='具体输入、方法与交付条件待确认',source_and_basis='能力底表仅确认所列布局/线索；该病种、样本和指标用途的适配尚未核实。',capability_source_path=capability_path,capability_source_locator=f'第{line_no}行，{capid}',capability_source_excerpt=line,capability_source_sha256=hashlib.sha256((ROOT/capability_path).read_bytes()).hexdigest(),is_confirmed_application=False,clinical_priority='evidence_needed',proposal_note='新增研究设想，不是原报告已采用的检测方法。' if relation=='new_research_hypothesis' else '方法或分析参与候选；不代表现成病种检测产品。')
  add('match',m['match_id'],m,r,'按公司能力底表逐条核对；原填confirmed/优先标签缺少场景证据，统一保留待适配复核。')
 for review in incoming['biomarker_extraction_reviews']:
  positive=review['outcome_status']=='positive'
  r=dict(outcome_status='title_candidate' if positive else 'pending_content_review',reading_level='title_only' if review['source_kind']=='report' else 'directory_excerpt',basis_detail='题名有候选名称/研究方向；结果、检测方法、验证待补。' if positive else '仅凭题名不能确认无相关标志物；CGM/血糖轨迹等也须按指标范围重新检查。',review_status='local_title_checked')
  add('extraction',review['review_id'],review,r,'本地只有题名证据，纠正全文已读及负向排除断言。')
 for run in incoming['biomarker_analysis_runs']:
  positives=sum(x['outcome_status']=='positive' for x in incoming['biomarker_extraction_reviews']);pending=len(incoming['biomarker_extraction_reviews'])-positives
  r=dict(source_manifest_or_version='原始资料/WorkBuddy更新_2026-11-18/数据库.zip；本地题名对照v1',analysis_window='首轮选定样本；非发表时间窗口',processed_denominator=30,gaps_count=30,input_hash=raw_hash,statistical_metrics=dict(reviewed_title_sources=30,title_candidates=positives,pending_content_review=pending,report_sources=20,paper_sources=10,biomarkers=19,evidence_mentions=24,result_evidence=0,validated_independent_studies=None,external_validation_confirmed=0),rule='题名提及按来源ID去重；报告/论文分列；未处理来源不能记0。')
  add('run',run['run_id'],run,r,'原统计23正7负与实际24正6负不符，且输入hash为占位；改用真实输入指纹，未获取结果均保留缺口。')
 with c:
  c.executescript('''CREATE TABLE IF NOT EXISTS biomarker_review_versions (
version_id TEXT PRIMARY KEY,created_at TEXT NOT NULL,input_sha256 TEXT NOT NULL,rule_text TEXT NOT NULL,is_current INTEGER NOT NULL CHECK(is_current IN (0,1)));
CREATE TABLE IF NOT EXISTS biomarker_record_audits (
version_id TEXT NOT NULL REFERENCES biomarker_review_versions(version_id),record_kind TEXT NOT NULL CHECK(record_kind IN ('evidence','entity','context','match','extraction','run')),record_id TEXT NOT NULL,
original_row_sha256 TEXT NOT NULL,reviewed_json TEXT NOT NULL CHECK(json_valid(reviewed_json)),basis TEXT NOT NULL,PRIMARY KEY(version_id,record_kind,record_id));
CREATE UNIQUE INDEX IF NOT EXISTS uq_bm_current_review ON biomarker_review_versions(is_current) WHERE is_current=1;
CREATE VIEW IF NOT EXISTS v_biomarker_current_audits AS SELECT a.* FROM biomarker_record_audits a JOIN biomarker_review_versions v USING(version_id) WHERE v.is_current=1;
DROP VIEW IF EXISTS v_biomarker_audited_evidence;
CREATE VIEW v_biomarker_audited_evidence AS SELECT e.evidence_id,e.context_id,e.report_id,e.paper_id,
json_extract(a.reviewed_json,'$.study_id') AS study_id,
json_extract(a.reviewed_json,'$.evidence_role') AS evidence_role,
json_extract(a.reviewed_json,'$.reading_level') AS reading_level,
json_extract(a.reviewed_json,'$.result_text') AS result_text,
json_extract(a.reviewed_json,'$.validation_type') AS validation_type,
json_extract(a.reviewed_json,'$.direction') AS direction,
json_extract(a.reviewed_json,'$.review_status') AS review_status,
json_extract(a.reviewed_json,'$.has_result_evidence') AS has_result_evidence,
json_extract(a.reviewed_json,'$.has_external_validation') AS has_external_validation,
json_extract(a.reviewed_json,'$.source_title') AS source_title,
json_extract(a.reviewed_json,'$.source_locator') AS source_locator,
json_extract(a.reviewed_json,'$.material_id') AS material_id,
json_extract(a.reviewed_json,'$.raw_path') AS raw_path,
a.version_id AS audited_version,e.evidence_role AS imported_role,e.validation_type AS imported_validation_type,a.reviewed_json AS audited_json
FROM biomarker_evidence e JOIN v_biomarker_current_audits a ON a.record_kind='evidence' AND a.record_id=e.evidence_id;''')
  previous=c.execute('SELECT input_sha256 FROM biomarker_review_versions WHERE version_id=?',(VERSION,)).fetchone()
  if previous and previous[0]!=raw_hash:raise RuntimeError('Input changed; create a new audit version rather than overwrite this one')
  c.execute('UPDATE biomarker_review_versions SET is_current=0 WHERE version_id<>?',(VERSION,))
  c.execute('INSERT OR IGNORE INTO biomarker_review_versions VALUES(?,?,?,?,1)',(VERSION,datetime.now(timezone(timedelta(hours=8))).isoformat(),raw_hash,'仅按已有本地题名/目录核对；不新增采集，不把研究设想和能力匹配数当热度或成熟度。'))
  c.execute('UPDATE biomarker_review_versions SET is_current=1 WHERE version_id=?',(VERSION,))
  c.executemany('INSERT OR IGNORE INTO biomarker_record_audits VALUES(?,?,?,?,?,?)',records)
 assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not c.execute('PRAGMA foreign_key_check').fetchall()
 c.close()
 out=ROOT/'规则与说明/WorkBuddy更新复核_2026-11-18';out.mkdir(exist_ok=True,parents=True)
 result=dict(result='audited',version=VERSION,records=len(records),counts={kind:sum(r[1]==kind for r in records) for kind in ['evidence','entity','context','match','extraction','run']},result_evidence=0,new_collection=False,published=False)
 (out/'复核执行记录.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
