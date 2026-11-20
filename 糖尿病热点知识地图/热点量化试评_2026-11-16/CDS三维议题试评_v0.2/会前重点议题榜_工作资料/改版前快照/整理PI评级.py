from pathlib import Path
import json,re
R=Path(__file__).resolve().parent
E=R/'联网补证_2026-11-16'
arts={a['pmid']:a for a in json.loads((E/'PubMed合并候选.json').read_text())}
bios={a['id']:a for a in json.loads((E/'讲者官方简介.json').read_text())}
S={}
def src(k,title,url,note='已读取原始来源或官方页面检索缓存；2026-11-16核对'):
 S[k]=dict(id=k,title=title,url=url,reading_note=note,checked_at='2026-11-16');return k
src('ANHUI','安徽2023省自然基金立项名单（官方高校存档，PDF第13页341行）','https://kjc.ahmu.edu.cn/_upload/article/files/bd/fa/54dbe7b249bdad0d2790c793b9e4/5346776a-2282-4df6-aaec-038eaf13a4b8.pdf','PDF已下载；第13页逐行核对黄斌、安徽省立医院、2308085QH261。')
src('USTC','中国科大内分泌与代谢病研究所介绍（2023）','https://ioemd.ustc.edu.cn/2023/1027/c25994a615922/page.htm')
src('HENAN','河南2026高校科研项目立项名单（PDF第41页）','https://xcoss.henan.gov.cn/typtfile/20250731/3d403612a68b4e9a8a05154802815250.pdf','已读官方PDF解析表：26A320037、郑州大学、陈铎；不是国自然。PDF本地下载遇连接错误，保留官方链接。')
src('ZZU','郑大一附院平台说明（高校交流报道）','https://kjc.zut.edu.cn/info/1057/4027.htm')
src('SONG','宋金方官方导师简介（徐州医科大学）','https://yjsxxgl.xzhmu.edu.cn/gmis/%28S%28dd05atdj1somwygnc4gpj3rg%29%29/dsfc/dsfcgrxx/BACE94D5BE4543B7C9FF8E5946B54E0F','导师页与CDS简介均明确主持国自然青年；该会话链接可能失效，另保留CDS官方快照。不据论文致谢补填个人项目号。')
src('JIANGSU','江苏卫健委2025年医院评审通知','https://wjw.jiangsu.gov.cn/art/2025/7/17/art_55461_11604076.html')
src('KUANG','哈医大2022模范教师：匡洪宇个人段落','https://www.hrbmu.edu.cn/info/1018/4911.htm','官方页面缓存已读；多人合辑，仅采用匡洪宇段落；其他人主持20余项课题未归给匡洪宇。现任职另取2026CDS。')
src('SHENBIO','沈洁本人简介（医院2023成果报道）','https://www.sdrmyy.com/v-7-17652.aspx','官方缓存已读：本人主持国自然、市、省等近20项，不能拆成国自然20项；团队国自然数不算个人。')
src('SHENPROJECT','2025四大慢病专项子课题负责人：沈洁','https://www.sdrmyy.com/v-7-18370.aspx','官方缓存已读；明确子课题负责人，不升级总课题PI或多中心RCT牵头。')
src('SHEN3A','顺德医院2023官方招聘：医院三级甲等','https://www.sdrmyy.com/v-7-17357.aspx')
src('SHENALIAS','南医大2025医院更名：顺德医院即第八附属医院','https://news.smu.edu.cn/info/1013/114116.htm')
src('SHENPLATFORM','南医大：顺德医院省临床重点专科及队列（2024）','https://news.smu.edu.cn/info/1013/74446.htm')
src('SHGRANT','上海2025自然基金立项清单（PDF第54页829行）','https://stcsm.sh.gov.cn/cmsres/44/4480172e58ac434b94ace53c09eaf4ad/ff7a13eff6e543718f9b36c8f0991f1b.pdf','官方PDF表已核杨敏、上海五院、25ZR1402433、2025.07—2028.06；与论文基金号交叉匹配。')
src('SHHOSPITAL','上海卫健委2021医院等级复评审（上海一院甲等、五院乙等）','https://www.shanghai.gov.cn/nw49248/20210108/96f121c97bf1425bae479a8ce2abb84b.html')
src('CHENG','上海交大2024泥城队列调查启动','https://www.acem.sjtu.edu.cn/news/85337.html','研究设计和随访参与不等同独立项目或样本所有权。')
src('SIXTH','上海市六院2025预算公开：科室和研究平台','https://www.shanghai.gov.cn/cmsres/6e/6ebb2f416a5840e08de80e8a2f8679e7/d52a83a44520b7bdb121e2675033741a.pdf','糖尿病诊断预防中心、重点实验室和研究所可核；本轮未用未核实TOP5排名。')
src('XIAO','北京协和医院肖新华官方简介','https://www.pumch.cn/department_ims/doctor/detail/4389.html')
src('XIAOTEAM','协和医学院团队介绍（张茜导师页内肖新华段落）','https://yzbss.pumc.edu.cn/basicinfo/tutorinfo/tutordetail/J2009022859','肖新华段落支持牵头队列；页首基金主持人为张茜，不转计肖新华。')
src('PINGSHAN','深圳市政府坪山人民医院资料','https://www.sz.gov.cn/hospital/psxqyy/psrmyy/','标为三级、等级无；2025升三级，三甲为建设目标。按非三甲档暂评，不能把南方医科大学直属自动等同三甲。')
src('NHPLATFORM','南华大学官网：直属附属医院等级','https://www.usc.edu.cn/info/1012/2747.htm')
src('BEIJINGHOSP','北京医保局2026-10三甲医院名录（同仁/协和）','https://ybj.beijing.gov.cn/2020_zwfw/2020_bmcx/202003/t20200309_1682742.html')
src('ZHANGCN','首医大学报2024：张静宜中英文署名、同仁/糖尿病研究所及重点实验室','https://journal03.magtech.org.cn/Jweb_sdykdxxb/CN/10.3969/j.issn.1006-7795.2024.03.004','仅用于身份、机构及研究平台交叉确认，未作为PubMed论文或本人基金主持证据。')
metrics={
 'J Diabetes':(5.9,'2025','https://www.wolterskluwer.com/ja-jp/solutions/ovid/journal-of-diabetes-10761','授权期刊目录，非原出版社；年度注明2025'),
 'Clin Sci (Lond)':(7.3,'2025','https://portlandpress.com/clinsci/pages/impact_and_information','出版社'),
 'Diabetologia':(10.4,'2025','https://diabetologia-journal.org/about-the-journal/overview/','期刊'),
 'J Pharm Anal':(11.2,'2025年度JCR发布口径；2026-06公告','https://en.xjtu.edu.cn/2026-06/23/c_1197607.htm','期刊主办高校；区分JIF11.2与CiteScore12'),
 'BMJ':(55.1,'2025','https://www.bmj.com/about-bmj/publishing-model','出版社；2026出版集团说明同值'),
 'Front Endocrinol (Lausanne)':(5.7,'官网现值，页面未标指标年度','https://www.frontiersin.org/journals/endocrinology','出版社；年度仍待JCR核对；不参与跨期IF累计'),
 'Ren Fail':(3.8,'2025','https://www.tandfonline.com/action/journalInformation?journalCode=irnf20&show=editorialBoard','出版社'),
 'J Hepatol':(40.1,'2025','https://easl.eu/news/easl-journals-ifs-2025/','期刊所属学会2026-06-24公告'),
 'Lipids Health Dis':(6.9,'2025','https://link.springer.com/journal/12944','出版社'),
 'Nat Med':(52.3,'2025（官方期刊组合表现值）','https://www.nature.com/nature-portfolio/about-journals/journal-metrics','本轮官方组合表检索缓存为52.3；第三方出现52.5，未采用。档位>15不受该差异影响。')
}
for k,(v,y,u,n) in metrics.items():src('IF_'+k,k+' IF '+str(v)+' · '+y,u,n)
fullnames={'P01':('Bin','Huang'),'P02':('Mingwang','Zeng'),'P03':('Kang','Lei'),'P04':('Chaolun','Yu'),'P05':('Duo','Chen'),'P06':('Jinfang','Song'),'P07':('Hongyu','Kuang'),'P08':('Baiwei','Mao'),'P09':('Jingyi','Zhang'),'P10':('Jie','Shen'),'P11':('Min','Yang'),'P12':('Di','Cheng'),'P13':('Xinhua','Xiao'),'P14':('Jie','Wan')}
selections={
'P01':['39968673','40718584','40716618'], 'P02':[], 'P03':['40471558'],
'P04':['40979545','40414620','40042920'], 'P05':['38236410','38128823','41710879'],
'P06':['39350964','41923691','42542611','40474205'], 'P07':['39843169','42769213','42851386','43021325'],
'P08':['42289383','42569254'], 'P09':['42723850'],
'P10':['39084473','40403723','38652239','42504991'], 'P11':['42046136','41998543','42012885'],
'P12':['39030266','42297720','39895483','41062131'], 'P13':['42811187','38368766','42612614'], 'P14':[]}
# Only author's OWN affiliations are evidence for identity; list position alone is not corresponding-author proof.
def paper(pid,pm):
 a=arts[pm];f,l=fullnames[pid]
 hits=[(i,u) for i,u in enumerate(a['authors']) if u['first'].replace('-','').replace(' ','').lower()==f.lower() and u['last'].lower()==l.lower()]
 assert len(hits)==1,(pid,pm,hits)
 i,u=hits[0];j=a['journal_abbrev'];m=metrics.get(j)
 return dict(pmid=pm,title=a['title'],journal=a['journal'],journal_abbrev=j,doi=a['doi'],url=a['url'],dates=a['dates'],author_position=f'{i+1}/{len(a["authors"])}',author_role='第一列名作者' if i==0 else ('末位列名作者；通讯身份另核' if i==len(a['authors'])-1 else '列名共同作者；不视为牵头'),matched_author=u,if_value=m[0] if m else None,if_year=m[1] if m else None,if_source_id='IF_'+j if m else None,if_status='已核期刊指标（非单篇质量）' if m else '最新IF未核；不据此提高档位',raw_file=a['raw_file'],identity_review='英文全名与本人所属机构匹配；人工复核。')
