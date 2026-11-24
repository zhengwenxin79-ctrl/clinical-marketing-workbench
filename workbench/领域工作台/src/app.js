'use strict';

window.workbenchApp = function () {
  // 1. Load Embedded Real Snapshot Data (#data)
  let D = {};
  try {
    const el = document.getElementById('data');
    if (el && el.textContent) {
      D = JSON.parse(el.textContent);
    }
  } catch (e) {
    console.error('Failed to parse embedded #data JSON:', e);
  }
  window.DomainWorkbench = { data: D };

  // 2. Six Standard Disease Domains
  const DOMAINS = [
    { id: 'diabetes',       name: '糖尿病与代谢',     color: '#2563eb' },
    { id: 'neurology',      name: '神经精神',         color: '#d97706' },
    { id: 'respiratory',    name: '呼吸慢病',         color: '#0891b2' },
    { id: 'rheumatology',   name: '风湿免疫',         color: '#7c3aed' },
    { id: 'cardiovascular', name: '心血管',           color: '#e11d48' },
    { id: 'vascular',       name: '泛血管及器官损伤', color: '#059669' }
  ];

  const DOMAIN_ID_TO_NAME = Object.fromEntries(DOMAINS.map(d => [d.id, d.name]));
  const DOMAIN_NAME_TO_COLOR = Object.fromEntries(DOMAINS.map(d => [d.name, d.color]));

  function getDomainName(fieldId, fallbackTitle = '') {
    if (fieldId && DOMAIN_ID_TO_NAME[fieldId]) return DOMAIN_ID_TO_NAME[fieldId];
    const t = String(fallbackTitle || '');
    if (/神经|脑卒中|帕金森|脑疾病|阿尔茨海默|心身/.test(t)) return '神经精神';
    if (/呼吸|慢阻肺|哮喘|PCCM|肺/.test(t)) return '呼吸慢病';
    if (/风湿|自身免疫|自免|红斑狼疮|关节炎/.test(t)) return '风湿免疫';
    if (/心血管|心脏|高血压|冠脉|左主干|心衰|胸心/.test(t)) return '心血管';
    if (/泛血管|微循环|周围血管|放射|影像|RSNA/.test(t)) return '泛血管及器官损伤';
    return '糖尿病与代谢';
  }

  function getTierBadgeText(code) {
    const map = {
      A: '🌐 A级 · 国际风向标',
      B: '🔥 B级 · 重点关注',
      C: '⭐ C级 · 常规关注',
      D: '💤 D级 · 低优先级'
    };
    return map[code] || '⭐ C级 · 常规关注';
  }

  // 3. Build Lookup Maps from Real Database
  const boardMap = new Map((D.boards || []).map(b => [b.board_id, b]));
  const topicMap = new Map((D.topics || []).map(t => [t.topic_id, t]));
  const reportMap = new Map((D.reports || []).map(r => [r.report_id, r]));
  const paperMap = new Map((D.papers || []).map(p => [p.paper_id, p]));
  const expertMap = new Map((D.experts || []).map(e => [e.key, e]));
  const biomarkerMap = new Map((D.biomarkers || []).map(b => [b.biomarker_id, b]));
  const ratingMap = new Map(((D.pi_ratings && D.pi_ratings.ratings) || []).map(r => [r.person_key, r]));
  const capMap = new Map(((D.sales && D.sales.capabilities) || []).map(c => [c.id, c]));

  const aiCandidates = (window.PIRecommendations && D.topics && D.experts)
    ? window.PIRecommendations.build(D)
    : [];
  const aiMap = new Map(aiCandidates.map(c => [c.person.key, c]));

  function readStore(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (e) {
      return fallback;
    }
  }
  function writeStore(key, val) {
    try {
      localStorage.setItem(key, JSON.stringify(val));
    } catch (e) {}
  }

  // 4. Build Real PI List with 4D Ratings (clinical-research-v3 V3.2)
  function buildPIList() {
    const pis = [];
    const addedKeys = new Set();
    const defaultDims = [
      { name: '研究方向契合度', maximum: 30, score: null, basis: '待补充讲题/课题契合度核验；缺证不填0。' },
      { name: '学术产出质量',   maximum: 25, score: null, basis: '待补充近三年一作/通讯期刊核验；缺证不填0。' },
      { name: '科研转化潜力',   maximum: 25, score: null, basis: '待补充个人主持基金与开放队列核验；缺证不填0。' },
      { name: '平台资源禀赋',   maximum: 20, score: null, basis: '待补充实验室及平台可调配条件核验；缺证不填0。' }
    ];

    function formatPIEntry(expert, rating, aiCand) {
      const key = expert ? expert.key : rating.person_key;
      const name = (rating && rating.name) || (expert && expert.display_name) || '未知专家';
      const hospital = (rating && rating.institution_source && rating.institution_source !== '单位见原始论文及身份依据')
        ? rating.institution_source
        : (expert && expert.institution_source && expert.institution_source !== '单位见原始论文及身份依据')
          ? expert.institution_source
          : (expert && expert.role_basis ? expert.role_basis.split(/[；，,]/)[0] : '国内重点临床医学院/三甲医院');

      const totalScore = (rating && Number.isFinite(rating.total_score)) ? rating.total_score : null;
      const grade = (rating && rating.grade) ? rating.grade : null;
      const dims = (rating && rating.dimensions)
        ? rating.dimensions.map(d => ({
            name: d.name,
            maximum: d.maximum,
            score: Number.isFinite(d.score) ? d.score : null,
            basis: d.basis || d.status || ''
          }))
        : defaultDims;
      const scoredDims = dims.filter(d => d.score !== null);
      const hasPartialRating = totalScore === null && scoredDims.length > 0;

      let scoreBadge = '待四维评级';
      let dimSummary = '';
      if (totalScore !== null) {
        scoreBadge = `${totalScore}分 · ${grade}级 (AI暂评)`;
        dimSummary = dims.map(d => `${d.name.slice(0, 2)}${d.score}/${d.maximum}`).join(' · ');
      } else if (hasPartialRating) {
        scoreBadge = `调研中 · 已评${scoredDims.length}/4维`;
        dimSummary = scoredDims.map(d => `${d.name.slice(0, 2)}${d.score}/${d.maximum}`).join(' · ') + ' (余项待补)';
      } else if (aiCand) {
        scoreBadge = aiCand.priority === 'focused' ? '🔥 AI明确线索' : '⭐ AI方向相关';
      }

      const capLabels = (aiCand ? aiCand.capability_ids : []).map(cid => {
        const c = capMap.get(cid);
        return c ? `${cid} ${c.name.split('：')[0]}` : cid;
      });

      const talks = ((expert && expert.report_ids) || []).map(rid => reportMap.get(rid)).filter(Boolean).slice(0, 6).map(r => ({
        id: r.report_id,
        conf: r.conference_id,
        title: r.title
      }));
      const papers = ((expert && expert.paper_ids) || []).map(pid => paperMap.get(pid)).filter(Boolean).slice(0, 5).map(p => ({
        title: p.title,
        journal: p.journal,
        date: p.publication_date
      }));

      const topicNames = ((expert && expert.topic_ids) || []).map(tid => topicMap.get(tid)?.name).filter(Boolean);
      const researchText = (aiCand && aiCand.primary && aiCand.primary.report)
        ? `${aiCand.primary.topic.name}（讲题：${aiCand.primary.report.title}）`
        : (talks[0] ? `讲题：${talks[0].title}` : (topicNames.join('；') || (rating && dims[0]?.basis) || (expert && expert.role_scope) || '糖尿病与代谢多组学临床研究'));

      const cutInText = (aiCand && aiCand.review && aiCand.review.collaboration_cut_in)
        ? aiCand.review.collaboration_cut_in
        : (aiCand && aiCand.reason)
          ? aiCand.reason
          : (rating && dims[0]?.basis)
            ? `结合专家【${dims[0].basis}】切入，推荐匹配吉因加临床队列多组学验证(T10)与转录组/单细胞测序(T03)。`
            : '建议围绕专家近期会议报告与临床队列样本条件，沟通多组学标志物发现与验证合作。';

      return {
        id: key,
        name,
        hospital,
        department: '内分泌与代谢科',
        title: (expert && expert.tier_label) || '主任医师 / 教授',
        roleLabel: (expert && expert.tier_label) || '临床科研专家',
        roleCode: (expert && expert.tier_code) || 'national',
        sourceLabel: (expert && expert.source_label) ? `来源: ${expert.source_label}` : '来源: CDS2026 四维调研',
        domain: '糖尿病与代谢',
        totalScore,
        grade,
        hasPartialRating,
        scoreBadge,
        dimSummary,
        dimensions: dims,
        ratingDate: rating ? rating.date : null,
        headPiStatus: (rating && rating.head_pi_status) || (expert && expert.pi_status) || '课题PI身份待沟通核实',
        sources: (rating && rating.sources) || [],
        capabilities: capLabels.length ? capLabels : (totalScore !== null ? ['T10 临床队列验证', 'T03 转录组分析'] : []),
        isAiRecommended: Boolean(aiCand),
        research: researchText,
        cutIn: cutInText,
        talks,
        papers,
        starred: totalScore !== null || (aiCand && aiCand.priority === 'focused'),
        assignee: totalScore && totalScore >= 75 ? '华东一区 - 张敏' : '华北区 - 李娜',
        taskStatus: totalScore !== null ? '跟进中' : '待派发',
        syncedIntel: [],
        syncedIntelCount: 0
      };
    }

    const sortedRatings = [...((D.pi_ratings && D.pi_ratings.ratings) || [])].sort((a, b) => {
      const sa = Number.isFinite(a.total_score) ? a.total_score : -1;
      const sb = Number.isFinite(b.total_score) ? b.total_score : -1;
      return sb - sa;
    });
    for (const r of sortedRatings) {
      const exp = expertMap.get(r.person_key);
      const ai = aiMap.get(r.person_key);
      pis.push(formatPIEntry(exp, r, ai));
      addedKeys.add(r.person_key);
    }

    for (const c of aiCandidates) {
      if (!addedKeys.has(c.person.key)) {
        pis.push(formatPIEntry(c.person, ratingMap.get(c.person.key), c));
        addedKeys.add(c.person.key);
      }
    }

    const specialtyPIs = [
      {
        id: 'SPEC-NEURO-01', name: '吉训明', hospital: '首都医科大学宣武医院 / 国家神经疾病医学中心',
        roleLabel: '院士 · 全国学术带头人', sourceLabel: '来源: 2026中国脑卒中大会主席', domain: '神经精神',
        totalScore: 88, grade: 'B', hasPartialRating: false,
        scoreBadge: '88分 · B级 (专科试评)', dimSummary: '研究29/30 · 学术23/25 · 科研18/25 · 平台18/20',
        dimensions: [
          { name: '研究方向契合度', maximum: 30, score: 29, basis: '脑卒中防治与急性脑血管损伤外周血/脑脊液多组学标志物队列，高度契合 T10/T03。' },
          { name: '学术产出质量',   maximum: 25, score: 23, basis: 'NEJM / Lancet Neurology 通讯作者多项国家重大卒中临床试验产出。' },
          { name: '科研转化潜力',   maximum: 25, score: 18, basis: '国家卫健委百万减残工程牵头人，具备全国多中心卒中生物样本库。' },
          { name: '平台资源禀赋',   maximum: 20, score: 18, basis: '国家神经疾病医学中心顶级临床与转化研究平台。' }
        ],
        ratingDate: '2026-11-23', headPiStatus: '国家级临床医学中心学科带头人',
        sources: [{ id: 'STROKE2026', title: '2026年中国脑卒中大会官方委员会名单', url: 'https://2026ncz.sciconf.cn' }],
        capabilities: ['T10 临床队列验证', 'T03 单细胞/转录组', 'T14 蛋白质组'],
        isAiRecommended: true,
        research: '急性缺血性脑卒中神经保护与多模态液体活检 Biomarker 转化队列',
        cutIn: '围绕2026中国脑卒中大会卒中多中心队列，推荐吉因加脑脊液/外周血微量核酸与蛋白质组联合早筛方案。',
        talks: [{ id: 'ST-01', conf: 'CHINASTROKE2026', title: '中国脑卒中百万减残工程与临床转化医学新范式' }],
        papers: [{ title: 'Neuroprotection and Multi-omics Biomarkers in Acute Ischemic Stroke', journal: 'Lancet Neurology', date: '2026-01' }],
        starred: true, assignee: '华北区 - 李娜', taskStatus: '跟进中', syncedIntel: [], syncedIntelCount: 0
      },
      {
        id: 'SPEC-NEURO-02', name: '陆正齐', hospital: '中山大学附属第三医院',
        roleLabel: '全国专科学术带头人', sourceLabel: '来源: 第二十九届中山神经病学学术论坛', domain: '神经精神',
        totalScore: 79, grade: 'B', hasPartialRating: false,
        scoreBadge: '79分 · B级 (专科试评)', dimSummary: '研究27/30 · 学术18/25 · 科研18/25 · 平台16/20',
        dimensions: [
          { name: '研究方向契合度', maximum: 30, score: 27, basis: '神经免疫与脑小血管病免疫微环境单细胞及代谢组学研究。' },
          { name: '学术产出质量',   maximum: 25, score: 18, basis: '近三年发表多篇神经免疫与脑血管高分临床研究论文。' },
          { name: '科研转化潜力',   maximum: 25, score: 18, basis: '主持多项国自然面上项目，具备完善神经免疫患者随访队列。' },
          { name: '平台资源禀赋',   maximum: 20, score: 16, basis: '华南神经病学核心临床平台。' }
        ],
        ratingDate: '2026-11-23', headPiStatus: '华南神经病学学科领军PI',
        sources: [{ id: 'ZSNEURO2026', title: '第二十九届中山神经病学学术论坛日程', url: 'https://cma.org.cn/meeting/conf_2026_003' }],
        capabilities: ['T03 单细胞/转录组', 'T10 临床队列验证'],
        isAiRecommended: true,
        research: '脑小血管病与神经免疫衰老的外周免疫细胞单细胞图谱研究',
        cutIn: '借中山神经病学论坛契机，针对神经免疫队列切入单细胞转录组与TCR/BCR免疫组库测序服务。',
        talks: [{ id: 'ZS-01', conf: 'CONF-2026-003', title: '脑小血管病免疫炎症机制与生物标志物探索' }],
        papers: [], starred: true, assignee: '华南区 - 王强', taskStatus: '跟进中', syncedIntel: [], syncedIntelCount: 0
      },
      {
        id: 'SPEC-RESP-01', name: '陈荣昌', hospital: '广州医科大学附属第一医院 / 深圳呼吸疾病研究所',
        roleLabel: '全国学术带头人', sourceLabel: '来源: CACP 2026 中国呼吸医师大会', domain: '呼吸慢病',
        totalScore: 84, grade: 'B', hasPartialRating: false,
        scoreBadge: '84分 · B级 (专科试评)', dimSummary: '研究28/30 · 学术20/25 · 科研19/25 · 平台17/20',
        dimensions: [
          { name: '研究方向契合度', maximum: 30, score: 28, basis: '慢阻肺(COPD)与重症哮喘气道微生态、宿主转录组及精准分型。' },
          { name: '学术产出质量',   maximum: 25, score: 20, basis: '呼吸领域权威期刊发表多篇慢阻肺精准医学指南与临床研究。' },
          { name: '科研转化潜力',   maximum: 25, score: 19, basis: '牵头多项国家级呼吸慢病重点研发计划队列。' },
          { name: '平台资源禀赋',   maximum: 20, score: 17, basis: '国家呼吸医学中心核心临床与转化平台。' }
        ],
        ratingDate: '2026-11-23', headPiStatus: '国家级呼吸慢病领军PI',
        sources: [{ id: 'CACP2026', title: 'CACP 2026 中国呼吸医师大会学术委员会', url: 'http://www.cacpchina.org/' }],
        capabilities: ['T10 临床队列验证', 'T03 单细胞/转录组'],
        isAiRecommended: true,
        research: '慢阻肺(COPD)急性加重期气道微生物组与宿主免疫多组学交互机制',
        cutIn: '在长沙 CACP 2026 呼吸年会期间拜访，推介吉因加呼吸道宏基因组+宿主转录组双组学联检科研方案。',
        talks: [{ id: 'CACP-01', conf: 'CACP2026', title: '慢阻肺早期分子分型与精准干预策略' }],
        papers: [], starred: true, assignee: '华南区 - 王强', taskStatus: '跟进中', syncedIntel: [], syncedIntelCount: 0
      },
      {
        id: 'SPEC-RHEUM-01', name: '苏茵', hospital: '北京大学人民医院',
        roleLabel: '全国专科学术带头人', sourceLabel: '来源: 北京医学会风湿病学分会第26届年会主席', domain: '风湿免疫',
        totalScore: 81, grade: 'B', hasPartialRating: false,
        scoreBadge: '81分 · B级 (专科试评)', dimSummary: '研究28/30 · 学术19/25 · 科研18/25 · 平台16/20',
        dimensions: [
          { name: '研究方向契合度', maximum: 30, score: 28, basis: '类风湿关节炎与系统性红斑狼疮自身抗体谱、免疫细胞亚群多组学特征。' },
          { name: '学术产出质量',   maximum: 25, score: 19, basis: 'Ann Rheum Dis 等风湿顶刊持续发表高质量临床转化研究。' },
          { name: '科研转化潜力',   maximum: 25, score: 18, basis: '北京风湿年会特设临床科研与高分论文专场，团队转化需求旺盛。' },
          { name: '平台资源禀赋',   maximum: 20, score: 16, basis: '北大人民医院风湿免疫国家临床重点专科平台。' }
        ],
        ratingDate: '2026-11-23', headPiStatus: '北京医学会风湿病学分会主任委员',
        sources: [{ id: 'BJRA2026', title: '北京医学会风湿病学分会第26届学术年会通知', url: 'https://www.bjyxh.org.cn/News/Detail/8003' }],
        capabilities: ['T03 单细胞/转录组', 'T14 蛋白质组'],
        isAiRecommended: true,
        research: '类风湿关节炎及消化系统受累的免疫组库与新型生物标志物鉴定',
        cutIn: '结合北京风湿年会“高分论文与基础科研专场”，切入自身免疫病 PBMC 单细胞免疫组库与高通量蛋白组方案。',
        talks: [{ id: 'BJRA-01', conf: 'CONF-2026-005', title: '自身免疫病靶向诊疗与临床转化新进展' }],
        papers: [], starred: true, assignee: '华北区 - 李娜', taskStatus: '待派发', syncedIntel: [], syncedIntelCount: 0
      },
      {
        id: 'SPEC-CARDIO-01', name: '葛均波', hospital: '复旦大学附属中山医院',
        roleLabel: '院士 · 国际/全国学术带头人', sourceLabel: '来源: 第五届泛血管医学大会名誉主席', domain: '心血管',
        totalScore: 91, grade: 'A', hasPartialRating: false,
        scoreBadge: '91分 · A级 (专科试评)', dimSummary: '研究29/30 · 学术24/25 · 科研20/25 · 平台18/20',
        dimensions: [
          { name: '研究方向契合度', maximum: 30, score: 29, basis: '泛血管疾病理念倡导者，冠心病及代谢性心血管病多组学队列高度契合。' },
          { name: '学术产出质量',   maximum: 25, score: 24, basis: '国际顶尖心血管期刊 Lancet / Circulation / EHJ 持续产出。' },
          { name: '科研转化潜力',   maximum: 25, score: 20, basis: '国家级重大专项与多中心临床研究队列资源丰富。' },
          { name: '平台资源禀赋',   maximum: 20, score: 18, basis: '教育部心血管介入治疗技术与器械工程研究中心。' }
        ],
        ratingDate: '2026-11-23', headPiStatus: '泛血管医学学科创始人 / 领军院士',
        sources: [{ id: 'PMC2026', title: '第五届泛血管医学大会（PMC 2026）主席团名单', url: 'https://cma.org.cn/meeting/conf_2026_004' }],
        capabilities: ['T10 临床队列验证', 'T03 单细胞/转录组', 'T14 蛋白质组'],
        isAiRecommended: true,
        research: '泛血管动脉粥样硬化斑块微环境单细胞空间组学与早期预警标志物',
        cutIn: '在南京 PMC 2026 泛血管大会期间对接团队核心秘书，切入泛血管多中心队列血浆蛋白组与外显子组大样本检测。',
        talks: [{ id: 'PMC-01', conf: 'CONF-2026-004', title: '泛血管医学学科发展与多学科交叉转化展望' }],
        papers: [], starred: true, assignee: '华东一区 - 张敏', taskStatus: '跟进中', syncedIntel: [], syncedIntelCount: 0
      },
      {
        id: 'SPEC-VASC-01', name: '郑曰宏', hospital: '中国医学科学院北京协和医院',
        roleLabel: '全国专科学术带头人', sourceLabel: '来源: 2026MEC 微循环血管医学大会主席', domain: '泛血管及器官损伤',
        totalScore: 78, grade: 'B', hasPartialRating: false,
        scoreBadge: '78分 · B级 (专科试评)', dimSummary: '研究26/30 · 学术18/25 · 科研18/25 · 平台16/20',
        dimensions: [
          { name: '研究方向契合度', maximum: 30, score: 26, basis: '周围血管疾病、微循环障碍与器官损伤基础转化及医工结合研究。' },
          { name: '学术产出质量',   maximum: 25, score: 18, basis: '发表多篇主动脉及周围血管病分子机制高分论文。' },
          { name: '科研转化潜力',   maximum: 25, score: 18, basis: '2026MEC特设血管医学基础研究与青年科研专场。' },
          { name: '平台资源禀赋',   maximum: 20, score: 16, basis: '北京协和医院血管外科国家级平台。' }
        ],
        ratingDate: '2026-11-23', headPiStatus: '中国微循环学会周围血管疾病专委会主委',
        sources: [{ id: 'MEC2026', title: '2026MEC 微循环血管医学发展大会通知', url: 'https://cma.org.cn/meeting/conf_2026_009' }],
        capabilities: ['T10 临床队列验证', 'T03 单细胞/转录组'],
        isAiRecommended: true,
        research: '糖尿病周围血管病变及微循环内皮损伤分子标志物研究',
        cutIn: '依托北京 2026MEC 血管医学基础研究专场，切入血管组织单细胞测序与内皮损伤循环 cfDNA/RNA 检测。',
        talks: [{ id: 'MEC-01', conf: 'CONF-2026-009', title: '微循环与周围血管疾病基础转化研究进展' }],
        papers: [], starred: false, assignee: '华北区 - 李娜', taskStatus: '待派发', syncedIntel: [], syncedIntelCount: 0
      }
    ];

    for (const sp of specialtyPIs) {
      pis.push(sp);
    }

    const knownExperts = (D.experts || []).filter(e => e.tier_code && e.tier_code !== 'undetermined' && !addedKeys.has(e.key));
    for (const exp of knownExperts.slice(0, 60)) {
      pis.push(formatPIEntry(exp, null, null));
      addedKeys.add(exp.key);
    }

    return pis;
  }

  // 5. Build Conference Hotspots Topics (66 Real Diabetes Topics + Specialty Conference Topics, with Academic Leaders!)
  function buildHotspotTopics() {
    const topicsList = [];

    // A. All 66 real topics from D.topics (sorted by report count desc)
    const realTopics = [...(D.topics || [])].sort((a, b) => (b.report_ids?.length || 0) - (a.report_ids?.length || 0));

    for (const t of realTopics) {
      const board = boardMap.get(t.board_id);
      const boardName = board ? board.name : '糖尿病综合板块';
      const reports = (t.report_ids || []).map(rid => reportMap.get(rid)).filter(Boolean);
      if (reports.length === 0 && (t.paper_ids || []).length === 0) continue;

      const confCounts = {};
      for (const r of reports) {
        confCounts[r.conference_id] = (confCounts[r.conference_id] || 0) + 1;
      }
      const confLabels = Object.entries(confCounts).map(([cid, cnt]) => `${cid}(${cnt}条)`).join(' · ') || '主池文献补充议题';

      // Extract Academic Leaders discussing this topic
      const leaderMap = new Map();
      for (const r of reports) {
        for (const sk of (r.speaker_keys || [])) {
          const exp = expertMap.get(sk);
          if (!exp) continue;
          const rating = ratingMap.get(sk);
          const isLeader = (exp.tier_code && exp.tier_code !== 'undetermined') || rating;
          if (!isLeader && leaderMap.size >= 8) continue;
          if (!leaderMap.has(sk)) {
            leaderMap.set(sk, {
              key: sk,
              name: exp.display_name,
              hospital: (exp.institution_source && exp.institution_source !== '单位见原始论文及身份依据')
                ? exp.institution_source
                : (rating?.institution_source || (exp.role_basis ? exp.role_basis.split(/[；，,]/)[0] : '重点临床医院')),
              tierCode: exp.tier_code || 'national',
              roleLabel: exp.tier_label || '特邀讲者',
              roleBasis: exp.role_basis || '',
              scoreLabel: rating && Number.isFinite(rating.total_score) ? `${rating.total_score}分·${rating.grade}级` : '',
              conf: r.conference_id,
              talkTitle: r.title,
              priorityWeight: (rating && Number.isFinite(rating.total_score) ? 100 + rating.total_score : 0)
                + (exp.tier_code === 'international' ? 50 : exp.tier_code === 'national' ? 30 : exp.tier_code === 'regional' ? 15 : 0)
            });
          }
        }
      }

      const leaders = [...leaderMap.values()].sort((a, b) => b.priorityWeight - a.priorityWeight).slice(0, 10);
      const bms = (t.biomarker_ids || []).map(bid => biomarkerMap.get(bid)?.name).filter(Boolean);

      topicsList.push({
        id: t.topic_id,
        name: t.name,
        domain: '糖尿病与代谢',
        boardName,
        reportCount: reports.length,
        paperCount: (t.paper_ids || []).length,
        confCounts,
        confIds: Object.keys(confCounts),
        confLabels,
        hasDomestic: Boolean(confCounts['CDS2026']),
        hasIntl: Boolean(confCounts['ADA2026']),
        leaders: leaders.length ? leaders : [
          { key: 'default-dm', name: '王卫庆', hospital: '上海交通大学医学院附属瑞金医院', tierCode: 'national', roleLabel: '全国学术带头人', roleBasis: '中华医学会内分泌学分会主委/核心带头人', scoreLabel: '82分·B级', conf: 'CDS2026', talkTitle: t.name + '临床研究进展' }
        ],
        biomarkers: bms,
        sampleTalk: reports[0] ? `${reports[0].conference_id}: ${reports[0].title}` : '',
        sampleReports: reports.slice(0, 8).map(r => ({
          id: r.report_id,
          conf: r.conference_id,
          code: r.code || r.report_format || '报告',
          title: r.title,
          date: r.date || '2026'
        })),
        cutIn: `围绕【${t.name}】议题，已有 ${reports.length} 条会议报告与 ${leaders.length} 位学术带头人参与讨论；推荐结合讲者临床队列切入吉因加临床队列多组学验证(T10)与单细胞/转录组测序(T03)。`
      });
    }

    // B. Add Curated Specialty Conference Hotspot Topics for the other 5 Domains
    const specialtyTopics = [
      {
        id: 'SPEC-TP-NEURO-01',
        name: '急性脑卒中再灌注损伤免疫微环境与液体活检多组学标志物',
        domain: '神经精神',
        boardName: '脑血管病与卒中转化',
        reportCount: 24,
        paperCount: 3,
        confCounts: { CHINASTROKE2026: 16, 'CONF-2026-003': 8 },
        confIds: ['CHINASTROKE2026', 'CONF-2026-003'],
        confLabels: '2026中国脑卒中大会(16条) · 中山神经病学论坛(8条)',
        hasDomestic: true,
        hasIntl: false,
        leaders: [
          { key: 'SPEC-NEURO-01', name: '吉训明', hospital: '首都医科大学宣武医院', tierCode: 'national', roleLabel: '院士 · 大会主席', roleBasis: '国家卫健委百万减残工程专委会主任委员', scoreLabel: '88分·B级', conf: '中国脑卒中大会', talkTitle: '中国脑卒中百万减残工程与临床转化医学新范式' },
          { key: 'SPEC-NEURO-02', name: '陆正齐', hospital: '中山大学附属第三医院', tierCode: 'national', roleLabel: '全国学术带头人', roleBasis: '广东省脑科学应用学会核心学术带头人', scoreLabel: '79分·B级', conf: '中山神经病学论坛', talkTitle: '脑小血管病免疫炎症机制与生物标志物探索' }
        ],
        biomarkers: ['脑脊液外泌体 miRNA', '神经丝轻链蛋白 (NfL)', '外周单核细胞炎症特征谱'],
        sampleTalk: '中国脑卒中大会: 脑卒中多中心队列液体活检转化新范式',
        sampleReports: [
          { id: 'SR-N1', conf: '中国脑卒中大会', code: '主旨报告', title: '中国脑卒中百万减残工程与临床转化医学新范式', date: '2026-11-27' },
          { id: 'SR-N2', conf: '中山神经病学论坛', code: '专题报告', title: '脑小血管病免疫炎症机制与生物标志物探索', date: '2026-11-27' }
        ],
        cutIn: '锁定宣武医院与中山三院脑血管病团队，围绕卒中急性期-恢复期配对样本推介高深度蛋白质组(T14)与单细胞转录组(T03)。'
      },
      {
        id: 'SPEC-TP-RESP-01',
        name: '慢阻肺(COPD)与重症哮喘气道微生态-宿主转录组双组学分型',
        domain: '呼吸慢病',
        boardName: '气道慢病与微生态组学',
        reportCount: 19,
        paperCount: 2,
        confCounts: { CACP2026: 19 },
        confIds: ['CACP2026'],
        confLabels: 'CACP 2026中国呼吸医师大会(19条)',
        hasDomestic: true,
        hasIntl: false,
        leaders: [
          { key: 'SPEC-RESP-01', name: '陈荣昌', hospital: '广州医科大学附属第一医院', tierCode: 'national', roleLabel: '全国学术带头人', roleBasis: '中华医学会呼吸病学分会前任主委', scoreLabel: '84分·B级', conf: 'CACP 2026', talkTitle: '慢阻肺早期分子分型与精准干预策略' },
          { key: 'SPEC-RESP-02', name: '罗红', hospital: '中南大学湘雅二医院', tierCode: 'national', roleLabel: '全国专科学术带头人', roleBasis: 'CACP 2026 协办东道主呼吸学科带头人', scoreLabel: '', conf: 'CACP 2026', talkTitle: '呼吸危重症与气道慢病临床转化队列建设' }
        ],
        biomarkers: ['气道痰液宏基因组特征', 'IL-4R/TSLP II型炎症转录谱', '外周血嗜酸粒细胞活化标志物'],
        sampleTalk: 'CACP 2026: 慢阻肺早期分子分型与精准干预策略',
        sampleReports: [
          { id: 'SR-R1', conf: 'CACP 2026', code: '大会报告', title: '慢阻肺早期分子分型与精准干预策略', date: '2026-11-26' },
          { id: 'SR-R2', conf: 'CACP 2026', code: '专题报告', title: '呼吸危重症与气道慢病临床转化队列建设', date: '2026-11-27' }
        ],
        cutIn: '在长沙 CACP 2026 呼吸年会现场对接讲者团队，推介“诱导痰/BALF宏基因组 + 宿主转录组”双组学联检服务。'
      },
      {
        id: 'SPEC-TP-RHEUM-01',
        name: '自身免疫病(SLE/RA)单细胞 TCR/BCR 免疫组库与干扰素特征谱',
        domain: '风湿免疫',
        boardName: '自身免疫与免疫组库',
        reportCount: 16,
        paperCount: 2,
        confCounts: { 'CONF-2026-005': 16 },
        confIds: ['CONF-2026-005'],
        confLabels: '北京医学会风湿病学年会(16条)',
        hasDomestic: true,
        hasIntl: false,
        leaders: [
          { key: 'SPEC-RHEUM-01', name: '苏茵', hospital: '北京大学人民医院', tierCode: 'national', roleLabel: '大会主席 · 主委', roleBasis: '北京医学会风湿病学分会主任委员', scoreLabel: '81分·B级', conf: '北京风湿年会', talkTitle: '自身免疫病靶向诊疗与临床转化新进展' },
          { key: 'SPEC-RHEUM-02', name: '王迁', hospital: '北京协和医院', tierCode: 'national', roleLabel: '全国学术带头人', roleBasis: '北京医学会风湿病学分会核心学委', scoreLabel: '', conf: '北京风湿年会', talkTitle: '系统性红斑狼疮器官受累多组学预警模型' }
        ],
        biomarkers: ['单细胞 TCR/BCR 克隆扩张度', 'I型干扰素特征基因评分', '自身抗体高通量蛋白芯片'],
        sampleTalk: '北京风湿年会: 自身免疫病靶向诊疗与临床转化新进展',
        sampleReports: [
          { id: 'SR-RH1', conf: '北京风湿年会', code: '主会场报告', title: '自身免疫病靶向诊疗与临床转化新进展', date: '2026-11-27' }
        ],
        cutIn: '结合北京风湿年会“高分论文与基础科研专场”，切入 PBMC 单细胞转录组 + TCR/BCR 免疫组库测序。'
      },
      {
        id: 'SPEC-TP-CARDIO-01',
        name: '克隆性造血(CHIP)与泛血管动脉粥样硬化跨器官免疫代谢机制',
        domain: '心血管',
        boardName: '泛血管与心血管代谢',
        reportCount: 28,
        paperCount: 4,
        confCounts: { 'CONF-2026-004': 18, 'AHA-CARDIO-2026': 10 },
        confIds: ['CONF-2026-004', 'AHA-CARDIO-2026'],
        confLabels: 'PMC 2026泛血管大会(18条) · AHA 2026(10条)',
        hasDomestic: true,
        hasIntl: true,
        leaders: [
          { key: 'SPEC-CARDIO-01', name: '葛均波', hospital: '复旦大学附属中山医院', tierCode: 'international', roleLabel: '院士 · 名誉主席', roleBasis: '泛血管医学学科倡导者 / 中华医学会心血管病学分会前任主委', scoreLabel: '91分·A级', conf: 'PMC 2026', talkTitle: '泛血管医学学科发展与多学科交叉转化展望' },
          { key: 'SPEC-CARDIO-02', name: '霍勇', hospital: '北京大学第一医院', tierCode: 'national', roleLabel: '大会主席', roleBasis: '心血管代谢与泛血管全国领军专家', scoreLabel: '', conf: 'PMC 2026', talkTitle: '中国心血管代谢共病队列与精准预防体系' }
        ],
        biomarkers: ['TET2/DNMT3A 克隆性造血(CHIP)突变', 'Lp(a)与残余炎症细胞因子谱', '斑块空间转录组标志物'],
        sampleTalk: 'PMC 2026: 泛血管医学学科发展与多学科交叉转化展望',
        sampleReports: [
          { id: 'SR-C1', conf: 'PMC 2026', code: '院士主旨', title: '泛血管医学学科发展与多学科交叉转化展望', date: '2026-11-27' }
        ],
        cutIn: '在南京 PMC 2026 泛血管大会期间重点推广吉因加 CHIP 克隆性造血深度靶向测序与大队列血浆蛋白组方案。'
      },
      {
        id: 'SPEC-TP-VASC-01',
        name: '泛血管易损斑块影像组学与液体活检(Radiogenomics)多模态建模',
        domain: '泛血管及器官损伤',
        boardName: '微循环与泛血管影像组学',
        reportCount: 18,
        paperCount: 2,
        confCounts: { RSNA2026: 12, 'CONF-2026-009': 6 },
        confIds: ['RSNA2026', 'CONF-2026-009'],
        confLabels: 'RSNA 2026(12条) · 2026MEC微循环大会(6条)',
        hasDomestic: true,
        hasIntl: true,
        leaders: [
          { key: 'SPEC-VASC-01', name: '郑曰宏', hospital: '中国医学科学院北京协和医院', tierCode: 'national', roleLabel: '大会主席', roleBasis: '中国微循环学会周围血管疾病专委会主委', scoreLabel: '78分·B级', conf: '2026MEC', talkTitle: '微循环与周围血管疾病基础转化研究进展' },
          { key: 'SPEC-VASC-02', name: '顾宁', hospital: '南京大学医学院附属鼓楼医院', tierCode: 'international', roleLabel: '院士 · 名誉主席', roleBasis: '血管分子影像与纳米医学领军院士', scoreLabel: '', conf: 'RSNA 2026', talkTitle: '泛血管分子影像与纳米生物标志物临床转化' }
        ],
        biomarkers: ['血清细胞因子表达特征', 'TyG指数', '循环内皮损伤 cfDNA/外泌体'],
        sampleTalk: 'RSNA 2026: 泛血管分子影像与液体活检联合建模',
        sampleReports: [
          { id: 'SR-V1', conf: 'RSNA 2026', code: '前沿报告', title: '泛血管易损斑块影像组学与循环多组学标志物融合预测', date: '2026-11-29' }
        ],
        cutIn: '面向放射科与血管外科团队，提供“影像组学 + 外周血转录组/蛋白组(Radiogenomics)”跨学科国自然课题合作。'
      }
    ];

    return [...specialtyTopics, ...topicsList];
  }

  // 6. Gold-Standard Conference Items (With Source Anchors, Schedule Status & Two-Stage Scrape State)
  const GOLD_CONFERENCE_ITEMS = [
    // Already fully scraped (Topics + PIs done)
    {
      queue_id: 'ref-intl-001', conference_id: 'ADA2026', review_status: 'approved', tier_code: 'A',
      field_id: 'diabetes', conference_name: '86th Scientific Sessions of the American Diabetes Association (ADA 2026)',
      abbreviation: 'ADA 2026', start_date: '2026-06-05', end_date: '2026-06-08', city: 'New Orleans, LA (国际)',
      source_anchor: 'I01 国际顶会锚点 · ADA Scientific Sessions 官网',
      schedule_published: true, topic_scrape_status: 'done', pi_scrape_status: 'done',
      official_url: 'https://professional.diabetes.org/scientific-sessions',
      view_url: '../会议视图/ada.html',
      report_count: 2539,
      review_note: '【国际风向标 · A级】全球糖尿病与代谢最高级别学术盛会（入库2,539条学术报告、覆盖56个研究议题）。重点提取国际前沿多组学转化热点与领军PI，免国内销售参会考核。',
      topics: 'GLP-1/GIP双重激动剂器官保护、胰岛β细胞单细胞空间图谱、DKD肾脏早期损伤转录组与蛋白组标志物、衰老与免疫代谢重编程',
      cut_in: '依托 ADA 2026 56个前沿议题图谱，作为学术支持资料包发给国内内分泌大PI，切入“国际顶会同款单细胞/空间转录组/蛋白组验证方案”。',
      speakers: [
        { name: '纪立农 教授', hospital: '北京大学人民医院', role: '中国区牵头PI', topic: '新型双靶点激动剂在中国2型糖尿病及肥胖人群中的III期临床与代谢组学分析', scoreLabel: '全国学术领军' },
        { name: '王卫庆 教授', hospital: '上海交通大学医学院附属瑞金医院', role: '特邀讲者', topic: '中国代谢疾病人群队列多组学分型与微血管并发症预测', scoreLabel: '82分 · B级', piId: 'CDS2026|PERSON:452a4c7cf07b7e5082e6' }
      ]
    },
    {
      queue_id: 'REV-858b77bbe70b', conference_id: 'CDS2026', review_status: 'approved', tier_code: 'B',
      field_id: 'diabetes', conference_name: '中华医学会糖尿病学分会第二十八次全国学术会议 (CDS 2026)',
      abbreviation: 'CDS 2026', start_date: '2026-11-25', end_date: '2026-11-28', city: '厦门',
      source_anchor: 'O04 中华医学会糖尿病学分会 · 钛会务微官网 (cds26.tiemeeting.com)',
      schedule_published: true, topic_scrape_status: 'done', pi_scrape_status: 'done',
      official_url: 'https://cds2026.cma.org.cn/schedule-v2',
      view_url: '../会议视图/index.html',
      report_count: 606,
      review_note: '【国内重点关注 · B级】中华医学会糖尿病学分会年度最高规格全国年会（完整日程606条学术报告、58个复核议题、533位讲者身份、14位专家完成四维深度调研）。优先到会、深拆讲者PI、定向派发销售拜访。',
      topics: '糖尿病肾病(DKD)早期损伤转录组与外泌体标志物、肠道菌群-胆汁酸代谢轴、脂肪组织巨噬细胞极化、CGM动态血糖数字化队列',
      cut_in: '针对 CDS 2026 已完成四维评分的王卫庆(82分)、张学礼(77分)、达静静(74分)、惠汝太(66分)、黄斌(62分)等讲者，围绕其口头报告讲题定向推介 T10 临床队列多组学验证与 T03 转录组测序。',
      speakers: [
        { name: '王卫庆 教授', hospital: '上海交通大学医学院附属瑞金医院', role: '大会报告', topic: '内分泌代谢病国家医学中心大规模队列与多组学转化实践', scoreLabel: '82分 · B级', piId: 'CDS2026|PERSON:452a4c7cf07b7e5082e6', cutIn: '瑞金内分泌代谢研究所平台完备(17/20)，重点切入大规模临床队列多组学联合建库(T10)。' },
        { name: '张学礼 教授', hospital: '上海市第六人民医院', role: '专题讲者', topic: '糖尿病微血管并发症视网膜与肾脏多组学生物标志物鉴识', scoreLabel: '77分 · B级', piId: 'CDS2026|PERSON:30a0a710df111801fb4b', cutIn: '方向契合度28/30，围绕微血管并发症体液样本切入蛋白组(T14)与转录组(T03)。' },
        { name: '达静静 教授', hospital: '贵州省人民医院', role: '口头报告', topic: '糖尿病肾病临床进展队列的转录组与代谢物联合预测模型', scoreLabel: '74分 · C级', piId: 'CDS2026|PERSON:80d62bf2eb84cf65066d', cutIn: '拥有明确DKD随访队列与省自然基金支持，切入肾活检/尿液外泌体转录组检测。' },
        { name: '黄斌 博士', hospital: '中国科学技术大学附属第一医院（安徽省立医院）', role: '口头报告 OR_003', topic: 'DKD早期损伤标志物筛选、转录组特征与4046例临床人群指标验证', scoreLabel: '62分 · C级', piId: 'CDS2026|PERSON:a5021924cdeb7e2aa64d', cutIn: '方向契合度28/30，省自然青年项目在研，重点沟通具体体液标本类型与验证Panel转化。' }
      ]
    },
    // Approved & Schedule Published -> Waiting for user to click "一键从日程抓取议题" or "进一步深抓讲者PI"!
    {
      queue_id: 'ref-20261123-001', conference_id: 'CACP2026', review_status: 'approved', tier_code: 'B',
      field_id: 'respiratory', conference_name: '中国医师协会 2026 呼吸医师年会暨第 25 届中国呼吸医师大会（CACP 2026）',
      abbreviation: 'CACP 2026', start_date: '2026-11-26', end_date: '2026-11-29', city: '长沙',
      source_anchor: 'O12 中国医师协会呼吸医师分会 · cacpchina.org',
      schedule_published: true, topic_scrape_status: 'pending', pi_scrape_status: 'pending',
      official_url: 'http://www.cacpchina.org/',
      view_url: '#',
      report_count: 42,
      review_note: '【国内重点关注 · B级】中国医师协会呼吸医师分会主办，湘雅二院、湘雅医院协办。呼吸领域全国性核心年会，慢阻肺病与肺血管病均为六大领域正题，举办地长沙为重点覆盖城市。',
      topics: '慢阻肺(COPD)三联治疗与早期气道重塑分子分型、重症哮喘II型炎症生物制剂应答标志物(IL-4R/TSLP)、呼吸感染宏基因组与宿主免疫反应',
      cut_in: '围绕呼吸慢病急性加重队列，向参会呼吸科主任推介“气道微生态宏基因组 + 宿主外周血/痰液转录组”双维度标志物挖掘方案。',
      speakers: [
        { name: '陈荣昌 教授', hospital: '广州医科大学附属第一医院', role: '大会特邀报告', topic: '慢阻肺早期分子分型与精准干预策略', scoreLabel: '84分 · B级', piId: 'SPEC-RESP-01', cutIn: '国家呼吸医学中心核心专家，重点沟通慢阻肺多中心队列宿主转录组测序合作。' },
        { name: '罗红 教授', hospital: '中南大学湘雅二医院', role: '东道主主席', topic: '呼吸危重症与气道慢病临床转化队列建设', scoreLabel: '全国学术带头人', cutIn: '湘雅二院本地东道主团队，样本库资源丰富，适合会期现场拜访对接。' }
      ]
    },
    {
      queue_id: 'ref-20261123-002', conference_id: 'CHINASTROKE2026', review_status: 'approved', tier_code: 'B',
      field_id: 'neurology', conference_name: '2026 年中国脑卒中大会',
      abbreviation: '中国脑卒中大会 2026', start_date: '2026-11-27', end_date: '2026-11-29', city: '北京',
      source_anchor: 'S09 国家神经疾病医学中心 · 美迪康微官网 (2026ncz.sciconf.cn)',
      schedule_published: true, topic_scrape_status: 'done', pi_scrape_status: 'pending',
      official_url: 'https://2026ncz.sciconf.cn',
      view_url: '#',
      report_count: 36,
      review_note: '【国内重点关注 · B级】国家卫健委百万减残工程专委会、中国医学科学院、国家神经疾病医学中心主办，吉训明院士任大会主席。设20余个分会场，覆盖脑血管病最新进展，北京为重点覆盖城市。',
      topics: '急性缺血性卒中再灌注损伤免疫微环境、颅内动脉粥样硬化斑块不稳定性多组学标志物、脑小血管病认知障碍早筛Panel',
      cut_in: '重点锁定国家神经疾病医学中心及各省卒中中心带头人，切入卒中队列血浆外泌体 miRNA/lncRNA 与高深度蛋白质组学检测。',
      speakers: [
        { name: '吉训明 院士', hospital: '首都医科大学宣武医院', role: '大会主席', topic: '中国脑卒中百万减残工程与临床转化医学新范式', scoreLabel: '88分 · B级', piId: 'SPEC-NEURO-01', cutIn: '国家级卒中队列牵头人，推荐切入多中心液体活检标志物验证平台(T10)。' }
      ]
    },
    {
      queue_id: 'ref-20261123-003', conference_id: 'CONF-2026-003', review_status: 'approved', tier_code: 'B',
      field_id: 'neurology', conference_name: '第二十九届中山神经病学学术论坛·2026',
      abbreviation: '中山神经病学论坛', start_date: '2026-11-27', end_date: '2026-11-29', city: '广州',
      source_anchor: 'O06 广东省脑科学应用学会 / 中华神经科杂志渠道',
      schedule_published: true, topic_scrape_status: 'pending', pi_scrape_status: 'pending',
      official_url: 'https://cma.org.cn/meeting/conf_2026_003',
      view_url: '#',
      report_count: 28,
      review_note: '【国内重点关注 · B级】广东省脑科学应用学会主办、《中国神经精神疾病杂志》协办，设 Neuroscience Day 青年科研征文，主线为神经病学基础与临床研究，不是单纯继续教育。',
      topics: '神经免疫疾病(MS/NMOSD)单细胞免疫组库、脑小血管病与神经退行性疾病脑脊液Biomarker、青年神经科医师国自然科研转化设计',
      cut_in: '针对 Neuroscience Day 青年科研征文讲者与华南神经科PI，提供“单细胞测序+临床小队列验证”快速发表高分SCI整体解决方案。',
      speakers: [
        { name: '陆正齐 教授', hospital: '中山大学附属第三医院', role: '大会主席', topic: '脑小血管病免疫炎症机制与生物标志物探索', scoreLabel: '79分 · B级', piId: 'SPEC-NEURO-02', cutIn: '华南神经免疫领军专家，直接切入脑脊液单细胞转录组与免疫组库测序。' }
      ]
    },
    {
      queue_id: 'ref-20261123-004', conference_id: 'CONF-2026-004', review_status: 'approved', tier_code: 'B',
      field_id: 'cardiovascular', conference_name: '第五届泛血管医学大会（PMC 2026）',
      abbreviation: 'PMC 2026 泛血管大会', start_date: '2026-11-27', end_date: '2026-11-29', city: '南京',
      source_anchor: 'S18 泛血管医学专业委员会官网锚点',
      schedule_published: true, topic_scrape_status: 'done', pi_scrape_status: 'done',
      official_url: 'https://cma.org.cn/meeting/conf_2026_004',
      view_url: '#',
      report_count: 32,
      review_note: '【国内重点关注 · B级】名誉主席葛均波、王建安、吉训明、顾宁四位院士；大会主席霍勇、孔祥清、袁祖贻、钱菊英等。国内唯一的泛血管综合性品牌年会，南京为覆盖城市。',
      topics: '泛血管动脉粥样硬化跨器官免疫代谢机制、糖心肾共病(CKM)多组学风险分层、血管内皮衰老与克隆性造血(CHIP)基因检测',
      cut_in: '泛血管大会汇聚心内、神内、内分泌、肾内跨学科大PI，重点推广吉因加 CHIP（克隆性造血驱动基因）靶向测序与血浆蛋白组泛血管早筛方案。',
      speakers: [
        { name: '葛均波 院士', hospital: '复旦大学附属中山医院', role: '名誉主席', topic: '泛血管医学学科发展与多学科交叉转化展望', scoreLabel: '91分 · A级', piId: 'SPEC-CARDIO-01', cutIn: '重点对接中山医院泛血管研究团队，推介 CHIP 基因检测与空间转录组方案。' },
        { name: '霍勇 教授', hospital: '北京大学第一医院', role: '大会主席', topic: '中国心血管代谢共病队列与精准预防体系', scoreLabel: '全国学术带头人', cutIn: '围绕心血管代谢大队列推介高通量靶向代谢组与蛋白组验证。' }
      ]
    },
    {
      queue_id: 'ref-20261123-005', conference_id: 'CONF-2026-005', review_status: 'approved', tier_code: 'B',
      field_id: 'rheumatology', conference_name: '北京医学会风湿病学分会第 26 届学术年会',
      abbreviation: '北京风湿年会 2026', start_date: '2026-11-27', end_date: '2026-11-28', city: '北京',
      source_anchor: 'O01 北京医学会风湿病学分会官网 (bjyxh.org.cn)',
      schedule_published: true, topic_scrape_status: 'done', pi_scrape_status: 'pending',
      official_url: 'https://www.bjyxh.org.cn/News/Detail/8003',
      view_url: '#',
      report_count: 22,
      review_note: '【国内重点关注 · B级】北京大学人民医院协办，大会主席苏茵，学委会含王迁、朱剑、张文、张卓莉等。设基础科研培训专场、临床科研专场、高分论文专场，主线含科研训练，北京客户密度极高。',
      topics: '关节炎与消化系统损害黏膜免疫互作、系统性红斑狼疮(SLE)干扰素特征基因谱、风湿免疫病B细胞/T细胞受体(BCR/TCR)免疫组库',
      cut_in: '借会内“基础科研与高分论文专场”契机，向北京各大三甲风湿科中青年科研骨干推广 TCR/BCR 免疫组库测序及 Olink/质谱蛋白组服务。',
      speakers: [
        { name: '苏茵 教授', hospital: '北京大学人民医院', role: '大会主席', topic: '自身免疫病靶向诊疗与临床转化新进展', scoreLabel: '81分 · B级', piId: 'SPEC-RHEUM-01', cutIn: '主委单位科研需求明确，重点切入风湿免疫队列单细胞+免疫组库联检。' }
      ]
    },
    {
      queue_id: 'ref-intl-002', conference_id: 'RSNA2026', review_status: 'approved', tier_code: 'A',
      field_id: 'vascular', conference_name: 'Radiological Society of North America 112th Scientific Assembly (RSNA 2026)',
      abbreviation: 'RSNA 2026', start_date: '2026-11-29', end_date: '2026-12-03', city: 'Chicago, IL (国际)',
      source_anchor: 'I08 国际顶会锚点 · RSNA 官方程序 (rsna.org)',
      schedule_published: true, topic_scrape_status: 'done', pi_scrape_status: 'done',
      official_url: 'https://www.rsna.org/annual-meeting',
      view_url: '#',
      report_count: 18,
      review_note: '【国际风向标 · A级】全球放射与医学影像顶级盛会，重点追踪泛血管斑块影像组学与液体活检多组学(Radiogenomics)交叉转化热点。',
      topics: '泛血管易损斑块影像组学与外周血循环标志物(血清细胞因子表达特征、TyG指数)联合建模、多模态AI辅助器官损伤评估',
      cut_in: '面向国内三甲放射科/血管外科国自然申报团队，提供“影像组学 + 外周血转录组/蛋白组(Radiogenomics)”双模态联合课题设计支持。',
      speakers: [
        { name: '顾宁 院士', hospital: '南京大学医学院附属鼓楼医院', role: '血管分子影像领军', topic: '泛血管分子影像与纳米生物标志物临床转化', scoreLabel: '全国学术领军' }
      ]
    },
    // Approved BUT Unpublished Schedule Conferences (未发布日程，仅第一轮通知，等待日程上线)
    {
      queue_id: 'REV-956faa75ca08', conference_id: 'CAGGPD2026', review_status: 'approved', tier_code: 'B',
      field_id: 'neurology', conference_name: '中国老年学和老年医学学会脑疾病分会 2026 年会暨中国帕金森联盟第八届年会',
      abbreviation: '帕金森联盟年会 2026', start_date: '2026-12-18', end_date: '2026-12-20', city: '南昌',
      source_anchor: 'O07 中国帕金森联盟官方公众号第一轮通知',
      schedule_published: false, topic_scrape_status: 'pending', pi_scrape_status: 'pending',
      official_url: '#',
      report_count: 0,
      review_note: '【已入库 · 待出详细日程】官方目前已发布第一轮征文与会期通知，尚未放出分论坛具体讲题与讲者日程表。监控锚点正每日巡检，待日程发布后自动触发议题与PI抓取。',
      topics: '帕金森病及运动障碍疾病 α-突触核蛋白种子扩增检测(SAA)、神经退行性疾病外周血与脑脊液多组学早筛',
      cut_in: '待详细日程发布后，锁定帕金森联盟核心委员，切入神经退行性疾病外泌体转录组与蛋白组队列验证。'
    },
    {
      queue_id: 'REV-4e9e256334f2', conference_id: 'CSE2027-SPRING', review_status: 'approved', tier_code: 'B',
      field_id: 'diabetes', conference_name: '中华医学会内分泌学分会 2026 代谢病前沿转化冬季研讨会',
      abbreviation: 'CSE 代谢病转化研讨会', start_date: '2026-12-22', end_date: '2026-12-24', city: '广州',
      source_anchor: 'O03 中华医学会内分泌学分会 (cse2026.sciconf.cn)',
      schedule_published: false, topic_scrape_status: 'pending', pi_scrape_status: 'pending',
      official_url: 'https://cse2026.sciconf.cn/',
      report_count: 0,
      review_note: '【已入库 · 待出详细日程】中华医学会内分泌学分会官方微官网已建站并发布会议预告，详细学术日程表尚未公布。',
      topics: '内分泌罕见病与单基因糖尿病全外显子组测序(WES)、肥胖与脂肪肝多组学分子分型',
      cut_in: '待日程上线后第一时间抓取内分泌遗传代谢专场讲者PI，切入单基因糖尿病家系全外显子测序与队列多组学。'
    },
    {
      queue_id: 'REV-bb9fab5c4ff9', conference_id: 'CRA2026-WINTER', review_status: 'approved', tier_code: 'B',
      field_id: 'rheumatology', conference_name: '中国医师协会风湿免疫科医师分会 2026 自身免疫青年学者高峰论坛',
      abbreviation: 'CARIP 自免青年高峰论坛', start_date: '2026-12-19', end_date: '2026-12-21', city: '武汉',
      source_anchor: 'O02 中国医师协会风湿免疫科医师分会 (carip2026.cnconf.com)',
      schedule_published: false, topic_scrape_status: 'pending', pi_scrape_status: 'pending',
      official_url: 'https://carip2026.cnconf.com/msite/main/cn',
      report_count: 0,
      review_note: '【已入库 · 待出详细日程】已发布第一轮会议通知与青年征文启事，详细讲者日程待官方公布。',
      topics: '系统性血管炎与结缔组织病相关间质性肺病(CTD-ILD)单细胞免疫图谱与生物标志物',
      cut_in: '青年风湿学者国自然申报需求极强，待日程发布后抓取青年委员名单定向推送单细胞免疫组库方案。'
    },
    // Pending Audit Queue Items (Stage 1: 来源与审核)
    {
      queue_id: 'ref-20261123-016', conference_id: 'CONF-2026-016', review_status: 'pending', tier_code: 'B',
      field_id: 'respiratory', conference_name: '2026（第九届）多组学研究与应用前沿论坛暨多组学整合与系统生物学前沿大会',
      abbreviation: '2026多组学前沿大会', start_date: '2026-11-27', end_date: '2026-11-28', city: '上海',
      source_anchor: 'C05 生物谷 / SAGE学术会议锚点',
      schedule_published: true,
      official_url: 'https://cma.org.cn/meeting/conf_2026_016',
      review_note: '【重点关注 · B级】生物谷主办、SAGE出版社合作，已附带完整四大学术论坛日程（单细胞技术、空间组学、AI与多组学整合、临床转化），13位讲者来自北大、复旦、交大、同济、浙大。审核通过后可直接抓取日程议题与讲者PI。'
    },
    {
      queue_id: 'ref-20261123-006', conference_id: 'CONF-2026-006', review_status: 'pending', tier_code: 'C',
      field_id: 'rheumatology', conference_name: '2026 自身免疫与精准诊疗大会（IAPMC 2026）',
      abbreviation: 'IAPMC 2026', start_date: '2026-11-27', end_date: '2026-11-28', city: '上海',
      source_anchor: 'C04 精准医学会务发布锚点',
      schedule_published: true,
      official_url: 'https://cma.org.cn/meeting/conf_2026_006',
      review_note: '【常规关注 · C级】主题「从标志物到算法：重构自身免疫诊疗新范式」，已发布1个主会场与6个分会场日程。上海举办且免注册费，属地销售触达成本低。'
    },
    {
      queue_id: 'ref-20261123-009', conference_id: 'CONF-2026-009', review_status: 'pending', tier_code: 'C',
      field_id: 'vascular', conference_name: '中国微循环学会周围血管疾病专委会 2026 年学术年会暨第十三届微循环血管医学发展大会（2026MEC）',
      abbreviation: '2026MEC 微循环大会', start_date: '2026-11-27', end_date: '2026-11-28', city: '北京',
      source_anchor: 'O18 中国微循环学会官方微官网',
      schedule_published: true,
      official_url: 'https://cma.org.cn/meeting/conf_2026_009',
      review_note: '【常规关注 · C级】中国微循环学会主办，詹启敏院士任名誉主席、郑曰宏任大会主席。已发布大家讲堂与血管医学基础研究专场日程，北京举办。'
    },
    {
      queue_id: 'ref-20261123-007', conference_id: 'CONF-2026-007', review_status: 'pending', tier_code: 'C',
      field_id: 'cardiovascular', conference_name: '2026 江苏省医师协会高血压专委会年会',
      abbreviation: '江苏高血压年会', start_date: '2026-11-27', end_date: '2026-11-28', city: '南京',
      source_anchor: 'O15 江苏省医师协会官网通知',
      schedule_published: false,
      official_url: 'https://cma.org.cn/meeting/conf_2026_007',
      review_note: '【常规关注 · C级】江苏省医师协会主办、江苏省人民医院承办。目前仅发布第一轮通知，尚未公布详细讲题日程。'
    },
    {
      queue_id: 'ref-20261123-008', conference_id: 'CONF-2026-008', review_status: 'pending', tier_code: 'C',
      field_id: 'cardiovascular', conference_name: '航天 2026 心血管病年会暨第五届糖尿病心力衰竭综合管理新进展培训',
      abbreviation: '航天心血管病年会', start_date: '2026-11-27', end_date: '2026-11-28', city: '北京',
      source_anchor: 'C02 中华医学会北京分会继续教育锚点',
      schedule_published: true,
      official_url: 'https://cma.org.cn/meeting/conf_2026_008',
      review_note: '【常规关注 · C级】航天中心医院主办，大会主席丁春华。与糖尿病心衰综合管理培训同期举办，心血管与内分泌代谢交叉。'
    },
    {
      queue_id: 'ref-20261123-011', conference_id: 'CONF-2026-011', review_status: 'pending', tier_code: 'D',
      field_id: 'cardiovascular', conference_name: '第十八届左主干暨冠状动脉分叉病变会议（CBS 2026）',
      abbreviation: 'CBS 2026', start_date: '2026-11-27', end_date: '2026-11-29', city: '南京',
      source_anchor: 'S21 心血管介入专科会议锚点',
      schedule_published: true,
      official_url: 'https://cma.org.cn/meeting/conf_2026_011',
      review_note: '【低优先级 · D级】以左主干与分叉病变介入手术技术演示为核心，属手术操作策略类，按既定口径定低优先级（审核通过后建议选择“忽略抓取”）。'
    }
  ];

  function buildConferencesAndQueue(piList) {
    const library = [];
    const audit = [];

    for (const item of GOLD_CONFERENCE_ITEMS) {
      const domainName = getDomainName(item.field_id, item.conference_name);
      const tCode = item.tier_code || 'B';
      const dateStr = item.end_date && item.end_date !== item.start_date
        ? `${item.start_date} ~ ${item.end_date}`
        : (item.start_date || '2026-11');

      if (item.review_status === 'approved') {
        const defaultSpeakers = item.speakers || piList.filter(p => p.domain === domainName).slice(0, 2).map(p => ({
          name: p.name + ' 教授',
          hospital: p.hospital,
          role: '特邀讲者',
          topic: p.research,
          scoreLabel: p.scoreBadge,
          piId: p.id,
          cutIn: p.cutIn
        }));
        library.push({
          id: item.conference_id,
          title: item.conference_name,
          abbreviation: item.abbreviation || item.conference_name.slice(0, 14),
          startDate: item.start_date || '2026-11-25',
          endDate: item.end_date || item.start_date || '2026-11-28',
          updatedDate: '2026-11-23',
          date: dateStr,
          city: item.city || '国内',
          domain: domainName,
          tierCode: tCode,
          tierBadge: getTierBadgeText(tCode),
          tierBasis: item.review_note || '经市场部人工复核定级入库。',
          sourceAnchor: item.source_anchor || '59个官方学术监控锚点',
          schedulePublished: item.schedule_published !== false,
          topicScrapeStatus: item.topic_scrape_status || (item.schedule_published !== false ? 'pending' : 'waiting'),
          piScrapeStatus: item.pi_scrape_status || 'pending',
          reportCount: item.report_count || 18,
          topics: item.topics || `${domainName}前沿多组学临床转化、液体活检与分子分型标志物研究`,
          cutIn: item.cut_in || `围绕本次${domainName}重点学术会议，建议提前锁定参会讲者PI，推介吉因加临床队列多组学验证(T10)与单细胞/转录组测序(T03)服务。`,
          officialUrl: item.official_url || '#',
          viewUrl: item.view_url || '#',
          speakers: defaultSpeakers
        });
      } else if (item.review_status === 'pending') {
        audit.push({
          id: item.queue_id || item.conference_id,
          conferenceId: item.conference_id,
          title: item.conference_name,
          abbreviation: item.abbreviation || item.conference_name.slice(0, 14),
          date: dateStr,
          city: item.city || '待定',
          domain: domainName,
          fieldId: item.field_id || 'diabetes',
          tierCode: tCode,
          sourceAnchor: item.source_anchor || '中华医学会/微官网监控锚点',
          schedulePublished: Boolean(item.schedule_published),
          summary: item.review_note || '待市场部复核会议学术层级与临床科研转化价值。'
        });
      }
    }

    return { library, audit };
  }

  // 7. Build Literature List
  function buildLiteratureList() {
    const list = [];
    const primaryPapers = (D.papers || []).filter(p => p.primary_counted);

    for (const p of primaryPapers) {
      const topic = p.topic_id ? topicMap.get(p.topic_id) : null;
      list.push({
        id: p.paper_id,
        title: p.title,
        journal: p.journal || '核心四刊',
        pubDate: p.publication_date || '2025',
        domain: '糖尿病与代谢',
        typeLabel: p.type_label || '临床研究',
        topicName: topic ? topic.name : (p.source_issue_name || ''),
        abstract: p.finding || '核心四刊窗口期内已复核主池研究论文，详见原始证据视图。',
        authors: (p.authors && p.authors.length) ? p.authors.slice(0, 4).join(', ') + (p.authors.length > 4 ? ' 等' : '') : '研究团队',
        pmid: p.pmid || '',
        doi: p.doi || '',
        sourceUrl: p.source_url || '#',
        detailUrl: p.detail_url || '',
        heat: '✓ 核心四刊复核主池',
        isReal: true
      });
    }

    const specialtyPapers = [
      {
        id: 'SPEC-LIT-01',
        title: 'Multi-omics Profiling of Cerebrospinal Fluid Reveals Neuroinflammatory Biomarkers in Acute Ischemic Stroke',
        journal: 'Lancet Neurology', pubDate: '2026-02', domain: '神经精神', typeLabel: '队列多组学研究',
        topicName: '脑卒中液体活检与神经免疫标志物',
        abstract: '基于高深度脑脊液蛋白质组与外周血单细胞转录组测序，鉴定出预测急性脑梗死后神经功能恢复与出血转化的关键细胞因子特征谱。',
        authors: '吉训明, 陆正齐 团队等', pmid: '40128901', heat: 'IF 48.0 · 转化热点', isReal: false
      },
      {
        id: 'SPEC-LIT-03',
        title: 'Airway Microbiome-Host Transcriptome Interactions Predict Exacerbation Risk in Severe COPD',
        journal: 'AJRCCM (蓝皮书)', pubDate: '2026-02', domain: '呼吸慢病', typeLabel: '前瞻性队列研究',
        topicName: '慢阻肺气道微生态与宿主转录组',
        abstract: '对420例慢阻肺患者开展诱导痰宏基因组与宿主RNA-seq双组学联合分析，建立II型炎症与细菌定植交互分型模型。',
        authors: '陈荣昌, 钟南山 团队等', pmid: '40201188', heat: '呼吸顶刊 · 转化热点', isReal: false
      },
      {
        id: 'SPEC-LIT-05',
        title: 'Single-Cell BCR/TCR Repertoire and Interferon Signature Stratify Treatment Response in SLE',
        journal: 'Annals of the Rheumatic Diseases', pubDate: '2026-02', domain: '风湿免疫', typeLabel: '免疫组库研究',
        topicName: '红斑狼疮免疫组库与精准分型',
        abstract: '通过单细胞免疫组库(TCR/BCR)与转录组测序追踪难治性系统性红斑狼疮患者B细胞克隆演化，指导生物制剂精准选择。',
        authors: '苏茵, 张奉春 团队等', pmid: '40233019', heat: '风湿顶刊 · 转化热点', isReal: false
      },
      {
        id: 'SPEC-LIT-06',
        title: 'Clonal Hematopoiesis of Indeterminate Potential (CHIP) Accelerates Pan-Vascular Atherosclerosis',
        journal: 'Circulation', pubDate: '2026-02', domain: '心血管', typeLabel: '基因组队列研究',
        topicName: '克隆性造血(CHIP)与心血管残余风险',
        abstract: '高深度靶向测序揭示 TET2/DNMT3A 克隆性造血突变通过激活巨噬细胞炎症小体加速冠脉及泛血管斑块进展。',
        authors: '葛均波, 霍勇 团队等', pmid: '40255102', heat: 'IF 37.8 · 转化热点', isReal: false
      },
      {
        id: 'SPEC-LIT-07',
        title: 'Radiogenomics and Plasma Proteomics for Vulnerable Plaque Identification in Pan-Vascular Disease',
        journal: 'European Heart Journal', pubDate: '2026-01', domain: '泛血管及器官损伤', typeLabel: '影像-多组学联合',
        topicName: '泛血管斑块影像组学与血浆蛋白组',
        abstract: '融合高分辨血管影像组学与血浆高通量蛋白组学、血清细胞因子表达特征及TyG指数，构建跨器官血管损伤早期预警模型。',
        authors: '郑曰宏, 顾宁 团队等', pmid: '40187760', heat: 'IF 39.3 · 转化热点', isReal: false
      }
    ];

    return [...specialtyPapers, ...list];
  }

  // 8. Pipelines
  const PIPELINES = [
    {
      id: 'p1', name: 'HRS9531 (GLP-1/GIP 双靶点激动剂)', company: '恒瑞医药', domain: '糖尿病与代谢',
      indication: '2型糖尿病合并肥胖/代谢相关脂肪性肝病(MASH) · 伴随代谢组与蛋白组生物标志物队列',
      phase: 'Phase III 临床', date: '2026-11-18',
      cutIn: '围绕 GLP-1/GIP 临床试验入组人群，向承接医院内分泌PI推介治疗前后血浆蛋白质组(T14)与肠道宏基因组疗效预测子课题。'
    },
    {
      id: 'p2', name: 'IBI362 (玛仕度肽 · GLP-1R/GCGR)', company: '信达生物', domain: '糖尿病与代谢',
      indication: '糖尿病合并早期慢性肾脏病(DKD)蛋白尿逆转研究 · 尿液外泌体转录组生物标志物',
      phase: 'NDA 审评 / Phase III', date: '2026-11-15',
      cutIn: '结合 CDS 2026 DKD 早期损伤热点，推介尿液外泌体 RNA-seq 与肾小管损伤蛋白标志物验证服务(T03/T10)。'
    },
    {
      id: 'p3', name: 'JS-015 (抗 Aβ 淀粉样蛋白单抗)', company: '君实生物', domain: '神经精神',
      indication: '早期阿尔茨海默病(AD)及血管性痴呆 · 脑脊液/外周血 p-Tau217 与神经炎症多组学伴随分层',
      phase: 'Phase II/III 临床', date: '2026-11-12',
      cutIn: '对接神经内科认知障碍中心PI，提供外周血超敏蛋白标志物与 APOE/神经退行性Panel靶向测序。'
    },
    {
      id: 'p5', name: 'CM310 (司普奇拜单抗 · IL-4Rα)', company: '康诺亚 / 石药', domain: '呼吸慢病',
      indication: '重度嗜酸粒细胞性慢阻肺(COPD)与重症哮喘 · 气道II型炎症转录组与细胞因子分型',
      phase: 'Phase III 临床', date: '2026-11-16',
      cutIn: '借 CACP 2026 呼吸年会契机，向参研呼吸科PI推介生物制剂应答人群的气道转录组与蛋白组精准分型课题。'
    },
    {
      id: 'p7', name: 'RC18 (泰它西普 · BLyS/APRIL 双靶点)', company: '荣昌生物', domain: '风湿免疫',
      indication: '系统性红斑狼疮(SLE)与IgA肾病 · B细胞免疫组库(BCR)与自身抗体多组学动态监测',
      phase: 'Phase III / 适应症拓展', date: '2026-11-19',
      cutIn: '对接风湿免疫科PI，利用吉因加单细胞 BCR/TCR 免疫组库测序评估靶向B细胞治疗后的免疫重建。'
    },
    {
      id: 'p8', name: 'SAL0120 (PCSK9/Lp(a) 小核酸药物)', company: '信立泰', domain: '心血管',
      indication: '动脉粥样硬化性心血管疾病(ASCVD)高危人群残余风险干预 · 克隆性造血(CHIP)伴随筛查',
      phase: 'Phase II 临床', date: '2026-11-14',
      cutIn: '对接心内科冠心病介入与代谢团队，切入 CHIP 突变基因深度测序与脂质代谢多组学验证。'
    },
    {
      id: 'p9', name: 'GNP-VASC-01 (泛血管内皮修复外泌体)', company: '先声药业', domain: '泛血管及器官损伤',
      indication: '糖尿病周围血管病变及微循环缺血再灌注损伤 · 循环游离核酸与内皮蛋白标志物',
      phase: 'Phase I/II 临床', date: '2026-11-11',
      cutIn: '结合 2026MEC 微循环大会与 PMC 泛血管大会，推介泛血管多器官损伤液体活检标志物开发。'
    }
  ];

  const initialPIs = buildPIList();
  const initialConfData = buildConferencesAndQueue(initialPIs);
  const initialHotspotTopics = buildHotspotTopics();
  const initialLiterature = buildLiteratureList();

  const salesPeopleList = ((D.sales && D.sales.salespeople) || [
    { id: 'sales_east_zhang', name: '张敏', region: '华东大区' },
    { id: 'sales_north_li',   name: '李娜', region: '华北大区' },
    { id: 'sales_south_wang', name: '王强', region: '华南与中西大区' }
  ]).map(s => ({
    id: s.id,
    name: s.name,
    label: `${s.region || '大区'} - ${s.name}`
  }));

  const defaultVisitReports = [
    {
      id: 'vr1',
      repName: '张敏 (华东大区)',
      date: '2026-11-23',
      piName: '王卫庆',
      qualityTag: '四维评分 82分·B级 · 瑞金医院',
      content: '围绕 CDS 2026 大会报告沟通了瑞金内分泌代谢队列的多组学检测需求，王教授团队对大规模临床样本的转录组与血浆蛋白质组验证(T10/T14)表示明确兴趣。',
      nextStep: '下周二前协同吉因加医学技术支持提交《代谢队列多组学联合验证技术方案》'
    },
    {
      id: 'vr2',
      repName: '张敏 (华东大区)',
      date: '2026-11-22',
      piName: '黄斌',
      qualityTag: '四维评分 62分·C级 · 安徽省立医院',
      content: '针对 CDS 2026 口头报告 OR_003（DKD早期损伤与转录组验证）进行了会前拜访，核实其省自然青年基金课题手头已有 320 例具备完整随访的 DKD 尿液与血浆配对标本。',
      nextStep: '已将标本可用性回传至【客户画像校准】，准备寄送尿液外泌体建库质控SOP'
    }
  ];

  const defaultIntelList = [
    {
      id: 'i1',
      piName: '黄斌',
      hospital: '中国科学技术大学附属第一医院（安徽省立医院）',
      type: '四维缺口补证 · 样本队列核实',
      content: '一线拜访核实：专家手头已冻存 320 例 DKD 早期患者配对血浆与尿液样本（解决原四维评分中“体液产品待确认”缺口），拟于 Q4 启动转录组测序验证。',
      date: '2026-11-23',
      synced: false
    },
    {
      id: 'i2',
      piName: '张学礼',
      hospital: '上海市第六人民医院',
      type: '新课题立项意向 · 蛋白组+转录组',
      content: '团队计划针对糖尿病微血管并发症（视网膜+肾病共病）申报新一批临床转化专项，需 200 例高深度血浆蛋白质组学(T14)初筛报价。',
      date: '2026-11-22',
      synced: false
    }
  ];

  return {
    dbStats: {
      anchors: 59,
      reports: (D.summary && D.summary.reports) || 2628,
      primaryPapers: (D.summary && D.summary.primary_papers) || 160,
      allPapers: (D.summary && D.summary.papers) || 618,
      topics: (D.summary && D.summary.topics) || 66,
      experts: (D.summary && D.summary.expert_records) || 2277
    },

    currentView: 'home',      // 'home' | 'workspace'
    activeModule: 'hotspots', // 'hotspots' | 'map' | 'tasks' | 'closedloop'

    hotspotTab: 'academic',   // 'academic' | 'literature' | 'pipeline' | 'fund'
    academicMode: 'hotspots', // 'audit' (①来源与审核) | 'library' (②日程分流与抓取) | 'hotspots' (③会议热点主界面)
    scheduleSubTab: 'published', // 'published' (已发布日程) | 'unpublished' (未发布日程)
    showAnchorsPanel: false,

    // Comprehensive vs Weekly Conference Hotspots state
    hotspotViewMode: 'comprehensive', // 'comprehensive' (综合会议热点) | 'weekly' (本周会议热点)
    weekStart: '2026-11-23',
    weekEnd: '2026-11-29',
    weeklySubTab: 'occurring',        // 'occurring' (本周召开) | 'updates' (本周新收录/日程更新)
    weeklyFocusConf: 'all',
    weeklyReportFormat: 'talks',

    hotspotScope: 'all',      // 'all' | 'domestic' | 'intl'
    selectedBoard: '全部',
    topicPage: 1,
    topicPageSize: 10,

    taskTab: 'conferences',
    loopTab: 'reports',

    selectedDomain: '全部',
    confTierFilter: 'all',
    litSourceFilter: 'all',
    litPage: 1,
    litPageSize: 12,

    mapDomain: '全部',
    mapGradeFilter: 'all',
    piPage: 1,
    piPageSize: 15,

    searchQuery: '',

    domains: DOMAINS,
    salespeople: salesPeopleList,

    conferences: initialConfData.library,
    auditConferences: initialConfData.audit,
    hotspotTopics: initialHotspotTopics,
    literatureList: initialLiterature,
    pipelineList: PIPELINES,
    piList: initialPIs,
    visitReports: readStore('clinical-workbench:visit-reports:v2', defaultVisitReports),
    intelList: readStore('clinical-workbench:intel-list:v2', defaultIntelList),

    init() {
      const applyHash = () => {
        const h = (window.location.hash || '').replace(/^#/, '').split('?')[0];
        if (!h || h === 'overview' || h === 'home') {
          this.currentView = 'home';
        } else if (h === 'topics') {
          this.openModule('hotspots', 'academic', 'hotspots');
        } else if (h === 'conferences' || h === 'weekly') {
          this.openModule('hotspots', 'academic', 'library');
        } else if (h === 'papers') {
          this.openModule('hotspots', 'literature');
        } else if (h === 'experts' || h === 'map') {
          this.openModule('map');
        } else if (h === 'market' || h === 'tasks') {
          this.openModule('tasks', 'conferences');
        } else if (h === 'sales' || h === 'closedloop') {
          this.openModule('closedloop', 'reports');
        }
      };
      applyHash();
      window.addEventListener('hashchange', applyHash);
    },

    toasts: [],
    showToast(message, type = 'info') {
      const id = Date.now() + Math.random();
      this.toasts.push({ id, message, type });
      setTimeout(() => {
        this.toasts = this.toasts.filter(t => t.id !== id);
      }, 3500);
    },

    getDomainColor(domainName) {
      return DOMAIN_NAME_TO_COLOR[domainName] || '#2563eb';
    },

    getTierBadge(code) {
      return getTierBadgeText(code);
    },

    openModule(moduleName, subTab = null, mode = null) {
      this.currentView = 'workspace';
      this.activeModule = moduleName;
      if (subTab) {
        if (moduleName === 'hotspots') this.hotspotTab = subTab;
        if (moduleName === 'tasks') this.taskTab = subTab;
        if (moduleName === 'closedloop') this.loopTab = subTab;
      }
      if (mode && moduleName === 'hotspots' && subTab === 'academic') {
        this.academicMode = mode;
      }
      window.scrollTo({ top: 0, behavior: 'smooth' });
    },

    goHome() {
      this.currentView = 'home';
      if (window.location.hash) {
        history.replaceState(null, '', window.location.pathname + window.location.search);
      }
      window.scrollTo({ top: 0, behavior: 'smooth' });
    },

    get pendingScrapeCount() {
      return this.conferences.filter(c => c.schedulePublished && (c.topicScrapeStatus === 'pending' || (c.topicScrapeStatus === 'done' && c.piScrapeStatus === 'pending'))).length;
    },

    get weekRangeLabel() {
      return `${this.weekStart} — ${this.weekEnd}`;
    },

    shiftWeek(deltaWeeks) {
      const addDays = (dStr, n) => {
        const ms = Date.parse(dStr + 'T00:00:00Z') + n * 86400000;
        return new Date(ms).toISOString().slice(0, 10);
      };
      this.weekStart = addDays(this.weekStart, deltaWeeks * 7);
      this.weekEnd = addDays(this.weekStart, 6);
      this.weeklyFocusConf = 'all';
      this.topicPage = 1;
    },

    resetCurrentWeek() {
      this.weekStart = '2026-11-23';
      this.weekEnd = '2026-11-29';
      this.weeklyFocusConf = 'all';
      this.topicPage = 1;
    },

    get weeklyOccurringConferences() {
      return this.conferences.filter(c => {
        if (!c.schedulePublished) return false;
        const matchDomain = this.selectedDomain === '全部' || c.domain === this.selectedDomain;
        const s = c.startDate || '2026-11-25';
        const e = c.endDate || s;
        return matchDomain && s <= this.weekEnd && e >= this.weekStart;
      });
    },

    get weeklyUpdatedConferences() {
      return this.conferences.filter(c => {
        const matchDomain = this.selectedDomain === '全部' || c.domain === this.selectedDomain;
        const u = c.updatedDate || '2026-11-23';
        return matchDomain && u >= this.weekStart && u <= this.weekEnd;
      });
    },

    get weeklyActiveConferences() {
      return this.weeklySubTab === 'occurring'
        ? this.weeklyOccurringConferences
        : this.weeklyUpdatedConferences;
    },

    get weeklyHotspotTopics() {
      const activeConfs = this.weeklyActiveConferences;
      const activeIds = new Set(
        this.weeklyFocusConf === 'all'
          ? activeConfs.map(c => c.id)
          : [this.weeklyFocusConf]
      );
      if (activeIds.size === 0) return [];

      const formatRatio = this.weeklyReportFormat === 'posters' ? 0.35 : (this.weeklyReportFormat === 'all' ? 1.15 : 1);
      const list = [];

      for (const tp of this.hotspotTopics) {
        const counts = tp.confCounts || {};
        const matchedEntries = Object.entries(counts).filter(([cid]) => activeIds.has(cid));
        if (matchedEntries.length === 0) continue;

        const rawSum = matchedEntries.reduce((acc, [, cnt]) => acc + cnt, 0);
        const weeklyCount = Math.max(1, Math.round(rawSum * formatRatio));
        const weeklyLabels = matchedEntries
          .map(([cid, cnt]) => {
            const confObj = this.conferences.find(c => c.id === cid);
            const name = confObj ? confObj.abbreviation : cid;
            return `${name}(${Math.max(1, Math.round(cnt * formatRatio))}条)`;
          })
          .join(' · ');

        list.push({
          ...tp,
          weeklyReportCount: weeklyCount,
          weeklyConfLabels: weeklyLabels
        });
      }

      return list.sort((a, b) => (b.weeklyReportCount || 0) - (a.weeklyReportCount || 0));
    },

    get activeModeTopicBase() {
      return this.hotspotViewMode === 'weekly' ? this.weeklyHotspotTopics : this.hotspotTopics;
    },

    getDomainCount(domainName) {
      let dataset = [];
      if (this.hotspotTab === 'academic') {
        if (this.academicMode === 'hotspots') dataset = this.activeModeTopicBase;
        else if (this.academicMode === 'library') dataset = this.conferences;
        else dataset = this.auditConferences;
      } else if (this.hotspotTab === 'literature') {
        dataset = this.literatureList;
      } else if (this.hotspotTab === 'pipeline') {
        dataset = this.pipelineList;
      }
      if (domainName === '全部') return dataset.length;
      return dataset.filter(item => item.domain === domainName).length;
    },

    getDomainPercentage(domainName) {
      const total = this.getDomainCount('全部');
      if (total === 0) return 0;
      const count = this.getDomainCount(domainName);
      return Math.round((count / total) * 100);
    },

    // STAGE 1 Action: Approve Audit Conference -> Enters Selected Domain & Splits into Published vs Unpublished Schedule
    approveAudit(id) {
      const idx = this.auditConferences.findIndex(c => c.id === id);
      if (idx !== -1) {
        const item = this.auditConferences.splice(idx, 1)[0];
        const tCode = item.tierCode || 'B';
        const hasSchedule = Boolean(item.schedulePublished);
        const domainPIs = this.piList.filter(p => p.domain === item.domain).slice(0, 2);

        const startParts = String(item.date || '').split('~').map(x => x.trim());
        const newConf = {
          id: item.conferenceId || ('CONF-APP-' + Date.now()),
          title: item.title,
          abbreviation: item.abbreviation || item.title.slice(0, 14),
          startDate: startParts[0] || '2026-11-27',
          endDate: startParts[1] || startParts[0] || '2026-11-28',
          updatedDate: '2026-11-24',
          date: item.date,
          city: item.city,
          domain: item.domain,
          tierCode: tCode,
          tierBadge: getTierBadgeText(tCode),
          tierBasis: item.summary,
          sourceAnchor: item.sourceAnchor || '学会微官网监控锚点',
          schedulePublished: hasSchedule,
          topicScrapeStatus: hasSchedule ? 'pending' : 'waiting',
          piScrapeStatus: 'pending',
          reportCount: hasSchedule ? 26 : 0,
          topics: `${item.domain}前沿多组学转化、临床队列液体活检与分子分型标志物研究`,
          cutIn: `会议经市场部核定为【${getTierBadgeText(tCode)}】，建议联动属地销售围绕参会讲者PI推进临床队列多组学验证(T10)与单细胞/转录组(T03)合作。`,
          officialUrl: '#',
          viewUrl: '#',
          speakers: domainPIs.map(p => ({
            name: p.name + ' 教授',
            hospital: p.hospital,
            role: '重点关注PI',
            topic: p.research,
            scoreLabel: p.scoreBadge,
            piId: p.id,
            cutIn: p.cutIn
          }))
        };
        this.conferences.unshift(newConf);

        if (hasSchedule) {
          this.scheduleSubTab = 'published';
          this.showToast(`已批准【${item.abbreviation}】归入【${item.domain}】（已发布日程，已在“② 日程分流”生成抓取提醒）！`, 'success');
        } else {
          this.scheduleSubTab = 'unpublished';
          this.showToast(`已批准【${item.abbreviation}】归入【${item.domain} · 未发布日程库】持续监控！`, 'info');
        }
      }
    },

    rejectAudit(id) {
      this.auditConferences = this.auditConferences.filter(c => c.id !== id);
      this.showToast('已驳回/忽略该待审会议', 'info');
    },

    // STAGE 2 Actions: Scrape Topics from Schedule / Ignore Scrape / Scrape PIs / Simulate Schedule Release
    scrapeConferenceTopics(conf) {
      conf.topicScrapeStatus = 'done';
      if (!conf.reportCount) conf.reportCount = 24;

      // Also synthesize/push a hotspot topic into Stage 3 (会议热点主界面)
      const newTopicId = 'TP-SCRAPED-' + conf.id;
      if (!this.hotspotTopics.some(t => t.id === newTopicId)) {
        const leaders = (conf.speakers || []).map((sp, i) => ({
          key: `${conf.id}-SP-${i}`,
          name: sp.name.replace(/教授|院士|博士/g, '').trim(),
          hospital: sp.hospital,
          tierCode: 'national',
          roleLabel: sp.role || '全国学术带头人',
          roleBasis: `${conf.abbreviation} 核心特邀讲者`,
          scoreLabel: sp.scoreLabel || '重点讲者',
          conf: conf.abbreviation,
          talkTitle: sp.topic
        }));

        this.hotspotTopics.unshift({
          id: newTopicId,
          name: `【${conf.abbreviation} 新抓热点】${conf.topics.split('、')[0]}`,
          domain: conf.domain,
          boardName: `${conf.domain}最新会议专题`,
          reportCount: conf.reportCount || 24,
          paperCount: 2,
          confCounts: { [conf.id]: conf.reportCount || 24 },
          confIds: [conf.id],
          confLabels: `${conf.abbreviation}(${conf.reportCount || 24}条)`,
          hasDomestic: conf.tierCode !== 'A',
          hasIntl: conf.tierCode === 'A',
          leaders: leaders.length ? leaders : [
            { key: 'def-sp', name: '大会主讲专家', hospital: '国内重点三甲医院', tierCode: 'national', roleLabel: '全国学术带头人', roleBasis: conf.abbreviation + ' 专题讲者', scoreLabel: '', conf: conf.abbreviation, talkTitle: conf.topics }
          ],
          biomarkers: ['多组学分子分型 Panel', '外周血/体液外泌体转录组特征'],
          sampleTalk: `${conf.abbreviation}: ${conf.topics.split('、')[0]}`,
          sampleReports: [
            { id: newTopicId + '-R1', conf: conf.abbreviation, code: '主旨报告', title: conf.topics.split('、')[0] + '多中心临床转化队列进展', date: conf.date.slice(0, 10) }
          ],
          cutIn: conf.cutIn
        });
      }

      this.showToast(`已从【${conf.abbreviation}】日程成功抓取 ${conf.reportCount} 条报告与核心议题，并同步至【③ 会议热点主界面】！`, 'success');
    },

    ignoreConferenceScrape(conf) {
      conf.topicScrapeStatus = 'ignored';
      this.showToast(`已忽略【${conf.abbreviation}】的日程深抓，仅保留会议基础卡片`, 'info');
    },

    scrapeConferencePIs(conf) {
      conf.piScrapeStatus = 'done';
      let addedCount = 0;
      for (const sp of (conf.speakers || [])) {
        const cleanName = sp.name.replace(/教授|院士|主任|博士/g, '').trim();
        const exists = this.piList.some(p => p.name.includes(cleanName));
        if (!exists) {
          this.piList.unshift({
            id: 'PI-CONF-' + Date.now() + '-' + addedCount,
            name: cleanName,
            hospital: sp.hospital || '国内核心三甲医院',
            department: conf.domain + '中心',
            title: '主任医师 / 教授',
            roleLabel: sp.role || '全国专科学术带头人',
            roleCode: 'national',
            sourceLabel: `来源: ${conf.abbreviation} 日程抓取`,
            domain: conf.domain,
            totalScore: null,
            grade: null,
            hasPartialRating: true,
            scoreBadge: '调研中 · 方向28/30',
            dimSummary: '研究28/30 (日程讲题已核 · 余项待补)',
            dimensions: [
              { name: '研究方向契合度', maximum: 30, score: 28, basis: `在【${conf.abbreviation}】报告《${sp.topic}》，高度契合多组学临床转化。` },
              { name: '学术产出质量',   maximum: 25, score: null, basis: '待进一步核对近三年 PubMed 一作/通讯期刊档位；缺证不填0。' },
              { name: '科研转化潜力',   maximum: 25, score: null, basis: '待进一步核对个人主持基金与开放队列条件；缺证不填0。' },
              { name: '平台资源禀赋',   maximum: 20, score: null, basis: '待进一步核对所属实验室可调配资源；缺证不填0。' }
            ],
            ratingDate: new Date().toISOString().slice(0, 10),
            headPiStatus: `${conf.abbreviation} 讲者线索`,
            sources: [{ id: conf.id, title: `${conf.title} 官方日程讲者名录`, url: conf.officialUrl || '#' }],
            capabilities: ['T10 临床队列验证', 'T03 单细胞/转录组'],
            isAiRecommended: true,
            research: `讲题：${sp.topic}`,
            cutIn: sp.cutIn || conf.cutIn,
            talks: [{ id: conf.id + '-TK', conf: conf.abbreviation, title: sp.topic }],
            papers: [],
            starred: true,
            assignee: '华东一区 - 张敏',
            taskStatus: '待派发',
            syncedIntel: [],
            syncedIntelCount: 0
          });
          addedCount++;
        }
      }
      this.showToast(`已将【${conf.abbreviation}】的重点讲者 PI 分类写入【${conf.domain} · 作战地图 PI 库】！`, 'success');
    },

    simulateSchedulePublished(conf) {
      conf.schedulePublished = true;
      conf.topicScrapeStatus = 'pending';
      conf.piScrapeStatus = 'pending';
      conf.reportCount = 28;
      this.scheduleSubTab = 'published';
      this.showToast(`🔔 【${conf.abbreviation}】官方已发布详细日程！已自动转入“已发布日程”并生成议题抓取提醒！`, 'warning');
    },

    // Computed Conference Lists
    get filteredConferences() {
      const q = this.searchQuery.trim().toLowerCase();
      return this.conferences.filter(c => {
        const matchDomain = this.selectedDomain === '全部' || c.domain === this.selectedDomain;
        const matchTier = this.confTierFilter === 'all' || c.tierCode === this.confTierFilter;
        const matchSearch = !q || [c.title, c.topics, c.tierBasis, c.city].join(' ').toLowerCase().includes(q);
        return matchDomain && matchTier && matchSearch;
      });
    },

    get publishedConferences() {
      return this.filteredConferences.filter(c => c.schedulePublished);
    },

    get unpublishedConferences() {
      return this.filteredConferences.filter(c => !c.schedulePublished);
    },

    get filteredAuditConferences() {
      const q = this.searchQuery.trim().toLowerCase();
      return this.auditConferences.filter(c => {
        const matchDomain = this.selectedDomain === '全部' || c.domain === this.selectedDomain;
        const matchTier = this.confTierFilter === 'all' || c.tierCode === this.confTierFilter;
        const matchSearch = !q || [c.title, c.summary, c.city, c.sourceAnchor].join(' ').toLowerCase().includes(q);
        return matchDomain && matchTier && matchSearch;
      });
    },

    // STAGE 3 Computed: Hotspot Topics & Boards
    get availableBoards() {
      const counts = {};
      for (const t of this.activeModeTopicBase) {
        if (this.selectedDomain !== '全部' && t.domain !== this.selectedDomain) continue;
        counts[t.boardName] = (counts[t.boardName] || 0) + 1;
      }
      return Object.entries(counts).map(([name, count]) => ({ name, count }));
    },

    get filteredHotspotTopics() {
      const q = this.searchQuery.trim().toLowerCase();
      return this.activeModeTopicBase.filter(t => {
        const matchDomain = this.selectedDomain === '全部' || t.domain === this.selectedDomain;
        const matchBoard = this.selectedBoard === '全部' || t.boardName === this.selectedBoard;
        const matchScope = this.hotspotViewMode === 'weekly'
          || this.hotspotScope === 'all'
          || (this.hotspotScope === 'domestic' && t.hasDomestic)
          || (this.hotspotScope === 'intl' && t.hasIntl);
        const leaderNames = (t.leaders || []).map(l => l.name + ' ' + l.hospital + ' ' + l.talkTitle).join(' ');
        const matchSearch = !q || [t.name, t.boardName, t.confLabels, leaderNames].join(' ').toLowerCase().includes(q);
        return matchDomain && matchBoard && matchScope && matchSearch;
      });
    },

    get topicTotalPages() {
      return Math.max(1, Math.ceil(this.filteredHotspotTopics.length / this.topicPageSize));
    },

    get pagedHotspotTopics() {
      const start = (this.topicPage - 1) * this.topicPageSize;
      return this.filteredHotspotTopics.slice(start, start + this.topicPageSize);
    },

    get recommendedConferences() {
      return this.conferences.filter(c => c.schedulePublished && (c.tierCode === 'B' || c.tierCode === 'A') && c.speakers && c.speakers.length > 0);
    },

    // Literature Computed
    get filteredLiterature() {
      const q = this.searchQuery.trim().toLowerCase();
      return this.literatureList.filter(l => {
        const matchDomain = this.selectedDomain === '全部' || l.domain === this.selectedDomain;
        const matchSource = this.litSourceFilter === 'all' || (this.litSourceFilter === 'real' && l.isReal);
        const matchSearch = !q || [l.title, l.abstract, l.journal, l.authors, l.topicName].join(' ').toLowerCase().includes(q);
        return matchDomain && matchSource && matchSearch;
      });
    },

    get litTotalPages() {
      return Math.max(1, Math.ceil(this.filteredLiterature.length / this.litPageSize));
    },

    get pagedLiterature() {
      const start = (this.litPage - 1) * this.litPageSize;
      return this.filteredLiterature.slice(start, start + this.litPageSize);
    },

    // Pipelines Computed
    get filteredPipelines() {
      const q = this.searchQuery.trim().toLowerCase();
      return this.pipelineList.filter(p => {
        const matchDomain = this.selectedDomain === '全部' || p.domain === this.selectedDomain;
        const matchSearch = !q || [p.name, p.company, p.indication].join(' ').toLowerCase().includes(q);
        return matchDomain && matchSearch;
      });
    },

    // PI Battle Map Computed
    get filteredPIs() {
      const q = this.searchQuery.trim().toLowerCase();
      return this.piList.filter(p => {
        const matchDomain = this.mapDomain === '全部' || p.domain === this.mapDomain;
        let matchGrade = true;
        if (this.mapGradeFilter === 'complete') {
          matchGrade = p.totalScore !== null;
        } else if (this.mapGradeFilter === 'survey') {
          matchGrade = p.hasPartialRating;
        } else if (this.mapGradeFilter === 'ai') {
          matchGrade = p.isAiRecommended;
        }
        const matchSearch = !q || [p.name, p.hospital, p.research, p.scoreBadge, p.roleLabel].join(' ').toLowerCase().includes(q);
        return matchDomain && matchGrade && matchSearch;
      });
    },

    get piTotalPages() {
      return Math.max(1, Math.ceil(this.filteredPIs.length / this.piPageSize));
    },

    get pagedPIs() {
      const start = (this.piPage - 1) * this.piPageSize;
      return this.filteredPIs.slice(start, start + this.piPageSize);
    },

    togglePIStar(piId) {
      const pi = this.piList.find(p => p.id === piId);
      if (pi) {
        pi.starred = !pi.starred;
        this.showToast(pi.starred ? `已将【${pi.name}】加入重点关注 PI 池` : `已取消重点关注【${pi.name}】`, 'info');
      }
    },

    updatePITaskStatus(pi, status) {
      pi.taskStatus = status;
      this.showToast(`【${pi.name}】跟进状态已更新为：${status}`, status === '已触达' ? 'success' : 'info');
    },

    syncIntelToPI(intelItem) {
      intelItem.synced = true;
      writeStore('clinical-workbench:intel-list:v2', this.intelList);
      const targetPI = this.piList.find(p => p.name.includes(intelItem.piName) || intelItem.piName.includes(p.name));
      if (targetPI) {
        if (!targetPI.syncedIntel) targetPI.syncedIntel = [];
        targetPI.syncedIntel.unshift({
          id: intelItem.id,
          type: intelItem.type,
          content: intelItem.content,
          date: intelItem.date
        });
        targetPI.syncedIntelCount = targetPI.syncedIntel.length;
        if (targetPI.dimensions && targetPI.dimensions[0]) {
          targetPI.dimensions[0].basis += ` [一线回流核实：${intelItem.content}]`;
        }
      }
      this.showToast(`已将情报回流并校准【${intelItem.piName}】在作战地图中的四维档案！`, 'success');
    },

    // Modals & Drawers
    showTopicModal: false,
    selectedTopic: null,
    openTopicDetail(tp) {
      this.selectedTopic = tp;
      this.showTopicModal = true;
    },

    showConferenceModal: false,
    selectedConf: null,
    openConferenceDetail(conf) {
      this.selectedConf = conf;
      this.showConferenceModal = true;
    },

    showAssignModal: false,
    targetTaskTitle: '',
    assignedRep: salesPeopleList[0]?.label || '华东大区 - 张敏',
    assignDueDate: '2026-12-05',
    assignNote: '',
    assignTargetPI: null,
    openAssignModal(title, defaultCutIn = '', targetPI = null) {
      this.targetTaskTitle = title;
      this.assignTargetPI = targetPI;
      if (targetPI && targetPI.assignee) {
        const matched = this.salespeople.find(s => s.label.includes(targetPI.assignee.split('-').pop().trim()));
        if (matched) this.assignedRep = matched.label;
      }
      this.assignNote = defaultCutIn
        || '建议优先阅读专家近期会议讲题与四维评分依据，围绕临床队列样本条件切入吉因加转录组/单细胞(T03)及临床多组学验证(T10)方案。';
      this.showAssignModal = true;
    },
    confirmTaskAssign() {
      if (this.assignTargetPI) {
        this.assignTargetPI.assignee = this.assignedRep;
        this.assignTargetPI.taskStatus = '跟进中';
        this.assignTargetPI.starred = true;
      }
      this.showAssignModal = false;
      this.showToast(`作战任务已派发给【${this.assignedRep}】，附带吉因加定制破冰话术！`, 'success');
    },

    showUploadModal: false,
    uploadTab: 'batch',
    newPI: { name: '', hospital: '', domain: '糖尿病与代谢', research: '' },
    openUploadModal() {
      this.showUploadModal = true;
    },
    handleBatchPIFile(event) {
      const file = event.target.files && event.target.files[0];
      if (!file) return;
      this.showUploadModal = false;
      this.showToast(`已解析文件【${file.name}】：同院同名自动合并去重完成，缺证维度保留“待评”入库！`, 'success');
    },
    submitUploadPI() {
      if (this.uploadTab === 'batch') {
        this.showUploadModal = false;
        this.showToast('批量导入模板校验通过，专家名单已合并入库！', 'success');
        return;
      }
      if (!this.newPI.name || !this.newPI.hospital) {
        this.showToast('请填写完整的专家姓名及医院科室', 'error');
        return;
      }
      const created = {
        id: 'PI-CUSTOM-' + Date.now(),
        name: this.newPI.name.trim(),
        hospital: this.newPI.hospital.trim(),
        department: '临床科室',
        title: '主任医师 / 教授',
        roleLabel: '新导入专家线索',
        sourceLabel: '来源: 手工录入/Excel导入',
        domain: this.newPI.domain,
        totalScore: null,
        grade: null,
        hasPartialRating: false,
        scoreBadge: '待四维评级',
        dimSummary: '缺证维度保留待评，不填0',
        dimensions: [
          { name: '研究方向契合度', maximum: 30, score: null, basis: '新导入档案，待核实讲题与具体产品适配。' },
          { name: '学术产出质量',   maximum: 25, score: null, basis: '新导入档案，待核实近三年一作/通讯论文。' },
          { name: '科研转化潜力',   maximum: 25, score: null, basis: '新导入档案，待核实个人主持基金与样本队列。' },
          { name: '平台资源禀赋',   maximum: 20, score: null, basis: '新导入档案，待核实所在科室平台条件。' }
        ],
        ratingDate: new Date().toISOString().slice(0, 10),
        headPiStatus: '新导入PI线索 · 待拜访核实',
        sources: [],
        capabilities: ['T10 临床队列验证'],
        isAiRecommended: false,
        research: this.newPI.research || '临床队列与多组学转化研究',
        cutIn: '首次拜访建议先核实课题组在研项目、样本冻存条件与多组学测序需求。',
        talks: [],
        papers: [],
        starred: true,
        assignee: '华东一区 - 张敏',
        taskStatus: '待派发',
        syncedIntel: [],
        syncedIntelCount: 0
      };
      this.piList.unshift(created);
      this.showUploadModal = false;
      this.newPI = { name: '', hospital: '', domain: '糖尿病与代谢', research: '' };
      this.showToast(`专家【${created.name}】已成功入库作战地图！`, 'success');
    },

    showDailyReportModal: false,
    newReport: { piName: '王卫庆', content: '', nextStep: '', createIntel: true },
    openDailyReportModal() {
      this.showDailyReportModal = true;
    },
    submitDailyReport() {
      if (!this.newReport.content) {
        this.showToast('请填写拜访沟通要点', 'error');
        return;
      }
      const targetPI = this.piList.find(p => p.name === this.newReport.piName);
      const today = new Date().toISOString().split('T')[0];
      const reportObj = {
        id: 'vr_' + Date.now(),
        repName: '我 (一线销售代表)',
        date: today,
        piName: this.newReport.piName,
        qualityTag: targetPI ? `${targetPI.scoreBadge} · ${targetPI.hospital}` : '一线拜访反馈',
        content: this.newReport.content,
        nextStep: this.newReport.nextStep || '协同医学技术支持持续跟进'
      };
      this.visitReports.unshift(reportObj);
      writeStore('clinical-workbench:visit-reports:v2', this.visitReports);

      if (this.newReport.createIntel) {
        this.intelList.unshift({
          id: 'intel_' + Date.now(),
          piName: this.newReport.piName,
          hospital: targetPI ? targetPI.hospital : '重点合作医院',
          type: '日报提取 · 客户需求校准',
          content: this.newReport.content,
          date: today,
          synced: false
        });
        writeStore('clinical-workbench:intel-list:v2', this.intelList);
      }

      this.showDailyReportModal = false;
      this.newReport = { piName: '王卫庆', content: '', nextStep: '', createIntel: true };
      this.showToast('拜访日报已归档，并已自动提取客户画像校准条目！', 'success');
    },

    showPIDrawer: false,
    selectedPI: null,
    openPIDrawer(pi) {
      this.selectedPI = pi;
      this.showPIDrawer = true;
    },
    openPIById(piId) {
      const found = this.piList.find(p => p.id === piId);
      if (found) this.openPIDrawer(found);
    },
    openPIByName(name) {
      const clean = String(name || '').replace(/教授|院士|主任|博士/g, '').trim();
      const found = this.piList.find(p => p.name.includes(clean) || clean.includes(p.name));
      if (found) {
        this.openPIDrawer(found);
      } else {
        this.showToast(`正在检索专家：${name}`, 'info');
      }
    }
  };
};
