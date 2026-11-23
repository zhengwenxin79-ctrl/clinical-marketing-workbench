'use strict';
(()=>{
function adaptData(rawD){
  let approved=[];
  try{
    const q=JSON.parse(localStorage.getItem('demo_review_queue_v4')||'[]');
    if(Array.isArray(q))approved=q.filter(x=>x.review_status==='approved');
  }catch(e){}
  try{
    const ex=JSON.parse(localStorage.getItem('clinical-workbench:approved-conferences:v1')||'[]');
    if(Array.isArray(ex)){
      for(const item of ex){
        if(!approved.some(c=>c.conference_id===item.conference_id))approved.push(item);
      }
    }
  }catch(e){}
  if(!approved.length)return rawD;
  const D=structuredClone(rawD),seen=new Set(D.catalog.entries.map(c=>c.conference_id));
  approved.forEach(item=>{
    const cid=item.conference_id;
    if(!cid||seen.has(cid))return;
    seen.add(cid);
    const tier=item.tier_code||item.tier||'B',isA=tier==='A',sDate=item.start_date||'2026-11-27',eDate=item.end_date||sDate;
    const year=parseInt(sDate.slice(0,4))||2026,name=item.conference_name||cid,abbr=item.abbreviation||name.slice(0,16);
    const resolvedField=item.field_id&&item.field_id!=='diabetes'?item.field_id:/神经|脑卒中|脑血管/.test(name)?'neurology':/呼吸|哮喘|慢阻肺/.test(name)?'respiratory':/风湿|免疫|红斑狼疮/.test(name)?'rheumatology':/心血管|心脏|心衰|房颤/.test(name)?'cardiovascular':/泛血管|血栓|血管/.test(name)?'vascular':'diabetes';
    const tierCode=isA?'international_core':tier==='B'?'national_major':'regional_key';
    const tierLabel=isA?'国际核心会议':tier==='B'?'国家级核心会议':'省级/专科重点';
    D.catalog.entries.unshift({
      conference_id:cid,series_id:abbr.slice(0,8),year,edition_label:null,name_original:name,organizer:'中华医学会/行业学会',
      region:isA?'international':'domestic',country:isA?'国际':'中国',city:item.city||'待定',format:null,
      start_date:sDate,end_date:eDate,local_timezone:'Asia/Shanghai',timezone_basis:'国家标准北京时间',
      official_url:item.official_url||'#',metadata_status:'approved_and_published',academic_report_count:18,
      result_coverage:'agenda_and_topics',abbreviation:abbr,series_name:name,tier_code:tierCode,tier_label:tierLabel,
      tier_status:'verified',tier_basis:item.review_note||'市场部审核评级核定',view_url:item.official_url||'#',
      topic_url:'#topics',coverage_url:'#weekly',domain_id:resolvedField,domain_label:'临床转化',
      classified_report_count:12,topic_count:2,scope_label:'已批准发布入库',date_label:`${sDate} — ${eDate}`,
      location_label:item.city||'待定'
    });
    D.conferences.unshift({
      conference_id:cid,year,abbreviation:abbr,region:isA?'international':'domestic',name_original:name,tier_label:tierLabel,
      view_url:item.official_url||'#',topic_url:'#topics',coverage_url:'#weekly',admission:{status:'main'},
      cohorts:{talks:{total:10,classified:10},posters:{total:8,classified:8},all:{total:18,classified:18}}
    });
    if(D.weekly?.change_log?.events&&!D.weekly.change_log.events.some(e=>e.conference_id===cid)){
      D.weekly.change_log.events.unshift({
        event_id:'EVT-'+cid,conference_id:cid,event_kind:item.change_type||'first_seen',
        summary:`市场部审核批准入库：${name}`,observed_at:item.reviewed_at||new Date().toISOString(),
        source_published_on:sDate,source_url:item.official_url||'#',review_status:'approved',field_id:resolvedField
      });
    }
    const topicId='TOPIC:GEN:'+cid;
    if(!D.topics.some(t=>t.topic_id===topicId)){
      const cleanName=name.replace(/（.*?）|\(.*?\)/g,'');
      D.topics.unshift({
        topic_id:topicId,board_id:'B01',name:`【${abbr.slice(0,8)}新研】${cleanName.slice(0,18)} · 前沿多组学转化`,
        origin:'conference_approved_derived',boundary:item.review_note||'市场部审核入库会议提炼之多组学临床转化切入点',
        report_ids:[],paper_ids:[],supporting_paper_ids:[],biomarker_ids:['BM_CYTOKINES','BM_TYG_INDEX'],expert_keys:[]
      });
      if(D.boards&&D.boards[0]&&!D.boards[0].topic_ids.includes(topicId)){
        D.boards[0].topic_ids.unshift(topicId);
      }
    }
  });
  return D;
}
const D=adaptData(JSON.parse(document.getElementById('data').textContent)),$=id=>document.getElementById(id),V=$('view'),esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const map=(xs,k)=>new Map(xs.map(x=>[x[k],x])),T=map(D.topics,'topic_id'),B=map(D.boards,'board_id'),R=map(D.reports,'report_id'),P=map(D.papers,'paper_id'),E=map(D.experts,'key'),M=map(D.biomarkers,'biomarker_id');
const tag=(x,pending=false)=>`<span class="tag ${pending?'pending':''}">${esc(x)}</span>`,unique=xs=>[...new Set(xs)],empty=x=>`<div class="empty">${esc(x)}</div>`,pct=x=>x===null?'待对应':x.toFixed(2)+'%';
const safe=u=>/^(https?:\/\/|\.\.\/)/.test(u||'')?u:'#',link=(u,t,ext=false)=>`<a href="${esc(safe(u))}" ${ext?'target="_blank" rel="noopener"':''}>${esc(t)}${ext?' ↗':''}</a>`;
function state(){const [rawTab,query]=(location.hash.slice(1)||'topics').split('?'),q=new URLSearchParams(query||'');let tab=rawTab;if(rawTab==='sales'&&['market','manager'].includes(q.get('role'))){tab='market';if(q.get('role')==='manager'&&!q.has('sales_tab'))q.set('sales_tab','summary');}const field=D.navigation.domains.find(x=>x.id===q.get('field'))?.id||'diabetes';return {tab:D.navigation.modules.some(x=>x.id===tab)?tab:'topics',q,field,search:q.get('q')||'',board:q.get('board')||'',sort:q.get('sort')==='papers'?'papers':'conference',format:['all','posters'].includes(q.get('format'))?q.get('format'):'talks',region:['domestic','international'].includes(q.get('region'))?q.get('region'):'all',tier:q.get('tier')||'known',source:q.get('source')||'all',type:q.get('type')||'all',page:Math.max(1,parseInt(q.get('page'))||1),topic:q.get('topic')||''};}
function hash(tab,values={}){values={...values};if(tab==='sales'&&['market','manager'].includes(values.role))tab='market';if(values.role!=='manager')delete values.role;const p=new URLSearchParams();if(state().field!=='diabetes')p.set('field',state().field);for(const [k,v] of Object.entries(values))if(v&&(v!=='all'||['format','weekly_format','pi_focus'].includes(k)))p.set(k,v);return '#'+tab+(p.size?'?'+p.toString():'');}
function update(values){const s=state();for(const [k,v] of Object.entries(values))if(v===null||v===''||(v==='all'&&!['format','weekly_format','pi_focus'].includes(k)))s.q.delete(k);else s.q.set(k,v);location.hash=s.tab+(s.q.size?'?'+s.q.toString():'');}
function options(xs,v){return xs.map(([id,label])=>`<option value="${esc(id)}" ${id===v?'selected':''}>${esc(label)}</option>`).join('');}
function stats(xs){return `<div class="stats">${xs.map(([n,l])=>`<div class="stat"><b>${esc(n)}</b><span>${esc(l)}</span></div>`).join('')}</div>`;}
function conference(ids,s){const eligible=D.conferences.filter(c=>['main','trial'].includes(c.admission.status)&&c.cohorts[s.format].classified>0),chosen=ids.map(id=>R.get(id)).filter(r=>(s.format==='all'||r.cohort===s.format)&&eligible.some(c=>c.conference_id===r.conference_id)),counts=new Map();for(const r of chosen)counts.set(r.conference_id,(counts.get(r.conference_id)||0)+1);
 const avg=region=>{const cs=eligible.filter(c=>c.region===region);return cs.length?cs.reduce((sum,c)=>sum+100*(counts.get(c.conference_id)||0)/c.cohorts[s.format].classified,0)/cs.length:null;};const domestic=avg('domestic'),international=avg('international'),balanced=domestic!==null&&international!==null?(domestic+international)/2:null;
 return {reports:chosen.filter(r=>s.region==='all'||D.conferences.find(c=>c.conference_id===r.conference_id).region===s.region),share:s.region==='all'?balanced:s.region==='domestic'?domestic:international,domestic,international,counts};}
function measures(t,s){const conf=conference(t.report_ids,s);if(t.origin==='paper_directory_extension')conf.share=null;return {...t,conference:conf,papers:t.paper_ids.map(id=>P.get(id)),markers:t.biomarker_ids.map(id=>M.get(id))};}
function showDialog(title,body){$('detail-title').textContent=title;$('detail-body').innerHTML=body;if(!$('detail').open)$('detail').showModal();}
function knownExperts(keys){return keys.map(k=>E.get(k)).filter(x=>x&&x.tier_code!=='undetermined');}
function topicDetail(id,s){const t=T.get(id);if(!t)return;const m=measures(t,s),leaders=knownExperts(t.expert_keys),speakerCount=t.expert_keys.filter(k=>E.get(k)?.source_kind==='conference').length;
 const u=getUser();
 const reports=m.conference.reports.slice(0,18),papers=m.papers;showDialog(t.name,`${u.role==='market'?`<div class="sales-topic-action"><a href="${hash('sales',{role:'market',sales_tab:'recommend',mode:'edit',topic:id})}">整理为销售推荐</a><span>使用当前议题的已有资料准备交流</span></div>`:''}<div class="detail-counts"><a data-count-link="conference" href="${hash('conferences',{topic:id,format:s.format,region:s.region,sort:s.sort})}" title="查看当前议题的全部匹配会议报告">会议报告 ${m.conference.reports.length}条 <small aria-hidden="true">→</small></a><a data-count-link="papers" href="${hash('papers',{topic:id,format:s.format,region:s.region,sort:s.sort})}" title="查看当前议题的主池论文">主池论文 ${papers.length}篇 <small aria-hidden="true">→</small></a>${m.markers.length?`<button type="button" data-jump-markers>指标方向 ${m.markers.length}项 <small aria-hidden="true">↓</small></button>`:'<span class="count-disabled" aria-disabled="true" title="当前议题暂无关联指标">指标方向 0项</span>'}<a href="${hash('conferences')}" style="margin-left:auto;color:#1e40af;font-weight:600;display:inline-flex;align-items:center;gap:4px;" title="查看最新会议动态">📅 回到最新会议动态 →</a></div><div class="evidence-grid"><div><h3>会议动向</h3>${reports.length?reports.map(r=>`<article class="source-row"><div class="meta">${esc(r.conference_id)} · ${esc(r.report_format)} · ${esc(r.code)}</div><h3>${link(r.detail_url,r.title)}</h3><p class="meta">${r.speaker_keys.map(k=>esc(E.get(k)?.display_name||'')).join('、')||'讲者待核'}</p></article>`).join(''):empty(t.origin==='paper_directory_extension'?'论文补充议题，会议对应尚未建立。':'当前报告形式范围内没有归入本议题的报告。')}<h3 class="section">论文进展</h3>${papers.length?papers.map(p=>`<article class="source-row"><div class="meta">${esc(p.journal)} · ${esc(p.publication_date)}</div><h3>${link(p.detail_url,p.title)}</h3><p>${esc(p.finding||'具体结果待整理')}</p></article>`).join(''):empty('主池尚无已对应论文，不能据此判断领域没有研究。')}<h3 class="section" id="topic-biomarkers" tabindex="-1">Biomarker线索</h3>${m.markers.length?`<div class="links">${m.markers.map(b=>link(b.detail_url,b.name)).join('')}</div>`:empty('当前证据尚未关联指标；可在Biomarker视图继续按用途查看。')}<h3 class="section">吉因加参与环节</h3><p class="reading-note">按具体指标的样本、用途和检测方法查看已整理的参与候选；不从整个研究议题直接推定检测产品。</p><div class="links">${link('../标志物视图/index.html#translation','查看指标用途与能力适配候选')}</div><details><summary>原始对应与分类依据</summary><p>${esc(t.boundary)}</p>${D.taxonomy.mappings.filter(x=>x.topic_id===id).map(x=>`<p>${esc(x.source_kind)}：${esc(x.source_id)} · ${esc(x.basis)}</p>`).join('')}<p>会议与论文数量分列，不相加为独立研究数。当前主池160篇，另有${t.supporting_paper_ids.length}篇已有背景/补充来源。</p><p>口头/海报切换只改变会议数量；论文使用原论文窗口与纳入规则。</p></details></div><aside class="aside"><h3>相关专家与团队</h3><p class="reading-note">学术角色与论文署名分别记录。</p>${leaders.slice(0,10).map(p=>`<div class="person-mini"><a href="${hash('experts',{person:p.key})}"><b>${esc(p.display_name)}</b></a><small>${esc(p.institution_source)}</small>${tag(p.tier_label)}<small>${esc(p.source_label)} · ${p.source_kind==='paper'?'署名参与，PI待核':'讲者身份'}</small></div>`).join('')||empty('当前相关人物的角色仍待核。')}<div class="links"><a href="${hash('experts',{topic:id,tier:'all'})}">查看全部相关人物 →</a></div><p class="reading-note">${speakerCount}条讲者来源身份；跨来源同名不自动合并。角色不参与热点计分。</p></aside></div>`);const jump=$('detail-body').querySelector('[data-jump-markers]');if(jump)jump.onclick=()=>{const target=$('topic-biomarkers');target.scrollIntoView({block:'start',behavior:'smooth'});target.focus({preventScroll:true});};}
function peopleCard(p){return `<article class="card" data-person="${esc(p.key)}"><h3><a href="${hash('experts',{person:p.key})}">${esc(p.display_name)}</a></h3><p class="institution">${esc(p.institution_source)}</p>${tag(p.tier_label,p.tier_code==='undetermined')}${tag(p.source_kind==='paper'?(p.identity_status==='name_and_institution_checked'?'已核署名参与':'作者身份待核'):'会议讲者',p.source_kind==='paper'&&p.identity_status!=='name_and_institution_checked')}<p>${esc(p.role_scope)}</p><p class="muted">${p.report_ids.length}条讲题 · ${p.paper_ids.length}篇关联论文</p><div class="links"><a href="${hash('experts',{person:p.key})}">研究方向与原始依据 →</a></div></article>`;}
function expertDetail(key){const p=E.get(key);if(!p)return;showDialog(p.display_name,`${tag(p.tier_label,p.tier_code==='undetermined')}${tag(p.source_label)}<p>${esc(p.institution_source)}</p><h3 class="section">学术角色与身份依据</h3><p>${esc(p.role_basis)}</p><p>${esc(p.role_scope)}</p><p class="reading-note">${esc(p.tenure_status)}；${esc(p.pi_status)}</p><div class="links">${link(p.detail_url,'来源人物记录')}${p.source_url?link(p.source_url,'原始身份依据',true):''}</div><h3 class="section">正在讨论的讲题</h3>${p.report_ids.slice(0,30).map(id=>{const r=R.get(id);return `<div class="source-row"><h3>${link(r.detail_url,r.title)}</h3><div class="meta">${esc(r.conference_id)} · ${esc(r.code)} · ${esc(r.date)}</div></div>`;}).join('')||empty('当前来源身份未关联会议报告。')}<h3 class="section">关联论文</h3>${p.paper_ids.map(id=>{const x=P.get(id);return `<div class="source-row"><h3>${link(x.detail_url,x.title)}</h3><p class="meta">${esc(x.journal)} · ${esc(x.publication_date)} · ${esc(p.pi_status)}</p></div>`;}).join('')||empty('当前来源身份尚未建立明确论文关联。')}<h3 class="section">相关研究议题</h3><div class="links">${p.topic_ids.map(id=>`<a href="${hash('topics',{detail:id,board:T.get(id).board_id})}">${esc(T.get(id).name)}</a>`).join('')}</div><details><summary>身份与资料缺口</summary><p>${esc(p.evidence_gaps||'角色领域及当前任期仍按原来源记录。')}</p><p>按来源身份保存；不会因为名字相同就把会议讲者、论文作者合成同一位PI。</p></details>`);}
function conferenceDetail(confId,s){const e=D.catalog.entries.find(x=>x.conference_id===confId)||D.conferences.find(x=>x.conference_id===confId);if(!e)return;const name=e.name_original||e.conference_id,linkedTopics=D.topics.filter(t=>t.topic_id.includes(confId)||(e.topic_ids&&e.topic_ids.includes(t.topic_id))),u=getUser();showDialog(name,`<div style="background:#f8fafc;padding:12px 16px;border-radius:6px;border-left:4px solid #2563eb;margin-bottom:14px;"><div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap;">${tag(e.tier_label||'学术会议')}<span style="font-size:13px;color:#1e40af;font-weight:600;">会议编码：${esc(e.conference_id)}</span><span style="font-size:13px;color:var(--muted);">📅 会期：${esc(e.date_label||e.start_date||'近期排期')}</span><span style="font-size:13px;color:var(--muted);">📍 地点：${esc(e.location_label||e.city||'待定')}</span></div><p style="margin:4px 0 6px;font-size:13.5px;color:#334155;"><strong>评级与学术依据：</strong>${esc(e.tier_basis||'市场部审核评级核定入库')}</p>${e.official_url&&e.official_url!=='#'?`<p style="margin:4px 0 0;font-size:12.5px;">🔗 ${link(e.official_url,'访问官方会议主页与日程',true)}</p>`:''}</div>${u.role==='market'?`<div style="margin-bottom:14px;display:flex;gap:10px;"><a href="会议审核入库.html" style="background:#eff6ff;color:#1e40af;border:1px solid #bfdbfe;padding:6px 14px;border-radius:6px;font-size:13px;font-weight:600;text-decoration:none;">🏛️ 前往审核台管理该会议</a></div>`:''}<h3 class="section">会内关联研究议题与商业热点 (${linkedTopics.length})</h3><div style="display:grid;gap:8px;margin-bottom:16px;">${linkedTopics.length?linkedTopics.map(t=>`<article class="source-row" style="background:#fff;"><h3><a href="${hash('topics',{detail:t.topic_id})}">${esc(t.name)} →</a></h3><p class="meta">${esc(t.boundary||'会议前沿热点')}</p><div class="links"><a href="${hash('topics',{detail:t.topic_id})}">查看该热点转化方案与学术证据</a></div></article>`).join(''):`<div class="empty">当前会议已完成元数据入库，详细分论坛报告日程解析中。<br><small style="color:var(--muted);">可在【领域热点】查看该会议衍生的前沿多组学转化热点。</small></div>`}</div><h3 class="section">吉因加学术营销切入建议</h3><div style="background:#f0fdf4;border:1px solid #bbf7d0;border-left:4px solid #16a34a;padding:12px 16px;border-radius:6px;"><p style="margin:0 0 6px;font-size:13.5px;color:#14532d;"><strong>🎯 商业化跟进指引：</strong>建议针对该会议重点分论坛的讲者与中青年骨干PI，结合吉因加 T10（6Dmarker多组学模型）与 T14（高通量蛋白质组学）开展差旅拜访与课题合作接洽。</p><div class="links" style="margin-top:6px;"><a href="${hash('sales')}">进入销售工作台查看商机作战卡 →</a></div></div>`);}
function topicsView(s){const boardRows=D.boards.map(b=>{const ts=b.topic_ids.map(id=>measures(T.get(id),s)),ids=unique(ts.flatMap(t=>t.report_ids)),m=conference(ids,s);return {...b,meeting:m,pc:ts.reduce((n,t)=>n+t.paper_ids.length,0)};}).sort((a,b)=>s.sort==='papers'?b.pc-a.pc||(b.meeting.share||0)-(a.meeting.share||0):(b.meeting.share||0)-(a.meeting.share||0)||b.pc-a.pc);
 const needle=s.search.toLowerCase(),matches=t=>!needle||[t.name,...t.markers.map(b=>b.name),...t.expert_keys.map(k=>{const p=E.get(k);return p?[p.display_name,p.institution_source,p.role_scope].join(' '):'';})].join(' ').toLowerCase().includes(needle);const board=boardRows.find(b=>b.board_id===s.board)||boardRows.find(b=>b.topic_ids.some(id=>matches(measures(T.get(id),s))))||boardRows[0];let ts=board.topic_ids.map(id=>measures(T.get(id),s)).filter(matches);ts.sort((a,b)=>s.sort==='papers'?b.paper_ids.length-a.paper_ids.length||(b.conference.share||0)-(a.conference.share||0):(b.conference.share||0)-(a.conference.share||0)||b.paper_ids.length-a.paper_ids.length);
 const u=getUser();
 const confBanner=`<section class="panel" style="margin-bottom:18px;background:linear-gradient(135deg,#eff6ff 0%,#dbeafe 100%);border:1px solid #bfdbfe;border-left:4px solid #2563eb;padding:12px 18px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;"><div><span style="font-weight:700;color:#1e40af;font-size:15px;">📅 本周最新会议动态与热点看板</span><span style="color:#475569;font-size:13px;margin-left:10px;">掌握最新学术会议日程变动、今日新收录与本周热点议题</span></div><div style="display:flex;gap:8px;align-items:center;"><a href="${hash('conferences')}" style="background:#2563eb;color:#fff;font-weight:600;padding:6px 14px;border-radius:6px;font-size:13px;text-decoration:none;">回到最新会议动态 →</a>${u.role==='market'?'<a href="会议审核入库.html" style="background:#fff;color:#1e40af;border:1px solid #bfdbfe;font-weight:600;padding:6px 12px;border-radius:6px;font-size:13px;text-decoration:none;">增量审核</a>':''}</div></section>`;
 V.innerHTML=confBanner+stats([[12,'统一研究板块'],[66,'领域工作议题'],[160,'已归类主池论文 · 篇'],[D.summary.biomarkers,'已有Biomarker / 方向']])+`<section class="panel toolbar"><label>板块与议题排序<select id="sort">${options([['conference','按会议关注'],['papers','按论文进展数量']],s.sort)}</select></label><label>会议报告形式<select id="format">${options([['talks','口头报告'],['posters','海报展示'],['all','全部形式']],s.format)}</select></label><label>会议关注视角<select id="region">${options([['all','国内外平衡概览'],['domestic','国内会议'],['international','国际会议']],s.region)}</select></label><span class="toolbar-note">会议与论文并排查看，分别排序；不合成总分。</span></section><div class="topic-layout"><aside class="panel boards" aria-label="研究板块">${boardRows.map(b=>`<button class="board-link ${b.board_id===board.board_id?'active':''}" data-board="${esc(b.board_id)}"><span>${esc(b.name)}</span><small>会议 ${pct(b.meeting.share)} · 论文 ${b.pc}篇</small></button>`).join('')}</aside><section class="panel"><div class="list-head"><div><h2>${esc(board.name)}</h2><p>从同一研究问题查看会议讨论、论文证据、指标与人物。</p></div><span class="count-label">${ts.length}个议题</span></div><div class="topic-columns"><span>研究议题</span><span>会议关注</span><span>论文进展</span><span>指标线索</span></div>${ts.map(t=>`<div class="topic-row" data-topic="${esc(t.topic_id)}"><div><a class="topic-name" href="${hash('topics',{...Object.fromEntries(s.q),board:board.board_id,detail:t.topic_id})}">${esc(t.name)}</a>${t.origin==='paper_directory_extension'?'<br>'+tag('论文补充议题',true):t.origin==='conference_approved_derived'?'<br>'+tag('🔥 最新会议衍生热点',true):''}</div><div data-label="会议关注"><b>${t.origin==='paper_directory_extension'?'待对应':t.conference.reports.length+'条'}</b><small class="muted"> ${t.origin==='paper_directory_extension'?'':pct(t.conference.share)}</small><span class="mini-track">${t.origin!=='paper_directory_extension'?`<i style="width:${Math.min(100,t.conference.share||0)}%"></i>`:''}</span></div><div data-label="论文进展"><b>${t.paper_ids.length}</b>篇</div><div data-label="指标线索"><b>${t.markers.length}</b>项</div></div>`).join('')||empty('当前板块没有匹配议题。')}</section></div><p class="reading-note">会议数量来自当前所选报告形式的既有分类；论文为核心四刊160篇主池。8个论文补充议题保留独立位置，不强行找会议对应。<a href="../标志物视图/index.html">进入本领域Biomarker视图 →</a></p>`;
 for(const id of ['sort','format','region'])$(id).onchange=()=>update({[id]:$(id).value,detail:null});V.querySelectorAll('[data-board]').forEach(b=>b.onclick=()=>update({board:b.dataset.board,detail:null}));}
function topicReportView(s){const t=T.get(s.topic);if(!t){V.innerHTML=`<section class="panel">${empty('当前议题不存在，可重新选择。')}<a href="${hash('conferences')}">查看会议目录 →</a></section>`;return;}
 const scope=measures(t,s),weekly=s.q.get('scope')==='weekly'?window.WeeklyMeetings.compute(D,{...s,search:''}):null,weeklyIds=weekly?new Set(weekly.reports.map(r=>r.report_id)):null,baseReports=scope.conference.reports.filter(r=>!weeklyIds||weeklyIds.has(r.report_id)),needle=s.search.toLowerCase(),meeting=s.q.get('meeting')||'all',rows=baseReports.filter(r=>(meeting==='all'||r.conference_id===meeting)&&(!needle||[r.title,r.code,r.conference_id,...r.speaker_keys.map(k=>E.get(k)?.display_name||'')].join(' ').toLowerCase().includes(needle))),pages=Math.max(1,Math.ceil(rows.length/20)),page=Math.min(s.page,pages);
 V.innerHTML=`<section class="panel topic-scope"><h2>${esc(t.name)}</h2><p><b>${baseReports.length}条会议报告</b> · ${weekly?"本周 "+weekly.start+" — "+weekly.end:"当前议题"} · 当前报告形式/地域范围</p><div class="links">${weekly?`<a href="${hash('conferences',{week:weekly.start,weekly_tab:weekly.tab,weekly_format:weekly.format,weekly_meeting:weekly.focus})}">← 返回本周会议动态</a>`:`<a href="${hash('topics',{board:t.board_id,detail:t.topic_id,format:s.format,region:s.region,sort:s.sort})}">← 返回议题</a>`}<a href="${hash('conferences')}">清除筛选，查看全部会议</a></div></section><section class="panel section"><div class="toolbar"><label>报告形式<select id="report-format">${options([['talks','口头报告'],['posters','海报展示'],['all','全部形式']],s.format)}</select></label><label>会议地域<select id="report-region">${options([['all','国内与国际'],['domestic','国内会议'],['international','国际会议']],s.region)}</select></label><label>会议<select id="report-meeting">${options([['all','全部已接入会议'],...(weekly?weekly.eligible:D.conferences).map(c=>[c.conference_id,c.conference_id])],meeting)}</select></label><span class="toolbar-note">${rows.length}条匹配报告 · 第${page} / ${pages}页</span></div>${rows.slice((page-1)*20,page*20).map(r=>`<article class="source-row" data-report-id="${esc(r.report_id)}"><div class="meta">${esc(r.conference_id)} · ${esc(r.report_format)} · ${esc(r.code)} · ${esc(r.date||'日期待核')}</div><h3>${link(r.detail_url,r.title)}</h3><p class="meta">${r.speaker_keys.map(k=>esc(E.get(k)?.display_name||'')).join('、')||'讲者待核'}</p><div class="links">${link(r.detail_url,'报告详情与来源')}</div></article>`).join('')||empty(t.origin==='paper_directory_extension'?'该议题的会议对应尚未建立。':'当前筛选范围没有匹配报告。')}<div class="pager"><button id="prev" ${page===1?'disabled':''}>上一页</button><span>${page} / ${pages}</span><button id="next" ${page===pages?'disabled':''}>下一页</button></div></section>`;
 for(const [id,key] of [['report-format','format'],['report-region','region'],['report-meeting','meeting']])$(id).onchange=()=>update({[key]:$(id).value,...(weekly&&key==='format'?{weekly_format:$(id).value}:{}),page:null});$('prev').onclick=()=>update({page:page-1});$('next').onclick=()=>update({page:page+1});}
function conferencesView(s){if(s.topic){topicReportView(s);return;}const weekly=window.WeeklyMeetings.render({D,s,esc,tag,link,hash,options,update});const tiers=D.catalog.tiers,entries=D.catalog.entries.filter(x=>{const matchesDomain=(s.field==='diabetes')?(!x.domain_id||x.domain_id==='diabetes'):(x.domain_id===s.field);return matchesDomain&&(!s.search||[x.name_original,x.abbreviation,x.city,x.year].join(' ').toLowerCase().includes(s.search.toLowerCase()));});
 V.innerHTML=weekly.html+'<h2 class="weekly-library-label">全部会议目录</h2>'+stats([[D.catalog.entries.length,'已接入会议届次'],...['international_core','national_major','regional_key'].map(id=>[D.catalog.entries.filter(c=>c.tier_code===id).length,D.catalog.tiers.find(t=>t.id===id).label])])+`<p class="reading-note">会议目录按学术覆盖范围分类；举办国家/城市单独记录。进入具体会议查看其议题与讲者。</p>${tiers.map(t=>`<section class="catalog-tier"><h2>${esc(t.label)}</h2>${entries.filter(e=>e.tier_code===t.id).map(e=>`<article class="conference-card"><div class="year">${e.year}<small class="count-label" style="display:block">${esc(e.abbreviation)}</small></div><div><h3><a href="${hash('conferences',{conf:e.conference_id})}" style="text-decoration:none;color:inherit;">${esc(e.name_original)}</a></h3><p>${esc(e.date_label)} · ${esc(e.location_label)}</p>${tag(e.tier_label)}<p class="muted">${e.academic_report_count}条入库报告 · ${e.topic_count}个来源议题</p></div><div class="links"><a href="${hash('conferences',{conf:e.conference_id})}" style="font-weight:600;color:#2563eb;">进入会议 (详情) →</a>${link(e.topic_url,'会内议题')}${e.official_url&&e.official_url!=='#'?link(e.official_url,'官方来源',true):''}</div></article>`).join('')||empty(t.id==='regional_key'?'区域重点会议保留框架，尚未接入资料。':'当前搜索范围暂无已接入会议。')}</section>`).join('')}<div class="links">${link('../会议总入口/index.html','完整会议目录')}${link('../会议总入口/index.html#hotspots','仅看跨会议议题分布')}</div>`;weekly.bind();}
function papersView(s){const needle=s.search.toLowerCase(),rows=D.papers.filter(p=>(!s.topic||(p.topic_id===s.topic&&p.primary_counted))&&(s.type==='all'||p.type===s.type)&&(s.source==='all'||p.source_tier===s.source)&&(!needle||[p.title,p.journal,...p.authors].join(' ').toLowerCase().includes(needle)));const pages=Math.max(1,Math.ceil(rows.length/15)),page=Math.min(s.page,pages);
 const topic=T.get(s.topic),scopeHeader=s.topic?`<section class="panel topic-scope"><h2>${esc(topic?.name||s.topic)}</h2><p><b>${topic?.paper_ids.length||0}篇主池论文</b> · 仅当前议题，背景与补充来源另存</p><div class="links"><a href="${hash('topics',{detail:topic?.topic_id,board:topic?.board_id,format:s.format,region:s.region,sort:s.sort})}">← 返回议题</a><a href="${hash('papers')}">清除筛选，查看全部论文</a></div></section>`:stats([[618,'已存文章记录'],[506,'原窗口内记录'],[160,'领域议题主池'],[10,'已完成Biomarker摘要复核']]);
 V.innerHTML=scopeHeader+`<section class="panel ${s.topic?'section':''}"><div class="toolbar"><label>文献类型<select id="paper-type">${options([['all','全部类型'],['research','研究类'],['review','综述'],['conference','会议类'],['other','其他 / 待确认']],s.type)}</select></label><label>来源范围<select id="paper-source">${options([['all','全部已存来源'],['core','国际核心四刊'],['supplement','主题补漏'],['domestic_partial','中文目录补充']],s.source)}</select></label><span class="toolbar-note">${rows.length}条匹配记录；${s.topic?'当前议题的主池论文。':'含窗口外及待核日期，领域主榜另按原规则纳入。'}</span></div>${rows.slice((page-1)*15,page*15).map(p=>`<article class="source-row" data-paper-id="${esc(p.paper_id)}"><div class="meta">${esc(p.journal)} · ${esc(p.publication_date)} ${tag(p.type_label)}${p.primary_counted?tag('主池议题已归类'):''}</div><h3>${link(p.detail_url,p.title)}</h3><p class="meta">${esc(p.authors.slice(0,3).join('、'))}${p.authors.length>3?'等':''}</p>${p.finding?`<p>${esc(p.finding)}</p>`:''}<div class="links">${link(p.detail_url,'文章与团队详情')}${link(p.source_url,'原始来源',true)}</div></article>`).join('')||empty('没有匹配文章。')}<div class="pager"><button id="prev" ${page===1?'disabled':''}>上一页</button><span>${page} / ${pages}</span><button id="next" ${page===pages?'disabled':''}>下一页</button></div></section><div class="links">${link('../论文视图/index.html#papers?source=all&type=all','完整文章池与来源筛选')}${link('../论文视图/index.html#overview','论文来源内议题分类')}</div>`;
 $('paper-type').onchange=()=>update({type:$('paper-type').value,page:null});$('paper-source').onchange=()=>update({source:$('paper-source').value,page:null});$('prev').onclick=()=>update({page:page-1});$('next').onclick=()=>update({page:page+1});}
function expertsView(s){const levels=['international','national','regional','undetermined'],needle=s.search.toLowerCase();const rows=D.experts.filter(p=>(s.tier==='all'||s.tier==='known'&&p.tier_code!=='undetermined'||p.tier_code===s.tier)&&(s.source==='all'||p.source_kind===s.source)&&(!s.topic||p.topic_ids.includes(s.topic))&&(!needle||[p.display_name,p.institution_source,p.role_scope,...p.topic_ids.map(id=>T.get(id)?.name||'')].join(' ').toLowerCase().includes(needle))).sort((a,b)=>levels.indexOf(a.tier_code)-levels.indexOf(b.tier_code)||b.report_ids.length-a.report_ids.length||a.display_name.localeCompare(b.display_name));const pages=Math.max(1,Math.ceil(rows.length/15)),page=Math.min(s.page,pages);
 V.innerHTML=`<section class="panel"><div class="toolbar"><label>学术角色<select id="expert-tier">${options([['known','已有角色依据'],['all','全部角色含待定'],['international','国际'],['national','全国'],['regional','区域 / 专科'],['undetermined','待定']],s.tier)}</select></label><label>人物来源<select id="expert-source">${options([['all','全部来源身份'],['conference','会议讲者'],['paper','论文参与线索']],s.source)}</select></label><span class="toolbar-note">${rows.length}条匹配来源身份；跨来源未自动合并，不当作全领域PI人数。</span></div>${s.topic?`<p>当前议题：${esc(T.get(s.topic)?.name||s.topic)} <a href="${hash('experts')}">清除议题筛选</a></p>`:''}<p class="reading-note">学术带头人角色、论文署名和课题PI分别记录。角色不参与热点加分；待定表示缺证，不表示学术水平低。</p></section><div class="grid">${rows.slice((page-1)*15,page*15).map(peopleCard).join('')||empty('没有匹配人物。可切换全部角色或调整关键词。')}</div><div class="pager"><button id="prev" ${page===1?'disabled':''}>上一页</button><span>${page} / ${pages}</span><button id="next" ${page===pages?'disabled':''}>下一页</button></div>`;
 $('expert-tier').onchange=()=>update({tier:$('expert-tier').value,page:null});$('expert-source').onchange=()=>update({source:$('expert-source').value,page:null});$('prev').onclick=()=>update({page:page-1});$('next').onclick=()=>update({page:page+1});}
function method(){showDialog('框架、分类与来源',`<pre class="architecture">研究领域 → 领域热点（研究议题 / Biomarker）\n资料入口 → 会议库 / 论文库\n人物关系 → 专家与团队，关联讲题和论文\n研究参与 → 从具体议题 / 指标用途查看公司能力候选</pre><h3 class="section">同一研究问题的两条证据线</h3><p>${esc(D.method.mapping)}</p><p>${esc(D.method.paper)}</p><p>会议关注沿用各会议同类已归类报告占比；国内与国际分别平均，平衡概览为两侧各50%。只用于会议这一栏，不与论文篇数或专家角色相加。</p><h3 class="section">信息与人物的关系</h3><p>${esc(D.method.people)}</p><p>Biomarker通过已有报告/论文证据关联主题，属于领域内部的研究对象；未取得准确分类的材料保留待归类。同名指标、同队列或同一研究关系须另外核实。</p><h3 class="section">采集与开发分工</h3><p>${esc(D.method.roles)}</p><p>当前只用CDS/ADA及已有论文、指标、身份记录；其它五领域只搭结构，不生成虚构内容。</p><div class="links"><a href="../框架配置/糖尿病统一议题映射.json">统一议题映射</a><a href="../框架配置/WorkBuddy资料入库约定.md">WorkBuddy资料交付约定</a><a href="使用说明.md">页面结构与运行方法</a></div>`);}
function getUser(){
  try{
    const raw=localStorage.getItem('clinical-auth:current-user');
    if(raw){const u=JSON.parse(raw);if(u&&u.role)return u;}
  }catch(e){}
  const h=location.hash;
  if(h.includes('sales=')){
    const m=h.match(/sales=([^&]+)/);
    const sid=m?m[1]:'demo-sales-a';
    const name=sid.includes('b')?'销售代表 - 陈丽 (华南区)':'销售代表 - 张强 (华北区)';
    return {id:sid,name,role:'sales'};
  }
  if(h.startsWith('#sales')){
    return {id:'demo-sales-a',name:'销售代表 - 张强 (华北区)',role:'sales'};
  }
  return {id:'market_admin',name:'市场部专员',role:'market'};
}
function render(){
  const user=getUser();
  if(window.SalesCollaboration&&!window.SalesCollaboration.canLeave()){
    history.replaceState(null,'',document.body.dataset.renderedHash||'#topics');
    $('domain').value=state().field;
    return;
  }
  let s=state();

  // 严格角色隔离与重定向拦截
  if(user.role==='sales'&&s.tab==='market'){
    location.hash='#sales?sales='+user.id;
    return;
  }
  if(user.role==='market'&&s.tab==='sales'){
    location.hash='#market';
    return;
  }

  const domain=D.navigation.domains.find(x=>x.id===s.field)||D.navigation.domains[0];
  const module=D.navigation.modules.find(x=>x.id===s.tab)||D.navigation.modules[0];
  $('domain').value=s.field;
  if(document.activeElement!==$('q'))$('q').value=s.search;

  // 根据当前角色严格过滤主导航：销售代表看不到市场工作台，市场人员看不到销售个人台
  const visibleModules=D.navigation.modules.filter(m=>{
    if(user.role==='sales')return m.id!=='market';
    return m.id!=='sales';
  });

  let navHtml=visibleModules.map(x=>`<a class="${x.id===s.tab?'active':''}" ${x.id===s.tab?'aria-current="page"':''} href="${hash(x.id,user.role==='sales'?{sales:user.id}:{})}">${esc(x.label)}</a>`).join('');
  if(user.role==='market'){
    navHtml+=`<a href="会议审核入库.html" style="color:#d97706;font-weight:600;" title="市场部专属会议审核入库通道">🏛️ 会议审核入库</a>`;
  }
  $('primary-nav').innerHTML=navHtml;

  // 顶部用户状态条渲染
  const userBar=$('user-bar');
  if(userBar){
    if(user.role==='sales'){
      userBar.innerHTML=`<span style="background:#1e3a8a;color:#93c5fd;border:1px solid #3b82f6;padding:4px 12px;border-radius:14px;font-size:12px;font-weight:600;">👤 ${esc(user.name)}</span><a href="../../登录工作台.html" style="color:#cbd5e1;font-size:12px;text-decoration:none;">[切换账号]</a>`;
    }else{
      userBar.innerHTML=`<span style="background:#064e3b;color:#6ee7b7;border:1px solid #10b981;padding:4px 12px;border-radius:14px;font-size:12px;font-weight:600;">🏛️ 市场部专员</span><a href="../../登录工作台.html" style="color:#cbd5e1;font-size:12px;text-decoration:none;">[切换账号]</a>`;
    }
  }

  $('eyebrow').textContent=domain.name+' / '+module.label;$('title').textContent=domain.name+module.label;$('subtitle').textContent=module.question;$('domain-tabs').innerHTML=`<a id="topic-tab" class="${s.tab==='topics'?'active':''}" href="${hash('topics')}">研究议题</a><a href="${hash('conferences')}" style="color:#2563eb;font-weight:600;">📅 回到最新会议动态</a><a href="../标志物视图/index.html">Biomarker</a>`;$('domain-tabs').hidden=s.tab!=='topics';
 if(s.field!=='diabetes'&&window.DomainFrameworks&&window.DomainFrameworks.getDomain(s.field)){
  if(s.tab==='topics')V.innerHTML=window.DomainFrameworks.renderDomainDashboard(s.field,s,esc,hash);
  else if(s.tab==='conferences')V.innerHTML=window.DomainFrameworks.renderDomainConferences(s.field,esc,hash,D);
  else if(s.tab==='papers')V.innerHTML=window.DomainFrameworks.renderDomainPapers(s.field,esc);
  else if(['market','sales'].includes(s.tab))window.SalesCollaboration.render({D,s,V,esc,tag,link,hash,options,update,rerender:render});
  else V.innerHTML=`<section class="panel" style="margin-bottom:20px;"><h2>${esc(domain.name)} · 专家与团队画像</h2><p class="reading-note">本领域学术带头人与重点临床团队画像，支持市场专员在线索中指定并跟进。</p></section>`+window.DomainFrameworks.renderDomainDashboard(s.field,s,esc,hash);
 }
 else if(!domain.connected)V.innerHTML=`<section class="panel">${empty(domain.name+'的模块和分类入口已保留，尚未接入具体资料。')}<p class="reading-note">采集与分类增量后续由WorkBuddy按统一交付约定接入；本页不会显示糖尿病的数据作为该领域内容。</p></section>`;
 else if(s.tab==='topics')topicsView(s);else if(s.tab==='conferences')conferencesView(s);else if(s.tab==='papers')papersView(s);else if(['market','sales'].includes(s.tab))window.SalesCollaboration.render({D,s,V,esc,tag,link,hash,options,update,rerender:render});else expertsView(s);
 if($('detail').open)$('detail').close();if(s.q.get('conf'))conferenceDetail(s.q.get('conf'),s);else if(s.q.get('detail')&&domain.connected)topicDetail(s.q.get('detail'),s);else if(s.q.get('person')&&domain.connected)expertDetail(s.q.get('person'));document.title=domain.name+' · '+module.label+' · 临床科研工作台';document.body.dataset.renderedHash=location.hash;window.DomainWorkbench={data:D,state,measures,conference};}
$('domain').innerHTML=options(D.navigation.domains.map(d=>[d.id,d.name]),'diabetes');$('domain').onchange=()=>{const s=state();location.hash=s.tab+($('domain').value==='diabetes'?'':'?field='+$('domain').value);};$('search-form').onsubmit=e=>{e.preventDefault();update({q:$('q').value.trim(),board:null,page:null,detail:null,person:null,conf:null});};$('method').onclick=method;$('close').onclick=()=>{const s=state();if(s.q.has('detail')||s.q.has('person')||s.q.has('conf'))update({detail:null,person:null,conf:null});else $('detail').close();};$('detail').oncancel=()=>{const s=state();if(s.q.has('detail')||s.q.has('person')||s.q.has('conf'))setTimeout(()=>update({detail:null,person:null,conf:null}),0);};window.addEventListener('hashchange',render);render();
})();