# scores and reason strings are editorial pilot judgements within the original Skill bands.
rows={
'P01':dict(role='副主任医师、博士/博士后、硕导（本届CDS简介）',scores=[28,11,11,12],head='青年临床科研负责人线索；未作全国头部结论',
 bases=['DKD早期损伤、转录组和临床指标验证，直接连接T03/T04/T10；具体体液产品待确认。','PubMed确认Journal of Diabetes 2025第一作者，IF5.9进入8—13档；本轮未以未核全篇IF累计加分。','官方省自然名单确认本人青年项目；已发表研究有临床人群与标本，支持8—13档。CDS题名4046例不是已验证可开放队列。','三甲及内分泌代谢研究所、省重点实验室可核，按区域平台11—15档暂评；不把研究所全部资源视作本人可调配。'],
 refs=[['profile'],['PM39968673','IF_J Diabetes'],['ANHUI','PM40718584'],['USTC']],
 gaps=['国家级课题的具体类别、负责人和在研期限；尚不足以按国自然主持1项加档。','最新完整论文清单与IF年度核对；可开放队列、样本使用权及当前合作需求。'],
 grants=[dict(level='省自然青年',name='维生素D调节肾小球内皮细胞糖萼和铁死亡改善糖尿病肾脏病',number='2308085QH261',role='负责人',status='官方名单与论文致谢交叉支持',source_ids=['ANHUI','PM39968673'])],
 action='围绕隐匿肾损伤与组织—体液验证交流；先确认具体采样和独立验证需求。'),
'P02':dict(role='天津医科大学研究生（CDS官方简介）',scores=[23,None,None,None],head='研究生报告人；独立PI与决策角色未确认',
 bases=['数据驱动β细胞衰竭分型连接T10；题名未指明分子检测需求，按18—24档。','限定机构/病种的PubMed检索未定位唯一论文；检索未命中不证明没有SCI。','未找到可归到本人的基金主持、队列权限或试验负责人证据。','当前只知天津医科大学，未确认就读/执业医院和科室；不套用某附属医院资源。'],refs=[['profile'],[],[],['profile']],
 gaps=['英文署名、导师及具体医院/课题组。','本人论文、独立基金或参与角色；分型研究负责人和临床资源联系人。'],grants=[],action='先确认导师或实际课题负责人，保留青年研究者交流入口。'),
'P03':dict(role='医学博士、主治医师；衡阳糖尿病专委会委员兼秘书',scores=[28,11,None,8],head='临床青年研究者；独立课题角色待核',
 bases=['NK细胞、T1D进展/缓解及免疫表型，直接相关单细胞与联合建模研究。','Clinical Science 2025第一作者；IF7.3支持8—13档。简介中的Nat Metab/Nat Commun未逐篇定位到近三年，不直接补分。','官方简介只说“主持及参与”，基金负责人和参与项目未分开；不能据此定独立基金档。','南华大学官网明确附二院为三甲，按6—10档暂评8；未核内分泌科区域排名及本人可调配资源。'],refs=[['profile','PM40471558'],['PM40471558','IF_Clin Sci (Lond)'],['profile'],['NHPLATFORM']],
 gaps=['各基金名称/负责人及本人角色，尤其国自然主持证明。','T1D样本队列及使用权限；最新科室平台和区域专科证据。'],grants=[],action='核对CD52+NK具体检测、患者队列和主管PI后讨论免疫状态验证。'),
'P04':dict(role='广东省人民医院报告人；公开招聘表有内分泌医师拟录用线索，现职待核',scores=[28,16,None,8],head='独立PI与任职层级待核',
 bases=['DKD单细胞/空间图谱直接连接T03/T04，另有微血管病和多组学论文。','J Pharm Anal 2025列名作者3/10，IF11.2进入14—19档；不是以第一/通讯作者计。','无已核本人主持基金、可开放队列及RCT牵头记录；论文合作不替代项目负责人。','三级甲等平台有国家临床研究中心成员单位名录支持；未加未经核对的科室排名分。'],refs=[['profile','PM40979545'],['PM40979545','IF_J Pharm Anal'],[],['PLATFORM_CSU']],
 gaps=['独立基金主持记录、本人职位和研究决策权。','图谱样本来源/获取权限；临床团队负责人及可合作环节。'],grants=[],action='先核对图谱研究团队分工，再讨论组织图谱及候选分子验证。'),
'P05':dict(role='郑大一附院内分泌科主治医师、医学博士（CDS简介）',scores=[28,16,11,8],head='青年课题负责人；全国头部未证实',
 bases=['单细胞/空间DKD图谱、代谢重编程和铁死亡，连接T03/T04及标志物验证。','Diabetologia 2024列名第二作者2/16，IF10.4支持14—19档。','官方省级教育科研项目负责人可核；Diabetologia研究35例DKD治疗前后血浆代谢组，支持省级基金+小临床队列8—13档。','高校来源确认三甲；本轮未核内分泌科全国/区域排名，只取三甲档。'],refs=[['profile','PM38236410'],['PM38236410','IF_Diabetologia'],['HENAN','PM38236410'],['ZZU']],
 gaps=['省级项目在研状态、队列本人职责和开放权限。','是否已有独立国自然、跨中心验证或临床转化项目；最新科室平台证据。'],
 grants=[dict(level='省教育科研',name='靶向抑制IER2相关DKD肾小管铁死亡研究',number='26A320037',role='负责人',status='官方立项名单；不按国自然计',source_ids=['HENAN'])],action='优先核对肾脏单细胞/空间图谱到体液标志物验证的实际项目需求。'),
'P06':dict(role='副主任药师、硕导、江南大学在站博士后（CDS简介）',scores=[28,16,16,8],head='有独立基金的药学研究者；全国头部未证实',
 bases=['代谢病药物应答、遗传多态性和定量蛋白组研究，直接连接应答分层/多组学建模。','J Pharm Anal 2024列名13/15，IF11.2支持14—19档；另核iScience和临床队列论文，不把共同作者改作牵头。','导师页与CDS简介均明确主持国自然青年；已发表10860例回顾队列与前瞻验证线索，支持14—19档。国自然项数未证明≥2，不入20—25档。','江苏卫健委确认江南大学附属医院三甲；药学科室全国排名未核，取6—10档。'],refs=[['profile','PM42542611'],['PM39350964','IF_J Pharm Anal'],['SONG','profile','PM41923691','PM42542611'],['JIANGSU']],
 gaps=['国自然个人立项原件/准确项目号与期限；本轮不将论文全部基金号归本人。','临床数据库与前瞻试验中本人角色、队列开放权限；CDS的Ppp1r3g与已发GSK3B不是同一指标。'],
 grants=[dict(level='国自然青年',name='官方导师与CDS简介明确主持；项目题名待补',number=None,role='主持（至少1项；准确数量待核）',status='官方简介交叉支持；NSFC项目详情待补',source_ids=['SONG','profile'])],action='可优先交流达格列净应答分层、药物基因组学及验证设计；公司具体交付先对齐。'),
'P07':dict(role='内分泌科/内科学主任、二级教授、博导；CDS副主任委员（2026简介）',scores=[27,21,None,13],head='全国学术任职已核；糖网方向牵头项目证据待补',
 bases=['糖网风险模型与分子/临床指标组合，与T10及候选分子验证相关。','BMJ 2025列名8/23，IF55.1支持20—25档；糖网论文有末位署名。高IF合作论文不等于全国头部PI证明。','有临床注册/试验合作及基金致谢，但本人主持项目数仍未获原始负责名单。不能把合辑中其他教师基金或论文致谢基金转给本人。','大学与CDS简介确认科主任、省糖尿病临床研究中心主任和全国任职，按区域知名平台11—15档；无已核TOP5科室排名。'],refs=[['profile','PM42769213'],['PM39843169','IF_BMJ','PM42851386'],['profile','PM43021325'],['KUANG','profile']],
 gaps=['本人NSFC主持记录/项目详情；临床队列和RCT中的中心负责人或总PI角色。','2026CDS糖网模型的原摘要、实际指标和跨中心验证。'],grants=[],action='属于应优先补基金归属的全国学术联系人；可先围绕糖网风险模型和验证需求沟通。'),
'P08':dict(role='2026级内分泌代谢博士研究生，导师王育璠（CDS简介）',scores=[28,11,None,8],head='博士研究生报告人；不视为独立PI',
 bases=['简介明确参与代谢组/蛋白组队列和微血管病早期分层，技术研究契合。','Renal Failure 2026在线发表第一作者，IF3.8支持8—13档；卷期标2026-12，Epub为06-14，分别展示。Materials Today Bio最新IF未核，不据此加档。','已确认参与队列；无本人独立基金或负责人证明，不能因学生身份自动填0。','上海卫健委复评通知将上海一院列在三级甲等：平台暂评8分，不假设学生可独立调配。'],refs=[['profile'],['PM42289383','IF_Ren Fail'],['profile'],['SHHOSPITAL']],
 gaps=['导师/项目PI及本人职责；独立基金情况。','DR/DKD临床队列与AKI机制论文的具体关系、样本与合作权限；Materials Today Bio最新IF。'],grants=[],action='可作青年团队入口；合作与采样权限需同导师/实际PI核对。'),
'P09':dict(role='北京市糖尿病研究所报告人；论文所属首都医大北京同仁医院体系',scores=[27,11,None,12],head='职称及独立PI身份待核',
 bases=['重度糖网极端表型机器学习，直接连接风险建模；现有变量以临床/生化为主，新增组学需求待核。','Front Endocrinol 2026第一作者1/8；官网现值IF5.7支持8—13档，指标年度待JCR复核。','已发712例极端表型及673例社区人群研究；没有本人基金主持证明，队列存在不等于独立负责。','首医大学报中英文署名交叉确认本人同仁/糖尿病研究所与重点实验室，医保局确认同仁三甲；按区域研究平台档暂评12，样本调用权限另核。'],refs=[['profile','PM42723850'],['PM42723850','IF_Front Endocrinol (Lausanne)'],['PM42723850'],['BEIJINGHOSP','ZHANGCN']],
 gaps=['中英文署名已有期刊交叉证明；本人职称/导师/独立PI角色待核。','本人基金主持、队列权限及研究负责人；期刊指标年度。'],grants=[],action='先核对实际课题负责人，讨论模型外部验证和新增检测是否有临床增量。'),
'P10':dict(role='南医大第八附属医院/顺德医院内分泌学科带头人、二级教授、博导',scores=[27,23,16,13],head='区域学科带头人与专项子课题负责人已核；全国头部需具体方向代表工作评议',
 bases=['妊娠代谢风险及代谢病队列/微生态、多组学工作，与早期分层及标志物研究相关。','J Hepatol正式2025、Epub2024，列名4/6，IF40.1支持20—25档；并列明共同作者身份，不把论文当本人单独成果。','本人官方简介明确主持国自然等课题，保守落入至少1项+队列14—19档；专项仅为子课题负责人。NSFC原始详情及准确项数仍需补，不按≥2项加档。','三甲区域医院的省临床重点专科、GCP研究室和区域网络有官方资料，11—15档。门诊人次/全科基金不算本人可直接转化资源。'],refs=[['SHENBIO','SHENPLATFORM'],['PM39084473','IF_J Hepatol'],['SHENBIO','SHENPROJECT','PM40403723'],['SHENPLATFORM','SHEN3A','SHENALIAS']],
 gaps=['本人在研国自然原始记录、项目号和准确项数；当前GDM合作队列的实际权限。','专项子课题设计、是否涉及本人牵头的多中心RCT，以及吉因加可承接的具体样本/检测。'],
 grants=[dict(level='国家级科研',name='国自然主持经历（官方本人简介）；项目题名待核',number=None,role='主持；至少1项口径暂评',status='官方本人简介；尚未查得NSFC原始项目详情',source_ids=['SHENBIO']),dict(level='四大慢病重大专项',name='糖尿病微血管并发症前瞻干预研究',number=None,role='子课题负责人、管理委员会副主任',status='官方医院报道；不升级总PI',source_ids=['SHENPROJECT'])],action='当前完整暂评中优先联系人；围绕早孕风险分层、队列验证和具体分子检测需求对接。'),
'P11':dict(role='复旦附属上海五院内分泌研究者；官方基金负责人和论文末位作者',scores=[26,11,11,4],head='省市基金负责人已核；全国头部未证实',
 bases=['早孕脂质风险指标与代谢调控，临床用途相关；新增组学检测价值仍需论证。','Lipids Health Dis 2026末位7/7，IF6.9支持8—13档；末位不自动等同通讯身份。','上海自然基金官方负责人同名同单位，基金号与论文匹配；1858例妊娠队列支持8—13档，未核NSFC主持。','上海卫健委2021完整正文将上海五院列在三级乙等；未核升级三甲，按非三甲0—5档暂评4。'],refs=[['PM42046136'],['PM42046136','IF_Lipids Health Dis'],['SHGRANT','PM42046136'],['SHHOSPITAL']],
 gaps=['本人职称和通讯作者职责进一步官方核实；当前队列权限和独立国自然情况。','AIP是常规血脂派生指标，新检测需证明在临床基线之上的增量。D级为本Skill暂评，不代表研究无价值。'],
 grants=[dict(level='上海市自然基金',name='APOE通过STRAP介导脂肪产热调控脂肪衰老的作用及机制',number='25ZR1402433',role='负责人',status='官方立项名单与论文基金号一致；2025.07—2028.06',source_ids=['SHGRANT','PM42046136'])],action='保留具体GDM验证合作线索；按Skill暂列D，不因总分将临床队列合作问题删除。'),
'P12':dict(role='上海糖尿病研究所助理研究员、医学博士（CDS简介）',scores=[27,20,None,13],head='临床队列/转化研究执行骨干；独立PI待核',
 bases=['社区/代谢队列、临床表型与样本整合，多指标风险与T10研究相符。','Nat Med 2024列名59/93，IF52.3落20—25档的入门分；另有Sci Bull 2026列名第二作者。Skill原规则无作者排位加权，明示合作论文的局限。','已核队列组织和临床试验合作，不证明独立基金或RCT牵头；BMJ Open论文是研究方案，不能当已完成试验。','官方预算文件确认糖尿病研究所、中心和重点实验室；按区域资源档保守暂评，未用未核TOP5排名。'],refs=[['profile','PM39895483'],['PM39030266','IF_Nat Med','PM42297720'],['profile','CHENG','PM41062131'],['SIXTH']],
 gaps=['本人基金负责记录、队列项目角色和可用资源权限。','是否承担多中心RCT牵头而非执行；科室最新排名原始依据。'],grants=[],action='可讨论社区队列和模型验证实施，预算与决策联系人需要进一步确认。'),
'P13':dict(role='北京协和内分泌主任医师、博导/博士后导师；CDS副主任委员',scores=[28,23,None,13],head='全国学术任职与队列牵头有官方证据；基金档位仍待核',
 bases=['遗传/早期糖代谢异常、母婴队列及尿液组学，与标志物分层和T10研究直接相关。','Nat Med 2026列名19/20，IF52.3进入20—25档；论文属于多中心合作，不将全部试验业绩归个人。','官方资料支持大规模母婴队列牵头；本人国家级课题类别/项数未核为NSFC。相近导师页基金属于张茜，南华大学同名专家基金也不计入。','协和内分泌与国家级学术职务已核，区域平台档暂评13；本轮未取得最新科室全国TOP5原始依据，未上16—20档。'],refs=[['XIAO','XIAOTEAM','PM38368766'],['PM42811187','IF_Nat Med'],['XIAOTEAM','XIAO'],['XIAO','profile','BEIJINGHOSP']],
 gaps=['本人NSFC原始负责人记录、在研项目与项数（不可用南华同名专家替代）。','科室TOP5的最新原始榜单；前期分型项目的具体临床队列及当前合作需求。'],grants=[],action='全国学术联系人优先补证；先交流前期分型/早期风险的临床验证问题，独立基金核实后再计客户总分。'),
'P14':dict(role='南医大深圳坪山医院住院医师（CDS简介）',scores=[23,None,None,4],head='青年临床报告人；独立PI待核',
 bases=['代谢年龄与T2D分型可连接T10，当前只掌握题名与广义方向，18—24档。','英文全名扩展检索发现同名作者，但未定位到本人坪山机构；保留缺失，不认定无SCI。','未核本人独立基金、队列权限及试验角色，不填0分。','市政府资料明确三级且未定甲等，三甲为创建目标；依Skill非三甲0—5档暂评4，未升级为三甲。'],refs=[['profile'],[],[],['PINGSHAN']],
 gaps=['英文署名及本人论文清单、导师/课题负责人。','独立基金和队列角色；医院后续正式等级评审结果。'],grants=[],action='先确认代谢年龄研究的实际PI与数据来源，可保留青年临床联系窗口。')}
