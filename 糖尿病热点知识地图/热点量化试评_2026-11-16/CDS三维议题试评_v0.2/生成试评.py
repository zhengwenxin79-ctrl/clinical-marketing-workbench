from pathlib import Path
from collections import Counter
import hashlib
import json
import math
import re

ROOT = Path(__file__).resolve().parent
PILOT = ROOT.parent
PROJECT = PILOT.parent
WORK = Path('/Users/zwx/Downloads/营销智能体')
AGENDA = PILOT/'原始材料/CDS_全日程结构化.json'
RAW = PILOT/'原始材料/CDS_详细日程_2026-11-16.html'
RULE = WORK/'clinical-research-v3/SKILL.md'
POOL = WORK/'outputs/20261102_market_intel_template/_work/客户池_v10.json'
CAP = PROJECT.parent/'实习实践/吉因加临床科研能力表.md'


def read(p): return json.loads(p.read_text(encoding='utf-8'))
def write(name, value): (ROOT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def clean(s): return re.sub(r'\s+', '', s)
def fingerprint(p): return hashlib.sha256(p.read_bytes()).hexdigest()


# Explicit, editable clinical-question assignments. Context reports do not count.
TOPICS = [
 dict(id='Q01', name='正常白蛋白尿人群的隐匿性肾小管损伤识别', category='早期识别',
      parent='肾脏损伤与糖尿病肾病', codes=['OR_003'], context=['OR_316','S_123','OR_008'],
      question='在白蛋白尿或肾功能尚未充分提示风险时，能否识别糖尿病患者的肾小管损伤？',
      grouping='仅OR_003直接限定正常白蛋白尿、肾功能保留人群。OR_316虽有尿液损伤指标线索，但题名未限定该人群，放背景而不加分。',
      cues=['题名：正常白蛋白尿且肾功能保留、4046例队列与多尺度转录组（OR_003）'],
      maturity='题名提示临床队列及尿液指标研究；研究设计、结果和验证层次待核。',
      opportunity='优先补证', action='优先核对临床人群、参考标准及独立验证',
      reason='用途明确，且题名给出临床队列线索，可先核对是否提供常规肾指标之外的增量。',
      stage='原始摘要与结果待补', next_evidence=['OR_003的临床参考标准、入排及组织/体液对应关系','OR_316与OR_003的适用人群差别；不得合并算同指标验证','候选指标相对UACR、eGFR的增量及独立验证'],
      participation='可讨论组织转录信号向尿液/血浆候选标志物的验证设计，并用临床指标作基线；具体核酸、蛋白或菌群路径按原研究样本确认。',
      capabilities=['T01','T02','T03','T04','T10'], fit='有科研连接路径；体液样本与候选指标待确认',
      capability_gap='cfRNA、甲基化细项仍待公司确认；组织转录信号到体液检测的可测性未证明。', priority=1),
 dict(id='Q02', name='胰岛素治疗人群的β细胞衰竭表型分型', category='分型与预测',
      parent='早期识别、分型与风险预测', codes=['OR_031'], context=['S_174','S_175','S_002'],
      question='在接受胰岛素治疗的糖尿病人群中，能否识别不同β细胞衰竭表型，并帮助后续管理分层？',
      grouping='仅OR_031直接限定胰岛素治疗人群与β细胞衰竭表型。糖尿病前期和代谢年龄分型另建Q09/Q10，不共同累计关注度。',
      cues=['题名：胰岛素治疗糖尿病人群、β细胞衰竭表型、数据驱动分型（OR_031）'],
      maturity='有临床人群和数据驱动分型题名；临床特征关联是否能支持管理决策尚未取得结果。',
      opportunity='优先补证', action='优先核对分型能否改变干预或风险判断',
      reason='人群和分型目标具体，适合核对能否从临床特征关联走向后续管理分层。',
      stage='原始摘要与结果待补', next_evidence=['入组糖尿病类型、胰岛素治疗史与β细胞功能指标','各亚型的定义、重复性及独立验证','相对现行分型的增量，以及是否改变管理或干预'],
      participation='可围绕已有临床分型设计组学增量研究，或核对多组学整合建模是否适用。先判断临床指标已能解决什么，再确定新增检测需求。',
      capabilities=['T10','T01','T02'], fit='建模研究相关；是否需要新增分子检测待核',
      capability_gap='6Dmarker等平台的任务与交付需确认；cfRNA/甲基化作为新增变量仍是研究设想。', priority=2),
 dict(id='Q03', name='外周血CD52⁺ NK细胞与T1D进展/缓解分层', category='分型与预测',
      parent='T1D免疫、细胞替代与β细胞保护', codes=['OR_262'], context=['S_029','S_030','OR_110','S_170'],
      question='外周血CD52⁺ NK细胞能否提示T1D疾病进展或缓解，并提供现有指标之外的分层信息？',
      grouping='仅OR_262直接研究CD52⁺ NK细胞。T1D抗体和异质性专题作为相关背景，不当作该亚群的独立支持。',
      cues=['题名：外周血CD52⁺ NK细胞与T1D进展及缓解相关（OR_262）'],
      maturity='题名给出外周血免疫亚群关联线索；尚未读到时间先后、预测性能或独立验证。',
      opportunity='优先补证', action='核对是否超越相关性并形成可测的分层组合',
      reason='外周血亚群和进展/缓解终点具体，适合核对免疫表型与现有临床指标的增量关系。',
      stage='原始摘要与结果待补', next_evidence=['免疫亚群的具体检测方法及参考标准','CD52⁺ NK是横断面关联、纵向预测还是干预结果','相对抗体、C肽等现有指标的增量与外部验证'],
      participation='可讨论单细胞描绘免疫状态、与临床/抗体表型联合建模；如需免疫组库，另核具体检测流程。CD52细胞表型实际检测方法以原研究为准。',
      capabilities=['T03','T05','T06','T10'], fit='免疫状态研究相关；现有指标检测与交付待确认',
      capability_gap='单细胞类别已确认；免疫组库细项待核。不能由转录表达直接替代细胞表面蛋白表型检测。', priority=4),
 dict(id='Q04', name='DKD细胞状态与纤维化来源的单细胞/空间解析', category='其他研究',
      parent='肾脏损伤与糖尿病肾病', codes=['OR_008','OR_143'], context=['OR_128','OR_027'],
      question='DKD纤维化涉及哪些细胞状态与组织位置，能否为后续损伤标志物筛选提供来源依据？',
      grouping='两条均明确采用单细胞与空间转录组研究DKD；人体图谱与纤维化机制保留各自目标。OR_027研究胰岛，器官不同，不计入肾脏议题。',
      cues=['题名：DKD纤维化微环境起源及机制（OR_008）','题名：人类DKD单细胞/空间图谱（OR_143）'],
      maturity='图谱与机制研究入口；尚无本轮已读证据证明可用于体液诊断或监测。',
      opportunity='机制到验证', action='先取得候选细胞/分子，再设计组织到体液验证',
      reason='方法与现有能力类别连接较直接，临床检测用途仍需从图谱发现继续验证。',
      stage='原始摘要与结果待补', next_evidence=['实际样本、平台、病例与对照设计','可复现的细胞状态/候选分子及跨样本验证','能否在尿液或血浆测到，并关联临床终点'],
      participation='可讨论单细胞/空间图谱分析、候选细胞状态与临床病理关联，再筛选可进行体液验证的分子。',
      capabilities=['T03','T04','T10'], fit='技术类别直接相关；平台和具体样本需核对',
      capability_gap='官网确认技术类别，未确认原研究平台与公司流程等价；组织图谱不直接证明体液可测。', priority=7),
 dict(id='Q05', name='达格列净肾脏获益个体差异的标志物预测', category='分型与预测',
      parent='肾脏损伤与糖尿病肾病', codes=['OR_006'], context=['S_090','OR_094','OR_108'],
      question='Ppp1r3g相关信号能否预测达格列净的肾脏获益，帮助区分治疗应答人群？',
      grouping='当前只有OR_006直接提出该分子、药物及预测用途。肾病治疗进展、药效或网状Meta分析不是该标志物的重复支持。',
      cues=['题名：Ppp1r3g、达格列净、获益个体差异及精准预测模型（OR_006）'],
      maturity='题名把机制与预测模型联系起来；模型是否基于患者、是否外部验证尚未知。',
      opportunity='优先补证', action='优先确认预测模型的人体依据和治疗决策价值',
      reason='干预与预测目标具体，若有可验证人体证据，较容易形成明确的分层研究问题。',
      stage='原始摘要与结果待补', next_evidence=['人体/动物/细胞各自证据及实际样本','模型训练、验证、校准及治疗交互证据','Ppp1r3g是组织机制信号还是可实施的临床检测变量'],
      participation='可讨论治疗前后采样、应答分层及组学验证，先确认候选分子实际检测基质和模型用途。',
      capabilities=['T10','T01','T02','T03'], fit='应答分层问题相关；检测路径尚未锁定',
      capability_gap='cfRNA或甲基化不是由该题名直接确认的测量方法；公司具体样本与交付待核。', priority=3),
 dict(id='Q06', name='糖网进展风险的多指标预警与异质性分层', category='分型与预测',
      parent='眼、足、神经与其他并发症', codes=['S_198','OR_007','OR_120'], context=['S_199','OR_175','OR_177'],
      question='哪些指标组合能识别糖尿病视网膜病变易感或进展风险，并补充现有临床评估？',
      grouping='围绕风险预警用途聚合多指标模型、代谢物纵向关联与极端表型分析。不同方法不是一个模型的三次验证；OR_007同时涉及肾病，保留次级标签。',
      cues=['题名：多维度标志物风险预警（S_198）','题名：代谢物与视网膜/肾病发生发展的纵向关联（OR_007）','题名：极端表型与易感/耐受特征（OR_120）'],
      maturity='有纵向、建模题名线索；终点、增量表现、标志物组成及独立验证待核。',
      opportunity='优先补证', action='核对模型组成、外部验证和临床增量',
      reason='临床预警用途清楚，但目前尚不知道哪些指标属于公司可参与的分子检测。',
      stage='原始摘要与结果待补', next_evidence=['模型的指标组成与临床终点定义','代谢物关联能否形成前瞻预测，时间窗口及验证','相对眼底/临床基线模型的增量、校准与决策效用'],
      participation='可讨论分子指标与已有临床风险模型联合验证；若主要为影像或常规指标，先作为对照/基线，不强行配置组学检测。',
      capabilities=['T10','T14','T15'], fit='建模可连接；分子检测类别待确认',
      capability_gap='蛋白组类别已确认但具体服务待核；代谢组仅本地线索，不能按题目直接承诺交付。', priority=5),
 dict(id='Q07', name='孕早期GDM风险预测的临床指标与验证', category='早期识别',
      parent='妊娠、儿童与老年等人群', codes=['S_074','OR_274'], context=['S_072','OR_304'],
      question='孕早期指标能否提前识别GDM风险，并提供可操作的干预窗口？',
      grouping='直接纳入孕早期预测综述及METS-IR双中心队列题目。OR_304虽含诊断基因，但题名未明确孕早期采样，暂作分子线索背景。',
      cues=['题名：孕早期GDM预测进展（S_074）','题名：METS-IR、非线性与阈值效应、中国双中心队列（OR_274）'],
      maturity='题名提示孕早期双中心队列；不等于完成外部预测验证或已证实临床效用。',
      opportunity='先核临床增量', action='先核采样孕周、基线模型及干预窗口',
      reason='早期用途明确，但现有直接报告主要为临床指标，新增分子检测需求还需证明。',
      stage='原始摘要与结果待补', next_evidence=['采样孕周、GDM诊断标准及随访完整性','双中心是合并样本还是独立验证','与现有风险模型比较及新增分子指标的增量空间'],
      participation='可用METS-IR等临床指标建立对照模型；确认存在增量空间后，再讨论孕期体液组学的独立验证设计。',
      capabilities=['T10','T01','T02'], fit='临床基线场景明确；新增检测价值待证',
      capability_gap='没有现有题名证据证明公司技术可替代该临床评分；孕期样本适配与具体交付需另核。', priority=6),
 dict(id='Q08', name='CKM 0–2期的循环标志物与心肾结局预测', category='分型与预测',
      parent='心脑血管、血脂与临床结局', codes=['OR_333'], context=['S_151','S_229'],
      question='CKM早期的循环标志物，能否预测后续心肾结局并支持风险分层？',
      grouping='OR_333直接提出分期、循环标志物和结局。CKM共识与大会精粹作为背景，不能算该指标组合的独立验证。',
      cues=['题名：循环生物标志物、CKM 0–2期、前瞻性队列（OR_333）'],
      maturity='题名给出前瞻性队列线索；具体标志物、样本、性能及验证尚未取得。',
      opportunity='先核指标组成', action='取得指标清单后再判断检测参与环节',
      reason='用途与临床终点具体，但尚不能判断循环标志物是常规项目、蛋白还是核酸。',
      stage='原始摘要与结果待补', next_evidence=['循环标志物名称、样本类型和检测方法','CKM分期、人群、随访及结局定义','相对常规风险工具的增量及独立验证'],
      participation='先核对指标组成及现有检测方案，再判断是否需要分子检测或多组学模型增量。',
      capabilities=['T10'], fit='风险建模方向相关；检测技术尚待识别',
      capability_gap='没有直接依据将“循环标志物”归为cfRNA、甲基化或蛋白组；应取得原始指标清单。', priority=8),
 dict(id='Q09', name='糖尿病前期精准分型与个体化干预选择', category='分型与预测',
      parent='早期识别、分型与风险预测', codes=['S_147'], context=['S_237','OR_313','S_002'],
      question='糖尿病前期能否通过分型选择更适合的干预，而非对所有人使用同一策略？',
      grouping='仅S_147明确把糖尿病前期、分型与个体化干预相连。干预后转归预测及一般多组学生活方式研究暂作背景。',
      cues=['题名：糖尿病前期精准分型及个体化干预（S_147）'],
      maturity='当前为专题报告题目；未取得亚型定义、研究结果或干预分层效用。',
      opportunity='先核分型效用', action='取得分型方案及对应干预证据',
      reason='问题针对糖尿病前期干预选择，但现有资料仅有专题题名，先确认有无具体研究与可检验增量。',
      stage='原始摘要与结果待补', next_evidence=['亚型定义、输入变量和适用人群','亚型间的干预效应差异与独立验证','相对常规风险分层的临床增量及成本'],
      participation='可讨论对已有前期分型加入分子变量的增量验证；先确认原方案是否需要新的检测。',
      capabilities=['T10','T01','T02'], fit='分型研究相关；新增分子检测需求待核',
      capability_gap='不能从专题题目推定采用cfRNA或甲基化；需要明确输入变量与公司样本适配。', priority=9),
 dict(id='Q10', name='代谢年龄分型与T2D白蛋白尿分层的跨人群验证', category='分型与预测',
      parent='早期识别、分型与风险预测', codes=['OR_105'], context=['OR_246','S_147'],
      question='基于代谢年龄的T2D分型，能否在不同人群中稳定区分白蛋白尿分层或肾损伤风险？',
      grouping='仅OR_105直接采用代谢年龄加速残差并关联白蛋白尿分期。OR_246虽为外部验证题目，但人群/终点不同，不合并。',
      cues=['题名：代谢年龄加速残差、T2D分型、白蛋白尿分期、中美双人群验证（OR_105）'],
      maturity='题名包含跨人群验证表述；尚未核实是否预测未来风险、是否独立外部验证。',
      opportunity='优先补证', action='核对双人群设计及相对临床模型的增量',
      reason='人群、分型变量与肾脏终点较具体，跨人群表述值得优先核对；不能由题目直接认定成熟。',
      stage='原始摘要与结果待补', next_evidence=['代谢年龄的输入指标和训练方法','中美人群的建模/验证关系及分型稳定性','白蛋白尿为横断分期还是纵向结局，及相对临床模型的增量'],
      participation='可讨论分型模型与肾脏临床终点关联分析；只有证明分子变量有增量时才扩展新的检测组合。',
      capabilities=['T10','T14','T15'], fit='建模方向相关；标志物类别待核',
      capability_gap='代谢年龄不自动等于代谢组；需确认实际变量，平台类别和可交付范围分别核实。', priority=4)
]


def generate():
    raw = read(AGENDA)
    bycode = {r['code']:r for r in raw['items'] if r['code']}
    academic = [r for r in raw['items'] if r['kind'] in ['大会报告','专题报告','论文发言']]
    existing_pool = read(POOL)
    pool_rows = next(s['rows'] for s in existing_pool['sheets'] if s['name']=='1_客户池')
    pool_names = {clean(str(v)):r for r in pool_rows for k,v in r['cells'].items() if k.startswith('B')}
    cap_lines = {}
    for line in CAP.read_text(encoding='utf-8').splitlines():
        m = re.match(r'\| (T\d+) \|', line)
        if m:
            cells = [v.strip() for v in line.strip('|').split('|')]
            cap_lines[m[1]] = {'id':m[1], 'name':cells[1], 'status':cells[2].replace('**',''), 'local_source_line':line}
    topics = []
    people = {}
    used = {}
    for spec in TOPICS:
        t = dict(spec)
        reports = []
        for code in t['codes']:
            assert code not in used, 'Primary assignments must be unique'
            used[code] = t['id']
            r = dict(bycode[code])
            reports.append(r)
            for p in r['people']:
                # Keep name AND institution together; meeting speakers are not assumed PIs.
                key = clean(p['name'])+'|'+clean(p['institution'])
                if key not in people:
                    match = pool_names.get(clean(p['name']))
                    people[key] = dict(id='P'+str(len(people)+1).zfill(2), name=clean(p['name']), institution=p['institution'],
                        role_status='日程确认报告人；是否课题负责人/通讯作者待核', profile_url=p['profile_url'],
                        topics=[], report_codes=[], evidence=[], customer_pool_match=bool(match),
                        customer_pool_row=match['row'] if match else None, total_score=None, grade=None,
                        rating_status='待评级', head_pi_status='待核实',
                        dimensions=[
                            dict(name='研究方向契合度',maximum=30,score=None,status='方向线索可见，长期主攻方向与技术需求待核',basis='现有报告题名与公司能力底表可支持问题关联；未完成PI主攻方向和具体交付核实。'),
                            dict(name='学术产出质量',maximum=25,score=None,status='资料不足',basis='本轮已读取资料中无可供该报告人评分的近三年逐篇核实论文及IF口径。'),
                            dict(name='科研转化潜力',maximum=25,score=None,status='资料不足',basis='报告题名不是该报告人主持基金、可用队列规模或牵头RCT角色的证明。'),
                            dict(name='平台资源禀赋',maximum=20,score=None,status='仅单位可见',basis='日程可核单位；科室排名、个人任职与实际资源需分别确认，不由医院名称补分。')])
                person = people[key]
                if t['id'] not in person['topics']:person['topics'].append(t['id'])
                person['report_codes'].append(code)
                person['evidence'].append({'code':code,'title':r['title'],'source_url':r['source_url'],'reading_level':'已存原始日程，计划题名级'})
        t['reports'] = reports
        t['context_reports'] = [bycode[c] for c in t['context']]
        t['n_reports'] = len(reports)
        t['kind_counts'] = dict(Counter(r['kind'] for r in reports))
        t['n_institutions'] = len({clean(p['institution']) for r in reports for p in r['people']})
        t['n_sessions'] = len({r['session_id'] for r in reports})
        t['n_speakers'] = len({clean(p['name'])+'|'+clean(p['institution']) for r in reports for p in r['people']})
        t['key_report_units'] = sum(3 if r['kind']=='大会报告' else 2 if r['kind']=='专题报告' else 0 for r in reports)
        t['capabilities'] = [cap_lines[x] for x in t['capabilities']]
        t['customer_score'] = None
        t['customer_status'] = '缺少完整V3评级，暂不计算加权分'
        t['clinical_evidence_status'] = '仅有计划题名，成熟度待评'
        topics.append(t)
    review = read(ROOT/'PI联网评级.json')
    overlay = {p['id']:p for p in review['people']}
    for p in people.values():
        p.update(overlay[p['id']])
    for t in topics:
        related = [p for p in people.values() if t['id'] in p['topics']]
        rated = [p for p in related if p['grade'] is not None]
        missing = [p for p in related if p['grade'] is None]
        t['customer_grade_counts'] = {g:sum(p['grade']==g for p in rated) for g in 'ABCD'}
        t['customer_known_subtotal'] = round(sum({'A':3,'B':2,'C':1,'D':0}[p['grade']]*p['total_score']/100 for p in rated), 3) if rated else None
        t['customer_score'] = t['customer_known_subtotal'] if not missing else None
        t['customer_status'] = '覆盖完整；基于公开资料AI暂评' if not missing else ('已评级贡献小计；尚非完整议题分' if rated else '缺少完整个人评级，保留缺失')
        t['customer_missing_names'] = [p['name'] for p in missing]
        t['customer_a_density'] = round(t['customer_grade_counts']['A']/len(related),3) if not missing else None
    weights = {'相关报告量':40, '重点报告覆盖':25, '报告机构覆盖':20, '专题覆盖':15}
    keys = ['n_reports','key_report_units','n_institutions','n_sessions']
    maxima = {k:max(t[k] for t in topics) for k in keys}
    variants = {'默认':[40,25,20,15], '等权':[25,25,25,25], '偏报告量':[50,20,15,15]}
    for t in topics:
        t['attention_components'] = []
        t['normalized_components'] = []
        for (label,w),k in zip(weights.items(),keys):
            normalized = math.log1p(t[k])/math.log1p(maxima[k]) if maxima[k] else 0
            t['normalized_components'].append(normalized)
            t['attention_components'].append(dict(name=label,raw=t[k],sample_max=maxima[k],weight=w,score=round(normalized*w,2)))
        t['attention_score'] = round(sum(x*w for x,w in zip(t['normalized_components'],weights.values())),1)
        t['attention_basis'] = '本轮10个候选议题的会前日程相对关注度；AI试行权重，非年度热度或结果强度'
        t['scenario_scores'] = {n:round(sum(x*w for x,w in zip(t['normalized_components'],ws)),1) for n,ws in variants.items()}
        t['scenario_ranks'] = {}
    for scenario in variants:
        for t in topics:
            # Competition ranking, using the displayed precision so ties stay ties.
            t['scenario_ranks'][scenario] = 1+sum(s['scenario_scores'][scenario]>t['scenario_scores'][scenario] for s in topics)
    for t in topics:
        t['attention_rank'] = t['scenario_ranks']['默认']
        t['people_ids'] = [p['id'] for p in people.values() if t['id'] in p['topics']]
        t['rated_speakers'] = sum(p['grade'] is not None for p in people.values() if t['id'] in p['topics'])
    topics.sort(key=lambda t:(-t['attention_score'],t['id']))
    source_files = [AGENDA,RAW,RULE,POOL,CAP,ROOT/'PI联网评级.json']
    ledger = dict(as_of='2026-11-16',version='v0.2',status='AI试评；待导师校准',external_collection=True,
        input_files=[dict(path=str(p),sha256=fingerprint(p)) for p in source_files],
        source_scope=dict(total_sessions=len(raw['sessions']),total_rows=len(raw['items']),numbered_reports=sum(bool(re.fullmatch(r'(S_|OR_|PL_)\d+',r['code'])) for r in raw['items']),academic_reports=len(academic),selected_reports=len(used),selected_topics=len(topics),unselected_academic_reports=len(academic)-len(used),speakers=len(people),complete_v3_ratings=sum(p['grade'] is not None for p in people.values()),customer_pool_name_matches=sum(p['customer_pool_match'] for p in people.values()),original_results_read=0),
        scope_note='在已存完整日程中选择10个临床问题做颗粒度试评；不是全会重分类。未选条目不等于无关或低热。',
        rating_rule=dict(source=str(RULE),version='V3.2',dimensions=[['研究方向契合度',30],['学术产出质量',25],['科研转化潜力',25],['平台资源禀赋',20]],grades={'A':'90–100','B':'75–89','C':'60–74','D':'<60'},adaptation='仅将契合度示例的病种换为糖尿病，分项满分与等级阈值保留；无足够证据不生成总分。',customer_aggregation='同议题按人员去重，Σ等级权重×总分/100（A3/B2/C1/D0）。D另列；资料缺失不计0。只有全员完成四维暂评才给议题完整分，否则只列已评级贡献小计与覆盖率。不是百分制、没有强/弱阈值。',head_pi='客户综合高分不是独立学术头部结论；还需相关方向的代表工作、牵头角色和任职证据。',confidence_labels='使用“日程记录/本地资料/待核”；不将证据核实ABC混同客户ABC。'),
        method=dict(weights=weights,maxima=maxima,variants=variants,normalization='分项=权重×log(1+原始量)/log(1+本轮10题最大量)；总分取未舍入分项之和后保留1位小数。重点报告量=3×大会报告+2×专题报告，论文发言在报告总量中计数。',assumptions=['原始报告编号去重；不同编号尚不能视为独立研究。','机构按日程原名去空白计数，未当作独立团队或外部验证。','多个相关性分项共同反映覆盖，存在相关性；权重和议题边界仍需导师校准。','不计PI会内角色代理分，避免替代V3客户评级。','背景报告不参与计数；一条报告本轮仅有一个主议题。','无跨年对照和已读结果，本轮不判断升温、持续热点或临床可用。','公司参与建议为研究环节初判，不纳入关注度分。']),
        source_review=[
            dict(source=str(POOL),result='客户池按可动性分档，不是V3四维评级；仅做姓名精确匹配，所选报告人未命中。'),
            dict(source=str(PROJECT.parent/'实习实践/代谢领域知识库/04 研究团队与客户画像地图.md'),result='研究入口地图，不含所选14位报告人的完整V3评分；既有团队线索未改写为客户需求。'),
            dict(source=str(WORK/'outputs/20261104_customer_rating/医学科研情报工作台_客户评级版.html'),result='资金/机构联动工作台，不含所选报告人的完整四维评级。'),
            dict(source=str(WORK/'clinical-research-v3/examples/peng_linyi_example.html'),result='示例报告，不是本届CDS所选报告人的评级证据；不导入示例分数。')],
        next_review=['确认10个议题的范围与背景报告边界，特别是不同人群是否还需拆分。','校准关注度权重；单报告问题保留为候选，不因临床问题明确即称热点。','优先补肖新华、匡洪宇等人的本人基金原始负责记录，并核实青年报告人对应的实际PI；补齐后重算客户机会。','取得原始摘要/报告结果后评价Biomarker验证成熟度与临床增量。','公司技术人员确认样本、当前版本和可交付范围；确认后再决定Skill封装。'],
        unchanged_scope=['正式网站、正式源数据和GitHub','既有v0.1榜单与ADA内容','采集配置与定时任务','未创建热点量化Skill包'])
    ledger['version'] = 'v0.2 · PI联网补证'
    ledger['pi_review'] = review['meta']
    ledger['rating_rule']['adaptation'] += ' 官方省级教育科研项目仅在8—13档作同层级参照，需导师确认；本人官方简介支持保守基金档，但未核个人国自然项目号仍列缺口。'
    ledger['source_review'].append(dict(source=str(ROOT/'PI联网评级.json'),result='本轮14人联网补证、35篇代表作逐篇PubMed核实、官方讲者/机构/省级基金与期刊指标；全评分5人，部分评分9人。'))
    payload_data = dict(meta=ledger,topics=topics,people=list(people.values()),pi_sources=review['sources'])
    write('试评数据.json',payload_data)
    write('材料覆盖.json',ledger)
    write('PI评级与缺口.json',list(people.values()))
    write('PI待评级.json',[p for p in people.values() if p['grade'] is None])
    write('议题逐条归属.json',[dict(code=r['code'],title=r['title'],primary_topic=used.get(r['code']),status='本轮直接纳入' if r['code'] in used else '本轮未选入；未作低相关判断',source_url=r['source_url']) for r in academic])
    (ROOT/'PI评级规则快照.txt').write_text(RULE.read_text(encoding='utf-8'),encoding='utf-8')
    payload=json.dumps(payload_data,ensure_ascii=False).replace('</','<\\/')
    template=(ROOT/'页面模板.html').read_text(encoding='utf-8')
    (ROOT/'index.html').write_text(template.replace('__DATA__',payload),encoding='utf-8')
    print(json.dumps(ledger['source_scope'],ensure_ascii=False))


if __name__ == '__main__':generate()
