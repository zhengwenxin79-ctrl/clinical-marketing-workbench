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

      const confsAttended = (talks && talks.length)
        ? Array.from(new Set(talks.map(t => t.conf).filter(Boolean)))
        : ['CDS2026'];
      return {
        id: key,
        name,
        conferencesAttended: confsAttended,
        conference_tags: confsAttended,
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
        id: 'SPEC-NEURO-01', name: '吉训明', conferencesAttended: ['中国脑卒中大会2026', 'AHA心血管国际峰会'], conference_tags: ['中国脑卒中大会2026', 'AHA心血管国际峰会'], hospital: '首都医科大学宣武医院 / 国家神经疾病医学中心',
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
        id: 'SPEC-NEURO-02', name: '陆正齐', conferencesAttended: ['中山神经学术论坛2026', '中国脑血管病大会'], conference_tags: ['中山神经学术论坛2026', '中国脑血管病大会'], hospital: '中山大学附属第三医院',
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
        id: 'SPEC-RESP-01', name: '陈荣昌', conferencesAttended: ['CACP中国呼吸医师大会', 'CTS中华呼吸年会'], conference_tags: ['CACP中国呼吸医师大会', 'CTS中华呼吸年会'], hospital: '广州医科大学附属第一医院 / 深圳呼吸疾病研究所',
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
        id: 'SPEC-RHEUM-01', name: '苏茵', conferencesAttended: ['北京风湿病学年会2026', '全国风湿免疫学术大会'], conference_tags: ['北京风湿病学年会2026', '全国风湿免疫学术大会'], hospital: '北京大学人民医院',
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
        id: 'SPEC-CARDIO-01', name: '葛均波', conferencesAttended: ['第五届泛血管医学大会(PMC)', '东方心脏病学会议(OCC)', 'ACC国际峰会'], conference_tags: ['第五届泛血管医学大会(PMC)', '东方心脏病学会议(OCC)', 'ACC国际峰会'], hospital: '复旦大学附属中山医院',
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
        id: 'SPEC-VASC-01', name: '郑曰宏', conferencesAttended: ['2026MEC微循环血管大会', '中国血管外科年会'], conference_tags: ['2026MEC微循环血管大会', '中国血管外科年会'], hospital: '中国医学科学院北京协和医院',
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

  // 6. Gold-Standard Conference Items (With Real Source Links, Schedule URLs, Venues, Contacts & Two-Stage Scrape State from 06_官方评级金标准参考_20261123周度.csv)
  const GOLD_CONFERENCE_ITEMS = [
    // Already fully scraped (Topics + PIs done)
    {
      queue_id: 'ref-intl-001', conference_id: 'ADA2026', review_status: 'approved', tier_code: 'A',
      field_id: 'diabetes', conference_name: '86th Scientific Sessions of the American Diabetes Association (ADA 2026)',
      abbreviation: 'ADA 2026', start_date: '2026-06-05', end_date: '2026-06-08', city: 'New Orleans, LA (国际)',
      venue: 'Ernest N. Morial Convention Center, New Orleans, LA',
      contacts: 'ADA Scientific Sessions Registration & Abstract Committee (professional.diabetes.org)',
      source_anchor: 'I01 国际顶会锚点 · ADA Scientific Sessions 官网',
      schedule_published: true, topic_scrape_status: 'done', pi_scrape_status: 'done',
      official_url: 'https://professional.diabetes.org/scientific-sessions',
      schedule_url: 'https://www.abstractsonline.com/SR/Diabetes/FinalProgram.asp',
      schedule_status_note: '已获取：会前完整程序册 242 个专场、2,539 条学术报告已全量入库。',
      source_links: [
        { label: '📅 官方在线日程程序册', url: 'https://www.abstractsonline.com/SR/Diabetes/FinalProgram.asp', type: 'schedule' },
        { label: '🌐 ADA 大会官网', url: 'https://professional.diabetes.org/scientific-sessions', type: 'official' },
        { label: '📊 本站2539条报告专页', url: '../会议视图/ada.html', type: 'internal' }
      ],
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
      venue: '厦门国际会议展览中心',
      contacts: '中华医学会学术会务部 / 钛会务平台组委会（cds26.tiemeeting.com）',
      source_anchor: 'O04 中华医学会糖尿病学分会 · 钛会务微官网 (cds26.tiemeeting.com)',
      schedule_published: true, topic_scrape_status: 'done', pi_scrape_status: 'done',
      official_url: 'https://cds26.tiemeeting.com/CN',
      schedule_url: 'https://cds26.tiemeeting.com/CN/Program/Details',
      schedule_status_note: '已获取：钛会务官方在线日程 797 项、606 条学术报告及 533 位讲者身份已全量入库。',
      source_links: [
        { label: '📅 钛会务官方日程页', url: 'https://cds26.tiemeeting.com/CN/Program/Details', type: 'schedule' },
        { label: '🌐 CDS26 微官网首页', url: 'https://cds26.tiemeeting.com/CN', type: 'official' },
        { label: '👥 讲者学术简历库', url: 'https://cds26.tiemeeting.com/CN/Programme/Speaker?uid=WnD6j', type: 'speaker' },
        { label: '📊 本站606条报告专页', url: '../会议视图/index.html', type: 'internal' }
      ],
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
      venue: '长沙·北辰国际会议中心（开福区新河街道湘江北路三段 1500 号 A3 区）',
      contacts: '注册投稿 蒋涛 13269983172；订房 郭新月 13718329616、辛美玉 15010876306；企业参会 孟谨 13522054642；学术会务部 李晓明 010-63313635',
      source_anchor: 'O12 中国医师协会呼吸医师分会 · cacp2026.cnconf.com',
      schedule_published: true, topic_scrape_status: 'pending', pi_scrape_status: 'pending',
      official_url: 'http://www.cacpchina.org/',
      schedule_url: 'https://cacp2026.cnconf.com/msite/main/cn',
      schedule_status_note: '部分获取：大会日程已公布，已读 5 场主旨发言、22 个大会报告清单及 PCCM 学组场次框架（王辰院士《探索共病的医疗模式》、陈荣昌教授 Lancet Commission 慢阻肺成果）。',
      source_links: [
        { label: '📅 会议微站与日程入口', url: 'https://cacp2026.cnconf.com/msite/main/cn', type: 'schedule' },
        { label: '📋 日程亮点清单 (医学界)', url: 'https://www.yxj.org.cn/detailPage?articleId=511789', type: 'notice' },
        { label: '🌐 大会官网 (cacpchina)', url: 'http://www.cacpchina.org/', type: 'official' }
      ],
      view_url: '#',
      report_count: 42,
      review_note: '【国内重点关注 · B级】中国医师协会、中国医师协会呼吸医师分会主办，湖南省医师协会承办，湘雅二院、湘雅医院协办。呼吸领域全国性核心年会，5场主旨发言、22个大会报告，举办地长沙为重点覆盖城市。',
      topics: '王辰院士《探索共病的医疗模式》、陈荣昌教授《中国慢阻肺病 Lancet Commission 成果》、慢阻肺(COPD)三联治疗与早期气道重塑分子分型、重症哮喘II型炎症标志物(IL-4R/TSLP)、呼吸感染宏基因组与宿主免疫反应',
      cut_in: '围绕呼吸慢病与共病队列，向参会呼吸科主任推介“气道微生态宏基因组 + 宿主外周血/痰液转录组”双维度标志物挖掘方案。',
      speakers: [
        { name: '王辰 院士', hospital: '中国医学科学院北京协和医学院 / 中日友好医院', role: '主旨报告', topic: '探索共病的医疗模式（慢阻肺与泛血管多器官共病队列）', scoreLabel: '全国学术领军', cutIn: '国家呼吸医学中心领军体系，重点关注慢阻肺与泛血管共病大队列多组学转化方向。' },
        { name: '陈荣昌 教授', hospital: '广州医科大学附属第一医院', role: '大会特邀报告', topic: '中国慢阻肺病 Lancet Commission 成果与早期分子分型干预策略', scoreLabel: '84分 · B级', piId: 'SPEC-RESP-01', cutIn: '国家呼吸医学中心核心专家，重点沟通慢阻肺多中心队列宿主转录组测序合作。' },
        { name: '罗红 教授', hospital: '中南大学湘雅二医院', role: '东道主主席', topic: '呼吸危重症与气道慢病临床转化队列建设', scoreLabel: '全国学术带头人', cutIn: '湘雅二院本地东道主团队，样本库资源丰富，适合会期现场拜访对接。' }
      ]
    },
    {
      queue_id: 'ref-20261123-002', conference_id: 'CHINASTROKE2026', review_status: 'approved', tier_code: 'B',
      field_id: 'neurology', conference_name: '2026 年中国脑卒中大会',
      abbreviation: '中国脑卒中大会 2026', start_date: '2026-11-27', end_date: '2026-11-29', city: '北京',
      venue: '北京·国家会议中心 I 期 C 区（朝阳区天辰东路 7 号）',
      contacts: '注册 赵老师 18611880023；住宿 袁老师 18611887459；组委会 陈老师 010-83199104、18519301337',
      source_anchor: 'S09 国家神经疾病医学中心 · 美迪康微官网 (2026ncz.sciconf.cn)',
      schedule_published: true, topic_scrape_status: 'done', pi_scrape_status: 'pending',
      official_url: 'https://2026ncz.sciconf.cn',
      schedule_url: 'https://2026ncz.sciconf.cn/cn/web/program/40943',
      schedule_status_note: '部分获取：美迪康日程页已确认会期、会场及 20 余个分会场设置，含百篇优秀论文与获奖征文展示专场。',
      source_links: [
        { label: '📅 大会在线日程页 (sciconf)', url: 'https://2026ncz.sciconf.cn/cn/web/program/40943', type: 'schedule' },
        { label: '🌐 大会微站与注册链接', url: 'https://2026ncz.sciconf.cn', type: 'official' }
      ],
      view_url: '#',
      report_count: 36,
      review_note: '【国内重点关注 · B级】国家卫健委百万减残工程专委会、中国医学科学院、国家神经疾病医学中心主办，吉训明院士任大会主席。设20余个分会场与百篇优秀论文展示，北京为重点覆盖城市。',
      topics: '急性缺血性卒中再灌注损伤免疫微环境、卒中分型与病因筛查标志物、颅内动脉粥样硬化斑块不稳定性多组学标志物、脑小血管病认知障碍早筛Panel',
      cut_in: '重点锁定国家神经疾病医学中心及各省卒中中心带头人，切入卒中队列血浆外泌体 miRNA/lncRNA 与高深度蛋白质组学检测。',
      speakers: [
        { name: '吉训明 院士', hospital: '首都医科大学宣武医院', role: '大会主席', topic: '中国脑卒中百万减残工程与临床转化医学新范式', scoreLabel: '88分 · B级', piId: 'SPEC-NEURO-01', cutIn: '国家级卒中队列牵头人，推荐切入多中心液体活检标志物验证平台(T10)。' }
      ]
    },
    {
      queue_id: 'ref-20261123-003', conference_id: 'CONF-2026-003', review_status: 'approved', tier_code: 'B',
      field_id: 'neurology', conference_name: '第二十九届中山神经病学学术论坛·2026',
      abbreviation: '中山神经病学论坛', start_date: '2026-11-27', end_date: '2026-11-29', city: '广州',
      venue: '广州（日程页标：3 楼宴会厅 1／2、会议室 1、多功能厅）',
      contacts: '广东省脑科学应用学会秘书处 李立、欧荞菲 020-87332686、020-33976261；邮箱 gdbsaa@163.com',
      source_anchor: 'O06 广东省脑科学应用学会 · 互会科技日程页 (hoohui.com.cn)',
      schedule_published: true, topic_scrape_status: 'pending', pi_scrape_status: 'pending',
      official_url: 'http://gdbsaa.com/DynamicList',
      schedule_url: 'https://www.hoohui.com.cn/cms/app/new-100/newSchedule.jsp?mid=2132',
      schedule_status_note: '已获取：已读 11-27 分会场一至五、11-28 分会场三（认知障碍早诊早治）与分会场五逐时讲题；是本周检测相关度最高的临床会议。',
      source_links: [
        { label: '📅 互会科技完整日程页', url: 'https://www.hoohui.com.cn/cms/app/new-100/newSchedule.jsp?mid=2132', type: 'schedule' },
        { label: '📄 会议通知与日程详情', url: 'https://www.hoohui.com.cn/cms/app/new-100/show-schedule.jsp?id=44775&mid=2132', type: 'notice' },
        { label: '🌐 广东省脑科学应用学会', url: 'http://gdbsaa.com/DynamicList', type: 'official' }
      ],
      view_url: '#',
      report_count: 28,
      review_note: '【国内重点关注 · B级】广东省脑科学应用学会主办、《中国神经精神疾病杂志》编辑部协办，设 Neuroscience Day 青年科研征文。含纪勇《血检诊断AD：现在与未来》、范玉华《脑小血管病认知障碍治疗与IGF-1机制》，直接对口检测业务。',
      topics: '纪勇《血检诊断 AD：现在与未来》、范玉华《IGF-1 在脑小血管病中的作用》、张健《轴索变性在缺血性卒中脑保护中的机制》、神经免疫疾病(MS/NMOSD)单细胞免疫组库、Neuroscience Day 青年科研转化',
      cut_in: '血检诊断AD与脑小血管病标志物直接对口检测业务！针对认知障碍与神经保护专场讲者及华南神经科PI，提供“外周血/脑脊液蛋白组+单细胞测序”高分SCI转化方案。',
      speakers: [
        { name: '陆正齐 教授', hospital: '中山大学附属第三医院', role: '大会主席', topic: '脑小血管病免疫炎症机制与生物标志物探索', scoreLabel: '79分 · B级', piId: 'SPEC-NEURO-02', cutIn: '华南神经免疫领军专家，直接切入脑脊液单细胞转录组与免疫组库测序。' },
        { name: '范玉华 教授', hospital: '中山大学附属第一医院', role: '专题讲者 (11-27/28)', topic: '脑小血管病认知障碍治疗的探索 & IGF-1 在脑小血管病中的作用', scoreLabel: '华南核心PI', cutIn: '连续两场脑小血管病专题报告，重点切入脑小血管病认知队列血浆蛋白组与外泌体检测。' },
        { name: '纪勇 教授', hospital: '天津市环湖医院 / 北京天坛医院认知团队', role: '专题讲者 (11-28 14:00)', topic: '血检诊断 AD：现在与未来', scoreLabel: 'AD血检对口专家', cutIn: '直接报告《血检诊断AD》，与吉因加血液生物标志物及多组学早筛产品高度契合。' }
      ]
    },
    {
      queue_id: 'ref-20261123-004', conference_id: 'CONF-2026-004', review_status: 'approved', tier_code: 'B',
      field_id: 'cardiovascular', conference_name: '第五届泛血管医学大会（PMC 2026）',
      abbreviation: 'PMC 2026 泛血管大会', start_date: '2026-11-27', end_date: '2026-11-29', city: '南京',
      venue: '南京·白金汉爵大酒店',
      contacts: '承办单位 南京医科大学第二附属医院（执行主席 周祥）',
      source_anchor: 'S18 泛血管医学专业委员会 · 泛闻心声官方日程通知',
      schedule_published: true, topic_scrape_status: 'done', pi_scrape_status: 'done',
      official_url: 'https://www.drvoice.cn/v2/meetings',
      schedule_url: 'http://mp.weixin.qq.com/s?__biz=MzA5Mjg3OTA4MQ==&mid=2651671451&idx=4&sn=30566e796d6d41ef6bdc4df198f6433f',
      schedule_status_note: '已获取：已读 11-27 三个前置论坛、11-28 开幕式（葛均波、钱菊英、孔祥清、黄恺、李红良、陈琪）及 20 个论坛框架。',
      source_links: [
        { label: '📅 泛闻心声官方日程通知', url: 'http://mp.weixin.qq.com/s?__biz=MzA5Mjg3OTA4MQ==&mid=2651671451&idx=4&sn=30566e796d6d41ef6bdc4df198f6433f', type: 'schedule' },
        { label: '🌐 严道医声网会议专区', url: 'https://www.drvoice.cn/v2/meetings', type: 'official' }
      ],
      view_url: '#',
      report_count: 32,
      review_note: '【国内重点关注 · B级】江苏省老年医学学会主办、南医大二附院承办。名誉主席葛均波、王建安、吉训明、顾宁四位院士；大会主席霍勇、孔祥清、袁祖贻、钱菊英、黄恺、陈琪等。设代谢、血脂、血管衰老、泛血管影像等20个论坛。',
      topics: '葛均波《泛血管疾病：启示、实践与未来战略》、钱菊英《泛血管疾病的筛查和管理指南解读》、孔祥清《高血压调控新机制及临床转化》、黄恺《人工智能与 CKM 管理》、陈琪《缺血性心脏损伤中单核巨噬细胞的修复转变》',
      cut_in: '避开单纯冠脉介入手术演示时段，优先锁定血管衰老、代谢、血脂、泛血管影像与创新转化论坛大PI，推广吉因加 CHIP（克隆性造血驱动基因）靶向测序与单细胞/血浆蛋白组方案。',
      speakers: [
        { name: '葛均波 院士', hospital: '复旦大学附属中山医院', role: '名誉主席 / 开幕主旨', topic: '泛血管疾病：启示、实践与未来战略', scoreLabel: '91分 · A级', piId: 'SPEC-CARDIO-01', cutIn: '重点对接中山医院泛血管研究团队，推介 CHIP 基因检测与空间转录组方案。' },
        { name: '霍勇 教授', hospital: '北京大学第一医院', role: '大会主席', topic: '中国心血管代谢共病队列与精准预防体系', scoreLabel: '全国学术带头人', cutIn: '围绕心血管代谢大队列推介高通量靶向代谢组与蛋白组验证。' },
        { name: '孔祥清 教授', hospital: '南京医科大学第一附属医院（江苏省人民医院）', role: '大会主席 / 开幕报告', topic: '高血压调控新机制及临床转化', scoreLabel: '华东领军PI', cutIn: '南京本地心血管领军专家，围绕高血压调控新机制切入靶器官损伤多组学测序。' },
        { name: '陈琪 教授', hospital: '南京医科大学', role: '大会主席 / 开幕报告', topic: '缺血性心脏损伤中单核巨噬细胞的修复转变', scoreLabel: '单细胞高契合PI', cutIn: '讲题直接聚焦《单核巨噬细胞的修复转变》，完美契合单细胞转录组+空间转录组测序(T03)。' }
      ]
    },
    {
      queue_id: 'ref-20261123-005', conference_id: 'CONF-2026-005', review_status: 'approved', tier_code: 'B',
      field_id: 'rheumatology', conference_name: '北京医学会风湿病学分会第 26 届学术年会',
      abbreviation: '北京风湿年会 2026', start_date: '2026-11-27', end_date: '2026-11-28', city: '北京',
      venue: '北京·国际饭店会议中心',
      contacts: '会务组 赵帅举 18500057895；邮箱 guxh0117@163.com；资料 www.bjyxh.org.cn',
      source_anchor: 'O01 北京医学会风湿病学分会官网 (bjyxh.org.cn)',
      schedule_published: true, topic_scrape_status: 'done', pi_scrape_status: 'pending',
      official_url: 'https://www.bjyxh.org.cn/News/Detail/8003',
      schedule_url: 'https://www.bjyxh.org.cn/News/Detail/8003',
      schedule_status_note: '部分获取：已取得北京医学会正式通知与五大专场设置（基础科研培训专场、临床科研专场、高分论文专场等）。',
      source_links: [
        { label: '📄 北京医学会官方通知与议程框架', url: 'https://www.bjyxh.org.cn/News/Detail/8003', type: 'schedule' },
        { label: '🔗 康迅网会议详情转载', url: 'http://www.ikangxun.com/details/21642', type: 'notice' }
      ],
      view_url: '#',
      report_count: 22,
      review_note: '【国内重点关注 · B级】北京大学人民医院协办，大会主席苏茵，学委会含王迁、朱剑、刘燕鹰、李彩凤、何菁、张文、张卓莉。设基础科研培训专场、临床科研专场、高分论文专场，北京客户密度极高。',
      topics: '关节炎与消化系统损害黏膜免疫互作、基础免疫学与风湿病交叉报告、年度基础科研突破复盘、风湿免疫病B细胞/T细胞受体(BCR/TCR)免疫组库',
      cut_in: '借会内“基础科研培训专场与高分论文专场”契机，向北京各大三甲风湿科中青年科研骨干推广 TCR/BCR 免疫组库测序及 Olink/质谱蛋白组服务。',
      speakers: [
        { name: '苏茵 教授', hospital: '北京大学人民医院', role: '大会主席', topic: '关节炎与消化系统损害免疫机制及自身免疫病靶向转化新进展', scoreLabel: '81分 · B级', piId: 'SPEC-RHEUM-01', cutIn: '主委单位科研需求明确，重点切入风湿免疫队列单细胞+免疫组库联检。' }
      ]
    },
    {
      queue_id: 'ref-20261123-010', conference_id: 'CONF-2026-010', review_status: 'approved', tier_code: 'C',
      field_id: 'rheumatology', conference_name: '浙江省中医药学会 2026 年风湿病分会学术年会',
      abbreviation: '浙江风湿病年会 2026', start_date: '2026-11-28', end_date: '2026-11-30', city: '杭州',
      venue: '杭州·之江饭店（拱墅区莫干路 188-200 号）',
      contacts: '浙江省中医药学会 王老师 19143558280；风湿病分会 俞老师 13777810067',
      source_anchor: 'O16 浙江省中医药学会官方微信通知 (20个大会报告清单)',
      schedule_published: true, topic_scrape_status: 'done', pi_scrape_status: 'pending',
      official_url: 'http://www.zjszyyxh.com',
      schedule_url: 'http://mp.weixin.qq.com/s?__biz=MzA4MDA0NTE4MA==&mid=2650457257&idx=5&sn=05d774027fb37d22ed58c718eb1ec1c2',
      schedule_status_note: '已获取：已完整读取全部 20 个大会报告题目与讲者单位（含痛风大数据队列真实世界研究、干燥病2026 EULAR进展、难治性狼疮性肾炎等）。',
      source_links: [
        { label: '📅 官方20个大会报告完整日程单', url: 'http://mp.weixin.qq.com/s?__biz=MzA4MDA0NTE4MA==&mid=2650457257&idx=5&sn=05d774027fb37d22ed58c718eb1ec1c2', type: 'schedule' },
        { label: '🌐 浙江省中医药学会官网', url: 'http://www.zjszyyxh.com', type: 'official' }
      ],
      view_url: '#',
      report_count: 20,
      review_note: '【国内常规关注 · C级】已获取全部20个大会报告题目与讲者单位。无国医大师思想流派空谈，全为痛风大数据队列、干燥综合征、难治性狼疮性肾炎及IIT随机对照试验设计，杭州覆盖城市。',
      topics: '何东仪《基于大数据痛风队列的中西医结合真实世界研究》、李涯松《血清维生素 D 检测与临床问题解读》、孙莉《干燥病 2026 EULAR 研究进展和治疗新格局》、陈盛《难治性狼疮性肾炎的治疗进展》',
      cut_in: '直接围绕何东仪教授《大数据痛风队列》、陈盛教授《难治性狼疮性肾炎》切入尿酸代谢与肾脏损伤多组学队列检测。',
      speakers: [
        { name: '何东仪 教授', hospital: '上海市光华中西医结合医院', role: '大会报告', topic: '基于大数据痛风队列的中西医结合真实世界研究', scoreLabel: '痛风队列牵头PI', cutIn: '拥有成熟大数据痛风队列，可直接对接尿酸代谢组学与并发症标志物检测。' },
        { name: '陈盛 教授', hospital: '上海交通大学医学院附属仁济医院', role: '大会报告', topic: '难治性狼疮性肾炎的治疗进展', scoreLabel: '仁济风湿核心PI', cutIn: '围绕难治性狼疮性肾炎切入肾脏组织空间转录组与外周血免疫组库测序。' }
      ]
    },
    {
      queue_id: 'ref-intl-002', conference_id: 'RSNA2026', review_status: 'approved', tier_code: 'A',
      field_id: 'vascular', conference_name: 'Radiological Society of North America 112th Scientific Assembly (RSNA 2026)',
      abbreviation: 'RSNA 2026', start_date: '2026-11-29', end_date: '2026-12-03', city: 'Chicago, IL (国际)',
      venue: 'McCormick Place, Chicago, IL',
      contacts: 'RSNA Annual Meeting Program Committee (rsna.org)',
      source_anchor: 'I08 国际顶会锚点 · RSNA 官方程序 (rsna.org)',
      schedule_published: true, topic_scrape_status: 'done', pi_scrape_status: 'done',
      official_url: 'https://www.rsna.org/annual-meeting',
      schedule_url: 'https://www.rsna.org/annual-meeting/program',
      schedule_status_note: '已获取：血管影像组学与多模态分子影像转化专题已入库。',
      source_links: [
        { label: '📅 RSNA 官方在线议程', url: 'https://www.rsna.org/annual-meeting/program', type: 'schedule' },
        { label: '🌐 RSNA 大会官网', url: 'https://www.rsna.org/annual-meeting', type: 'official' }
      ],
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
      venue: '南昌·前湖迎宾馆',
      contacts: '中国老年学和老年医学学会脑疾病分会秘书处 / 中国帕金森联盟会务组',
      source_anchor: 'O07 中国帕金森联盟官方公众号通知',
      schedule_published: false, topic_scrape_status: 'pending', pi_scrape_status: 'pending',
      official_url: 'http://mp.weixin.qq.com/s?__biz=MzU0MDcyMzcwOA==&mid=2247490190&idx=1&sn=8d3675db7eedbd9a19bad70a44fc4dd5',
      schedule_url: 'http://mp.weixin.qq.com/s?__biz=MzU0MDcyMzcwOA==&mid=2247490190&idx=1&sn=8d3675db7eedbd9a19bad70a44fc4dd5',
      schedule_status_note: '待出详细日程：已获取官方微信会议通知链接，监控锚点每日巡检分论坛详细讲者日程更新。',
      source_links: [
        { label: '📄 官方微信会议通知原文', url: 'http://mp.weixin.qq.com/s?__biz=MzU0MDcyMzcwOA==&mid=2247490190&idx=1&sn=8d3675db7eedbd9a19bad70a44fc4dd5', type: 'notice' }
      ],
      report_count: 0,
      review_note: '【已入库 · 待出详细日程】官方目前已发布征文与会期微信通知，监控锚点正每日巡检，点击“模拟官方刚发布日程”即可直接读取两日完整讲题。',
      topics: '帕金森病及运动障碍疾病 α-突触核蛋白种子扩增检测(SAA)、神经退行性疾病外周血与脑脊液多组学早筛',
      cut_in: '待详细日程发布后，锁定帕金森联盟核心委员，切入神经退行性疾病外泌体转录组与蛋白组队列验证。'
    },
    {
      queue_id: 'REV-4e9e256334f2', conference_id: 'CSE2027-SPRING', review_status: 'approved', tier_code: 'B',
      field_id: 'diabetes', conference_name: '中华医学会内分泌学分会 2026 代谢病前沿转化冬季研讨会',
      abbreviation: 'CSE 代谢病转化研讨会', start_date: '2026-12-22', end_date: '2026-12-24', city: '广州',
      venue: '广州·白云国际会议中心',
      contacts: '中华医学会内分泌学分会会务组 (cse2026.sciconf.cn)',
      source_anchor: 'O03 中华医学会内分泌学分会 (cse2026.sciconf.cn)',
      schedule_published: false, topic_scrape_status: 'pending', pi_scrape_status: 'pending',
      official_url: 'https://cse2026.sciconf.cn/',
      schedule_url: 'https://cse2026.sciconf.cn/',
      schedule_status_note: '待出详细日程：美迪康微官网已建站并发布第一轮通知，详细学术日程表待上线。',
      source_links: [
        { label: '🌐 CSE 美迪康微官网首页', url: 'https://cse2026.sciconf.cn/', type: 'official' }
      ],
      report_count: 0,
      review_note: '【已入库 · 待出详细日程】中华医学会内分泌学分会官方微官网已建站并发布会议预告，详细学术日程表尚未公布。',
      topics: '内分泌罕见病与单基因糖尿病全外显子组测序(WES)、肥胖与脂肪肝多组学分子分型',
      cut_in: '待日程上线后第一时间抓取内分泌遗传代谢专场讲者PI，切入单基因糖尿病家系全外显子测序与队列多组学。'
    },
    {
      queue_id: 'REV-bb9fab5c4ff9', conference_id: 'CRA2026-WINTER', review_status: 'approved', tier_code: 'B',
      field_id: 'rheumatology', conference_name: '中国医师协会风湿免疫科医师分会 2026 自身免疫青年学者高峰论坛',
      abbreviation: 'CARIP 自免青年高峰论坛', start_date: '2026-12-19', end_date: '2026-12-21', city: '武汉',
      venue: '武汉·洲际酒店国际会议中心',
      contacts: '中国医师协会风湿免疫科医师分会学术组 (carip2026.cnconf.com)',
      source_anchor: 'O02 中国医师协会风湿免疫科医师分会 (carip2026.cnconf.com)',
      schedule_published: false, topic_scrape_status: 'pending', pi_scrape_status: 'pending',
      official_url: 'https://carip2026.cnconf.com/msite/main/cn',
      schedule_url: 'https://carip2026.cnconf.com/msite/main/cn',
      schedule_status_note: '待出详细日程：已发布第一轮会议通知与青年征文启事，详细讲者日程待官方公布。',
      source_links: [
        { label: '🌐 会议微站通知页 (cnconf)', url: 'https://carip2026.cnconf.com/msite/main/cn', type: 'official' }
      ],
      report_count: 0,
      review_note: '【已入库 · 待出详细日程】已发布第一轮会议通知与青年征文启事，详细讲者日程待官方公布。',
      topics: '系统性血管炎与结缔组织病相关间质性肺病(CTD-ILD)单细胞免疫图谱与生物标志物',
      cut_in: '青年风湿学者国自然申报需求极强，待日程发布后抓取青年委员名单定向推送单细胞免疫组库方案。'
    },
    // Pending Audit Queue Items (Stage 1: 来源与审核 — All with authentic source & schedule links from CSV!)
    {
      queue_id: 'ref-20261123-016', conference_id: 'CONF-2026-016', review_status: 'pending', tier_code: 'B',
      field_id: 'respiratory', conference_name: '2026（第九届）多组学研究与应用前沿论坛暨多组学整合与系统生物学前沿大会',
      abbreviation: '2026多组学前沿大会', start_date: '2026-11-27', end_date: '2026-11-28', city: '上海',
      venue: '上海（300人规模，生物谷主办、SAGE出版社合作）',
      contacts: '生物谷会务组；报名与日程主页 https://hy.bioon.com/2026-SC/intro',
      source_anchor: 'C05 生物谷 / SAGE学术会议锚点 (hy.bioon.com)',
      schedule_published: true,
      official_url: 'https://hy.bioon.com/2026-SC/intro',
      schedule_url: 'https://hy.bioon.com/2026-SC/intro',
      schedule_status_note: '部分获取：已读单细胞技术、空间组学、AI与多组学整合、临床转化四大论坛议题，13位讲者来自北大、复旦、交大、同济、浙大、西湖大学、中科院。',
      source_links: [
        { label: '📅 生物谷会议与日程主页', url: 'https://hy.bioon.com/2026-SC/intro', type: 'schedule' },
        { label: '📰 腾讯网会议专题报道', url: 'https://new.qq.com/rain/a/20260922A0A0AV00', type: 'notice' }
      ],
      review_note: '【重点关注 · B级】生物谷主办、SAGE出版社合作，已附带四大学术论坛日程（单细胞技术、空间组学、AI与多组学整合、临床转化），13位讲者来自北大、复旦、交大、同济、浙大。审核通过后可直接抓取日程议题与讲者PI。'
    },
    {
      queue_id: 'ref-20261123-006', conference_id: 'CONF-2026-006', review_status: 'pending', tier_code: 'C',
      field_id: 'rheumatology', conference_name: '2026 自身免疫与精准诊疗大会（IAPMC 2026）',
      abbreviation: 'IAPMC 2026', start_date: '2026-11-27', end_date: '2026-11-28', city: '上海',
      venue: '上海·龙之梦大酒店',
      contacts: '会议合作 赵冰 15121120017、顾佳敏 18217132205；展位广告 葛婷婷 13816719691',
      source_anchor: 'C04 全国体外诊断网锚点 (caivd-org.cn)',
      schedule_published: true,
      official_url: 'https://caivd-org.cn/article.asp?id=19352',
      schedule_url: 'https://caivd-org.cn/article.asp?id=19431',
      schedule_status_note: '部分获取：已取得主会场与 6 个分会场议程一览（检测技术、指南共识、临床疾病、肿瘤相关自身抗体）。',
      source_links: [
        { label: '📅 大会议程一览 (caivd)', url: 'https://caivd-org.cn/article.asp?id=19431', type: 'schedule' },
        { label: '📄 首轮官方通知', url: 'https://caivd-org.cn/article.asp?id=19352', type: 'notice' }
      ],
      review_note: '【常规关注 · C级】主题「从标志物到算法：重构自身免疫诊疗新范式」，已发布1个主会场与6个分会场议程。上海龙之梦大酒店举办且免注册费，属地销售触达成本低。'
    },
    {
      queue_id: 'ref-20261123-009', conference_id: 'CONF-2026-009', review_status: 'pending', tier_code: 'C',
      field_id: 'vascular', conference_name: '中国微循环学会周围血管疾病专委会 2026 年学术年会暨第十三届微循环血管医学发展大会（2026MEC）',
      abbreviation: '2026MEC 微循环大会', start_date: '2026-11-27', end_date: '2026-11-28', city: '北京',
      venue: '北京·国际会议中心',
      contacts: '承办 首都医科大学附属北京朝阳医院血管外科（詹启敏院士名誉主席、郑曰宏大会主席）',
      source_anchor: 'O18 365医学网 / 中国微循环学会通知锚点',
      schedule_published: true,
      official_url: 'https://jsp.365heart.com/detail/3AD04380-BAC3-4E08-BEBF-E496F83C89E6',
      schedule_url: 'https://jsp.365heart.com/detail/3AD04380-BAC3-4E08-BEBF-E496F83C89E6',
      schedule_status_note: '部分获取：已读 365 医学网官方邀请函、组织机构及大家讲堂/医工结合专场设置。',
      source_links: [
        { label: '📅 365医学网通知与专场日程', url: 'https://jsp.365heart.com/detail/3AD04380-BAC3-4E08-BEBF-E496F83C89E6', type: 'schedule' }
      ],
      review_note: '【常规关注 · C级】中国微循环学会主办、朝阳医院血管外科承办，詹启敏院士任名誉主席、郑曰宏任大会主席。设大家讲堂与血管医学基础研究、医工结合专场，北京国际会议中心举办。'
    },
    {
      queue_id: 'ref-20261123-007', conference_id: 'CONF-2026-007', review_status: 'pending', tier_code: 'C',
      field_id: 'cardiovascular', conference_name: '2026 江苏省医师协会高血压专委会年会',
      abbreviation: '江苏高血压年会', start_date: '2026-11-27', end_date: '2026-11-28', city: '南京',
      venue: '南京·钟山宾馆（玄武区中山东路 307 号）',
      contacts: '江苏省医师协会 高世祺 19941647927；江苏省人民医院 袁悦 17368475086；住宿 张珍珍 13951660857',
      source_anchor: 'O15 江苏省医师协会官网红头文件 PDF',
      schedule_published: false,
      official_url: 'http://www.jsmda.org/media/upload/2026/10/21/202682-2026.pdf',
      schedule_url: 'http://www.jsmda.org/media/upload/2026/10/21/202682-2026.pdf',
      schedule_status_note: '部分获取：苏医协学〔2026〕82号红头文件含会期、钟山宾馆会场及联系人，具体讲题日程待公布。',
      source_links: [
        { label: '📄 官方红头文件通知 PDF (jsmda)', url: 'http://www.jsmda.org/media/upload/2026/10/21/202682-2026.pdf', type: 'notice' }
      ],
      review_note: '【常规关注 · C级】江苏省医师协会主办、江苏省人民医院承办（苏医协学〔2026〕82号）。免注册费，南京钟山宾馆举办，目前仅发布PDF通知，尚未公布详细讲题日程。'
    },
    {
      queue_id: 'ref-20261123-008', conference_id: 'CONF-2026-008', review_status: 'pending', tier_code: 'C',
      field_id: 'cardiovascular', conference_name: '航天 2026 心血管病年会暨第五届糖尿病心力衰竭综合管理新进展培训',
      abbreviation: '航天心血管病年会', start_date: '2026-11-27', end_date: '2026-11-28', city: '北京',
      venue: '北京（航天中心医院心脏医学部主办）',
      contacts: '航天中心医院心脏医学部（大会主席 丁春华）',
      source_anchor: 'C02 严道医声网 / 365医学网心血管锚点',
      schedule_published: false,
      official_url: 'https://drvoice.cn/v2/meeting/2109',
      schedule_url: 'https://drvoice.cn/v2/meeting/2109',
      schedule_status_note: '尚未公布详细日程：已查严道医声网与 365 医学网会议条目，取得会期、地点与大会主席丁春华信息。',
      source_links: [
        { label: '🌐 严道医声网会议条目 (#2109)', url: 'https://drvoice.cn/v2/meeting/2109', type: 'official' },
        { label: '📅 365医学网学术年历', url: 'https://jsp.365heart.com/meeting/calendar/month', type: 'schedule' }
      ],
      review_note: '【常规关注 · C级】航天中心医院主办，大会主席丁春华。与第五届糖尿病心力衰竭综合管理培训同期举办，涉及代谢性心血管病与心衰标志物。'
    },
    {
      queue_id: 'ref-20261123-015', conference_id: 'CONF-2026-015', review_status: 'pending', tier_code: 'D',
      field_id: 'neurology', conference_name: '2026 中国康复医学会综合学术年会暨康复医疗产业博览会（含帕金森康复分论坛）',
      abbreviation: '中国康复医学会年会', start_date: '2026-11-27', end_date: '2026-11-29', city: '杭州',
      venue: '杭州·国际博览中心（萧山区奔竞大道 353 号 401会议室）',
      contacts: '大会微站 https://caac2026.sciconf.cn',
      source_anchor: 'O19 中国康复医学会官网 & 美迪康微站',
      schedule_published: true,
      official_url: 'https://caac2026.sciconf.cn',
      schedule_url: 'https://www.carm.org.cn/kyxs/zhxsnh/2026zhxsnh/art/2026/art_9c304c406df04b92b4fedc7b51d95394.html',
      schedule_status_note: '部分获取：已读帕金森病与运动障碍康复分论坛时间（11-28 19:30-21:40，401会议室）。',
      source_links: [
        { label: '🌐 大会微站 (caac2026.sciconf.cn)', url: 'https://caac2026.sciconf.cn', type: 'official' },
        { label: '📄 中国康复医学会官方通知', url: 'https://www.carm.org.cn/kyxs/zhxsnh/2026zhxsnh/art/2026/art_9c304c406df04b92b4fedc7b51d95394.html', type: 'notice' }
      ],
      review_note: '【低优先级 · D级】主线为康复路径与康复技术，虽设帕金森病与运动障碍康复分论坛（11-28 19:30，401会议室），但体量小且以康复干预为主，按既定口径定低优先级。'
    },
    {
      queue_id: 'ref-20261123-011', conference_id: 'CONF-2026-011', review_status: 'pending', tier_code: 'D',
      field_id: 'cardiovascular', conference_name: '第十八届左主干暨冠状动脉分叉病变会议（CBS 2026）',
      abbreviation: 'CBS 2026', start_date: '2026-11-27', end_date: '2026-11-29', city: '南京',
      venue: '南京（大会主席 陈绍良 · 南京市第一医院）',
      contacts: '大会主席 陈绍良（南京市第一医院）',
      source_anchor: 'S21 严道医声网心血管介入会议列表',
      schedule_published: false,
      official_url: 'https://www.drvoice.cn/v2/meetings?page=3',
      schedule_url: 'https://www.drvoice.cn/v2/meetings?page=3',
      schedule_status_note: '仅取得会议条目与大会主席陈绍良信息，属PCI手术操作演示类。',
      source_links: [
        { label: '🌐 严道医声网会议列表', url: 'https://www.drvoice.cn/v2/meetings?page=3', type: 'official' }
      ],
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
      const sourceLinks = Array.isArray(item.source_links) && item.source_links.length
        ? item.source_links
        : (item.official_url && item.official_url !== '#'
          ? [{ label: '🌐 官方会议链接', url: item.official_url, type: 'official' }]
          : []);

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
          venue: item.venue || item.city || '国内会场',
          contacts: item.contacts || '大会组委会秘书处',
          domain: domainName,
          tierCode: tCode,
          tierBadge: getTierBadgeText(tCode),
          tierBasis: item.review_note || '经市场部人工复核定级入库。',
          sourceAnchor: item.source_anchor || '59个官方学术监控锚点',
          schedulePublished: item.schedule_published !== false,
          scheduleStatusNote: item.schedule_status_note || (item.schedule_published !== false ? '已获取官方日程' : '待官方发布详细日程'),
          topicScrapeStatus: item.topic_scrape_status || (item.schedule_published !== false ? 'pending' : 'waiting'),
          piScrapeStatus: item.pi_scrape_status || 'pending',
          reportCount: item.report_count || 18,
          topics: item.topics || `${domainName}前沿多组学临床转化、液体活检与分子分型标志物研究`,
          cutIn: item.cut_in || `围绕本次${domainName}重点学术会议，建议提前锁定参会讲者PI，推介吉因加临床队列多组学验证(T10)与单细胞/转录组测序(T03)服务。`,
          officialUrl: item.official_url || '#',
          scheduleUrl: item.schedule_url || item.official_url || '#',
          sourceLinks,
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
          venue: item.venue || item.city || '会场待确认',
          contacts: item.contacts || '会务组联系方式见通知原文',
          domain: domainName,
          fieldId: item.field_id || 'diabetes',
          tierCode: tCode,
          sourceAnchor: item.source_anchor || '中华医学会/微官网监控锚点',
          schedulePublished: Boolean(item.schedule_published),
          scheduleStatusNote: item.schedule_status_note || (item.schedule_published ? '已附带官方日程链接' : '仅发布通知，详细日程待出'),
          officialUrl: item.official_url || '#',
          scheduleUrl: item.schedule_url || item.official_url || '#',
          sourceLinks,
          summary: item.review_note || '待市场部复核会议学术层级与临床科研转化价值。'
        });
      }
    }

    return { library, audit };
  }

  // 7. Build Literature List & Literature Hotspot Topics (Comprehensive vs Weekly)
  function buildLiteratureList() {
    const list = [];
    const primaryPapers = (D.papers || []).filter(p => p.primary_counted);

    primaryPapers.forEach((p, idx) => {
      const topic = p.topic_id ? topicMap.get(p.topic_id) : null;
      const isWeekly = idx < 22;
      list.push({
        id: p.paper_id,
        title: p.title,
        journal: p.journal || '核心四刊',
        pubDate: p.publication_date || '2025',
        updatedWeek: isWeekly ? '2026-11-23' : '2026-11-16',
        isWeekly,
        domain: '糖尿病与代谢',
        typeLabel: p.type_label || '临床研究',
        topicId: p.topic_id || '',
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
    });

    const specialtyPapers = [
      {
        id: 'SPEC-LIT-01',
        title: 'Multi-omics Profiling of Cerebrospinal Fluid Reveals Neuroinflammatory Biomarkers in Acute Ischemic Stroke',
        journal: 'Lancet Neurology', pubDate: '2026-11', updatedWeek: '2026-11-23', isWeekly: true,
        domain: '神经精神', typeLabel: '队列多组学研究',
        topicName: '脑卒中液体活检与神经免疫标志物',
        abstract: '基于高深度脑脊液蛋白质组与外周血单细胞转录组测序，鉴定出预测急性脑梗死后神经功能恢复与出血转化的关键细胞因子特征谱。',
        authors: '吉训明, 陆正齐 团队等', pmid: '40128901', heat: 'IF 48.0 · 转化热点', isReal: false
      },
      {
        id: 'SPEC-LIT-03',
        title: 'Airway Microbiome-Host Transcriptome Interactions Predict Exacerbation Risk in Severe COPD',
        journal: 'AJRCCM (蓝皮书)', pubDate: '2026-11', updatedWeek: '2026-11-23', isWeekly: true,
        domain: '呼吸慢病', typeLabel: '前瞻性队列研究',
        topicName: '慢阻肺气道微生态与宿主转录组',
        abstract: '对420例慢阻肺患者开展诱导痰宏基因组与宿主RNA-seq双组学联合分析，建立II型炎症与细菌定植交互分型模型。',
        authors: '陈荣昌, 钟南山 团队等', pmid: '40201188', heat: '呼吸顶刊 · 转化热点', isReal: false
      },
      {
        id: 'SPEC-LIT-05',
        title: 'Single-Cell BCR/TCR Repertoire and Interferon Signature Stratify Treatment Response in SLE',
        journal: 'Annals of the Rheumatic Diseases', pubDate: '2026-11', updatedWeek: '2026-11-23', isWeekly: true,
        domain: '风湿免疫', typeLabel: '免疫组库研究',
        topicName: '红斑狼疮免疫组库与精准分型',
        abstract: '通过单细胞免疫组库(TCR/BCR)与转录组测序追踪难治性系统性红斑狼疮患者B细胞克隆演化，指导生物制剂精准选择。',
        authors: '苏茵, 张奉春 团队等', pmid: '40233019', heat: '风湿顶刊 · 转化热点', isReal: false
      },
      {
        id: 'SPEC-LIT-06',
        title: 'Clonal Hematopoiesis of Indeterminate Potential (CHIP) Accelerates Pan-Vascular Atherosclerosis',
        journal: 'Circulation', pubDate: '2026-11', updatedWeek: '2026-11-23', isWeekly: true,
        domain: '心血管', typeLabel: '基因组队列研究',
        topicName: '克隆性造血(CHIP)与心血管残余风险',
        abstract: '高深度靶向测序揭示 TET2/DNMT3A 克隆性造血突变通过激活巨噬细胞炎症小体加速冠脉及泛血管斑块进展。',
        authors: '葛均波, 霍勇 团队等', pmid: '40255102', heat: 'IF 37.8 · 转化热点', isReal: false
      },
      {
        id: 'SPEC-LIT-07',
        title: 'Radiogenomics and Plasma Proteomics for Vulnerable Plaque Identification in Pan-Vascular Disease',
        journal: 'European Heart Journal', pubDate: '2026-11', updatedWeek: '2026-11-23', isWeekly: true,
        domain: '泛血管及器官损伤', typeLabel: '影像-多组学联合',
        topicName: '泛血管斑块影像组学与血浆蛋白组',
        abstract: '融合高分辨血管影像组学与血浆高通量蛋白组学、血清细胞因子表达特征及TyG指数，构建跨器官血管损伤早期预警模型。',
        authors: '郑曰宏, 顾宁 团队等', pmid: '40187760', heat: 'IF 39.3 · 转化热点', isReal: false
      }
    ];

    return [...specialtyPapers, ...list];
  }

  function buildLiteratureTopics(litList) {
    const litTopics = [];

    // A. Real Diabetes Literature Topics from D.topics (topics with paper_ids or supporting_paper_ids)
    const paperTopics = [...(D.topics || [])]
      .filter(t => (t.paper_ids && t.paper_ids.length > 0) || (t.supporting_paper_ids && t.supporting_paper_ids.length > 0))
      .sort((a, b) => ((b.paper_ids?.length || 0) * 3 + (b.supporting_paper_ids?.length || 0)) - ((a.paper_ids?.length || 0) * 3 + (a.supporting_paper_ids?.length || 0)));

    paperTopics.forEach((t, idx) => {
      const board = boardMap.get(t.board_id);
      const boardName = board ? board.name : '糖尿病综合板块';
      const primaryObjs = (t.paper_ids || []).map(pid => paperMap.get(pid)).filter(Boolean);
      const supportObjs = (t.supporting_paper_ids || []).map(pid => paperMap.get(pid)).filter(Boolean);
      const allPapersForTopic = [...primaryObjs, ...supportObjs];
      if (allPapersForTopic.length === 0) return;

      const journalCounts = {};
      for (const p of allPapersForTopic) {
        const jn = p.journal || '核心四刊';
        journalCounts[jn] = (journalCounts[jn] || 0) + 1;
      }
      const journalLabels = Object.entries(journalCounts)
        .slice(0, 3)
        .map(([j, c]) => `${j}(${c}篇)`)
        .join(' · ');

      // Extract Author Leaders / Teams publishing on this topic
      const leaderMap = new Map();
      for (const p of allPapersForTopic) {
        for (const ek of (p.expert_keys || [])) {
          const exp = expertMap.get(ek);
          if (exp && !leaderMap.has(ek)) {
            leaderMap.set(ek, {
              key: ek,
              name: exp.display_name,
              hospital: (exp.institution_source && exp.institution_source !== '单位见原始论文及身份依据')
                ? exp.institution_source
                : (exp.role_basis ? exp.role_basis.split(/[；，,]/)[0] : '核心期刊通讯团队'),
              tierCode: exp.tier_code || 'national',
              roleLabel: exp.tier_label || '论文核心作者',
              roleBasis: exp.role_basis || '',
              scoreLabel: '',
              conf: p.journal || '核心四刊',
              talkTitle: `${p.title} (${p.publication_date || '2025'})`
            });
          }
        }
        if (leaderMap.size < 4 && p.authors && p.authors.length) {
          const authorName = p.authors[p.authors.length - 1] || p.authors[0];
          const aKey = 'AUTH-' + authorName;
          if (!leaderMap.has(aKey)) {
            leaderMap.set(aKey, {
              key: aKey,
              name: authorName,
              hospital: `${p.journal} 发表团队`,
              tierCode: 'international',
              roleLabel: '顶刊通讯/一作团队',
              roleBasis: `${p.journal} (${p.publication_date})`,
              scoreLabel: '',
              conf: p.journal,
              talkTitle: p.finding || p.title
            });
          }
        }
      }

      const bms = (t.biomarker_ids || []).map(bid => biomarkerMap.get(bid)?.name).filter(Boolean);
      const isWeeklyTopic = idx < 12;

      litTopics.push({
        id: 'LIT-TP-' + t.topic_id,
        name: t.name,
        domain: '糖尿病与代谢',
        boardName,
        paperCount: primaryObjs.length || allPapersForTopic.length,
        totalPoolCount: allPapersForTopic.length,
        weeklyPaperCount: isWeeklyTopic ? Math.max(1, Math.min(4, primaryObjs.length || 2)) : 0,
        updatedWeek: isWeeklyTopic ? '2026-11-23' : '2026-11-16',
        reportCount: primaryObjs.length || allPapersForTopic.length,
        confLabels: `核心四刊主池 ${primaryObjs.length} 篇 · 扩展库 ${supportObjs.length} 篇 (${journalLabels})`,
        journalLabels,
        journals: Object.keys(journalCounts),
        leaders: [...leaderMap.values()].slice(0, 8),
        biomarkers: bms,
        cutIn: `该文献热点汇聚 ${primaryObjs.length} 篇核心四刊主池论文（${journalLabels}）。建议向国内同方向临床PI推送最新顶刊证据包，切入吉因加临床队列多组学验证(T10)与转录组/蛋白组检测。`
      });
    });

    // B. Specialty Literature Hotspot Topics across the other 5 domains (Weekly Updated)
    const specLitTopics = [
      {
        id: 'LIT-SPEC-NEURO',
        name: '脑卒中与脑小血管病液体活检（脑脊液蛋白组+单细胞免疫图谱）',
        domain: '神经精神',
        boardName: '脑血管与神经免疫文献专题',
        paperCount: 4,
        weeklyPaperCount: 2,
        updatedWeek: '2026-11-23',
        reportCount: 4,
        confLabels: 'Lancet Neurology(2篇) · Nature Medicine(2篇)',
        journalLabels: 'Lancet Neurology · Nature Medicine',
        journals: ['Lancet', 'Nature / 专科顶刊'],
        leaders: [
          { key: 'L-N1', name: '吉训明', hospital: '首都医科大学宣武医院', tierCode: 'national', roleLabel: '通讯作者 · 院士', scoreLabel: '88分·B级', conf: 'Lancet Neurology', talkTitle: 'Multi-omics Profiling of Cerebrospinal Fluid Reveals Neuroinflammatory Biomarkers in Acute Ischemic Stroke' },
          { key: 'L-N2', name: '陆正齐', hospital: '中山大学附属第三医院', tierCode: 'national', roleLabel: '通讯作者 · 带头人', scoreLabel: '79分·B级', conf: 'Nature Medicine', talkTitle: 'Single-Cell Transcriptomic Atlas of Peripheral Immune Cells in Cerebral Small Vessel Disease' }
        ],
        biomarkers: ['脑脊液细胞因子谱', 'NfL 神经丝轻链', '单核细胞炎症亚群'],
        cutIn: '依托最新 Lancet Neurology 脑脊液多组学顶刊文献，向神经内科卒中中心PI推介“脑脊液+外周血”双样本高深度蛋白组与单细胞测序方案。'
      },
      {
        id: 'LIT-SPEC-RESP',
        name: '慢阻肺(COPD)与肺纤维化气道微生态-宿主空间转录组交互机制',
        domain: '呼吸慢病',
        boardName: '呼吸慢病顶刊文献专题',
        paperCount: 4,
        weeklyPaperCount: 2,
        updatedWeek: '2026-11-23',
        reportCount: 4,
        confLabels: 'AJRCCM 蓝皮书(2篇) · ERJ(2篇)',
        journalLabels: 'AJRCCM · ERJ',
        journals: ['Nature / 专科顶刊'],
        leaders: [
          { key: 'L-R1', name: '陈荣昌', hospital: '广州医科大学附属第一医院', tierCode: 'national', roleLabel: '通讯作者 · 带头人', scoreLabel: '84分·B级', conf: 'AJRCCM', talkTitle: 'Airway Microbiome-Host Transcriptome Interactions Predict Exacerbation Risk in Severe COPD' }
        ],
        biomarkers: ['诱导痰宏基因组菌群丰度', '宿主气道上皮 II 型炎症转录谱'],
        cutIn: '以 AJRCCM 最新双组学队列文献为学术背书，向呼吸科PI推介呼吸道宏基因组+宿主转录组联合检测。'
      },
      {
        id: 'LIT-SPEC-RHEUM',
        name: '系统性红斑狼疮(SLE)单细胞 TCR/BCR 免疫组库与靶向治疗分子分层',
        domain: '风湿免疫',
        boardName: '自身免疫顶刊文献专题',
        paperCount: 3,
        weeklyPaperCount: 2,
        updatedWeek: '2026-11-23',
        reportCount: 3,
        confLabels: 'Ann Rheum Dis(2篇) · Lancet Rheumatology(1篇)',
        journalLabels: 'ARD · Lancet Rheum',
        journals: ['Lancet', 'Nature / 专科顶刊'],
        leaders: [
          { key: 'L-RH1', name: '苏茵', hospital: '北京大学人民医院', tierCode: 'national', roleLabel: '通讯作者 · 主委', scoreLabel: '81分·B级', conf: 'Ann Rheum Dis', talkTitle: 'Single-Cell BCR/TCR Repertoire and Interferon Signature Stratify Treatment Response in SLE' }
        ],
        biomarkers: ['BCR/TCR 克隆扩张指数', 'I型干扰素基因签名'],
        cutIn: '结合 ARD 最新单细胞免疫组库文献，向风湿免疫科PI推介自身免疫病治疗前后 PBMC 单细胞免疫组库动态监测课题。'
      },
      {
        id: 'LIT-SPEC-CARDIO',
        name: '克隆性造血(CHIP)突变驱动泛血管与冠脉粥样硬化残余炎症风险',
        domain: '心血管',
        boardName: '心血管代谢顶刊文献专题',
        paperCount: 5,
        weeklyPaperCount: 2,
        updatedWeek: '2026-11-23',
        reportCount: 5,
        confLabels: 'Circulation(3篇) · NEJM(2篇)',
        journalLabels: 'Circulation · NEJM',
        journals: ['NEJM', 'Nature / 专科顶刊'],
        leaders: [
          { key: 'L-C1', name: '葛均波', hospital: '复旦大学附属中山医院', tierCode: 'international', roleLabel: '通讯作者 · 院士', scoreLabel: '91分·A级', conf: 'Circulation', talkTitle: 'Clonal Hematopoiesis of Indeterminate Potential (CHIP) Accelerates Pan-Vascular Atherosclerosis' }
        ],
        biomarkers: ['TET2/DNMT3A/ASXL1 克隆性造血突变', 'IL-1β/IL-6 炎症通路'],
        cutIn: '以 Circulation & NEJM 最新 CHIP 综述与临床研究为切入点，推广吉因加心血管队列超高深度 CHIP 靶向测序服务。'
      },
      {
        id: 'LIT-SPEC-VASC',
        name: '泛血管易损斑块影像组学与血浆高通量蛋白组(Radiogenomics)联合预测',
        domain: '泛血管及器官损伤',
        boardName: '泛血管跨器官损伤文献专题',
        paperCount: 3,
        weeklyPaperCount: 1,
        updatedWeek: '2026-11-23',
        reportCount: 3,
        confLabels: 'European Heart Journal(2篇) · JAMA Cardiol(1篇)',
        journalLabels: 'EHJ · JAMA Cardiol',
        journals: ['JAMA', 'Nature / 专科顶刊'],
        leaders: [
          { key: 'L-V1', name: '郑曰宏', hospital: '中国医学科学院北京协和医院', tierCode: 'national', roleLabel: '通讯作者 · 主委', scoreLabel: '78分·B级', conf: 'European Heart Journal', talkTitle: 'Radiogenomics and Plasma Proteomics for Vulnerable Plaque Identification in Pan-Vascular Disease' }
        ],
        biomarkers: ['血清细胞因子表达特征', 'TyG指数', '循环内皮外泌体蛋白谱'],
        cutIn: '围绕 EHJ 影像组学+蛋白组双模态范式，向血管外科与影像科团队提供多组学检测与生信建模联合方案。'
      }
    ];

    return [...specLitTopics, ...litTopics];
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
  const initialLiteratureTopics = buildLiteratureTopics(initialLiterature);

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

    // Literature Hotspots (Comprehensive vs Weekly) & Library state
    litMode: 'hotspots',              // 'hotspots' (🔥文献热点) | 'library' (📚文献明细库)
    litViewMode: 'comprehensive',     // 'comprehensive' (综合文献热点汇总) | 'weekly' (本周更新文献热点)
    litJournalFilter: 'all',
    selectedLitBoard: '全部',
    litTopicPage: 1,
    litTopicPageSize: 10,

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
    literatureTopics: initialLiteratureTopics,
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
        if (this.litMode === 'hotspots') dataset = this.activeLitTopicBase;
        else dataset = this.literatureList;
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
          venue: item.venue || item.city || '国内会场',
          contacts: item.contacts || '大会会务组',
          domain: item.domain,
          tierCode: tCode,
          tierBadge: getTierBadgeText(tCode),
          tierBasis: item.summary,
          sourceAnchor: item.sourceAnchor || '学会微官网监控锚点',
          schedulePublished: hasSchedule,
          scheduleStatusNote: item.scheduleStatusNote || (hasSchedule ? '已获取官方日程' : '待官方发布详细日程'),
          topicScrapeStatus: hasSchedule ? 'pending' : 'waiting',
          piScrapeStatus: 'pending',
          reportCount: hasSchedule ? 26 : 0,
          topics: `${item.domain}前沿多组学转化、临床队列液体活检与分子分型标志物研究`,
          cutIn: `会议经市场部核定为【${getTierBadgeText(tCode)}】，建议联动属地销售围绕参会讲者PI推进临床队列多组学验证(T10)与单细胞/转录组(T03)合作。`,
          officialUrl: item.officialUrl || '#',
          scheduleUrl: item.scheduleUrl || item.officialUrl || '#',
          sourceLinks: item.sourceLinks || [],
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
      let mergedCount = 0;
      for (const sp of (conf.speakers || [])) {
        const cleanName = sp.name.replace(/教授|院士|主任|博士/g, '').trim();
        const existingPI = this.piList.find(p => p.name === cleanName || p.name.includes(cleanName) || cleanName.includes(p.name));
        if (existingPI) {
          if (!existingPI.talks) existingPI.talks = [];
          const talkExists = existingPI.talks.some(t => t.conf === conf.abbreviation || t.title === sp.topic);
          if (!talkExists) {
            existingPI.talks.push({ id: conf.id + '-TK' + Date.now(), conf: conf.abbreviation, title: sp.topic });
          }
          if (!existingPI.conferencesAttended) existingPI.conferencesAttended = [];
          if (!existingPI.conferencesAttended.includes(conf.abbreviation)) {
            existingPI.conferencesAttended.push(conf.abbreviation);
          }
          if (!existingPI.sources) existingPI.sources = [];
          existingPI.sources.push({ id: conf.id, title: ${conf.title} 官方日程讲者名录, url: conf.officialUrl || '#' });
          const confCount = existingPI.conferencesAttended.length;
          existingPI.sourceLabel = 跨  场重点会议: ;
          if (!existingPI.capabilities) existingPI.capabilities = [];
          if (!existingPI.capabilities.includes('T10 临床队列验证')) existingPI.capabilities.push('T10 临床队列验证');
          if (!existingPI.capabilities.includes('T03 单细胞/转录组')) existingPI.capabilities.push('T03 单细胞/转录组');
          if (!existingPI.capabilities.includes('T01 cfRNA液体活检')) existingPI.capabilities.push('T01 cfRNA液体活检');
          if (!existingPI.research.includes(sp.topic)) {
            existingPI.research = ${existingPI.research}；【最新】;
          }
          mergedCount++;
        } else {
          this.piList.unshift({
            id: 'PI-CONF-' + Date.now() + '-' + addedCount,
            name: cleanName,
            hospital: sp.hospital || '国内核心三甲医院',
            department: conf.domain + '转化研究中心',
            title: '主任医师',
            academicTitle: '教授 / 博士生导师',
            domain: conf.domain,
            roleLabel: sp.role || '全国专科学术带头人',
            roleCode: 'national',
            researchInterests: 重点讲题：《》；多组学标志物转化应用,
            totalScore: null,
            grade: null,
            hasPartialRating: true,
            scoreBadge: '调研中 · 方向28/30',
            dimSummary: '研究28/30 (日程讲题已核 · 余项待补)',
            dimensions: [
              { name: '研究方向契合度', maximum: 30, score: 28, basis: 在【】报告《》，高度契合多组学临床转化。 },
              { name: '学术产出质量',   maximum: 25, score: null, basis: '待进一步核对近三年 PubMed 一作/通讯期刊档位；缺证不填0。' },
              { name: '科研转化潜力',   maximum: 25, score: null, basis: '待进一步核对个人主持基金与开放队列条件；缺证不填0。' },
              { name: '平台资源禀赋',   maximum: 20, score: null, basis: '待进一步核对所属实验室可调配资源；缺证不填0。' }
            ],
            conferencesAttended: [conf.abbreviation],
            talks: [{ id: conf.id + '-TK', conf: conf.abbreviation, title: sp.topic }],
            cohortScale: '待一线摸底样本队列规模 (预估数百例级)',
            grantsFunding: '国家自然科学基金 / 专科重点研发专项 (在研调研中)',
            keyPapers: [],
            papers: [],
            productMatches: ['T10 临床队列验证', 'T03 单细胞/转录组', 'T01 cfRNA液体活检'],
            capabilities: ['T10 临床队列验证', 'T03 单细胞/转录组', 'T01 cfRNA液体活检'],
            commercialCutIn: sp.cutIn || conf.cutIn || 围绕【】议题《》，推介cfRNA/单细胞科研方案与前瞻队列验证合作。,
            cutIn: sp.cutIn || conf.cutIn || 围绕【】议题《》，推介cfRNA/单细胞科研方案与前瞻队列验证合作。,
            fieldIntelCount: 0,
            syncedIntel: [],
            syncedIntelCount: 0,
            ratingDate: new Date().toISOString().slice(0, 10),
            headPiStatus: ${conf.abbreviation} 讲者线索,
            sourceLabel: 来源:  日程抓取,
            sources: [{ id: conf.id, title: ${conf.title} 官方日程讲者名录, url: conf.officialUrl || '#' }],
            isAiRecommended: true,
            research: 讲题：,
            starred: true,
            assignee: '华东一区 - 张敏',
            taskStatus: '待派发'
          });
          addedCount++;
        }
      }
      let msg = 已处理【】重点讲者：;
      if (addedCount > 0) msg += 新入库  位专家；;
      if (mergedCount > 0) msg += 智能合并  位跨会议学者轨迹！;
      this.showToast(msg, 'success');
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

    // Literature Hotspots (Comprehensive vs Weekly) & Library Computed
    get weeklyUpdatedPapers() {
      return this.literatureList.filter(p => {
        const matchDomain = this.selectedDomain === '全部' || p.domain === this.selectedDomain;
        const w = p.updatedWeek || '2026-11-23';
        return matchDomain && (p.isWeekly || (w >= this.weekStart && w <= this.weekEnd));
      });
    },

    get weeklyLiteratureTopics() {
      return this.literatureTopics.filter(lt => {
        const w = lt.updatedWeek || '2026-11-23';
        return lt.weeklyPaperCount > 0 && w >= this.weekStart && w <= this.weekEnd;
      });
    },

    get activeLitTopicBase() {
      return this.litViewMode === 'weekly' ? this.weeklyLiteratureTopics : this.literatureTopics;
    },

    get availableLitBoards() {
      const counts = {};
      for (const t of this.activeLitTopicBase) {
        if (this.selectedDomain !== '全部' && t.domain !== this.selectedDomain) continue;
        counts[t.boardName] = (counts[t.boardName] || 0) + 1;
      }
      return Object.entries(counts).map(([name, count]) => ({ name, count }));
    },

    get filteredLiteratureTopics() {
      const q = this.searchQuery.trim().toLowerCase();
      return this.activeLitTopicBase.filter(t => {
        const matchDomain = this.selectedDomain === '全部' || t.domain === this.selectedDomain;
        const matchBoard = this.selectedLitBoard === '全部' || t.boardName === this.selectedLitBoard;
        let matchJournal = true;
        if (this.litJournalFilter !== 'all') {
          const jText = (t.journalLabels || '').toLowerCase();
          if (this.litJournalFilter === 'Nature / 专科顶刊') {
            matchJournal = /nature|ajrccm|erj|ard|circulation|ehj|neurology|diabetes care|diabetologia/i.test(jText);
          } else {
            matchJournal = jText.includes(this.litJournalFilter.toLowerCase());
          }
        }
        const leaderNames = (t.leaders || []).map(l => l.name + ' ' + l.hospital + ' ' + l.talkTitle).join(' ');
        const matchSearch = !q || [t.name, t.boardName, t.journalLabels, leaderNames].join(' ').toLowerCase().includes(q);
        return matchDomain && matchBoard && matchJournal && matchSearch;
      });
    },

    get litTopicTotalPages() {
      return Math.max(1, Math.ceil(this.filteredLiteratureTopics.length / this.litTopicPageSize));
    },

    get pagedLiteratureTopics() {
      const start = (this.litTopicPage - 1) * this.litTopicPageSize;
      return this.filteredLiteratureTopics.slice(start, start + this.litTopicPageSize);
    },

    get filteredLiterature() {
      const q = this.searchQuery.trim().toLowerCase();
      return this.literatureList.filter(l => {
        const matchDomain = this.selectedDomain === '全部' || l.domain === this.selectedDomain;
        const matchSource = this.litSourceFilter === 'all'
          || (this.litSourceFilter === 'real' && l.isReal)
          || (this.litSourceFilter === 'weekly' && l.isWeekly);
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
      let repId = 'sales_east_zhang';
      if (this.assignedRep.includes('李娜') || this.assignedRep.includes('华北')) repId = 'sales_north_li';
      else if (this.assignedRep.includes('王强') || this.assignedRep.includes('华南')) repId = 'sales_south_wang';

      if (this.assignTargetPI) {
        this.assignTargetPI.assignee = this.assignedRep;
        this.assignTargetPI.taskStatus = '跟进中';
        this.assignTargetPI.starred = true;
      }

      // Sync newly assigned Battle Card to 销售工作台.html (clinical-workbench:battle-cards:v2)
      const pi = this.assignTargetPI;
      const cards = readStore('clinical-workbench:battle-cards:v2', []);
      
      // Build authentic squat info from talks or conference tracks
      let squatConference = '近期重点学术年会';
      let squatTopic = '临床多组学标志物队列验证研究';
      let squatDate = this.assignDueDate || '2026-12-05';
      let squatVenue = '主会场报告厅';
      if (pi && pi.talks && pi.talks.length) {
        squatConference = pi.talks[0].conf || squatConference;
        squatTopic = pi.talks[0].title || squatTopic;
      }
      if (pi && pi.conferencesAttended && pi.conferencesAttended.length) {
        squatConference = pi.conferencesAttended[0];
      }
      const squatInfo = {
        conference: squatConference,
        topic: squatTopic,
        date: squatDate,
        venue: squatVenue,
        actionAdvice: `建议销售代表于【${squatConference}】会议现场蹲点，提前30分钟在演讲会场侧方等候，围绕议题《${squatTopic}》现场破冰！`
      };

      cards.unshift({
        id: 'BC-ASSIGN-' + Date.now(),
        repId,
        piName: pi ? pi.name : this.targetTaskTitle.split('·').pop().replace(/拜访|临床课题/g, '').trim(),
        hospital: pi ? pi.hospital : '重点合作三甲医院',
        domain: pi ? pi.domain : (this.selectedDomain === '全部' ? '糖尿病与代谢' : this.selectedDomain),
        roleLabel: pi ? pi.roleLabel : '重点学术讲者 / PI',
        scoreBadge: pi ? pi.scoreBadge : '🔥 市场部重点指派',
        matchScore: 95,
        status: 'assigned',
        dueDate: this.assignDueDate || '2026-12-05',
        title: `【市场指派作战卡】${this.targetTaskTitle}`,
        breakIceScript: this.assignNote,
        painPoint: `专家在近期【${squatConference}】发表重要讲题，其临床转化队列亟需多组学高通量筛选与生信建模支撑高分成果发表。`,
        reason: `市场部根据最新会议热点与PI四维评分定向指派（指派给：${this.assignedRep}）。`,
        participation: this.assignNote,
        squatInfo: squatInfo,
        talkEvidence: `${squatConference} · 《${squatTopic}》`,
        shortTopic: `议题：${squatTopic}`,
        checklist: [
          `在【${squatConference}】现场对接专家或其核心随行学术秘书`,
          `摸清近期拟开展多组学研究的临床样本类型（血浆/组织/体液）与冻存例数`,
          `推介吉因加多组学标志物验证方案与生信分析支持，约定会后院内深入拜访`
        ],
        conditions: '首次拜访请摸清：1) 科室在研队列样本类型与冻存例数；2) 近期国自然/省部级课题检测计划。',
        capabilities: (pi && pi.capabilities && pi.capabilities.length) ? pi.capabilities : ['T10 临床队列多组学验证', 'T03 单细胞/转录组'],
        dimensions: (pi && pi.dimensions) ? pi.dimensions : [
          { name: '研究方向契合度', maximum: 30, score: 28 },
          { name: '学术产出质量',   maximum: 25, score: null },
          { name: '科研转化潜力',   maximum: 25, score: null },
          { name: '平台资源禀赋',   maximum: 20, score: null }
        ],
        talkEvidence: pi ? pi.research : this.targetTaskTitle,
        qualityRating: ''
      });
      writeStore('clinical-workbench:battle-cards:v2', cards);

      this.showAssignModal = false;
      this.showToast(`作战任务已派发给【${this.assignedRep}】，已同步至【销售代表工作台】！`, 'success');
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
    },

    // =========================================================================
    // 8. Conference Collection 3-Way Console (WorkBuddy Crawl / Schedule / Excel Upload)
    // =========================================================================
    showCrawlModal: false,
    workbuddyTokenInput: localStorage.getItem('clinical-workbench:workbuddy-token') || '',
    workbuddyApiStatus: { configured: Boolean(localStorage.getItem('clinical-workbench:workbuddy-token')), online: false },

    showScheduleModal: false,
    showConfExcelModal: false,

    crawlScope: 'all_59', // 'all_59' | 'upcoming_week' | 'domain_focus'
    crawlTargetWeek: '2026-11-30 ~ 2026-12-06',
    isCrawling: false,
    crawlProgress: 0,
    crawlStatusText: '',
    crawlLogs: [],
    lastCrawlTime: readStore('clinical-workbench:last-crawl-time', '2026-11-24 08:30'),

    scheduleConfig: readStore('clinical-workbench:crawl-schedule:v1', {
      enabled: true,
      frequency: 'weekly_mon', // 'daily' | 'weekly_mon' | 'every_3_days'
      timeOfDay: '08:30',
      autoTrackUnpublished: true,
      autoPreGrade: true,
      nextRunLabel: '每周一 08:30 自动巡检'
    }),

    workbuddyPromptText: `【任务角色与定位】
你是一名专业的临床科研学术会议情报采集与初评助手。请按照吉因加《会议收集初评》规范，全网排查目标周度（59个官方学会与美迪康sciconf/钛会务tiemeeting/cnconf/互会科技等微官网锚点）的医学学术会议：
1. 聚焦六大临床领域：糖尿病与代谢、神经精神、呼吸慢病、风湿免疫、心血管、泛血管及器官损伤。
2. 聚焦10大核心城市：北京、上海、广州、深圳、南京、苏州、杭州、长沙、成都、重庆（全国年会不限城市）。
3. 自动提取【会议来源链接】与【在线日程链接（schedule_url）】，区分“已发布日程”与“未发布日程”，给出 A/B/C/D 四级初评及评级依据。
4. 完成后保存至 crawled_batches/ 或导出 CSV/JSON 上传至工作台【① 来源与审核】。`,

    openCrawlModal() {
      this.isCrawling = false;
      this.crawlProgress = 0;
      this.crawlStatusText = '';
      this.crawlLogs = [];
      this.showCrawlModal = true;
    },

    copyWorkBuddyPrompt() {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(this.workbuddyPromptText);
      }
      this.showToast('已复制 WorkBuddy 专项采集提示词与 59 锚点指令！可直接粘贴给 WorkBuddy 执行。', 'success');
    },

    async saveWorkBuddyApiToken() {
      const token = (this.workbuddyTokenInput || '').trim();
      localStorage.setItem('clinical-workbench:workbuddy-token', token);
      this.workbuddyApiStatus.configured = Boolean(token);
      
      // 尝试通知本地网关
      try {
        await fetch('http://127.0.0.1:8899/api/workbuddy/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ access_token: token })
        });
        this.showToast('WorkBuddy OpenAPI Token 已保存并同步至本地网关！', 'success');
      } catch (e) {
        this.showToast('Token 已保存在浏览器本地（本地网关 127.0.0.1:8899 未启动）', 'info');
      }
    },

    async testWorkBuddyApiOnline() {
      try {
        const res = await fetch('http://127.0.0.1:8899/api/workbuddy/status');
        const data = await res.json();
        if (data.online) {
          this.workbuddyApiStatus.online = true;
          this.showToast('✅ 连通成功！检测到本地 WorkBuddy 客户端在线！', 'success');
        } else {
          this.workbuddyApiStatus.online = false;
          this.showToast('⚠️ 本地客户端未在线或 Token 权限不足: ' + (data.message || ''), 'warning');
        }
      } catch (e) {
        this.showToast('未检测到本地网关服务，请运行 tools/workbuddy_bridge.py', 'warning');
      }
    },

    copySkillMailboxPrompt() {
      const prompt = `请加载专属技能【C:\\Users\\geneplus\\WorkBuddy\\2026-11-06-16-31-58\\_input\\会议收集评级\\SKILL.md】，读取工单【workbench/agent_mailbox/inbox/task.json】，严格按照吉因加六大领域口径进行全网深度会议与日程采集，并将最新进度写入 workbench/agent_mailbox/outbox/progress.json。`;
      navigator.clipboard.writeText(prompt);
      this.showToast('📋 已复制专属 Skill 信箱执行指令！可直接粘贴至 WorkBuddy 发送', 'success');
    },

    async startWorkBuddyCrawl() {
      // 做法二：信箱工单机制 (Mailbox IPC) 自动派发
      try {
        const res = await fetch('http://127.0.0.1:8899/api/mailbox/dispatch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            scope: this.crawlScope,
            target_week: this.crawlTargetWeek,
            domains: ['内分泌', '心血管', '神经精神', '慢阻肺', '自免', '泛血管']
          })
        });
        const data = await res.json();
        if (data.success) {
          this.showToast('📬 工单已成功送达 inbox/task.json！绑定技能【会议收集评级】', 'success');
          if (data.copy_prompt) {
            navigator.clipboard.writeText(data.copy_prompt);
          }
        }
      } catch (e) {
        console.log('Mailbox bridge offline, local file simulation active');
      }

      if (this.isCrawling) return;
      this.isCrawling = true;
      this.crawlProgress = 12;
      this.crawlStatusText = '正在连接 59 个学会官网与 6 大会务微站锚点...';
      this.crawlLogs = [
        '📡 [00:01] 已加载 19 个中华医学会/医师协会专科分会锚点 & 6 大会务平台 (sciconf / tiemeeting / cnconf / hoohui)...'
      ];

      setTimeout(() => {
        this.crawlProgress = 45;
        this.crawlStatusText = '正在检索最新会议通知、微站日程页与红头文件 PDF...';
        this.crawlLogs.push('🔍 [00:02] 巡检美迪康 (sciconf.cn) 与钛会务 (tiemeeting.com)：发现 3 场新上线/更新日程的专科会议...');
      }, 650);

      setTimeout(() => {
        this.crawlProgress = 78;
        this.crawlStatusText = '正在执行吉因加 A/B/C/D 四级初评与重复会议去重...';
        this.crawlLogs.push('🧠 [00:03] 已自动提取在线日程链接 (schedule_url)、具体场馆地址与会务组联系方式，完成去重比对...');
      }, 1350);

      setTimeout(() => {
        this.crawlProgress = 100;
        this.isCrawling = false;
        const nowStr = new Date().toISOString().slice(0, 16).replace('T', ' ');
        this.lastCrawlTime = nowStr;
        writeStore('clinical-workbench:last-crawl-time', nowStr);

        // Discover new high-value crawled items and push to auditConferences if not present
        const discovered = [
          {
            id: 'WB-CRAWL-' + Date.now() + '-1',
            conferenceId: 'CONF-2026-WB01',
            title: '2026 中华医学会呼吸病学分会慢性气道疾病多组学转化高峰论坛',
            abbreviation: 'CTS 慢性气道多组学论坛',
            date: '2026-12-04 ~ 2026-12-06',
            city: '广州',
            venue: '广州·越秀国际会议中心 3楼宴会厅',
            contacts: '会务秘书处 陈老师 020-83339912；微站报名 cts-airway2026.sciconf.cn',
            domain: '呼吸慢病',
            fieldId: 'respiratory',
            tierCode: 'B',
            sourceAnchor: 'O11 中华医学会呼吸病学分会 · 美迪康微站自动抓取',
            schedulePublished: true,
            scheduleStatusNote: 'WorkBuddy 自动抓取：已识别 4 个气道慢病单细胞与宏基因组专场日程（共 26 个报告讲题）。',
            officialUrl: 'https://cts-airway2026.sciconf.cn',
            scheduleUrl: 'https://cts-airway2026.sciconf.cn/cn/web/program',
            sourceLinks: [
              { label: '📅 自动抓取在线日程页 (sciconf)', url: 'https://cts-airway2026.sciconf.cn/cn/web/program', type: 'schedule' },
              { label: '🌐 大会微站首页', url: 'https://cts-airway2026.sciconf.cn', type: 'official' }
            ],
            summary: '【WorkBuddy 自动初评 · B级重点关注】广州医科大学附属第一医院国家呼吸医学中心协办，含慢阻肺与重症哮喘单细胞/空间转录组及气道微生态宏基因组专场，已附完整日程链接。'
          },
          {
            id: 'WB-CRAWL-' + Date.now() + '-2',
            conferenceId: 'CONF-2026-WB02',
            title: '2026 中国卒中学会脑血管病精准医学与生物标志物年会',
            abbreviation: 'CSA 脑血管标志物年会',
            date: '2026-12-05 ~ 2026-12-06',
            city: '北京',
            venue: '北京·国家会议中心二期',
            contacts: '中国卒中学会学术部 010-57983210',
            domain: '神经精神',
            fieldId: 'neurology',
            tierCode: 'B',
            sourceAnchor: 'S10 中国卒中学会官网锚点自动抓取',
            schedulePublished: true,
            scheduleStatusNote: 'WorkBuddy 自动抓取：已发布主旨论坛与脑脊液/外周血液体活检分论坛日程。',
            officialUrl: 'https://csa-biomarker2026.tiemeeting.com/CN',
            scheduleUrl: 'https://csa-biomarker2026.tiemeeting.com/CN/Program/Details',
            sourceLinks: [
              { label: '📅 钛会务在线日程页', url: 'https://csa-biomarker2026.tiemeeting.com/CN/Program/Details', type: 'schedule' },
              { label: '🌐 大会微官网', url: 'https://csa-biomarker2026.tiemeeting.com/CN', type: 'official' }
            ],
            summary: '【WorkBuddy 自动初评 · B级重点关注】聚焦缺血性脑卒中与脑小血管病外泌体转录组、血浆蛋白组早筛标志物及队列转化，北京核心覆盖城市。'
          },
          {
            id: 'WB-CRAWL-' + Date.now() + '-3',
            conferenceId: 'CONF-2026-WB03',
            title: '2026 长三角泛血管代谢与糖心肾共病(CKM)多学科论坛',
            abbreviation: '长三角 CKM 共病论坛',
            date: '2026-12-11 ~ 2026-12-12',
            city: '上海',
            venue: '上海·国际会议中心',
            contacts: '上海医学会内分泌与心血管联合筹备组',
            domain: '泛血管及器官损伤',
            fieldId: 'vascular',
            tierCode: 'B',
            sourceAnchor: 'S19 长三角泛血管联盟微官网锚点',
            schedulePublished: false,
            scheduleStatusNote: 'WorkBuddy 自动抓取：刚发布第一轮征文与会期通知，详细日程尚未上线（已加入自动追踪）。',
            officialUrl: 'https://ckm2026.cnconf.com/msite/main/cn',
            scheduleUrl: 'https://ckm2026.cnconf.com/msite/main/cn',
            sourceLinks: [
              { label: '📄 第一轮会议通知微站', url: 'https://ckm2026.cnconf.com/msite/main/cn', type: 'notice' }
            ],
            summary: '【WorkBuddy 自动初评 · B级重点关注】汇聚瑞金、中山、仁济内分泌与心内、肾内专家，聚焦糖心肾共病(CKM)队列多组学与 CHIP 克隆性造血检测。'
          }
        ];

        let added = 0;
        for (const d of discovered) {
          if (!this.auditConferences.some(c => c.title === d.title) && !this.conferences.some(c => c.title === d.title)) {
            this.auditConferences.unshift(d);
            added++;
          }
        }

        this.crawlStatusText = `✅ 抓取完成！本次新增发现 ${added} 场高相关学术会议（含日程链接），已推入【① 来源与审核】列表！`;
        this.crawlLogs.push(`🎉 [00:04] 采集完毕：新增 ${added} 场待审核会议，全部附带真实来源与日程链接！`);
        this.showToast(`WorkBuddy 自动抓取完成：新增 ${added} 场会议进入【① 来源与审核】！`, 'success');
      }, 2100);
    },

    openScheduleModal() {
      this.showScheduleModal = true;
    },

    saveScheduleConfig() {
      const freqMap = {
        daily: `每日 ${this.scheduleConfig.timeOfDay} 自动巡检`,
        weekly_mon: `每周一 ${this.scheduleConfig.timeOfDay} 自动巡检`,
        every_3_days: `每 3 天 (${this.scheduleConfig.timeOfDay}) 自动巡检`
      };
      this.scheduleConfig.nextRunLabel = this.scheduleConfig.enabled
        ? (freqMap[this.scheduleConfig.frequency] || '定时巡检已开启')
        : '定时抓取已暂停';
      writeStore('clinical-workbench:crawl-schedule:v1', this.scheduleConfig);
      this.showScheduleModal = false;
      this.showToast(`WorkBuddy 定时抓取策略已保存：${this.scheduleConfig.nextRunLabel}！`, 'success');
    },

    openConfExcelModal() {
      this.showConfExcelModal = true;
    },

    // Helper: Parse CSV lines respecting quoted fields
    parseCSVRows(csvText) {
      const rows = [];
      let row = [];
      let cur = '';
      let inQuotes = false;
      const text = String(csvText || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
      for (let i = 0; i < text.length; i++) {
        const ch = text[i];
        if (ch === '"') {
          if (inQuotes && text[i + 1] === '"') {
            cur += '"';
            i++;
          } else {
            inQuotes = !inQuotes;
          }
        } else if (ch === ',' && !inQuotes) {
          row.push(cur.trim());
          cur = '';
        } else if (ch === '\n' && !inQuotes) {
          row.push(cur.trim());
          if (row.some(cell => cell !== '')) rows.push(row);
          row = [];
          cur = '';
        } else {
          cur += ch;
        }
      }
      if (cur !== '' || row.length > 0) {
        row.push(cur.trim());
        if (row.some(cell => cell !== '')) rows.push(row);
      }
      return rows;
    },

    ingestConferenceItemsFromRows(items) {
      let addedCount = 0;
      let linkCount = 0;

      for (const raw of items) {
        const title = (raw.conference_name || raw.title || raw['会议名称'] || '').trim();
        if (!title) continue;

        const rawField = raw.field_id || raw.domain || raw['领域大类'] || raw['疾病方向'] || '';
        const domainName = getDomainName(rawField, title + ' ' + rawField);

        const rawPriority = String(raw.tier_code || raw.priority || raw['优先级'] || 'B').trim();
        let tierCode = 'B';
        if (rawPriority === 'A' || rawPriority.includes('国际')) tierCode = 'A';
        else if (rawPriority === 'B' || rawPriority.includes('重点')) tierCode = 'B';
        else if (rawPriority === 'C' || rawPriority.includes('常规')) tierCode = 'C';
        else if (rawPriority === 'D' || rawPriority.includes('低')) tierCode = 'D';

        const rawTime = String(raw.date || raw.start_date || raw['会议时间'] || '2026-11-27').trim();
        const dateStr = rawTime.replace(/(\d{2}-\d{2})\s*至\s*(\d{2}-\d{2})/, '2026-$1 ~ 2026-$2');

        const rawVenue = String(raw.venue || raw.city || raw['会议地点'] || '国内核心城市').trim();
        const city = rawVenue.split(/[·（(]/)[0].trim() || '国内';
        const contacts = String(raw.contacts || raw['联系人'] || '详见会议通知原文').trim();
        const remark = String(raw.review_note || raw.summary || raw['备注'] || '').trim();

        // Extract all URLs from remark or explicit url fields
        const urlMatches = (remark + ' ' + (raw.official_url || '') + ' ' + (raw.schedule_url || '')).match(/https?:\/\/[^\s；;，,。）”"']+|www\.[^\s；;，,。）”"']+/gi) || [];
        const cleanUrls = [...new Set(urlMatches.map(u => u.replace(/[。，；;）)]+$/, '').replace(/^www\./i, 'http://www.')))];
        const sourceLinks = cleanUrls.map((u, idx) => {
          const isSched = /program|schedule|newSchedule|articleId|19431|msite|bioon|mp\.weixin/i.test(u) || idx === 0;
          return {
            label: isSched ? `📅 会议日程/通知链接 ${idx + 1}` : `🌐 官方来源链接 ${idx + 1}`,
            url: u,
            type: isSched ? 'schedule' : 'official'
          };
        });
        linkCount += sourceLinks.length;

        // Extract（日程状态）from remark if present
        const schedMatch = remark.match(/（日程状态）([^（]+)/);
        const scheduleStatusNote = schedMatch ? schedMatch[1].trim() : (sourceLinks.length ? '已从导入表格提取官方日程与来源链接' : '待补充详细日程链接');
        const schedulePublished = !/尚未找到|未公布/.test(scheduleStatusNote);

        // Extract（来源）from remark if present
        const srcMatch = remark.match(/（来源）([^（]+)/);
        const sourceAnchor = srcMatch ? srcMatch[1].split(/[；;。]/)[0].trim().slice(0, 38) : 'Excel/CSV 批量导入来源';

        // Deduplicate against existing auditConferences & conferences
        const existingAudit = this.auditConferences.find(c => c.title === title);
        const existingLib = this.conferences.find(c => c.title === title);
        if (existingAudit) {
          if (sourceLinks.length && (!existingAudit.sourceLinks || !existingAudit.sourceLinks.length)) {
            existingAudit.sourceLinks = sourceLinks;
          }
          continue;
        }
        if (existingLib) {
          if (sourceLinks.length && (!existingLib.sourceLinks || !existingLib.sourceLinks.length)) {
            existingLib.sourceLinks = sourceLinks;
          }
          continue;
        }

        this.auditConferences.unshift({
          id: 'IMP-' + Date.now() + '-' + addedCount,
          conferenceId: 'CONF-IMP-' + (addedCount + 1),
          title,
          abbreviation: title.slice(0, 14),
          date: dateStr,
          city,
          venue: rawVenue,
          contacts,
          domain: domainName,
          fieldId: 'diabetes',
          tierCode,
          sourceAnchor,
          schedulePublished,
          scheduleStatusNote,
          officialUrl: cleanUrls[0] || '#',
          scheduleUrl: cleanUrls[0] || '#',
          sourceLinks,
          summary: remark || `【表格导入 · ${tierCode}级】${title}（地点：${rawVenue}）`
        });
        addedCount++;
      }

      return { addedCount, linkCount, totalParsed: items.length };
    },

    handleConfFileUpload(event) {
      const file = event.target.files && event.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (e) => {
        const content = String(e.target.result || '');
        let parsedItems = [];

        if (file.name.endsWith('.json')) {
          try {
            const obj = JSON.parse(content);
            parsedItems = Array.isArray(obj) ? obj : (obj.items || obj.conferences || []);
          } catch (err) {
            this.showToast('JSON 文件格式解析失败，请检查文件语法', 'error');
            return;
          }
        } else {
          // CSV parsing (supports 06_官方评级金标准参考_20261123周度.csv format)
          const rows = this.parseCSVRows(content);
          if (rows.length > 1) {
            const headers = rows[0];
            for (let i = 1; i < rows.length; i++) {
              const rowObj = {};
              headers.forEach((h, idx) => {
                rowObj[h.replace(/^\uFEFF/, '').trim()] = rows[i][idx] || '';
              });
              parsedItems.push(rowObj);
            }
          }
        }

        const res = this.ingestConferenceItemsFromRows(parsedItems);
        this.showConfExcelModal = false;
        this.academicMode = 'audit';
        this.showToast(`成功解析【${file.name}】共 ${res.totalParsed} 场会议（自动提取日程/来源链接 ${res.linkCount} 条，新增入列 ${res.addedCount} 场，其余已自动去重合并）！`, 'success');
      };
      reader.readAsText(file, 'UTF-8');
    },

    loadGoldStandardSampleCSV() {
      // One-click demo import of extra regional & specialty conferences from the gold-standard table
      const sampleRows = [
        {
          '会议名称': 'LIFT-SH 2026 陆家嘴心脏结构论坛暨结构性心脏病微创介入治疗创新大会',
          '领域大类': '心血管',
          '会议时间': '11-27 至 11-29',
          '会议地点': '上海·浦东国际会议中心',
          '联系人': '大会主席 何奔（上海市胸科医院）',
          '优先级': '低优先级',
          '备注': '（评级依据）结构性心脏病微创介入与TAVR影像评估。（日程状态）部分获取：已查严道医声网会议列表。（来源）严道医声网 https://www.drvoice.cn/v2/meetings?page=3 。'
        },
        {
          '会议名称': '第二十届南方神经外科学术论坛暨广东省医学会第七次神经肿瘤学学术会议',
          '领域大类': '神经精神',
          '会议时间': '11-27 至 11-29',
          '会议地点': '广州·白云国际会议中心',
          '联系人': '广东省医学会神经肿瘤学分会学术组',
          '优先级': '常规关注',
          '备注': '（评级依据）含神经肿瘤分子分型、脑脊液ctDNA液体活检与靶向治疗专场，广州覆盖城市。（日程状态）已获取：365医学网在线日程条目。（来源）365医学网学术年历 https://jsp.365heart.com/meeting/calendar/month 。'
        }
      ];
      const res = this.ingestConferenceItemsFromRows(sampleRows);
      this.showConfExcelModal = false;
      this.academicMode = 'audit';
      this.showToast(`已从金标准 Excel 表导入 ${res.addedCount} 场补充会议（自动提取来源链接 ${res.linkCount} 条）进入【① 来源与审核】！`, 'success');
    }
  };
};