src('PLATFORM_CSU','国家临床研究中心成员单位名录','https://ncrcgdxy.csu.edu.cn/xtcx/fzxjhxcydw.htm','确认广东省人民医院、安徽省立医院、郑大一附院等三甲身份；不是科室排名。')
original=json.loads((R/'试评数据.json').read_text())['people'];people=[]
for p in original:
 pid=p['id'];x=rows[pid];sources=[]
 src('BIO_'+pid,p['name']+' · CDS2026官方讲者简介',p['profile_url'],'官方页已读取并存本地快照；当前简介不保证所有基金/论文为近三年。')
 papers=[paper(pid,k) for k in selections[pid]]
 for a in papers:src('PM'+a['pmid'],a['journal']+' · PMID '+a['pmid'],a['url'],'NCBI PubMed XML逐篇核实：题名、期刊、日期、英文全名、本人机构及作者位置；本地保存原始XML。')
 dims=[]
 for old,score,basis,refs in zip(p['dimensions'],x['scores'],x['bases'],x['refs']):
  refs=['BIO_'+pid if v=='profile' else v for v in refs]
  dims.append(dict(name=old['name'],maximum=old['maximum'],score=score,status='有原始来源支持的AI暂评；待人工校准' if score is not None else '本轮已检索，证据仍不足',basis=basis,source_ids=refs))
 complete=all(v is not None for v in x['scores']);total=sum(x['scores']) if complete else None;grade=('A' if total>=90 else 'B' if total>=75 else 'C' if total>=60 else 'D') if complete else None
 grants=x['grants']
 for g in grants:g['source_ids']=['BIO_'+pid if v=='profile' else v for v in g['source_ids']]
 people.append(dict(id=pid,role_status=x['role'],head_pi_status=x['head'],dimensions=dims,total_score=total,grade=grade,rating_status='四维暂评完成' if complete else '部分维度已评分',rating_date='2026-11-16',scored_dimensions=sum(v is not None for v in x['scores']),known_subtotal=sum(v for v in x['scores'] if v is not None),known_maximum=sum(d['maximum'] for d in dims if d['score'] is not None),papers=papers,grants=grants,gaps=x['gaps'],contact_action=x['action'],identity_note='以中文姓名+机构、本人英文全名+作者自身机构共同核对；仍需本人/团队核验。',evidence_status='公开资料AI暂评，未经过人工/本人确认',profile_read=True))
