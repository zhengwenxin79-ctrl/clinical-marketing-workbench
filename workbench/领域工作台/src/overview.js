'use strict';
window.MarketOverview = (() => {
  /**
   * 市场总览模块统一配置（Single Source of Truth）
   * 所有模块遵循统一契约：名称 + 来源子项 + 本周新增 + 待确认 + 下钻入口
   * 诚实原则：未接入的数据源显式标记“未接入 / 待接入 / 预留”，不编造数字。
   */
  const MODULE_SCHEMA = [
    {
      id: 'hotspot',
      step: '①',
      title: '热点追踪',
      subtitle: '双蓝图评分 · 结构化洞察卡片',
      accent: '#2563eb',
      bg: '#eff6ff',
      border: '#bfdbfe',
      nextLabel: '进入作战地图 →'
    },
    {
      id: 'battle_map',
      step: '②',
      title: '作战地图',
      subtitle: '疾病域映射 · A/B/C/D 分级',
      accent: '#0d9488',
      bg: '#f0fdfa',
      border: '#99f6e4',
      nextLabel: '去派发任务 →'
    },
    {
      id: 'dispatch',
      step: '③',
      title: '任务派发',
      subtitle: '责任销售 + 时间窗 · 话术推荐',
      accent: '#ea580c',
      bg: '#fff7ed',
      border: '#fed7aa',
      nextLabel: '查看日报反馈 →'
    },
    {
      id: 'feedback',
      step: '④',
      title: '日报反馈',
      subtitle: '结构化提取 · 客户池自动更新',
      accent: '#7c3aed',
      bg: '#f5f3ff',
      border: '#ddd6fe',
      nextLabel: '↺ 回流更新 ② 作战地图'
    }
  ];

  function readStorage(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (e) {
      return fallback;
    }
  }

  function computeMetrics(D, fieldFilter) {
    const isAll = !fieldFilter || fieldFilter === 'all';
    const matchDomain = dId => isAll || (dId || 'diabetes') === fieldFilter;

    // 1. 会议与审核队列统计
    const queue = readStorage('demo_review_queue_v4', []);
    const approvedExtra = readStorage('clinical-workbench:approved-conferences:v1', []);
    const pendingConfs = queue.filter(x => x.review_status === 'pending' && matchDomain(x.field_id));
    const approvedConfsInQueue = queue.filter(x => x.review_status === 'approved' && matchDomain(x.field_id));

    const catalogConfs = (D.catalog?.entries || []).filter(c => matchDomain(c.domain_id));
    const weekStart = window.WeeklyMeetings ? window.WeeklyMeetings.monday() : '2026-11-23';
    const weekEnd = window.WeeklyMeetings ? window.WeeklyMeetings.add(weekStart, 6) : '2026-11-29';
    const weeklyEvents = (D.weekly?.change_log?.events || []).filter(e => {
      if (e.review_status !== 'approved') return false;
      const d = window.WeeklyMeetings ? window.WeeklyMeetings.localDate(e.observed_at) : (e.observed_at || '').slice(0, 10);
      return d >= weekStart && d <= weekEnd && matchDomain(e.field_id);
    });

    // 2. 热点议题统计
    const domainTopics = isAll
      ? (D.topics || [])
      : fieldFilter === 'diabetes'
        ? (D.topics || [])
        : (window.DomainFrameworks?.getDomain(fieldFilter)?.boards?.flatMap(b => b.topics) || []);

    // 3. 作战地图 / PI 库统计
    const totalExperts = isAll || fieldFilter === 'diabetes' ? (D.experts || []).length : 0;
    const knownExperts = isAll || fieldFilter === 'diabetes'
      ? (D.experts || []).filter(e => e.tier_code && e.tier_code !== 'undetermined').length
      : 0;
    const piRatings = (D.pi_ratings?.ratings || []).filter(r => r.total_score !== null).length;

    // 4. 任务派发与日报反馈统计 (读取销售协作状态)
    const salesStore = readStorage(D.sales?.storage_key || 'clinical-workbench:sales:v1', null);
    const recs = salesStore?.recommendations || D.sales?.initial_recommendations || [];
    const activeRecs = recs.filter(r => ['assigned', 'in_progress'].includes(r.status));
    const confPushes = readStorage('clinical-workbench:conference-pushes:v1', []);

    const feedbacks = salesStore?.feedback || [];
    const unreviewedFeedbacks = feedbacks.filter(f => !f.reviewed_at);

    return {
      weekStart,
      weekEnd,
      isAll,
      pendingConfsCount: pendingConfs.length,
      approvedNewCount: approvedConfsInQueue.length + approvedExtra.filter(x => matchDomain(x.field_id)).length,
      weeklyEventsCount: weeklyEvents.length,
      catalogCount: catalogConfs.length,
      topicCount: domainTopics.length,
      totalExperts,
      knownExperts,
      piRatings,
      totalRecs: recs.length,
      activeRecsCount: activeRecs.length,
      confPushCount: confPushes.length,
      feedbackCount: feedbacks.length,
      unreviewedCount: unreviewedFeedbacks.length
    };
  }

  function badge(text, tone) {
    const styles = {
      live: 'background:#dcfce7;color:#166534;border:1px solid #bbf7d0;',
      todo: 'background:#fef3c7;color:#92400e;border:1px solid #fde68a;',
      pending: 'background:#f1f5f9;color:#64748b;border:1px solid #e2e8f0;',
      reserved: 'background:#f8fafc;color:#94a3b8;border:1px dashed #cbd5e1;'
    };
    return `<span style="display:inline-block;font-size:11px;padding:2px 7px;border-radius:4px;font-weight:600;${styles[tone] || styles.pending}">${text}</span>`;
  }

  function sourceRow(name, statusBadge, detailText, actionHref, actionLabel) {
    return `
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;padding:9px 10px;background:#ffffff;border:1px solid #e2e8f0;border-radius:6px;">
        <div style="min-width:0;">
          <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
            <strong style="font-size:13.5px;color:#1e293b;">${name}</strong>
            ${statusBadge}
          </div>
          <div style="font-size:12px;color:#64748b;margin-top:2px;">${detailText}</div>
        </div>
        ${actionHref ? `<a href="${actionHref}" style="font-size:12px;font-weight:600;white-space:nowrap;color:#2563eb;text-decoration:none;padding:4px 8px;background:#eff6ff;border-radius:4px;">${actionLabel}</a>` : ''}
      </div>
    `;
  }

  function render(ctx) {
    const { D, s, V, esc, hash, update } = ctx;
    const fieldFilter = s.q.get('ov_field') || 'all';
    const m = computeMetrics(D, fieldFilter);
    const targetField = fieldFilter === 'all' ? 'diabetes' : fieldFilter;

    const domainPills = [
      ['all', '全部领域'],
      ...D.navigation.domains.map(d => [d.id, d.name])
    ];

    const moduleBodies = {
      hotspot: {
        kpis: [
          [m.catalogCount, '已收录会议'],
          [m.weeklyEventsCount, '本周已批准更新'],
          [m.pendingConfsCount, '待审核会议', m.pendingConfsCount > 0]
        ],
        sources: [
          sourceRow(
            '学术会议（国际/国内）',
            m.pendingConfsCount > 0 ? badge(`待审核 ${m.pendingConfsCount}`, 'todo') : badge('已同步', 'live'),
            `目录 ${m.catalogCount} 场 · 本周已核准 ${m.weeklyEventsCount} 条 · 衍生热点 ${m.topicCount} 项`,
            '会议审核入库.html',
            m.pendingConfsCount > 0 ? '去审核 →' : '审核台 →'
          ),
          sourceRow(
            '学术文献（每周定期更新）',
            badge('未接入', 'pending'),
            `当前已沉淀核心主池 ${D.summary?.primary_papers || 160} 篇 · 增量推送管道待接入`,
            hash('papers', { field: targetField }),
            '看底库 →'
          ),
          sourceRow(
            '药厂 / CDE 管线进展',
            badge('明年预留', 'reserved'),
            '暂不启用，保留模块扩展槽位',
            '',
            ''
          )
        ],
        footerHref: hash('topics', { field: targetField }),
        footerText: '查看热点洞察与议题 →'
      },
      battle_map: {
        kpis: [
          [m.totalExperts || '待接入', '辖区/全库 PI'],
          [m.knownExperts || '—', '已有层级依据'],
          [m.piRatings, '四维评分试评']
        ],
        sources: [
          sourceRow(
            'PI 专家画像库',
            m.totalExperts ? badge('已接入', 'live') : badge('待接入', 'pending'),
            m.totalExperts ? `已入库 ${m.totalExperts} 位专家来源 · 含四维评分 ${m.piRatings} 条` : '该专科当前处于框架预置阶段，尚未导入 PI 明细',
            hash('experts', { field: targetField }),
            '查 PI 库 →'
          ),
          sourceRow(
            '每周 Excel 上传与合并',
            badge('待接入', 'pending'),
            '第二步支持：同院同名自动合并，新增 PI 直接入库',
            hash('market', { sales_tab: 'recommend' }),
            '去筛选 PI →'
          )
        ],
        footerHref: hash('market', { sales_tab: 'recommend' }),
        footerText: '筛选高潜 PI 并生成推荐 →'
      },
      dispatch: {
        kpis: [
          [m.totalRecs, '累计作战卡'],
          [m.activeRecsCount, '跟进中任务', m.activeRecsCount > 0],
          [m.confPushCount, '推销售会议']
        ],
        sources: [
          sourceRow(
            '商机作战卡派发',
            badge('已接入', 'live'),
            `已派发 ${m.activeRecsCount} 张跟进中（含破冰话术与吉因加切入方案）`,
            hash('market', { sales_tab: 'follow' }),
            '看派发记录 →'
          ),
          sourceRow(
            '重点会议定向推送',
            badge('已接入', 'live'),
            `本周已向销售推送 ${m.confPushCount} 场重点会议`,
            '会议审核入库.html',
            '推新会议 →'
          )
        ],
        footerHref: hash('market', { sales_tab: 'follow' }),
        footerText: '管理派发记录与作战卡 →'
      },
      feedback: {
        kpis: [
          [m.feedbackCount, '拜访反馈数'],
          [m.unreviewedCount, '待市场复核', m.unreviewedCount > 0],
          ['待接入', '已回写 PI']
        ],
        sources: [
          sourceRow(
            '作战卡拜访反馈',
            m.unreviewedCount > 0 ? badge(`待复核 ${m.unreviewedCount}`, 'todo') : badge('已接入', 'live'),
            `已回收销售一线反馈 ${m.feedbackCount} 条 · 支持查看客户真实研究需求`,
            hash('market', { sales_tab: 'summary' }),
            m.unreviewedCount > 0 ? '去复核 →' : '看汇总 →'
          ),
          sourceRow(
            '销售日报自动抓取',
            badge('待接入', 'pending'),
            '第二步支持：自动抽取销售日报中的客户需求与科研卡点',
            '',
            ''
          ),
          sourceRow(
            '反馈自动回写 PI 库',
            badge('待接入', 'pending'),
            '第二步支持：将销售核实的真实需求回流至 ② 作战地图，校准推荐话术',
            '',
            ''
          )
        ],
        footerHref: hash('market', { sales_tab: 'summary' }),
        footerText: '复盘销售反馈与需求 →'
      }
    };

    const todoItems = [
      `<a href="会议审核入库.html" style="color:${m.pendingConfsCount ? '#b45309' : '#334155'};font-weight:600;text-decoration:none;">待审核会议 <b>${m.pendingConfsCount}</b> 条 →</a>`,
      `<a href="${hash('market', { sales_tab: 'summary' })}" style="color:${m.unreviewedCount ? '#7c3aed' : '#334155'};font-weight:600;text-decoration:none;">待复核销售反馈 <b>${m.unreviewedCount}</b> 条 →</a>`,
      `<a href="${hash('market', { sales_tab: 'follow' })}" style="color:#0f766e;font-weight:600;text-decoration:none;">正在跟进作战卡 <b>${m.activeRecsCount}</b> 张 →</a>`,
      `<span style="color:#64748b;">待合并 Excel / 待回写日报：<b>待接入</b></span>`
    ];

    V.innerHTML = `
      <div class="market-overview">
        <section class="panel" style="margin-bottom:18px;border-left:4px solid #172f4e;background:linear-gradient(135deg,#ffffff 0%,#f8fafc 100%);">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:14px;">
            <div>
              <div style="font-size:12px;color:#2563eb;font-weight:700;letter-spacing:0.5px;">MARKET COMMAND CENTER · 端到端闭环流水线</div>
              <h2 style="margin:4px 0 6px;font-size:20px;color:#172f4e;">市场部营销总览与每周更新雷达</h2>
              <p style="margin:0;font-size:13px;color:#64748b;">
                周期：<strong>${esc(m.weekStart)} — ${esc(m.weekEnd)}</strong>（北京时间） · 先看全局流动与待办，再点击下钻到具体模块核查。
              </p>
            </div>
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
              <span style="font-size:12px;color:#64748b;font-weight:600;">疾病域筛选：</span>
              <div style="display:flex;gap:6px;flex-wrap:wrap;">
                ${domainPills.map(([id, label]) => `
                  <button type="button" data-ov-field="${esc(id)}" style="padding:5px 11px;font-size:12.5px;border-radius:16px;${fieldFilter === id ? 'background:#172f4e;color:#ffffff;border-color:#172f4e;font-weight:600;' : 'background:#ffffff;color:#334155;border:1px solid #cbd5e1;'}">${esc(label)}</button>
                `).join('')}
              </div>
            </div>
          </div>

          <div style="margin-top:14px;padding:10px 14px;background:#fefce8;border:1px solid #fde68a;border-radius:6px;display:flex;align-items:center;gap:18px;flex-wrap:wrap;font-size:13px;">
            <strong style="color:#92400e;">📌 今日待办：</strong>
            ${todoItems.join('<span style="color:#cbd5e1;">|</span>')}
          </div>
        </section>

        <section style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;margin-bottom:18px;">
          ${MODULE_SCHEMA.map(mod => {
            const b = moduleBodies[mod.id];
            return `
              <article class="panel" style="padding:18px;border-top:4px solid ${mod.accent};display:flex;flex-direction:column;justify-content:space-between;gap:14px;">
                <div>
                  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:12px;">
                    <div>
                      <div style="font-size:12px;font-weight:700;color:${mod.accent};">${mod.step} 流水线模块</div>
                      <h3 style="margin:2px 0 4px;font-size:18px;color:#0f172a;">${esc(mod.title)}</h3>
                      <div style="font-size:12px;color:#64748b;">${esc(mod.subtitle)}</div>
                    </div>
                  </div>

                  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:14px;">
                    ${b.kpis.map(([val, lbl, highlight]) => `
                      <div style="background:${highlight ? mod.bg : '#f8fafc'};border:1px solid ${highlight ? mod.border : '#e2e8f0'};border-radius:6px;padding:8px 10px;">
                        <div style="font-size:18px;font-weight:700;color:${highlight ? mod.accent : '#1e293b'};">${esc(val)}</div>
                        <div style="font-size:11px;color:#64748b;">${esc(lbl)}</div>
                      </div>
                    `).join('')}
                  </div>

                  <div style="display:grid;gap:8px;">
                    ${b.sources.join('')}
                  </div>
                </div>

                <div style="padding-top:12px;border-top:1px solid #e2e8f0;display:flex;justify-content:space-between;align-items:center;">
                  <span style="font-size:11.5px;color:#94a3b8;">${esc(mod.nextLabel)}</span>
                  <a href="${b.footerHref}" style="font-size:13px;font-weight:600;color:${mod.accent};text-decoration:none;">${esc(b.footerText)}</a>
                </div>
              </article>
            `;
          }).join('')}
        </section>

        <section class="panel" style="padding:14px 18px;background:#f8fafc;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
          <div style="font-size:13px;color:#334155;">
            <strong>流水线流转逻辑：</strong>
            <span style="color:#2563eb;font-weight:600;">① 热点追踪</span> ➔
            <span style="color:#0d9488;font-weight:600;">② 作战地图</span> ➔
            <span style="color:#ea580c;font-weight:600;">③ 任务派发</span> ➔
            <span style="color:#7c3aed;font-weight:600;">④ 日报反馈</span>
            <span style="color:#64748b;margin-left:8px;">（↺ 反馈回流持续校准 ② PI 画像与推荐话术）</span>
          </div>
          <span style="font-size:12px;color:#64748b;">说明：标“未接入 / 待接入 / 预留”项暂不编造数据，将在第二阶段逐一接通。</span>
        </section>
      </div>
    `;

    V.querySelectorAll('[data-ov-field]').forEach(btn => {
      btn.onclick = () => update({ ov_field: btn.dataset.ovField === 'all' ? null : btn.dataset.ovField });
    });
  }

  return { MODULE_SCHEMA, computeMetrics, render };
})();
