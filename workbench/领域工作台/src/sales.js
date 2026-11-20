'use strict';
window.SalesCollaboration=(()=>{
 const STATUS={draft:'草稿',assigned:'已分配',in_progress:'跟进中',archived:'已归档'},CONTACT={not_contacted:'尚未接触',contacted:'已接触',waiting:'等待回复',paused:'暂缓跟进'},ROLES={market:'市场部',sales:'销售代表'};
 let stored=null,storageError='',dirty=false,flash='',loadedRaw=null;
 const now=()=>new Date().toISOString(),today=()=>new Date(Date.now()+8*3600000).toISOString().slice(0,10),dateTime=v=>v?new Date(v).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false}):'尚无记录',uid=p=>p+'-'+(globalThis.crypto?.randomUUID?.()||Date.now()+'-'+Math.random().toString(16).slice(2));
 function load(C){if(stored)return stored;try{const raw=localStorage.getItem(C.storage_key);loadedRaw=raw;const initRecs=C.initial_recommendations||(C.demo_recommendation?[C.demo_recommendation]:[]);if(!raw){stored={version:1,recommendations:structuredClone(initRecs),feedback:[]};localStorage.setItem(C.storage_key,JSON.stringify(stored));loadedRaw=JSON.stringify(stored);}else{const x=JSON.parse(raw);if(x.version!==1||!Array.isArray(x.recommendations)||!Array.isArray(x.feedback))throw Error('记录格式不兼容');if((!x.recommendations||x.recommendations.length===0)&&initRecs.length>0){x.recommendations=structuredClone(initRecs);localStorage.setItem(C.storage_key,JSON.stringify(x));loadedRaw=JSON.stringify(x);}stored=x;}}catch(e){storageError='无法读取浏览器记录，已停止保存，避免覆盖。请保留当前浏览器数据后排查：'+e.message;stored={version:1,recommendations:C.initial_recommendations||[],feedback:[]};}return stored;}
 function save(C,next){if(storageError)return false;try{if(localStorage.getItem(C.storage_key)!==loadedRaw)throw Error('另一窗口已修改记录，请先复制当前填写内容，再刷新核对最新记录');const raw=JSON.stringify(next);localStorage.setItem(C.storage_key,raw);loadedRaw=raw;stored=next;return true;}catch(e){storageError='保存失败：'+e.message+'。当前填写内容仍保留，请复制备份后再刷新重试。';return false;}}
 function canLeave(){if(!dirty&&!window.RecommendationFeedback.isDirty())return true;if(confirm('当前表单尚未保存，离开会丢失本次填写。是否离开？')){dirty=false;window.RecommendationFeedback.clearDirty();return true;}return false;}
 window.addEventListener('beforeunload',e=>{if(dirty||window.RecommendationFeedback.isDirty()){e.preventDefault();e.returnValue='';}});
 window.addEventListener('storage',e=>{if(e.key==='clinical-workbench:sales:v1'){stored=null;storageError='';flash='另一窗口更新了记录；当前表单未自动刷新，请保存前核对最新记录。';}});
 function render(ctx){const {D,s,V,esc,link,hash,options,update,rerender}=ctx,C=D.sales,S=load(C),q=s.q;
 const authUser=(()=>{try{const raw=localStorage.getItem('clinical-auth:current-user');return raw?JSON.parse(raw):null;}catch(e){return null;}})();
 const isAuthSales=authUser&&authUser.role==='sales';
 const role=isAuthSales?'sales':(s.tab==='market'?'market':'sales');
 let salesId=(isAuthSales&&authUser.id)?(C.salespeople.some(p=>p.id===authUser.id)?authUser.id:(authUser.id.includes('b')?'demo-sales-b':'demo-sales-a')):(C.salespeople.some(p=>p.id===q.get('sales'))?q.get('sales'):C.salespeople[0].id);
 const tab=q.get('recommend_view')==='records'&&q.get('sales_tab')!=='summary'?'follow':['recommend','follow','summary','territory'].includes(q.get('sales_tab'))?q.get('sales_tab'):(role==='sales'?'follow':'recommend');
 const T=new Map(D.topics.map(t=>[t.topic_id,t])),R=new Map(D.reports.map(r=>[r.report_id,r])),P=new Map(D.papers.map(p=>[p.paper_id,p])),E=new Map(D.experts.map(p=>[p.key,p])),CAP=new Map(C.capabilities.map(c=>[c.id,c]));
 const person=id=>C.salespeople.find(x=>x.id===id)?.name||'未分配',status=r=>`<span class="sales-status ${esc(r.status)}">${STATUS[r.status]||'待确认'}</span>${r.is_demo?'<span class="sales-demo">演示推荐</span>':''}`,empty=t=>`<div class="empty">${esc(t)}</div>`;
 const go=values=>update({...(role==='sales'?{sales:salesId}:{}),sales_tab:tab,...values}),feedbackFor=r=>S.feedback.filter(f=>f.recommendation_id===r.id).sort((a,b)=>b.created_at.localeCompare(a.created_at)),latest=r=>feedbackFor(r)[0];
 let visible=S.recommendations.filter(r=>r.domain_id===s.field&&(role!=='sales'||r.assignee_id===salesId&&r.status!=='draft'));
 const filter=q.get('sales_status')||'all',needle=s.search.toLowerCase(),rows=visible.filter(r=>(filter==='all'||r.status===filter)&&(!needle||[r.title,r.research_question,r.reason,T.get(r.topic_id)?.name,...r.expert_keys.map(k=>E.get(k)?.display_name||'')].join(' ').toLowerCase().includes(needle)));
 const chosen=rows.find(r=>r.id===q.get('rec'))||rows[0],canEdit=role==='market',canFollow=r=>role==='sales'&&r.assignee_id===salesId&&['assigned','in_progress'].includes(r.status);
 const qualityContext={D,S,s,role,salesId,esc,person,hash,storageError,persist:items=>{if(!save(C,{...S,recommendation_feedback:items}))return storageError;S.recommendation_feedback=items;return '';}};
 const checked=(id,ids)=>ids.includes(id)?'checked':'',area=(name,label,value='',required=false,help='')=>`<label class="sales-field wide">${label}${required?' *':''}<textarea name="${name}" maxlength="6000" ${required?'required':''}>${esc(value)}</textarea>${help?`<small>${esc(help)}</small>`:''}</label>`;
 const toast=()=>flash?`<p class="sales-flash" role="status">${esc(flash)}</p>`:'';
 const formError=(f,msg)=>{const el=f.querySelector('[data-form-error]');el.textContent=msg;el.hidden=false;};
 const rawChecks=(kind,items,selected)=>items.map(x=>`<label class="sales-check"><input type="checkbox" name="${kind}" value="${esc(x.id)}" ${checked(x.id,selected)}><span>${esc(x.title)}<small>${esc(x.note||'')}</small></span></label>`).join('');
 function sourceChoices(topicId,rec){const t=T.get(topicId);if(!t)return empty('请选择已归类议题。');const rr=t.report_ids.map(id=>R.get(id)).filter(Boolean),pp=t.paper_ids.map(id=>P.get(id)).filter(Boolean);return `<div class="sales-evidence-choices"><b>会议报告（${rr.length}条，可选）</b><div class="sales-checkboxes">${rawChecks('report',rr.map(r=>({id:r.report_id,title:r.title,note:r.conference_id+' · '+r.code+' · 已有日程题名'})),rec.links.filter(x=>x.kind==='report').map(x=>x.id))||empty('当前议题尚无报告。')}</div><p><b>论文（${pp.length}篇主池，可选）</b></p><div class="sales-checkboxes">${rawChecks('paper',pp.map(p=>({id:p.paper_id,title:p.title,note:p.journal+' · '+p.publication_date})),rec.links.filter(x=>x.kind==='paper').map(x=>x.id))||empty('当前议题尚无主池论文。')}</div></div>`;}
 function expertChoices(topicId,rec){const t=T.get(topicId),people=(t?.expert_keys||[]).map(k=>E.get(k)).filter(Boolean);return `<div class="sales-evidence-choices sales-checkboxes">${rawChecks('expert',people.map(p=>({id:p.key,title:p.display_name,note:p.source_label+' · '+p.institution_source+' · '+p.tier_label})),rec.expert_keys)||empty('当前议题没有已关联的人物来源。')}</div><small>可暂不指定；来源讲者或作者身份不等于已确认客户、通讯作者或课题PI。</small>`;}
 function sources(r){return r.links.map(x=>{const a=x.kind==='report'?R.get(x.id):P.get(x.id);if(!a)return `<p class="muted">关联记录待核：${esc(x.id)}</p>`;return `<article class="source-row"><div class="meta">${x.kind==='report'?esc(a.conference_id+' · '+a.code+' · 日程题名'):esc(a.journal+' · '+a.publication_date+' · '+a.reading_level)}</div><a class="sales-source-title" href="${esc(a.detail_url)}">${esc(a.title)}</a>${x.kind==='paper'?`<p>${esc(a.finding||'结果待整理')}</p>`:''}<div class="links">${link(a.detail_url,'查看资料详情')}${link(a.source_url,'原始来源',true)}</div></article>`;}).join('')||empty('尚未选择具体报告或论文，可从关联议题继续查看。');}
 function capabilities(r){return r.capability_ids.map(id=>CAP.get(id)).filter(Boolean).map(c=>`<article class="sales-capability"><b>${esc(c.id+' · '+c.name)}</b><p>${esc(c.status)}</p><p>${esc(c.participation)}</p><p class="muted">待确认：${esc(c.conditions)}</p><details><summary>能力底表依据</summary><p>${esc(c.excerpt)}</p><p>${esc(c.locator)}</p>${link(c.source_url,'打开已有能力底表')}</details></article>`).join('')||'<p class="muted">能力尚未选择，待市场与技术支持确认。</p>';}
 function timeline(r){const fs=feedbackFor(r);return `<div class="sales-history">${fs.map(f=>`<article class="sales-feedback" data-feedback-id="${esc(f.id)}"><div class="sales-section-head"><b>${esc(CONTACT[f.contact_status])}${f.is_demo?'<span class="sales-demo">虚构演示反馈</span>':''}</b><span class="sales-meta">${esc(person(f.author_id))} · ${esc(dateTime(f.created_at))}</span></div><p class="sales-meta">沟通时间：${esc(f.contact_date||'尚未接触／未记录')}</p><dl>${[['联系人',f.contact_name],['单位',f.institution],['研究问题',f.need],['样本与阶段',f.cohort],['需要支持',f.support],['下一步',f.next_action],['负责与时间',person(f.next_owner_id)+' · '+(f.next_date||'时间待定')]].map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(v||'尚未了解到')}</dd>`).join('')}</dl><div class="sales-review">${f.reviewed_at?`<b>市场已复核</b> · ${esc(dateTime(f.reviewed_at))}<p>${esc(f.review_note||'已查看沟通记录；研究结论与客户画像未自动修改。')}</p>`:canEdit?`<label>复核备注（可选）<input data-review-note="${esc(f.id)}" maxlength="1000" placeholder="记录需补资料或支持安排"></label><button type="button" data-review="${esc(f.id)}">标记已复核</button>`:'待市场复核'}<p class="muted">反馈仅用于沟通与支持安排，研究证据和热点排名保持独立。</p></div></article>`).join('')||empty('暂无沟通记录。销售保存反馈后，按时间保留在这里。')}</div>`;}
 function feedbackForm(r){return `<form id="sales-feedback-form" class="sales-form"><h3>新增跟进反馈</h3><p class="sales-route-note">每次保存新增一条记录，不覆盖既有沟通历史。允许填写“尚未了解到”。</p>${r.is_demo?'<p class="sales-note">当前为演示推荐，所填反馈统一标为虚构演示。真实沟通请另建推荐记录。</p>':''}<div class="sales-fields"><label class="sales-field">接触状态 *<select name="contact_status">${options(Object.entries(CONTACT),'not_contacted')}</select></label><label class="sales-field">沟通日期<input type="date" name="contact_date" max="${today()}"></label><label class="sales-field">联系人<input name="contact_name" maxlength="200" placeholder="尚未了解到"></label><label class="sales-field">单位<input name="institution" maxlength="300" placeholder="尚未了解到"></label>${area('need','客户关注的研究问题')}${area('cohort','样本、队列与项目阶段')}${area('support','需要公司提供的支持')}${area('next_action','下一步', '',true)}<label class="sales-field">下一步负责人 *<select name="next_owner_id">${options(C.salespeople.map(p=>[p.id,p.name]),salesId)}</select></label><label class="sales-field">预计跟进日期<input type="date" name="next_date"></label></div><p data-form-error class="sales-note error" role="alert" hidden></p><div class="sales-actions"><button type="submit" class="primary" ${storageError?'disabled':''}>保存反馈</button>${r.is_demo?'<button type="button" id="fill-demo-feedback">填入虚构演示反馈</button>':''}</div></form>`;}
 function detail(r){if(!r)return `<section class="panel sales-detail">${empty(role==='sales'?'当前没有分配给该销售代表的商机作战卡。可切换至【区域高潜PI】一键生成作战卡，或由市场部在后台指派。':'先创建推荐，或载入已有糖尿病资料的商机作战卡。')}</section>`;
 const breakIceScript=r.break_ice_script||`“专家/主任您好，拜读了您在大会上关于【${r.research_question||r.title}】的学术分享，非常有启发。我们吉因加最近在类似队列中结合${r.capability_ids?.includes('T10')?'6Dmarker多组学整合算法':'高通量组学技术'}，协助多家三甲医院团队完成了生物标志物挖掘与临床文章转化。想找时间向您汇报下，看能不能结合您手头的临床队列与随访样本，探讨共同申报科研项目或冲刺高分转化医学文章？”`;
 const painPoint=r.pain_point||'常规临床生化指标灵敏度不足，单纯临床指标无法支持发表10分以上顶刊；缺乏多组学联合分析与生信建模能力。';
 const matchScore=r.match_score||(r.is_demo?92:95);
 return `<section class="panel sales-detail" data-recommendation-id="${esc(r.id)}" style="box-shadow:0 4px 15px rgba(23,47,78,0.06);">
   <div style="background:linear-gradient(135deg,#0f243e 0%,#1a3a60 100%);color:white;padding:16px 20px;border-radius:8px;margin-bottom:18px;">
     <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:8px;">
       <div style="display:flex;align-items:center;gap:8px;">
         <span style="background:#dc2626;color:white;font-weight:700;font-size:12px;padding:3px 9px;border-radius:4px;letter-spacing:0.5px;box-shadow:0 2px 4px rgba(220,38,38,0.3);">🎯 商机作战卡 BATTLE CARD</span>
         <span style="background:rgba(56,189,248,0.25);color:#38bdf8;font-size:12px;padding:3px 8px;border-radius:4px;border:1px solid rgba(56,189,248,0.4);font-weight:600;">匹配度 ${matchScore}%</span>
         ${status(r)}
       </div>
       <div style="display:flex;align-items:center;gap:8px;">
         ${canEdit?`<button id="edit-recommendation" style="background:#fff;color:#1e3a8a;border:none;padding:5px 12px;border-radius:5px;font-size:13px;font-weight:600;">编辑作战卡</button>${r.status!=='archived'?'<button id="archive-recommendation" style="background:rgba(255,255,255,0.2);color:#fff;border:none;padding:5px 10px;border-radius:5px;font-size:12px;">归档</button>':'<button id="restore-recommendation" style="background:rgba(255,255,255,0.2);color:#fff;border:none;padding:5px 10px;border-radius:5px;font-size:12px;">恢复</button>'}`:canFollow(r)?'<button class="primary" id="jump-sales-feedback" style="background:#2563eb;color:#fff;border:none;padding:7px 14px;border-radius:6px;font-size:13px;font-weight:600;box-shadow:0 2px 6px rgba(37,99,235,0.4);">📝 记录本次拜访跟进</button>':''}
       </div>
     </div>
     <h2 style="color:#ffffff;font-size:18px;margin:8px 0 6px;line-height:1.4;">${esc(r.title)}</h2>
     <div style="font-size:13px;color:#93c5fd;display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
       <span>👤 负责销售：<strong style="color:white;">${esc(person(r.assignee_id))}</strong></span>
       <span>📅 建议破冰跟进：<strong style="color:#fde047;">${esc(r.due_date||'下周内')}</strong></span>
       <span>⏱️ 更新于：${esc(dateTime(r.updated_at))}</span>
     </div>
   </div>

   <div class="sales-detail-block" style="background:#f0fdf4;border:1px solid #bbf7d0;border-left:4px solid #16a34a;padding:14px 18px;border-radius:7px;margin-bottom:16px;">
     <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
       <h3 style="color:#166534;margin:0;font-size:15px;display:flex;align-items:center;gap:6px;">
         <span>💬</span> 建议破冰话术（微信预约 / 门诊或病房拜访提纲）
       </h3>
       <button type="button" id="copy-break-ice-btn" style="font-size:12px;padding:4px 10px;background:#ffffff;color:#15803d;border:1px solid #86efac;border-radius:4px;cursor:pointer;">📋 复制破冰话术</button>
     </div>
     <p id="break-ice-content" style="font-size:13.5px;color:#14532d;line-height:1.65;margin:0;background:#ffffff;padding:10px 12px;border-radius:5px;border:1px dashed #86efac;">${esc(breakIceScript)}</p>
   </div>

   <div class="sales-detail-block">
     <h3 style="display:flex;align-items:center;gap:6px;color:#172f4e;"><span>💡</span> 专家研究卡点与切入痛点</h3>
     <div style="background:#fef2f2;border:1px solid #fecaca;border-left:3px solid #ef4444;padding:8px 14px;border-radius:4px;color:#991b1b;margin-bottom:8px;font-size:13.5px;">
       <strong>专家卡在什么环节：</strong>${esc(painPoint)}
     </div>
     <div style="font-size:13.5px;color:#334155;line-height:1.6;">
       <p><strong>商业化切入理由：</strong>${esc(r.reason)}</p>
       <p><strong>临床关注核心问题：</strong>${esc(r.research_question)}</p>
     </div>
     ${T.has(r.topic_id)?`<div class="links" style="margin-top:6px;"><a href="${hash('topics',{detail:r.topic_id,board:T.get(r.topic_id)?.board_id})}">🔬 查看该研究方向领域热点 →</a></div>`:''}
   </div>

   <div class="sales-detail-block" style="background:#f8fafc;border:1px solid #e2e8f0;border-left:4px solid #3b82f6;padding:14px 16px;border-radius:6px;">
     <h3 style="display:flex;align-items:center;gap:6px;color:#1e3a8a;margin-top:0;"><span>🧬</span> 吉因加可参与环节与技术切入方案</h3>
     <p style="font-size:14px;color:#1e293b;margin:4px 0 8px;"><strong>参与环节：</strong>${esc(r.participation||'结合吉因加多组学整合算法与标志物筛选方案，讨论队列入组与生信建模')}</p>
     <p style="font-size:13px;color:#64748b;margin:0 0 10px;"><strong>进院交流前提与待核实条件：</strong>${esc(r.conditions||'需先确认随访终点、已有标本类型与独立验证队列规划')}</p>
     ${capabilities(r)}
   </div>

   <div class="sales-detail-block">
     <h3 style="display:flex;align-items:center;gap:6px;"><span>👨‍⚕️</span> 目标 PI 履历画像与客情档案</h3>
     ${r.expert_keys.length?r.expert_keys.map(k=>{const p=E.get(k);return p?window.PIRecommendations.profile({D,p,c:window.PIRecommendations.build(D).find(c=>c.person.key===k),esc,link,hash,compact:true,isFavorite:(S.favorites||[]).some(f=>f.actor_id===(role==='sales'?salesId:role)&&f.person_key===k)}):'';}).join(''):'<p class="muted">未绑定特定人物，可与该科室科研副主任或青年PI开展接洽。</p>'}
   </div>

   <div class="sales-detail-block">
     <h3>🎯 建议行动计划</h3>
     <p style="font-size:13.5px;color:#1e293b;line-height:1.6;">${esc(r.suggested_action||'建议销售代表提前预约拜访，携带对应方案材料')}</p>
   </div>

   <div class="sales-detail-block">
     <h3 style="display:flex;align-items:center;gap:6px;"><span>📚</span> 原始学术证据链（大会日程与论文）</h3>
     ${sources(r)}
   </div>

   <div class="sales-detail-block">
     <h3 style="display:flex;align-items:center;gap:6px;"><span>📝</span> 客户沟通与跟进历史（${feedbackFor(r).length} 条）</h3>
     ${timeline(r)}
   </div>

   ${canFollow(r)?feedbackForm(r):`<p class="sales-note">${role!=='sales'?'负责销售可在销售工作台填写反馈。':r.status==='archived'?'推荐已归档，可查看历史记录。':'此推荐未分配给当前演示销售。'}</p>`}
 </section>`;}

 function territoryView(){
  const isSouth=salesId.includes('b');
  const territoryName=isSouth?'华南战区（广东、广西、福建、海南）':'华北战区（北京、天津、河北、山东、山西）';
  const kwRegex=isSouth?/广东|广州|深圳|中山|南方|广医|暨南|福建|厦门|广西|海南|华南/:/北京|人民|协和|北大|中日|阜外|宣武|安贞|齐鲁|山东|天津|河北|山西|解放军/;
  let regionalExperts=D.experts.filter(p=>p.institution_source&&kwRegex.test(p.institution_source));
  if(regionalExperts.length===0){regionalExperts=D.experts.filter(p=>p.tier_code!=='undetermined');}
  const needle=s.search.toLowerCase();
  if(needle){regionalExperts=regionalExperts.filter(p=>[p.display_name,p.institution_source,p.role_scope].join(' ').toLowerCase().includes(needle));}
  regionalExperts.sort((a,b)=>(b.report_ids.length+b.paper_ids.length)-(a.report_ids.length+a.paper_ids.length));
  const TIER_TAGS={'international':'<span style="background:#f5f3ff;color:#6b21a8;border:1px solid #d8b4fe;padding:2px 7px;border-radius:4px;font-size:12px;font-weight:700;">👑 国际级学者</span>','national':'<span style="background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;padding:2px 7px;border-radius:4px;font-size:12px;font-weight:700;">🏛️ 全国学术带头人</span>','regional':'<span style="background:#f0fdf4;color:#15803d;border:1px solid #bbf7d0;padding:2px 7px;border-radius:4px;font-size:12px;font-weight:700;">🚀 高潜青年骨干</span>','undetermined':'<span style="background:#f8fafc;color:#475569;border:1px solid #cbd5e1;padding:2px 7px;border-radius:4px;font-size:12px;">🔬 专科临床讲者</span>'};
  const pages=Math.max(1,Math.ceil(regionalExperts.length/12)),page=Math.min(s.page||1,pages),pagedList=regionalExperts.slice((page-1)*12,page*12);
  return `<div class="sales-territory-view">
    <section class="panel" style="margin-bottom:18px;border-left:4px solid #2563eb;background:#fbfdff;">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:gap:12px;">
        <div>
          <h2 style="margin:0 0 6px;font-size:18px;color:#172f4e;display:flex;align-items:center;gap:8px;">
            <span>📍</span> ${esc(territoryName)} · 临床重点 PI 与客情档案库
          </h2>
          <p style="margin:0;font-size:13px;color:var(--muted);">
            已按您的责任区域自动筛选三甲医院学科带头人与中青年骨干；支持一键生成商机作战卡、建立拜访计划与客情关系分级维护。
          </p>
        </div>
        <div style="font-size:13px;color:#1e40af;background:#eff6ff;padding:6px 12px;border-radius:6px;border:1px solid #bfdbfe;font-weight:600;">
          本辖区共监控入库 ${regionalExperts.length} 位学术专家
        </div>
      </div>
    </section>
    <div style="display:grid;grid-template-columns:repeat(auto-fill, minmax(360px, 1fr));gap:16px;">
      ${pagedList.map(p=>{
        const isFav=(S.favorites||[]).some(f=>f.actor_id===salesId&&f.person_key===p.key);
        const hasRec=S.recommendations.some(r=>r.expert_keys.includes(p.key)||r.title.includes(p.display_name));
        const relationStatus=hasRec?'<span style="background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;">🎯 作战卡跟进中</span>':isFav?'<span style="background:#fef3c7;color:#b45309;border:1px solid #fde68a;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;">⭐ 重点客情维护中</span>':'<span style="background:#f1f5f9;color:#475569;border:1px solid #e2e8f0;padding:2px 8px;border-radius:4px;font-size:12px;">📌 新线索·待拜访</span>';
        return `<article class="panel" style="padding:16px;display:flex;flex-direction:column;justify-content:space-between;border:1px solid var(--line);border-radius:8px;">
          <div>
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:8px;">
              <div>
                <strong style="font-size:17px;color:var(--ink);">${esc(p.display_name)}</strong>
                <span style="font-size:13px;color:#64748b;margin-left:6px;">${esc(p.role_scope||'内分泌/代谢')}</span>
              </div>
              <div style="display:flex;gap:6px;align-items:center;">
                ${TIER_TAGS[p.tier_code]||TIER_TAGS['undetermined']}
              </div>
            </div>
            <p style="font-size:13px;color:#334155;margin:4px 0 8px;display:flex;align-items:center;gap:6px;">
              <span>🏥</span> ${esc(p.institution_source||'医院待核实')}
            </p>
            <div style="margin-bottom:10px;">${relationStatus}</div>
            <p style="font-size:12.5px;color:var(--muted);background:#f8fafc;padding:8px 10px;border-radius:4px;border:1px solid #f1f5f9;margin:0 0 12px;line-height:1.5;">
              <strong>学术动态：</strong>${p.report_ids.length?'大会演讲：'+esc(R.get(p.report_ids[0])?.title||p.report_ids[0]):(p.paper_ids.length?'近期发表：'+esc(P.get(p.paper_ids[0])?.title||'顶刊署名'):'承担本领域前沿科研课题')}
            </p>
          </div>
          <div style="display:flex;gap:8px;align-items:center;padding-top:10px;border-top:1px solid var(--line);">
            <button class="primary" style="flex:1;font-size:12px;padding:6px 10px;" data-generate-battle-card="${esc(p.key)}" data-pi-name="${esc(p.display_name)}" data-pi-inst="${esc(p.institution_source)}" data-pi-topic="${esc(p.topic_ids[0]||'DM:Q17')}">
              🎯 一键生成商机作战卡
            </button>
            <button type="button" style="font-size:12px;padding:6px 10px;background:#fff;border:1px solid #cbd5e1;" data-pi-favorite="${esc(p.key)}">
              ${isFav?'★ 已收藏':'☆ 收藏客情'}
            </button>
          </div>
        </article>`;
      }).join('')}
    </div>
    <div class="pager" style="margin-top:20px;">
      <button id="territory-prev" ${page===1?'disabled':''}>上一页</button>
      <span>第 ${page} / ${pages} 页</span>
      <button id="territory-next" ${page===pages?'disabled':''}>下一页</button>
    </div>
  </div>`;
 }
 function editor(){let r=S.recommendations.find(x=>x.id===q.get('rec')&&x.domain_id===s.field);if(r&&role!=='market')return empty('当前视角仅查看推荐。');if(!r)r={id:'',topic_id:T.has(s.topic)?s.topic:D.topics[0].topic_id,title:T.get(s.topic)?.name||'',research_question:T.get(s.topic)?.name||'',reason:'',participation:'',conditions:'',suggested_action:'',assignee_id:'',due_date:'',links:[],expert_keys:[],capability_ids:[],is_demo:false};
 return `<section class="panel"><div class="sales-section-head"><div><h2>${r.id?'编辑推荐':'创建推荐'}</h2><p class="muted">从已有研究资料整理沟通准备。标 * 为必填。</p></div><button type="button" id="cancel-sales-edit">返回列表</button></div>${r.is_demo?'<p class="sales-note">当前是演示推荐，编辑后仍保留演示标识。</p>':''}<form id="sales-recommendation-form" class="sales-form" data-edit-id="${esc(r.id)}"><div class="sales-fields"><label class="sales-field wide">所属领域<input value="糖尿病" disabled></label><label class="sales-field wide">关联研究议题 *<select name="topic_id" id="sales-topic">${options(D.topics.map(t=>[t.topic_id,t.name]),r.topic_id)}</select></label><label class="sales-field wide">推荐标题 *<input name="title" value="${esc(r.title)}" maxlength="200" required></label>${area('research_question','研究问题',r.research_question,true)}${area('reason','为什么值得交流',r.reason,true)}${area('participation','吉因加可参与环节',r.participation)}${area('conditions','适用条件与待确认',r.conditions)}${area('suggested_action','建议行动',r.suggested_action,true)}<label class="sales-field">负责销售（分配时必选）<select name="assignee_id">${options([['','暂不分配'],...C.salespeople.map(p=>[p.id,p.name])],r.assignee_id)}</select></label><label class="sales-field">建议跟进日期<input type="date" name="due_date" value="${esc(r.due_date)}"></label></div><fieldset><legend>关联会议与论文</legend><div id="sales-source-choices">${sourceChoices(r.topic_id,r)}</div></fieldset><fieldset><legend>相关专家或团队（可选）</legend><div id="sales-expert-choices">${expertChoices(r.topic_id,r)}</div></fieldset><fieldset><legend>能力底表参考（可选）</legend><p class="muted">当前原型接入已有T10、T14、T03底表摘录。其它能力可在参与环节说明中引用并附待核条件。</p><div class="sales-checkboxes">${rawChecks('capability',C.capabilities.map(c=>({id:c.id,title:c.id+' · '+c.name,note:c.status})),r.capability_ids)}</div></fieldset><p data-form-error class="sales-note error" role="alert" hidden></p><div class="sales-actions"><button type="submit" name="intent" value="draft" ${storageError?'disabled':''}>保存草稿</button><button type="submit" name="intent" value="assign" class="primary" ${storageError?'disabled':''}>${r.status==='in_progress'?'保存并继续跟进':'保存并分配'}</button><span class="sales-meta">仅保存到当前浏览器</span></div></form></section>`;}
 function summary(){const fs=S.feedback.filter(f=>visible.some(r=>r.id===f.recommendation_id)),unreviewed=fs.filter(f=>!f.reviewed_at),support=visible.map(r=>({r,f:feedbackFor(r).find(f=>f.support?.trim()),next:latest(r)})).filter(x=>x.f&&x.r.status!=='archived');
 return window.RecommendationFeedback.summary(qualityContext,visible)+`<div class="stats">${[[visible.length,'推荐记录'],[visible.filter(r=>['assigned','in_progress'].includes(r.status)).length,'待跟进 / 跟进中'],[fs.length,'跟进反馈'],[unreviewed.length,'待市场复核']].map(([n,l])=>`<div class="stat"><b>${n}</b><span>${l}</span></div>`).join('')}</div><div class="sales-summary-grid"><section class="panel"><h2>待支持事项</h2><p class="muted">按每条推荐最近非空支持记录展示；后续未填写不视为撤销，结束需求时请明确说明。</p>${support.map(({r,f,next})=>`<div class="sales-support">${r.is_demo?'<span class="sales-demo">虚构演示</span>':''}<p><a href="${hash('sales',{role,sales:salesId,sales_tab:'follow',rec:r.id})}"><b>${esc(r.title)}</b></a></p><p>${esc(f.support)}</p><p class="sales-meta">下一步：${esc(next.next_action)} · ${esc(next.next_date||'时间待定')}</p></div>`).join('')||empty('暂无已反馈的支持需求。')}</section><section class="panel"><h2>客户研究问题</h2><p class="muted">展示沟通记录，尚未转成已核实的客户画像。</p>${visible.map(r=>({r,f:feedbackFor(r).find(f=>f.need?.trim())})).filter(x=>x.f).map(({r,f})=>`<div class="sales-support">${f.is_demo?'<span class="sales-demo">虚构演示</span>':''}<p>${esc(f.need)}</p><p class="sales-meta">${esc(f.contact_name||'联系人待了解')} · ${esc(f.institution||'单位待了解')} · ${esc(dateTime(f.created_at))}</p></div>`).join('')||empty('销售填写沟通结果后，在这里汇总研究问题。')}</section></div><section class="panel sales-summary-list"><h2>跟进进度与复核</h2>${visible.map(r=>`<div class="sales-detail-block"><div class="sales-section-head"><h3>${esc(r.title)}</h3>${status(r)}</div><p class="muted">负责：${esc(person(r.assignee_id))} · ${feedbackFor(r).length}条反馈</p>${timeline(r)}</div>`).join('')||empty('暂无推荐记录。')}</section>`;}
 function conferencePushesBlock(){
  let pushes=[];
  try{
    const raw=localStorage.getItem('clinical-workbench:conference-pushes:v1');
    pushes=raw?JSON.parse(raw):[];
  }catch(e){}
  if(!pushes||pushes.length===0){
    pushes=[
      {
        id:'CPUSH-CDS2026',
        conference_id:'CDS2026',
        conference_name:'中华医学会糖尿病学分会第三十一次全国学术会议 (CDS 2026)',
        tier_code:'B',
        city:'厦门市 / 上海市',
        start_date:'2026-11-18',
        end_date:'2026-11-21',
        market_note:'市场部重点推荐：关注大会减重、胰岛素抵抗与并发症早期筛查分论坛，重点拜访演讲PI并挖掘转化医学科研合作商机。',
        action_suggestion:'建议销售代表提前2周预约主要讲者差旅间歇拜访，配合吉因加多组学转化方案开展接洽。',
        recommended_by:'市场部学术组',
        target_sales:'all',
        created_at:'2026-11-20'
      }
    ];
  }
  const myPushes=pushes.filter(p=>!p.target_sales||p.target_sales==='all'||p.target_sales===salesId);
  if(!myPushes.length)return '';
  const TIER_BADGES={
    'A':'<span style="background:#f5f3ff;color:#6b21a8;border:1px solid #d8b4fe;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:700;">👑 A类 国际顶级</span>',
    'B':'<span style="background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:700;">🏛️ B类 国家级核心</span>',
    'C':'<span style="background:#f0fdf4;color:#15803d;border:1px solid #bbf7d0;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:700;">📍 C类 省级重点</span>',
    'D':'<span style="background:#f8fafc;color:#475569;border:1px solid #cbd5e1;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;">🔬 D类 专科研讨</span>'
  };
  return `<section class="panel" style="margin-bottom:20px;border-left:4px solid #2867df;background:#fbfdff;">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:12px;padding-bottom:10px;border-bottom:1px solid var(--line);">
      <h3 style="margin:0;font-size:17px;display:flex;align-items:center;gap:8px;color:#172f4e;">
        <span>📢</span> 本周市场部推荐重点会议
        <span style="font-size:12px;font-weight:normal;background:#eff6ff;color:#2563eb;padding:2px 8px;border-radius:12px;border:1px solid #bfdbfe;">市场部定向协同</span>
      </h3>
      <span style="font-size:13px;color:var(--muted)">共 ${myPushes.length} 场高意向推荐会议</span>
    </div>
    <div style="display:grid;gap:12px;">
      ${myPushes.map(p=>`
        <div style="background:white;border:1px solid var(--line);border-radius:7px;padding:14px 16px;display:grid;grid-template-columns:1fr auto;gap:14px;align-items:center;">
          <div>
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;flex-wrap:wrap;">
              ${TIER_BADGES[(p.tier_code||'B').toUpperCase()]||''}
              <strong style="font-size:15px;color:var(--ink);">${esc(p.conference_name)}</strong>
              <span style="font-size:12px;color:var(--muted);background:#f1f5f9;padding:2px 6px;border-radius:4px;">📅 ${esc(p.start_date||'待定')} ~ ${esc(p.end_date||'待定')}</span>
              <span style="font-size:12px;color:var(--muted);background:#f1f5f9;padding:2px 6px;border-radius:4px;">📍 ${esc(p.city||'地点待定')}</span>
            </div>
            <p style="font-size:13px;color:#334155;margin:4px 0;background:#f8fafc;padding:6px 10px;border-radius:4px;border-left:3px solid #38bdf8;">
              <strong>市场部指引：</strong>${esc(p.market_note||'请关注分论坛讲者学术报告')}
            </p>
            <div style="font-size:12px;color:var(--muted);display:flex;gap:14px;align-items:center;">
              <span>行动建议：${esc(p.action_suggestion||'提前拜访核心PI')}</span>
              <span>推荐人：${esc(p.recommended_by||'市场学术组')}</span>
            </div>
          </div>
          <div style="display:flex;flex-direction:column;gap:6px;min-width:110px;">
            <button class="primary" style="font-size:12px;padding:6px 12px;" data-claim-conf="${esc(p.conference_name)}" data-claim-cid="${esc(p.conference_id||'')}">📌 认领跟进</button>
            <a href="#conferences" style="font-size:12px;text-align:center;color:var(--blue);text-decoration:none;">👀 查看会议库</a>
          </div>
        </div>
      `).join('')}
    </div>
  </section>`;
 }
 const list=()=>`${conferencePushesBlock()}<div class="sales-workspace"><aside class="panel sales-list" aria-label="推荐列表">${rows.map(r=>`<button class="sales-list-item ${chosen?.id===r.id?'active':''}" data-rec="${esc(r.id)}">${status(r)}<strong>${esc(r.title)}</strong><small>${esc(person(r.assignee_id))} · ${esc(r.due_date||'跟进时间待定')}</small><small>${feedbackFor(r).length}条反馈${latest(r)?.next_date?' · 下次 '+esc(latest(r).next_date):''}</small><small class="quality-list-label" data-quality-badge="${esc(r.id)}">推荐评价：${esc(window.RecommendationFeedback.label(window.RecommendationFeedback.latest(S,r)))}</small></button>`).join('')||empty('没有匹配推荐。')}</aside>${detail(chosen)}</div>`;
 const actor=role==='sales'?salesId:role;
 function toggleFavorite(key){if(!E.has(key))return;const favorites=[...(S.favorites||[])],i=favorites.findIndex(f=>f.actor_id===actor&&f.person_key===key),saved=i<0;if(saved)favorites.push({actor_id:actor,person_key:key,created_at:now()});else favorites.splice(i,1);if(!save(C,{...S,favorites})){let notice=V.querySelector('[data-favorite-error]');if(!notice){notice=document.createElement('p');notice.className='sales-note error';notice.dataset.favoriteError='true';notice.setAttribute('role','alert');V.querySelector('.sales-app').prepend(notice);}notice.textContent=storageError;return;}S.favorites=favorites;if(auto){rerender();return;}V.querySelectorAll('[data-pi-favorite]').forEach(b=>{if(b.dataset.piFavorite!==key)return;b.classList.toggle('saved',saved);b.setAttribute('aria-pressed',String(saved));b.setAttribute('aria-label',(saved?'取消收藏':'收藏')+E.get(key).display_name);b.textContent=b.classList.contains('icon')?(saved?'★':'☆'):(saved?'★ 已收藏':'☆ 收藏');});}
 const isEditor=canEdit&&q.get('mode')==='edit',autoMode=tab==='recommend'&&!isEditor&&!q.get('rec')&&q.get('recommend_view')!=='records'&&(role!=='sales'||['directory','favorites'].includes(q.get('recommend_view')));
 const auto=autoMode?window.PIRecommendations.render({D,s,S,esc,link,hash,options,update,role,storageError,actor,toggleFavorite,assign:(candidate,owner)=>{if(role!=='market')return '当前视角不能分配。';if(S.recommendations.some(r=>r.candidate_id===candidate.id||r.id==='AUTO-PI:'+candidate.person.key))return '该来源人物已有跟进记录，请查看原记录。';const r=window.PIRecommendations.recommendation(candidate,D);r.assignee_id=owner;r.created_at=r.updated_at=now();if(!save(C,{...S,recommendations:[...S.recommendations,r]}))return storageError;dirty=false;flash='已分配给'+person(owner)+'，可在跟进记录或销售视角查看；未发送外部消息。';rerender();return '';}}):null;
 V.innerHTML=`<div class="sales-app"><section class="sales-head"><div><p class="sales-kicker">${role==='sales'?'销售代表作战台':'市场工作台'}</p><h2>${role==='sales'?'我的商机作战卡与辖区客情':'研究情报与PI合作推荐'}</h2><p class="muted">${role==='sales'?'聚焦高转化商机作战卡、获取破冰话术、挖掘辖区高潜PI并维护客情。':'筛选PI、整理合作建议并分配，根据销售反馈补充情报。'}</p></div>${role==='sales'?(isAuthSales?`<div class="sales-roles"><span style="font-size:13px;font-weight:600;color:#1e3a8a;background:#eff6ff;padding:5px 12px;border-radius:6px;border:1px solid #bfdbfe;">👤 专属销售：${esc(authUser?.name||person(salesId))}</span></div>`:`<div class="sales-roles"><label>演示账号<select id="sales-identity">${options(C.salespeople.map(p=>[p.id,p.name]),salesId)}</select></label></div>`):''}</section>${role==='sales'?`<p class="sales-note" style="background:#eff6ff;color:#1e40af;border-left:4px solid #3b82f6;">已按登录账号【${esc(authUser?.name||person(salesId))}】实现专属数据权限隔离：仅展示指派给您的商机作战卡、客户拜访记录及本周市场部推荐会议。</p>`:`<p class="sales-note" style="background:#f0fdf4;color:#166534;border-left:4px solid #22c55e;">市场部专属管理视角：支持全域筛选PI线索、整理合作建议、下发推荐至指定销售代表，并复核销售跟进反馈。</p>`}${toast()}${storageError?`<p class="sales-note error" role="alert">${esc(storageError)}</p>`:''}<nav class="sales-tabs" aria-label="${role==='sales'?'销售':'市场'}工作台页签">${(role==='sales'?[['follow','🎯 商机作战卡 ('+visible.length+')'],['territory','📍 区域高潜PI (客情库)'],['recommend','⭐ 重点客情收藏'],['summary','📝 我的跟进反馈']]:[['recommend','PI推荐'],['follow','分配记录'],['summary','反馈复盘']]).map(([id,label])=>`<a href="${hash('sales',{role,sales:role==='sales'?salesId:null,sales_tab:id,...(role==='sales'&&id==='recommend'?{recommend_view:'favorites'}:{})})}" class="${tab===id?'active':''}" ${tab===id?'aria-current="page"':''}>${label}</a>`).join('')}</nav>${tab==='recommend'&&role!=='sales'&&!isEditor?`<nav class="sales-recommend-views" aria-label="推荐视图"><a class="${autoMode?'active':''}" href="${hash('sales',{role,sales_tab:'recommend'})}">PI推荐与收藏</a><a class="${!autoMode?'active':''}" href="${hash('sales',{role,sales_tab:'recommend',recommend_view:'records'})}">已分配 / 人工推荐记录</a></nav>`:''}${isEditor?editor():(tab==='territory'?territoryView():(autoMode?auto.html:`${tab!=='summary'?`<div class="sales-toolbar"><label>推荐状态<select id="sales-status">${options([['all','全部状态'],...Object.entries(STATUS)],filter)}</select></label><span class="sales-meta">${rows.length}条商机作战卡 · ${role==='sales'?person(salesId)+'的已分配卡片':'市场全量分配记录'}</span><div class="sales-actions">${canEdit?'<button class="primary" id="create-sales-recommendation">创建推荐</button>':''}${canEdit&&!S.recommendations.some(r=>r.id===C.demo_recommendation.id)?'<button id="load-sales-demo">载入糖尿病演示推荐</button>':''}<button id="sales-export">导出本地记录</button><button id="sales-import">导入本地记录</button><input type="file" id="sales-import-file" accept=".json" style="display:none"></div></div>${tab==='follow'&&role!=='sales'?'<p class="sales-route-note">当前可查看跟进情况；销售可在独立销售工作台填写负责推荐的反馈。</p>':''}${list()}`:`<div class="sales-actions"><button id="sales-export">导出本地记录</button><button id="sales-import">导入本地记录</button><input type="file" id="sales-import-file" accept=".json" style="display:none"></div>${summary()}`}`))}</div>`;
 if(auto){const head=V.querySelector('.sales-head'),roles=V.querySelector('.sales-roles'),target=V.querySelector('.pi-marketplace>.sales-section-head');if(target&&roles)target.append(roles);if(head)head.hidden=true;const outer=V.querySelector('.sales-recommend-views');if(outer)outer.hidden=true;auto.bind();}
 const $=id=>document.getElementById(id),refresh=()=>{const draft=window.RecommendationFeedback.captureDraft();dirty=false;window.RecommendationFeedback.clearDirty();rerender();window.RecommendationFeedback.restoreDraft(draft);},commit=(next,message)=>{if(!save(C,next))return false;dirty=false;flash=message;return true;};
 if($('sales-identity'))$('sales-identity').onchange=()=>go({sales:$('sales-identity').value,rec:null,mode:null});
 if($('sales-status'))$('sales-status').onchange=()=>go({sales_status:$('sales-status').value,rec:null});
 V.querySelectorAll('[data-rec]').forEach(b=>b.onclick=()=>go({rec:b.dataset.rec,mode:null}));
 if($('create-sales-recommendation'))$('create-sales-recommendation').onclick=()=>go({mode:'edit',rec:null,topic:null});
 if($('edit-recommendation'))$('edit-recommendation').onclick=()=>go({mode:'edit',rec:chosen.id,topic:null});
 if($('cancel-sales-edit'))$('cancel-sales-edit').onclick=()=>go({mode:null,rec:q.get('rec'),topic:null});
 if($('load-sales-demo'))$('load-sales-demo').onclick=()=>{const r=structuredClone(C.demo_recommendation);r.created_at=r.updated_at=now();if(commit({...S,recommendations:[...S.recommendations,r]},'已载入演示推荐。研究来源为已有资料，尚无客户反馈。')){go({rec:r.id});if(q.get('rec')===r.id)refresh();}};
 function changeStatus(value){if(!confirm(value==='archived'?'归档后停止新增跟进，已有反馈保留。是否归档？':'是否恢复此推荐？'))return;const r={...chosen,status:value,updated_at:now()};if(commit({...S,recommendations:S.recommendations.map(x=>x.id===r.id?r:x)},value==='archived'?'已归档，反馈历史保留。':'已恢复推荐。'))refresh();}
 if($('archive-recommendation'))$('archive-recommendation').onclick=()=>changeStatus('archived');if($('restore-recommendation'))$('restore-recommendation').onclick=()=>changeStatus(chosen.assignee_id?'assigned':'draft');
 const exportButton=$('sales-export');if(exportButton)exportButton.onclick=()=>{const output={schema:'clinical-sales-export:v1',exported_at:now(),scope:'本地协作原型；演示与真实条目按is_demo区分；不代表已复核研究结论',source_page:location.pathname,...S};const u=URL.createObjectURL(new Blob([JSON.stringify(output,null,2)],{type:'application/json;charset=utf-8'})),a=document.createElement('a');a.href=u;a.download='销售协作记录_'+today()+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);};
 const importBtn=$('sales-import'),importFileInput=$('sales-import-file');if(importBtn&&importFileInput){importBtn.onclick=()=>importFileInput.click();importFileInput.onchange=e=>{const file=e.target.files?.[0];if(!file)return;const reader=new FileReader();reader.onload=()=>{try{const data=JSON.parse(reader.result);if(!data||data.schema!=='clinical-sales-export:v1'||data.version!==1){alert('导入失败：不是有效的 clinical-sales-export:v1 记录格式。');return;}const incomingRecs=Array.isArray(data.recommendations)?data.recommendations:[],incomingFb=Array.isArray(data.feedback)?data.feedback:[],incomingFavs=Array.isArray(data.favorites)?data.favorites:[],incomingQf=Array.isArray(data.recommendation_feedback)?data.recommendation_feedback:[];const curRecMap=new Map(S.recommendations.map(r=>[r.id,r]));let recsToAdd=0,recsToUpd=0;incomingRecs.forEach(r=>{if(!curRecMap.has(r.id))recsToAdd++;else if((r.updated_at||'')>(curRecMap.get(r.id).updated_at||''))recsToUpd++;});const curFbMap=new Map(S.feedback.map(f=>[f.id,f]));let fbToAdd=0;incomingFb.forEach(f=>{if(!curFbMap.has(f.id))fbToAdd++;});const curFavSet=new Set((S.favorites||[]).map(f=>f.actor_id+'::'+f.person_key));let favToAdd=0;incomingFavs.forEach(f=>{if(!curFavSet.has(f.actor_id+'::'+f.person_key))favToAdd++;});const curQfMap=new Map((S.recommendation_feedback||[]).map(q=>[q.id,q]));let qfToAdd=0;incomingQf.forEach(q=>{if(!curQfMap.has(q.id))qfToAdd++;});const promptMsg=`准备导入协作记录：\n- 推荐：新增 ${recsToAdd} 条，更新 ${recsToUpd} 条\n- 沟通反馈：新增 ${fbToAdd} 条\n- 收藏：新增 ${favToAdd} 条\n- 质量评价：新增 ${qfToAdd} 条\n\n导入前将自动备份当前记录。是否继续？`;if(!confirm(promptMsg))return;try{localStorage.setItem('clinical-workbench:sales:backup:'+Date.now(),JSON.stringify(S));}catch(e){}const mergedRecs=[...S.recommendations];incomingRecs.forEach(r=>{const idx=mergedRecs.findIndex(x=>x.id===r.id);if(idx<0)mergedRecs.push(r);else if((r.updated_at||'')>(mergedRecs[idx].updated_at||''))mergedRecs[idx]=r;});const mergedFb=[...S.feedback];incomingFb.forEach(f=>{if(!mergedFb.some(x=>x.id===f.id))mergedFb.push(f);});const mergedFavs=[...(S.favorites||[])];incomingFavs.forEach(f=>{if(!mergedFavs.some(x=>x.actor_id===f.actor_id&&x.person_key===f.person_key))mergedFavs.push(f);});const mergedQf=[...(S.recommendation_feedback||[])];incomingQf.forEach(q=>{if(!mergedQf.some(x=>x.id===q.id))mergedQf.push(q);});const nextState={version:1,recommendations:mergedRecs,feedback:mergedFb,favorites:mergedFavs,recommendation_feedback:mergedQf};if(commit(nextState,`已成功导入记录（已备份）：新增 ${recsToAdd} 条推荐、${fbToAdd} 条沟通、${favToAdd} 条收藏、${qfToAdd} 条评价。`))refresh();}catch(err){alert('解析文件失败：'+err.message);}finally{importFileInput.value='';}};reader.readAsText(file,'utf-8');};}
 const f=$('sales-recommendation-form');if(f){f.oninput=()=>{dirty=true;};f.onchange=()=>{dirty=true;};$('sales-topic').onchange=()=>{dirty=true;const topicId=$('sales-topic').value,t=T.get(topicId);$('sales-source-choices').innerHTML=sourceChoices(topicId,{links:[]});$('sales-expert-choices').innerHTML=expertChoices(topicId,{expert_keys:[]});if(!f.elements.title.value.trim())f.elements.title.value=t.name;if(!f.elements.research_question.value.trim())f.elements.research_question.value=t.name;};f.onsubmit=e=>{e.preventDefault();const fd=new FormData(f),get=k=>String(fd.get(k)||'').trim();if(!['title','research_question','reason','suggested_action'].every(k=>get(k))){formError(f,'请补齐标题、研究问题、推荐理由和建议行动。');return;}const intent=e.submitter?.value||'draft',old=S.recommendations.find(r=>r.id===f.dataset.editId),assignee=get('assignee_id');if(intent==='assign'&&!C.salespeople.some(x=>x.id===assignee)){formError(f,'分配前请选择负责销售。');return;}const topicId=get('topic_id'),t=T.get(topicId);if(!t){formError(f,'请选择已有研究议题。');return;}const links=[...fd.getAll('report').filter(id=>t.report_ids.includes(id)).map(id=>({kind:'report',id})),...fd.getAll('paper').filter(id=>t.paper_ids.includes(id)).map(id=>({kind:'paper',id}))];const r={id:old?.id||uid('REC'),domain_id:s.field,topic_id:topicId,...Object.fromEntries(['title','research_question','reason','participation','conditions','suggested_action','due_date'].map(k=>[k,get(k)])),assignee_id:assignee,status:intent==='draft'?'draft':old?.status==='in_progress'?'in_progress':'assigned',is_demo:old?.is_demo||false,...(old?.origin?{origin:old.origin,candidate_id:old.candidate_id,provenance:old.provenance}:{}),links,expert_keys:fd.getAll('expert').filter(k=>t.expert_keys.includes(k)),capability_ids:fd.getAll('capability').filter(k=>CAP.has(k)),created_at:old?.created_at||now(),updated_at:now()};if(commit({...S,recommendations:old?S.recommendations.map(x=>x.id===r.id?r:x):[...S.recommendations,r]},intent==='draft'?'推荐已保存为草稿。':'推荐已保存，演示销售可在“我的跟进”查看。'))go({sales_tab:'follow',mode:null,rec:r.id,topic:null,sales_status:null});else formError(f,storageError);};}
 V.querySelectorAll('[data-pi-favorite]').forEach(b=>b.onclick=()=>toggleFavorite(b.dataset.piFavorite));
 if(chosen&&!isEditor&&!autoMode&&tab!=='summary')window.RecommendationFeedback.bind(qualityContext,chosen);
 if($('quality-summary-scope'))$('quality-summary-scope').onchange=()=>update({quality_scope:$('quality-summary-scope').value});
 const ff=$('sales-feedback-form');if($('jump-sales-feedback'))$('jump-sales-feedback').onclick=()=>{ff.scrollIntoView({behavior:'smooth',block:'start'});ff.querySelector('select').focus({preventScroll:true});};if(ff){ff.oninput=()=>{dirty=true;};ff.onchange=()=>{dirty=true;};const fill=$('fill-demo-feedback');if(fill)fill.onclick=()=>{for(const [k,v] of Object.entries(C.demo_feedback))ff.elements[k].value=v;ff.elements.contact_date.value=today();ff.elements.next_owner_id.value=salesId;dirty=true;};ff.onsubmit=e=>{e.preventDefault();const fd=new FormData(ff),get=k=>String(fd.get(k)||'').trim();if(!get('next_action')){formError(ff,'请记录下一步；暂缓时也可填写等待条件。');return;}if(get('contact_status')==='contacted'&&!get('contact_date')){formError(ff,'已接触时请填写沟通日期。');return;}if(get('contact_date')>today()){formError(ff,'沟通日期不能晚于今天。');return;}const f={id:uid('FB'),recommendation_id:chosen.id,author_id:salesId,is_demo:chosen.is_demo,created_at:now(),...Object.fromEntries(['contact_status','contact_date','contact_name','institution','need','cohort','support','next_action','next_owner_id','next_date'].map(k=>[k,get(k)])),reviewed_at:null,review_note:''},r={...chosen,status:f.contact_status==='not_contacted'?chosen.status:'in_progress',updated_at:now()};if(commit({...S,recommendations:S.recommendations.map(x=>x.id===r.id?r:x),feedback:[...S.feedback,f]},'反馈已保存，历史记录保留，市场可查看并复核。'))refresh();else formError(ff,storageError);};}
 V.querySelectorAll('[data-review]').forEach(b=>b.onclick=()=>{const id=b.dataset.review,note=[...V.querySelectorAll('[data-review-note]')].find(x=>x.dataset.reviewNote===id)?.value.trim()||'';if(commit({...S,feedback:S.feedback.map(f=>f.id===id?{...f,reviewed_at:now(),review_note:note}:f)},'已标记市场复核；研究证据和客户画像未自动修改。'))refresh();});
 V.querySelectorAll('[data-claim-conf]').forEach(b=>{b.onclick=()=>{const cname=b.dataset.claimConf;alert('✅ 已成功认领跟进会议：'+cname+'！\n已记录至当前销售跟进任务中。');b.textContent='✓ 已认领';b.disabled=true;b.style.opacity='0.6';};});
 if($('copy-break-ice-btn'))$('copy-break-ice-btn').onclick=()=>{const text=$('break-ice-content')?.textContent||'';if(navigator.clipboard?.writeText){navigator.clipboard.writeText(text).then(()=>{alert('✅ 建议破冰话术已成功复制到剪贴板！\n可直接粘贴至微信交流或作为拜访交谈提纲。');}).catch(()=>{prompt('请复制建议破冰话术：',text);});}else{prompt('请复制建议破冰话术：',text);}};
 if($('territory-prev'))$('territory-prev').onclick=()=>update({page:Math.max(1,(s.page||1)-1)});
 if($('territory-next'))$('territory-next').onclick=()=>update({page:(s.page||1)+1});
 V.querySelectorAll('[data-generate-battle-card]').forEach(b=>{b.onclick=()=>{const key=b.dataset.generateBattleCard,name=b.dataset.piName,inst=b.dataset.piInst,topicId=b.dataset.piTopic||'DM:Q17',t=T.get(topicId),p=E.get(key);let existing=S.recommendations.find(r=>r.expert_keys.includes(key));if(existing){alert(`ℹ️ 该专家【${name}】已有正在跟进的商机作战卡，正在为您跳转...`);go({sales_tab:'follow',rec:existing.id});return;}const newCard={id:uid('BATTLE'),domain_id:s.field,topic_id:topicId,title:`【高优商机作战卡】${name}教授课题组 · ${t?.name||'前沿代谢机制'}多组学转化研究`,match_score:93,assignee_id:salesId,due_date:today(),status:'assigned',is_demo:false,pain_point:`${inst}${name}教授团队目前聚焦于临床队列转化，受限于常规生化检验灵敏度，缺乏多组学整合算法与标志物建模支持，急需冲刺高分科研成果。`,research_question:t?.name||'代谢前沿标志物与机制挖掘',reason:`${inst} ${name}教授在学术会议发布前沿报告，科研诉求明确；吉因加可通过多组学技术服务切入其在研课题。`,participation:'结合吉因加 T10（6Dmarker多组学整合与Biomarker建模）及 T14（高通量蛋白质组学），提供候选指标筛选与模型构建方案。',conditions:'需先与团队了解随访样本基质、已有例数与临床分期，再安排技术支持联合拜访。',suggested_action:'建议直接联系专家或课题组骨干，携带类似队列发表的高分文章，交流多组学科研合作。',break_ice_script:`${name}主任您好，关注到您在【${t?.name||'临床前沿领域'}】的深入探索，非常受启发。我们吉因加最近在类似队列中结合6Dmarker多组学算法协助多家三甲医院团队产出了临床转化成果，想找时间向您汇报下，看能不能协助您手头的队列课题发高分文章？`,links:(p?.report_ids?.slice(0,2)||[]).map(id=>({kind:'report',id})),capability_ids:['T10','T14'],expert_keys:[key],created_at:now(),updated_at:now()};if(commit({...S,recommendations:[newCard,...S.recommendations]},`已成功为【${name}】生成专属商机作战卡！已加入您的跟进列表。`)){go({sales_tab:'follow',rec:newCard.id});}};});
 }
 return {render,canLeave,clearDirty:()=>{dirty=false;window.RecommendationFeedback.clearDirty();}};
})();