lookup={s['id']:s for s in S.values()}
for p in people:
 for d in p['dimensions']:
  for sid in d['source_ids']:assert sid in lookup,(p['id'],sid)
meta=dict(date='2026-11-16',version='v0.2-PI联网补证',rating_skill='clinical-research-v3 V3.2',complete=sum(p['grade'] is not None for p in people),partial=sum(p['grade'] is None for p in people),grade_counts={g:sum(p['grade']==g for p in people) for g in 'ABCD'},selected_pubmed_papers=sum(len(p['papers']) for p in people),speaker_profiles_read=len(bios),window='2023-11-16至2026-11-16滚动三年；PubMed日期检索后逐篇核对正式年与Epub。已在线但卷期未来的论文标明两类日期，不把未来卷期当今天正式出版。',score_policy='保留30/25/25/20及A90/B75/C60/D<60；证据支持的档内AI暂评，缺证不填0、不归一化成100分。单篇期刊IF用于Skill档位，不等于个人质量；合作作者不计为论文PI。',grant_policy='官方本人简介可支持保守档位；国家基金未取得NSFC原始详情者不填写未核个人项目号，并列待补。省级基金负责人由政府/高校原始清单核对。研究参与与主持分开。',author_policy='按原Skill有高IF论文的规则暂评分，作者排位单独展示；原Skill未要求仅第一/通讯作者计分，本轮没有擅自新增该门槛。',source_confidence='官方单源事实标出来源与局限；未把同域复刻页或同一新闻转载视为两个独立证据。客户等级ABC/D与证据等级分开。',search_limits=['P07初检176条仅取60，扩展检索后已取全176条XML；按全名和本人机构筛入27条身份匹配候选。','P10初检62条取60，后按顺德/第八附院扩展70条；不是完整学术履历审计。','P02初检无命中；P08/P09/P14已用全名扩大检索，P08匹配2条、P09匹配1条，P14仍未唯一定位。','未新采集会议结果或其他会议；补采仅用于14人评级。CDS本届报告仍是日程题名级，科学转化成熟度未重评。','未登录NSFC项目库或向PI求证；官方简介不足以明确个人项目时，科研转化维度保留缺失。','Nature Medicine官方缓存52.3与第三方52.5存在数值差异，采用官方来源并保留缺口；均>15，不改变本轮档位。'],excluded_identity_cases=[dict(person='沈洁',reason='Washington University骨科及上海六院病案/数据同名作者排除，不能用其他作者南医大地址归人。'),dict(person='肖新华',reason='南华大学同名专家和协和张茜导师页页首的基金不计入。'),dict(person='毛百微',reason='光学领域同名作者排除；保留本人上海一院肾脏研究机构文章。'),dict(person='张静宜/万杰',reason='同名且本人作者机构不匹配的Kailuan/海外/中医/肿瘤论文不计入。')])
(R/'PI联网评级.json').write_text(json.dumps(dict(meta=meta,people=people,sources=list(S.values())),ensure_ascii=False,indent=2)+'\n')
print(json.dumps(meta,ensure_ascii=False,indent=2))
for p in people:print(p['id'],p['total_score'],p['grade'],p['known_subtotal'],p['known_maximum'])
