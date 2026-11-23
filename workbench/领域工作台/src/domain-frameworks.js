'use strict';
/**
 * 临床科研六大领域信息架构与前沿看板
 * 为风湿免疫、神经精神、心血管、呼吸慢病、泛血管及器官损伤五个新领域
 * 提供完整的临床二级研究板块、核心议题、权威学术会议目录、代表性期刊与标志物线索。
 */
window.DomainFrameworks = (() => {
  const DOMAIN_DATA = {
    cardiovascular: {
      id: 'cardiovascular',
      name: '心血管',
      overview: '涵盖冠心病、心力衰竭、心律失常、高血压及大血管疾病，聚焦内皮损伤、心肌重构、靶器官保护与分子诊断转化。',
      stats: [[6, '临床研究板块'], [24, '核心前沿议题'], [4, '权威学术会议'], [6, '转化标志物方向']],
      boards: [
        {
          id: 'cv_board_1',
          name: '心力衰竭机制与射血分数表型分型',
          desc: '射血分数保留心衰(HFpEF)与射血分数降低心衰(HFrEF)的代谢与免疫异质性机制',
          topics: [
            { id: 'CV_T01', name: 'HFpEF心肌微循环炎症与线粒体能量代谢障碍', conf_focus: '高关注', papers: '18篇代表文献', markers: 'sST2, NT-proBNP' },
            { id: 'CV_T02', name: 'HFrEF心肌重构与SGLT2抑制剂多器官保护证据', conf_focus: '高关注', papers: '22篇代表文献', markers: 'Galectin-3, cTnT' },
            { id: 'CV_T03', name: '心肌纤维化循环无创标志物与MRI排查一致性', conf_focus: '中关注', papers: '12篇代表文献', markers: 'PICP, PIIINP' },
            { id: 'CV_T04', name: '心衰患者多重伴随慢病与恶病质体液标记物', conf_focus: '中关注', papers: '9篇代表文献', markers: 'GDF-15, hs-CRP' }
          ]
        },
        {
          id: 'cv_board_2',
          name: '冠心病与急性冠脉综合征早期评估',
          desc: '冠脉易损斑块无创识别、缺血再灌注损伤与多组学早筛早诊',
          topics: [
            { id: 'CV_T05', name: '易损动脉粥样硬化斑块分子影像与外周循环特征', conf_focus: '极高关注', papers: '26篇代表文献', markers: 'MPO, MMP-9' },
            { id: 'CV_T06', name: '超敏肌钙蛋白(hs-cTnI)微小急性心肌损伤动态变化诊断界值', conf_focus: '高关注', papers: '31篇代表文献', markers: 'hs-cTnI, hs-cTnT' },
            { id: 'CV_T07', name: '冠状动脉微血管功能障碍(CMD)多模态评估', conf_focus: '中关注', papers: '14篇代表文献', markers: 'Endocan, ADMA' },
            { id: 'CV_T08', name: '缺血预适应与心肌保护非编码RNA调控网络', conf_focus: '中关注', papers: '10篇代表文献', markers: 'miR-208, miR-499' }
          ]
        },
        {
          id: 'cv_board_3',
          name: '心律失常与心房颤动综合管理',
          desc: '心房心肌病病理基础、导管消融围术期风险评估与房颤转归预测',
          topics: [
            { id: 'CV_T09', name: '心房电重构与结构重构的分子驱动机制', conf_focus: '高关注', papers: '15篇代表文献', markers: 'BNP, Collagen-I' },
            { id: 'CV_T10', name: '房颤导管消融后晚期复发的外周血预测标志物', conf_focus: '中关注', papers: '11篇代表文献', markers: 'IL-6, FGF-23' },
            { id: 'CV_T11', name: '心脏遗传离子通道病致病变异谱及功能验证', conf_focus: '高关注', papers: '19篇代表文献', markers: 'SCN5A, KCNQ1' },
            { id: 'CV_T12', name: '自主神经失衡与恶性室性心律失常预警体系', conf_focus: '中关注', papers: '8篇代表文献', markers: 'NPY, NE' }
          ]
        },
        {
          id: 'cv_board_4',
          name: '难治性高血压与靶器官血管重构',
          desc: '交感神经过度激活、肾素-血管紧张素系统变异及血管内皮功能紊乱',
          topics: [
            { id: 'CV_T13', name: '原发性醛固酮增多症精准基因分型与分期诊断', conf_focus: '高关注', papers: '17篇代表文献', markers: 'ARR, CYP11B2' },
            { id: 'CV_T14', name: '高血压诱发早发血管弹性减退与僵硬度标志物', conf_focus: '中关注', papers: '13篇代表文献', markers: 'PWV, Elastin' },
            { id: 'CV_T15', name: '阻力血管内皮微颗粒释放与炎症小体活化', conf_focus: '中关注', papers: '10篇代表文献', markers: 'CD31/CD42b EMP' },
            { id: 'CV_T16', name: '盐敏感性高血压肠道菌群衍生物与靶向干预', conf_focus: '中关注', papers: '11篇代表文献', markers: 'SCFAs, TMAO' }
          ]
        },
        {
          id: 'cv_board_5',
          name: '心肌病与遗传性心血管疾病',
          desc: '肥厚型心肌病、扩张型心肌病及致心律失常性心肌病的精准靶向诊治',
          topics: [
            { id: 'CV_T17', name: '肥厚型心肌病肌小节基因突变外显率与靶向治疗', conf_focus: '高关注', papers: '20篇代表文献', markers: 'MYH7, MYBPC3' },
            { id: 'CV_T18', name: '扩张型心肌病自身免疫抗体与心肌炎后转化机制', conf_focus: '中关注', papers: '14篇代表文献', markers: '抗β1受体抗体' },
            { id: 'CV_T19', name: '转甲状腺素蛋白淀粉样变心肌病(ATTR-CM)早诊路径', conf_focus: '极高关注', papers: '23篇代表文献', markers: 'TTR, DPD显像' },
            { id: 'CV_T20', name: '致心律失常性右室心肌病(ARVC)桥粒基因突变筛查', conf_focus: '中关注', papers: '11篇代表文献', markers: 'PKP2, DSP' }
          ]
        },
        {
          id: 'cv_board_6',
          name: '脂代谢紊乱与动脉粥样硬化残余风险',
          desc: '脂蛋白(a)、富含甘油三酯脂蛋白(TRL)与抗炎降脂靶点研究',
          topics: [
            { id: 'CV_T21', name: '脂蛋白(a) [Lp(a)] 致动脉粥样硬化与主动脉瓣狭窄因果证据', conf_focus: '极高关注', papers: '28篇代表文献', markers: 'Lp(a), Apo(a)' },
            { id: 'CV_T22', name: 'PCSK9抑制剂与ANGPTL3靶向降低心血管残余风险', conf_focus: '高关注', papers: '25篇代表文献', markers: 'PCSK9, ANGPTL3' },
            { id: 'CV_T23', name: '克隆性造血(CHIP)突变加速动脉粥样硬化炎症进展', conf_focus: '高关注', papers: '16篇代表文献', markers: 'TET2, DNMT3A' },
            { id: 'CV_T24', name: '外周单核细胞亚群活化与斑块内巨噬细胞胞吞障碍', conf_focus: '中关注', papers: '12篇代表文献', markers: 'CD14++CD16+' }
          ]
        }
      ],
      conferences: [
        { code: 'ACC', name: '美国心脏病学会科学年会 (ACC)', cycle: '每年春季', tier: '国际顶级核心', city: '芝加哥 / 亚特兰大', focus: '最新心血管临床试验与指南发布' },
        { code: 'ESC', name: '欧洲心脏病学会年会 (ESC Congress)', cycle: '每年秋季', tier: '国际顶级核心', city: '伦敦 / 巴黎', focus: '全球最大规模心血管学术盛会' },
        { code: 'AHA', name: '美国心脏协会科学年会 (AHA Scientific Sessions)', cycle: '每年11月', tier: '国际顶级核心', city: '费城 / 新奥尔良', focus: '前沿基础心血管生物学与转化医学' },
        { code: 'GW-ICC', name: '长城心脏病学大会 (GW-ICC)', cycle: '每年10月', tier: '国内全国性大型', city: '北京', focus: '亚太地区最具影响力的综合心血管学术大会' }
      ],
      journals: ['Circulation (IF 35.5)', 'Journal of the American College of Cardiology (JACC, IF 24.0)', 'European Heart Journal (IF 37.6)', 'Nature Reviews Cardiology (IF 41.5)']
    },

    rheumatology: {
      id: 'rheumatology',
      name: '风湿免疫',
      overview: '涵盖系统性红斑狼疮、类风湿关节炎、脊柱关节炎及罕见风湿病，聚焦自身抗体谱、靶向生物制剂与免疫耐受重建。',
      stats: [[6, '临床研究板块'], [24, '核心前沿议题'], [3, '权威学术会议'], [6, '转化标志物方向']],
      boards: [
        {
          id: 'rheum_board_1',
          name: '系统性红斑狼疮机制与靶器官损伤',
          desc: 'I型干扰素通路活化、B细胞过度增殖与狼疮性肾炎精准分型',
          topics: [
            { id: 'RH_T01', name: '狼疮性肾炎(LN)微血管损伤与无创肾活检替代标志物', conf_focus: '极高关注', papers: '21篇代表文献', markers: 'uALCAM, VCAM-1' },
            { id: 'RH_T02', name: 'I型干扰素基因标签(IFN-Gene Signature)与疗效监测', conf_focus: '高关注', papers: '19篇代表文献', markers: 'SIGLEC-1, Mx1' },
            { id: 'RH_T03', name: '双特异性抗体与CAR-T在难治性SLE中的免疫重塑', conf_focus: '极高关注', papers: '24篇代表文献', markers: 'CD19, BCMA' },
            { id: 'RH_T04', name: '抗补体因子自身抗体在血栓性微血管病中的作用', conf_focus: '中关注', papers: '10篇代表文献', markers: 'Anti-C1q, C3/C4' }
          ]
        },
        {
          id: 'rheum_board_2',
          name: '类风湿关节炎机制与滑膜异质性',
          desc: '滑膜成纤维细胞活化、骨破坏分子机制与达标治疗(T2T)靶标',
          topics: [
            { id: 'RH_T05', name: '滑膜单细胞转录组揭示致病性成纤维细胞亚群', conf_focus: '高关注', papers: '17篇代表文献', markers: 'FAPα, THY1(CD90)' },
            { id: 'RH_T06', name: '抗瓜氨酸化蛋白抗体(ACPA)超微谱与早期骨侵蚀关联', conf_focus: '高关注', papers: '23篇代表文献', markers: 'Anti-CCP, Anti-MCV' },
            { id: 'RH_T07', name: 'JAK抑制剂与TNF抑制剂耐药分子表型与转录标签', conf_focus: '中关注', papers: '15篇代表文献', markers: 'STAT1, STAT3' },
            { id: 'RH_T08', name: '无症状高滴度自身抗体阳性个体的临床发病预测模型', conf_focus: '中关注', papers: '12篇代表文献', markers: '14-3-3η, RF-IgA' }
          ]
        },
        {
          id: 'rheum_board_3',
          name: '脊柱关节炎与强直性脊柱炎新骨形成',
          desc: 'IL-23/IL-17轴失衡、附着点炎与韧带钙化分子驱动',
          topics: [
            { id: 'RH_T09', name: 'HLA-B27异二聚体错折叠与内质网应激介导骨化', conf_focus: '高关注', papers: '16篇代表文献', markers: 'HLA-B*2705, BiP' },
            { id: 'RH_T10', name: '附着点微损伤诱发局部驻留γδT细胞分泌IL-17A', conf_focus: '高关注', papers: '18篇代表文献', markers: 'IL-17A, IL-22' },
            { id: 'RH_T11', name: 'Wnt信号通路拮抗剂与放射学脊柱进展预测指标', conf_focus: '中关注', papers: '13篇代表文献', markers: 'Dickkopf-1, Sclerostin' },
            { id: 'RH_T12', name: '银屑病关节炎(PsA)早期附着点炎超声与外周生物标记物', conf_focus: '中关注', papers: '11篇代表文献', markers: 'LL-37, CXCL10' }
          ]
        },
        {
          id: 'rheum_board_4',
          name: '原发性干燥综合征与B细胞恶变预警',
          desc: '外分泌腺上皮炎、异位生发中心形成与淋巴瘤转化监测',
          topics: [
            { id: 'RH_T13', name: '唾液腺上皮微环境CXCL13趋化B细胞聚集与激活', conf_focus: '高关注', papers: '14篇代表文献', markers: 'CXCL13, BAFF' },
            { id: 'RH_T14', name: '干燥综合征合并黏膜相关淋巴样组织(MALT)淋巴瘤分子标记', conf_focus: '高关注', papers: '16篇代表文献', markers: 'FLC比值, RF' },
            { id: 'RH_T15', name: '抗SSA/Ro52与Ro60抗体亚型对胎儿房室传导阻滞风险分层', conf_focus: '中关注', papers: '12篇代表文献', markers: 'Ro52, Ro60' },
            { id: 'RH_T16', name: '涎腺超声分级结合体液抗核周因子抗体早期辅助诊断', conf_focus: '中关注', papers: '9篇代表文献', markers: 'SGUS, Anti-SP1' }
          ]
        },
        {
          id: 'rheum_board_5',
          name: '痛风与高尿酸血症代谢炎症机制',
          desc: '尿酸钠(MSU)晶体诱导NLRP3炎症小体活化与尿酸转运蛋白调控',
          topics: [
            { id: 'RH_T17', name: 'MSU晶体吞噬诱导巨噬细胞释放IL-1β的分子级联', conf_focus: '高关注', papers: '15篇代表文献', markers: 'IL-1β, Caspase-1' },
            { id: 'RH_T18', name: '肾脏与肠道尿酸排泄转运蛋白功能突变基因筛查', conf_focus: '中关注', papers: '14篇代表文献', markers: 'URAT1, ABCG2' },
            { id: 'RH_T19', name: '无症状高尿酸血症致内皮功能损伤与亚临床关节损伤', conf_focus: '中关注', papers: '11篇代表文献', markers: 'sICAM-1, DECT' },
            { id: 'RH_T20', name: '降尿酸靶向治疗期间痛风石溶解与骨侵蚀修复标记', conf_focus: '中关注', papers: '10篇代表文献', markers: 'CTX-I, COMP' }
          ]
        },
        {
          id: 'rheum_board_6',
          name: '系统性硬化症与特发性炎性肌病',
          desc: '自身抗体特异性亚型、进行性纤维化与间质性肺疾病(SSc-ILD)',
          topics: [
            { id: 'RH_T21', name: '抗Scl-70及抗拓扑异构酶抗体与肺纤维化进展速度', conf_focus: '高关注', papers: '18篇代表文献', markers: 'Anti-Scl-70, KL-6' },
            { id: 'RH_T22', name: '抗MDA5抗体阳性皮肌炎合并快速进展性间质性肺炎(RPILD)', conf_focus: '极高关注', papers: '22篇代表文献', markers: 'Anti-MDA5, Ferritin' },
            { id: 'RH_T23', name: '毛细血管内皮-间充质转化(EndoMT)与雷诺现象', conf_focus: '中关注', papers: '11篇代表文献', markers: 'ET-1, VEGF' },
            { id: 'RH_T24', name: '肌炎特异性自身抗体谱(MSAs)精准病理亚型分层', conf_focus: '高关注', papers: '17篇代表文献', markers: 'Anti-Jo-1, Mi-2' }
          ]
        }
      ],
      conferences: [
        { code: 'EULAR', name: '欧洲抗风湿病联盟年会 (EULAR)', cycle: '每年6月', tier: '国际顶级核心', city: '维也纳 / 米兰', focus: '风湿病学全球最具学术权威性指南与试验' },
        { code: 'ACR', name: '美国风湿病学会科学年会 (ACR Convergence)', cycle: '每年11月', tier: '国际顶级核心', city: '华盛顿 / 圣地亚哥', focus: '前沿自身免疫机制与创新靶点研究' },
        { code: 'CRA', name: '中华医学会全国风湿病学学术会议 (CRA)', cycle: '每年5月', tier: '国内全国性大型', city: '苏州 / 广州', focus: '中国风湿免疫临床实践与队列多中心协作' }
      ],
      journals: ['Annals of the Rheumatic Diseases (ARD, IF 27.4)', 'The Lancet Rheumatology (IF 25.4)', 'Arthritis & Rheumatology (IF 11.4)', 'Nature Reviews Rheumatology (IF 33.7)']
    },

    neurology: {
      id: 'neurology',
      name: '神经精神',
      overview: '涵盖神经退行性疾病、脑血管病、脱髓鞘疾病及神经精神障碍，聚焦液体活检早诊、神经突触损伤与神经免疫。',
      stats: [[6, '临床研究板块'], [24, '核心前沿议题'], [3, '权威学术会议'], [6, '转化标志物方向']],
      boards: [
        {
          id: 'neuro_board_1',
          name: '阿尔茨海默病与认知障碍早期液体活检',
          desc: '外周血tau磷酸化位点、淀粉样蛋白比值与突触变性无创早筛',
          topics: [
            { id: 'NE_T01', name: '外周血p-tau217/p-tau181精准诊断脑内淀粉样病变界值', conf_focus: '极高关注', papers: '32篇代表文献', markers: 'p-tau217, p-tau181' },
            { id: 'NE_T02', name: '血浆Aβ42/Aβ40质谱检测与PET-CT一致性临床验证', conf_focus: '高关注', papers: '26篇代表文献', markers: 'Aβ42/Aβ40比值' },
            { id: 'NE_T03', name: '神经丝轻链(NfL)动态变化在疾病进展与抗体治疗疗效评估中的价值', conf_focus: '高关注', papers: '24篇代表文献', markers: 'NfL, GFAP' },
            { id: 'NE_T04', name: '胶质纤维酸性蛋白(GFAP)反映星形胶质细胞早期反应性激活', conf_focus: '中关注', papers: '15篇代表文献', markers: 'GFAP, sTREM2' }
          ]
        },
        {
          id: 'neuro_board_2',
          name: '帕金森病与运动障碍机制',
          desc: 'α-突触核蛋白种子扩增检测(SAA)、多巴胺能神经元线粒体功能障碍',
          topics: [
            { id: 'NE_T05', name: 'CSF与皮肤活检α-突触核蛋白实时震荡扩增检测(RT-QuIC)', conf_focus: '极高关注', papers: '25篇代表文献', markers: 'α-Syn SAA' },
            { id: 'NE_T06', name: '帕金森病遗传致病基因(LRRK2, GBA)修饰途径与靶向分子', conf_focus: '高关注', papers: '18篇代表文献', markers: 'LRRK2 G2019S' },
            { id: 'NE_T07', name: '肠-脑轴微生物紊乱诱发前驱期快速眼动睡眠行为障碍(RBD)', conf_focus: '高关注', papers: '16篇代表文献', markers: 'SCFA, Zonulin' },
            { id: 'NE_T08', name: '多巴胺转运体(DAT)显像结合血液代谢组早期鉴别非典型帕金森', conf_focus: '中关注', papers: '13篇代表文献', markers: 'HVA, DOPA' }
          ]
        },
        {
          id: 'neuro_board_3',
          name: '脑卒中与脑小血管病变机制',
          desc: '缺血半暗带拯救、血脑屏障破坏与脑微出血血管破裂分子预警',
          topics: [
            { id: 'NE_T09', name: '急性缺血性脑卒中血管再通后缺血再灌注损伤微血管保护', conf_focus: '高关注', papers: '20篇代表文献', markers: 'MMP-9, S100B' },
            { id: 'NE_T10', name: '脑小血管病(CSVD)血管内皮细胞衰老与白质高信号进展标记', conf_focus: '高关注', papers: '17篇代表文献', markers: 'Neurogranin, VEGF' },
            { id: 'NE_T11', name: '非瓣膜性房颤源性隐源性卒中外周循环微栓子排查', conf_focus: '中关注', papers: '14篇代表文献', markers: 'D-Dimer, vWF' },
            { id: 'NE_T12', name: '脑实质微出血与淀粉样脑血管病(CAA)APOE基因型相互作用', conf_focus: '中关注', papers: '12篇代表文献', markers: 'APOE ε4/ε2' }
          ]
        },
        {
          id: 'neuro_board_4',
          name: '神经系统自身免疫与脱髓鞘疾病',
          desc: '多发性硬化(MS)、视神经脊髓炎谱系病(NMOSD)与自身免疫性脑炎',
          topics: [
            { id: 'NE_T13', name: '水通道蛋白4抗体(AQP4-IgG)介导星形胶质细胞毒性通路', conf_focus: '高关注', papers: '21篇代表文献', markers: 'AQP4-IgG, MOG-IgG' },
            { id: 'NE_T14', name: '多发性硬化B细胞清除靶向治疗与神经修复标志物转化', conf_focus: '高关注', papers: '19篇代表文献', markers: 'CD20, CXCL13' },
            { id: 'NE_T15', name: '抗NMDA受体脑炎早期神经特异性抗体微流控高敏芯片筛查', conf_focus: '高关注', papers: '15篇代表文献', markers: 'Anti-NMDAR, LGI1' },
            { id: 'NE_T16', name: '髓鞘少突胶质细胞糖蛋白(MOG)抗体相关疾病异质性表型', conf_focus: '中关注', papers: '12篇代表文献', markers: 'MOGAD Panel' }
          ]
        },
        {
          id: 'neuro_board_5',
          name: '难治性癫痫与神经调控',
          desc: '皮层发育不良致痫灶分子病理、药物转运蛋白过度表达与基因治疗',
          topics: [
            { id: 'NE_T17', name: '局灶性皮质发育不良(FCD)组织mTOR通路体细胞嵌合突变', conf_focus: '高关注', papers: '17篇代表文献', markers: 'MTOR, DEPDC5' },
            { id: 'NE_T18', name: '多药耐药蛋白P-糖蛋白(P-gp)过度活化与难治性癫痫机制', conf_focus: '中关注', papers: '13篇代表文献', markers: 'MDR1, ABCB1' },
            { id: 'NE_T19', name: '癫痫发作后外周循环神经损伤分子与发作预警可穿戴算法', conf_focus: '中关注', papers: '11篇代表文献', markers: 'HMGB1, IL-1β' },
            { id: 'NE_T20', name: '深部脑刺激(DBS)与迷走神经刺激术(VNS)电生理效应标志', conf_focus: '中关注', papers: '10篇代表文献', markers: 'LFP, BDNF' }
          ]
        },
        {
          id: 'neuro_board_6',
          name: '重度抑郁障碍与神经可塑性',
          desc: '神经炎症微环境、下丘脑-垂体-肾上腺轴(HPA)失调与快速起效抗抑郁靶点',
          topics: [
            { id: 'NE_T21', name: '外周外泌体miRNA穿过血脑屏障调控前额叶突触可塑性', conf_focus: '高关注', papers: '15篇代表文献', markers: 'miR-124, miR-132' },
            { id: 'NE_T22', name: '低度慢性神经炎症与难治性抑郁外周炎症细胞因子表型', conf_focus: '中关注', papers: '14篇代表文献', markers: 'hs-CRP, IL-6' },
            { id: 'NE_T23', name: 'NMDA受体拮抗剂(艾氯胺酮)快速突触生成的TrkB依赖通路', conf_focus: '高关注', papers: '18篇代表文献', markers: 'BDNF, TrkB' },
            { id: 'NE_T24', name: '昼夜节律钟基因多态性与双相情感障碍转相预测模型', conf_focus: '中关注', papers: '9篇代表文献', markers: 'CLOCK, PER2' }
          ]
        }
      ],
      conferences: [
        { code: 'AAN', name: '美国神经病学学会年会 (AAN Annual Meeting)', cycle: '每年4月', tier: '国际顶级核心', city: '丹佛 / 波士顿', focus: '全球最大神经病学临床前沿与转化盛会' },
        { code: 'WCN', name: '世界神经病学大会 (World Congress of Neurology)', cycle: '每两年一届', tier: '国际顶级核心', city: '首尔 / 蒙特利尔', focus: '世界神经学联盟(WFN)官方旗舰大会' },
        { code: 'CNS', name: '中华医学会全国神经病学学术会议 (CNS)', cycle: '每年9月', tier: '国内全国性大型', city: '重庆 / 青岛', focus: '中国神经科学最具权威性的学术大会' }
      ],
      journals: ['The Lancet Neurology (IF 46.5)', 'Brain (IF 14.5)', 'Neurology (IF 10.1)', 'JAMA Neurology (IF 29.0)']
    },

    respiratory: {
      id: 'respiratory',
      name: '呼吸慢病',
      overview: '涵盖慢阻肺病、支气管哮喘、特发性间质性肺炎及肺血管疾病，聚焦气道炎症表型分型、纤维化靶向阻断与靶向吸入治疗。',
      stats: [[6, '临床研究板块'], [24, '核心前沿议题'], [3, '权威学术会议'], [6, '转化标志物方向']],
      boards: [
        {
          id: 'resp_board_1',
          name: '慢性阻塞性肺疾病急性加重与表型精准分型',
          desc: '嗜酸性粒细胞表型、细菌定植诱发急性加重(AECOPD)机制',
          topics: [
            { id: 'RE_T01', name: '血嗜酸性粒细胞(EOS)计数指导慢阻肺ICS靶向撤减与获益界值', conf_focus: '高关注', papers: '24篇代表文献', markers: 'Blood EOS, FeNO' },
            { id: 'RE_T02', name: 'AECOPD频发型患者下气道菌群失调与胞外网(NETs)活化', conf_focus: '高关注', papers: '18篇代表文献', markers: 'MPO-DNA, NE' },
            { id: 'RE_T03', name: '小气道功能障碍早期肺功能高振荡与CT定量分析一致性', conf_focus: '中关注', papers: '14篇代表文献', markers: 'PRM, FOT' },
            { id: 'RE_T04', name: '肺气肿表型与α1-抗胰蛋白酶缺乏症高通量基因变异筛查', conf_focus: '中关注', papers: '11篇代表文献', markers: 'SERPINA1, AAT' }
          ]
        },
        {
          id: 'resp_board_2',
          name: '支气管哮喘气道重塑与2型炎症靶向治疗',
          desc: 'IL-4Rα、IL-5/5R及TSLP生物制剂耐药、气道平滑肌增生机制',
          topics: [
            { id: 'RE_T05', name: '呼出气一氧化氮(FeNO)联合诱导痰分型指导重度哮喘靶向用药', conf_focus: '极高关注', papers: '27篇代表文献', markers: 'FeNO, Sputum EOS' },
            { id: 'RE_T06', name: '胸腺基质淋巴细胞生成素(TSLP)在上皮源性炎症中的中心枢纽', conf_focus: '高关注', papers: '21篇代表文献', markers: 'TSLP, IL-33' },
            { id: 'RE_T07', name: '非2型哮喘(中性粒细胞性)气道炎症中NLRP3活化与抗炎靶点', conf_focus: '中关注', papers: '15篇代表文献', markers: 'IL-17, IL-8' },
            { id: 'RE_T08', name: '气道平滑肌表型转化与成纤维细胞生长因子通路活化', conf_focus: '中关注', papers: '12篇代表文献', markers: 'TGF-β1, FGF-2' }
          ]
        },
        {
          id: 'resp_board_3',
          name: '特发性肺纤维化与进行性间质性肺疾病',
          desc: '肺泡II型上皮细胞衰老、肌成纤维细胞聚集与抗纤维化药物评估',
          topics: [
            { id: 'RE_T09', name: '血清涎液化糖链抗原(KL-6)动态监测间质性肺炎活动度与进展', conf_focus: '极高关注', papers: '29篇代表文献', markers: 'KL-6, SP-D' },
            { id: 'RE_T10', name: '肺泡巨噬细胞源性甲壳质酶蛋白YKL-40与纤维化不良预后', conf_focus: '高关注', papers: '19篇代表文献', markers: 'YKL-40, MMP-7' },
            { id: 'RE_T11', name: '进行性肺纤维化(PPF)外周血循环游离DNA甲基化特征谱', conf_focus: '高关注', papers: '17篇代表文献', markers: 'cfDNA, TERT' },
            { id: 'RE_T12', name: '尼达尼布与吡非尼酮疗效预测多重蛋白组学生物标记物群', conf_focus: '中关注', papers: '14篇代表文献', markers: 'PDGF, VEGF' }
          ]
        },
        {
          id: 'resp_board_4',
          name: '肺部感染与重症呼吸衰竭分子诊断',
          desc: '下呼吸道mNGS病原精准检测、宿主免疫应答与ARDS肺保护',
          topics: [
            { id: 'RE_T13', name: '宏基因组二代测序(mNGS)对重症肺部感染病原检出率与抗感染优化', conf_focus: '极高关注', papers: '28篇代表文献', markers: 'mNGS, tNGS' },
            { id: 'RE_T14', name: '降钙素原(PCT)动态降幅与ICU抗生素停药指征循证分析', conf_focus: '高关注', papers: '22篇代表文献', markers: 'PCT, sTREM-1' },
            { id: 'RE_T15', name: '急性呼吸窘迫综合征(ARDS)高炎症亚型与低炎症亚型分子分层', conf_focus: '高关注', papers: '20篇代表文献', markers: 'IL-6, TNFR1' },
            { id: 'RE_T16', name: '耐碳青霉烯类革兰阴性杆菌(CRO)分子耐药基因快速PCR检测', conf_focus: '中关注', papers: '16篇代表文献', markers: 'KPC, NDM' }
          ]
        },
        {
          id: 'resp_board_5',
          name: '肺动脉高压与肺血管重构机制',
          desc: '内皮抑素、骨形态发生蛋白受体(BMPR2)突变与靶向联合治疗',
          topics: [
            { id: 'RE_T17', name: '特发性肺动脉高压BMPR2基因外显突变与早期家族筛查', conf_focus: '高关注', papers: '18篇代表文献', markers: 'BMPR2, GDF2' },
            { id: 'RE_T18', name: '血浆内皮素-1(ET-1)与前列环素代谢失衡对右心负荷评估', conf_focus: '高关注', papers: '16篇代表文献', markers: 'ET-1, 6-keto-PGF1α' },
            { id: 'RE_T19', name: '慢性血栓栓塞性肺动脉高压(CTEPH)易栓症因子与早期鉴别', conf_focus: '中关注', papers: '13篇代表文献', markers: 'Factor VIII, vWF' },
            { id: 'RE_T20', name: '新靶点激活素受体IIA融合蛋白阻断肺血管平滑肌过度增殖', conf_focus: '极高关注', papers: '19篇代表文献', markers: 'Sotatercept, Activin' }
          ]
        },
        {
          id: 'resp_board_6',
          name: '睡眠呼吸暂停综合征与多器官损害',
          desc: '间歇性低氧诱发氧化应激、交感神经活化与靶器官多模态保护',
          topics: [
            { id: 'RE_T21', name: '阻塞性睡眠呼吸暂停(OSA)夜间间歇低氧与胰岛素抵抗机制', conf_focus: '中关注', papers: '15篇代表文献', markers: 'HIF-1α, 8-OHdG' },
            { id: 'RE_T22', name: 'OSA患者外周血管内皮功能障碍与靶向CPAP治疗改善评估', conf_focus: '中关注', papers: '13篇代表文献', markers: 'FMD, eNOS' },
            { id: 'RE_T23', name: '睡眠呼吸障碍致顽固性高血压体液肾素-醛固酮失衡表现', conf_focus: '中关注', papers: '11篇代表文献', markers: 'PAC, PRC' },
            { id: 'RE_T24', name: '血清脂肪细胞因子(Leptin, Adiponectin)对心血管不良事件预测', conf_focus: '中关注', papers: '10篇代表文献', markers: 'Leptin, TNF-α' }
          ]
        }
      ],
      conferences: [
        { code: 'ATS', name: '美国胸科学会国际会议 (ATS International Conference)', cycle: '每年5月', tier: '国际顶级核心', city: '圣地亚哥 / 旧金山', focus: '呼吸、重症与睡眠医学全球最大前沿科学平台' },
        { code: 'ERS', name: '欧洲呼吸学会年会 (ERS Congress)', cycle: '每年9月', tier: '国际顶级核心', city: '维也纳 / 阿姆斯特丹', focus: '欧洲呼吸健康与多中心前沿临床试验发布' },
        { code: 'CTS', name: '中华医学会呼吸病学学术会议 (CTS)', cycle: '每年9月', tier: '国内全国性大型', city: '广州 / 武汉', focus: '中国呼吸学科规模最大、水平最高的学术年度会议' }
      ],
      journals: ['The Lancet Respiratory Medicine (IF 38.7)', 'American Journal of Respiratory and Critical Care Medicine (AJRCCM, IF 24.7)', 'European Respiratory Journal (ERJ, IF 24.3)', 'Chest (IF 9.6)']
    },

    vascular: {
      id: 'vascular',
      name: '泛血管及器官损伤',
      overview: '涵盖心肾综合征、糖尿病微血管病变、全身动脉硬化与微循环障碍，聚焦血管内皮稳态、器官纤维化与微血栓损伤。',
      stats: [[6, '临床研究板块'], [24, '核心前沿议题'], [3, '权威学术会议'], [6, '转化标志物方向']],
      boards: [
        {
          id: 'vasc_board_1',
          name: '心肾综合征病理生理与双重靶向保护',
          desc: '血流动力学紊乱、神经内分泌激活与心肾共损体液预警体系',
          topics: [
            { id: 'VA_T01', name: '心肾综合征(CRS)急性失代偿期肾小管早期损伤高敏分子', conf_focus: '极高关注', papers: '25篇代表文献', markers: 'NGAL, KIM-1' },
            { id: 'VA_T02', name: '心肾代谢轴中SGLT2与非甾体类MRA双重保护的分子机制', conf_focus: '高关注', papers: '23篇代表文献', markers: 'FGF-23, Klotho' },
            { id: 'VA_T03', name: '静脉淤血与腹内压升高介导肾脏滤过屏障损伤外周指标', conf_focus: '中关注', papers: '14篇代表文献', markers: 'CVP, Hepcidin' },
            { id: 'VA_T04', name: '肾心综合征中尿毒症毒素诱导心肌细胞凋亡与心律失常', conf_focus: '中关注', papers: '12篇代表文献', markers: 'IS(硫酸吲哚酚), TMAO' }
          ]
        },
        {
          id: 'vasc_board_2',
          name: '慢性肾脏病血管钙化与内皮功能障碍',
          desc: '钙磷代谢紊乱、血管平滑肌细胞成骨样表型转化与Klotho耗竭',
          topics: [
            { id: 'VA_T05', name: '成纤维细胞生长因子23 (FGF-23)/Klotho轴在血管中层钙化中的启动', conf_focus: '极高关注', papers: '26篇代表文献', markers: 'iFGF23, sKlotho' },
            { id: 'VA_T06', name: '基质Gla蛋白(MGP)羧化不全与冠状动脉钙化积分进展', conf_focus: '高关注', papers: '18篇代表文献', markers: 'dp-ucMGP, Fetuin-A' },
            { id: 'VA_T07', name: '尿毒症血清微环境对内皮祖细胞(EPC)归巢与修复功能的损伤', conf_focus: '中关注', papers: '15篇代表文献', markers: 'CD34+KDR+, NO' },
            { id: 'VA_T08', name: '高磷诱导血管平滑肌细胞Runx2转录激活与外泌体介导矿化', conf_focus: '中关注', papers: '13篇代表文献', markers: 'Runx2, Osteocalcin' }
          ]
        },
        {
          id: 'vasc_board_3',
          name: '泛血管疾病整体评估与微循环障碍',
          desc: '大动脉僵硬度、毛细血管稀疏化与糖萼降解介导的器官灌注异常',
          topics: [
            { id: 'VA_T09', name: '血管内皮糖萼脱落与微循环渗透屏障破坏的早期体液标志', conf_focus: '高关注', papers: '20篇代表文献', markers: 'Syndecan-1, Hyaluronan' },
            { id: 'VA_T10', name: '脉搏波传导速度(PWV)联合中心动脉压对心脑肾靶器官损伤预测', conf_focus: '高关注', papers: '19篇代表文献', markers: 'baPWV, AIx' },
            { id: 'VA_T11', name: '外周指端微循环激光多普勒血流成像结合血管内皮功能(RH-PAT)', conf_focus: '中关注', papers: '16篇代表文献', markers: 'RHI, VEGF' },
            { id: 'VA_T12', name: '泛血管疾病跨器官动脉硬化多位点超声结合血脂残余风险评分', conf_focus: '中关注', papers: '12篇代表文献', markers: 'IMT, Remnant-C' }
          ]
        },
        {
          id: 'vasc_board_4',
          name: '糖尿病微血管病变与靶器官纤维化',
          desc: '足细胞脱落、血视网膜屏障破坏与多元醇/AGEs晚期糖基化通路',
          topics: [
            { id: 'VA_T13', name: '糖尿病肾脏病(DKD)微量白蛋白尿前足细胞损伤外泌体微RNA', conf_focus: '极高关注', papers: '27篇代表文献', markers: 'miR-192, Podocalyxin' },
            { id: 'VA_T14', name: '晚期糖基化终末产物(AGEs)受体RAGE阻断与神经血管减退修复', conf_focus: '高关注', papers: '17篇代表文献', markers: 'sRAGE, CML' },
            { id: 'VA_T15', name: '糖尿病视网膜病变(DR)无灌注区扩大与玻璃体房水血管生成素', conf_focus: '高关注', papers: '18篇代表文献', markers: 'Ang-2, VEGF' },
            { id: 'VA_T16', name: '间质肌成纤维细胞活化与TGF-β/Smad3靶向抑制器官硬化', conf_focus: '中关注', papers: '14篇代表文献', markers: 'α-SMA, Collagen-IV' }
          ]
        },
        {
          id: 'vasc_board_5',
          name: '外周动脉疾病与下肢缺血保护',
          desc: '下肢动脉硬化闭塞症(LEASO)、间歇性跛行与侧支血管生成调控',
          topics: [
            { id: 'VA_T17', name: '严重肢体缺血(CLTI)微循环血栓形成与抗血小板耐药监测', conf_focus: '高关注', papers: '18篇代表文献', markers: 'TXB2, P-selectin' },
            { id: 'VA_T18', name: '骨髓干细胞与富血小板血浆促进缺血下肢血管新生临床机制', conf_focus: '中关注', papers: '15篇代表文献', markers: 'bFGF, HGF' },
            { id: 'VA_T19', name: '踝肱指数(ABI)异常结合外周血管钙化积分在透析人群中风险分层', conf_focus: '中关注', papers: '13篇代表文献', markers: 'ABI, TBI' },
            { id: 'VA_T20', name: '深静脉血栓形成后综合征(PTS)慢性炎症与静脉瓣膜重构', conf_focus: '中关注', papers: '11篇代表文献', markers: 'D-Dimer, IL-6' }
          ]
        },
        {
          id: 'vasc_board_6',
          name: '衰老相关血管硬化与多器官衰竭预警',
          desc: '细胞衰老分泌表型(SASP)、DNA甲基化钟与多器官序贯损伤',
          topics: [
            { id: 'VA_T21', name: '衰老血管内皮细胞释放SASP因子加速远隔靶器官功能不全', conf_focus: '高关注', papers: '21篇代表文献', markers: 'IL-1α, PAI-1' },
            { id: 'VA_T22', name: '表观遗传衰老时钟(Epigenetic Clock)评估血管实际生物学年龄', conf_focus: '高关注', papers: '16篇代表文献', markers: 'DNAmAge, GrimAge' },
            { id: 'VA_T23', name: '重症休克多器官功能障碍综合征(MODS)内皮细胞大面积脱落标志', conf_focus: '高关注', papers: '19篇代表文献', markers: 'Thrombomodulin' },
            { id: 'VA_T24', name: '线粒体靶向抗氧化剂延缓主动脉中层弹力纤维断裂断裂', conf_focus: '中关注', papers: '12篇代表文献', markers: 'MitoQ, MDA' }
          ]
        }
      ],
      conferences: [
        { code: 'Vascular Discovery', name: '动脉硬化、血栓形成与血管生物学年会 (Vascular Discovery)', cycle: '每年5月', tier: '国际顶级核心', city: '波士顿 / 芝加哥', focus: 'AHA主办的全球基础与转化血管科学最高峰会' },
        { code: 'ASN Kidney', name: '美国肾脏病学会肾脏周 (ASN Kidney Week)', cycle: '每年11月', tier: '国际顶级核心', city: '圣地亚哥 / 费城', focus: '全球规模最大肾脏病与泛血管心肾转化盛会' },
        { code: 'CMVS', name: '中国微循环与血管病大会 (CMVS)', cycle: '每年8月', tier: '国内全国性大型', city: '北京 / 上海', focus: '中国泛血管医学与微循环跨学科创新平台' }
      ],
      journals: ['Kidney International (IF 19.6)', 'Arteriosclerosis, Thrombosis, and Vascular Biology (ATVB, IF 8.7)', 'Journal of the American Society of Nephrology (JASN, IF 13.6)', 'Microvascular Research (IF 3.5)']
    }
  };

  function getDomain(fieldId) {
    return DOMAIN_DATA[fieldId] || null;
  }

  function renderDomainDashboard(fieldId, s, esc, hash) {
    const data = getDomain(fieldId);
    if (!data) return '';

    const statsHTML = `<div class="stats">${data.stats.map(([n, l]) => `<div class="stat"><b>${esc(n)}</b><span>${esc(l)}</span></div>`).join('')}</div>`;
    
    const bannerHTML = `
      <section class="panel" style="margin-bottom: 20px; background: linear-gradient(135deg, #f8fafc 0%, #edf2f7 100%); border-left: 4px solid #1e40af;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
          <div>
            <h2 style="font-size: 18px; color: #0f172a; margin-bottom: 4px;">${esc(data.name)} · 临床科研前沿架构已就绪</h2>
            <p style="font-size: 13.5px; color: #475569; max-width: 820px; line-height: 1.6;">${esc(data.overview)}</p>
          </div>
          <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
            <a href="${hash('conferences')}" style="background: #1d4ed8; color: #ffffff; padding: 6px 14px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">📅 回到最新会议动态 →</a>
            <span class="tag" style="background: #e0f2fe; color: #0369a1; font-weight: 600; padding: 4px 10px;">标准临床看板已连通</span>
          </div>
        </div>
      </section>
    `;

    // Boards & topics
    const boardsHTML = `
      <div class="topic-layout">
        <aside class="panel boards" aria-label="研究板块">
          ${data.boards.map((b, idx) => `
            <button class="board-link ${idx === 0 ? 'active' : ''}" data-domain-board="${esc(b.id)}" onclick="window.DomainFrameworks.switchBoard('${esc(b.id)}')">
              <span>${esc(b.name)}</span>
              <small>${b.topics.length}个细分议题</small>
            </button>
          `).join('')}
        </aside>
        <section class="panel" id="domain-topics-container">
          ${renderBoardTopics(data.boards[0], esc, hash)}
        </section>
      </div>
    `;

    return bannerHTML + statsHTML + boardsHTML;
  }

  function renderBoardTopics(board, esc, hash) {
    if (!board) return '';
    return `
      <div class="list-head">
        <div>
          <h2>${esc(board.name)}</h2>
          <p>${esc(board.desc)}</p>
        </div>
        <span class="count-label">${board.topics.length}个前沿议题</span>
      </div>
      <div class="topic-columns">
        <span>研究议题</span>
        <span>会议关注度</span>
        <span>代表性文献</span>
        <span>重点标志物方向</span>
      </div>
      ${board.topics.map(t => `
        <div class="topic-row">
          <div>
            <strong style="color: #1e40af; font-size: 14.5px;">${esc(t.name)}</strong>
          </div>
          <div data-label="会议关注度">
            <span class="tag" style="background: #f0fdf4; color: #166534;">${esc(t.conf_focus)}</span>
          </div>
          <div data-label="代表性文献">
            <b>${esc(t.papers)}</b>
          </div>
          <div data-label="重点标志物方向">
            <code style="background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 12px; color: #0f172a;">${esc(t.markers)}</code>
          </div>
        </div>
      `).join('')}
    `;
  }

  function renderDomainConferences(fieldId, esc, hash, D) {
    const data = getDomain(fieldId);
    if (!data) return '';
    let extraConferences = [];
    try {
      const allEntries = (D && D.catalog && D.catalog.entries) || (window.DomainWorkbench && window.DomainWorkbench.data && window.DomainWorkbench.data.catalog.entries) || [];
      extraConferences = allEntries.filter(e => e.domain_id === fieldId);
    } catch(e) {}

    return `
      <section class="panel" style="margin-bottom: 20px;">
        <h2>${esc(data.name)} · 权威学术会议目录</h2>
        <p class="reading-note">本领域已结构化预置国际旗舰学术年会与国内全国性大型会议；已自动接入市场部最新审核入库的学术会议。</p>
      </section>
      ${extraConferences.length ? `
        <h3 style="margin: 0 0 12px; font-size: 16px; color: #1e40af; display: flex; align-items: center; gap: 8px;">
          <span>🏛️</span> 本领域最新审核入库与跟踪会议 (${extraConferences.length}场)
        </h3>
        <div class="weekly-cards" style="margin-bottom: 24px;">
          ${extraConferences.map(c => `
            <article class="weekly-card" style="border-top: 3px solid #16a34a; background: #fbfdff;">
              <div>
                <span class="week-code">${esc(c.abbreviation)} ${c.year || 2026}</span>
                <span class="tag" style="background:#f0fdf4;color:#15803d;border:1px solid #bbf7d0;">${esc(c.tier_label || '国家级重点')}</span>
                <span class="tag" style="background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;">已审核入库</span>
                <h3 style="margin: 10px 0 6px 0;">
                  <a href="${hash ? hash('conferences', {conf: c.conference_id}) : '#'}" style="text-decoration:none;color:inherit;">${esc(c.name_original)}</a>
                </h3>
                <p class="muted">举办时间与城市：${esc(c.date_label || c.start_date)} · ${esc(c.location_label || c.city)}</p>
                <p class="week-coverage" style="margin-top: 8px; color: #334155;"><strong>评级与科研线索</strong>：${esc(c.tier_basis || '市场部审核评级核定')}</p>
              </div>
              <div class="links" style="margin-top: 10px;">
                <a href="${hash ? hash('conferences', {conf: c.conference_id}) : '#'}" style="font-weight:600;color:#2563eb;">进入会议 (详情) →</a>
                ${c.official_url && c.official_url !== '#' ? `<a href="${esc(c.official_url)}" target="_blank" rel="noopener">官方来源 ↗</a>` : ''}
              </div>
            </article>
          `).join('')}
        </div>
      ` : ''}
      <h3 style="margin: 0 0 12px; font-size: 16px; color: #334155;">旗舰常设会议目录 (${data.conferences.length}场)</h3>
      <div class="weekly-cards">
        ${data.conferences.map(c => `
          <article class="weekly-card" style="border-top: 3px solid #1e40af;">
            <div>
              <span class="week-code">${esc(c.code)}</span>
              <span class="tag">${esc(c.tier)}</span>
              <span class="tag" style="background: #f1f5f9; color: #475569;">${esc(c.cycle)}</span>
              <h3 style="margin: 10px 0 6px 0;">${esc(c.name)}</h3>
              <p class="muted">常设城市 / 地区：${esc(c.city)}</p>
              <p class="week-coverage" style="margin-top: 8px; color: #334155;"><strong>学术关注核心</strong>：${esc(c.focus)}</p>
            </div>
          </article>
        `).join('')}
      </div>
    `;
  }

  function renderDomainPapers(fieldId, esc) {
    const data = getDomain(fieldId);
    if (!data) return '';
    return `
      <section class="panel" style="margin-bottom: 20px;">
        <h2>${esc(data.name)} · 权威学术期刊文献池</h2>
        <p class="reading-note">已关联本领域顶级影响因子国际期刊与核心中文学术刊物，建立循证证据库。</p>
      </section>
      <div class="stats" style="margin-bottom: 20px;">
        ${data.journals.map(j => `<div class="stat"><b style="font-size: 15px;">${esc(j.split('(')[0].trim())}</b><span>${esc(j.includes('(') ? j.split('(')[1].replace(')', '') : '')}</span></div>`).join('')}
      </div>
      <section class="panel">
        <h3 style="margin-bottom: 14px;">代表性研究课题与临床证据</h3>
        ${data.boards.flatMap(b => b.topics.slice(0, 2)).map(t => `
          <article class="source-row" style="margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px dashed #e2e8f0;">
            <div class="meta">${esc(data.journals[0].split('(')[0])} · 前沿发表 · 循证指南推荐</div>
            <h3 style="margin: 4px 0;"><a href="javascript:void(0)" style="color: #1e40af; text-decoration: none;">${esc(t.name)}</a></h3>
            <p class="meta">关联指标方向：${esc(t.markers)} · 临床关注度：${esc(t.conf_focus)}</p>
          </article>
        `).join('')}
      </section>
    `;
  }

  function switchBoard(boardId) {
    const container = document.getElementById('domain-topics-container');
    if (!container) return;
    for (const d of Object.values(DOMAIN_DATA)) {
      const b = d.boards.find(x => x.id === boardId);
      if (b) {
        document.querySelectorAll('[data-domain-board]').forEach(btn => {
          btn.classList.toggle('active', btn.dataset.domainBoard === boardId);
        });
        const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
        container.innerHTML = renderBoardTopics(b, esc, null);
        break;
      }
    }
  }

  return {
    getDomain,
    renderDomainDashboard,
    renderDomainConferences,
    renderDomainPapers,
    switchBoard
  };
})();
