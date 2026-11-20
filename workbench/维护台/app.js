'use strict';
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
const state={overview:null,run:null,step:'import',reviewed:null,busy:false};
const esc=x=>String(x??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const labels={date_original:'原文日期',local_date:'标准日期',time_original:'报告时间',start_time:'开始时间',end_time:'结束时间',room_original:'会场'};
function notice(message,error=false){$('#notice').hidden=!message;$('#notice').className=error?'error':'';$('#notice').textContent=message;}
async function api(path,body){const opts=body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Maintenance-Token':state.overview.token},body:JSON.stringify(body)};const res=await fetch(path,opts);const data=await res.json();if(!res.ok)throw Error(data.error||'操作未完成');return data;}
async function task(fn){if(state.busy)return;state.busy=true;document.body.dataset.busy='true';$$('button').forEach(b=>b.dataset.wasDisabled=b.disabled?'1':'0');$$('button').forEach(b=>b.disabled=true);try{await fn();}catch(e){notice(e.message,true);}finally{state.busy=false;document.body.dataset.busy='false';$$('button').forEach(b=>b.disabled=b.dataset.wasDisabled==='1');render();}}
function setStep(step){state.step=step;$$('[data-step]').forEach(b=>{b.classList.toggle('active',b.dataset.step===step);b.setAttribute('aria-current',b.dataset.step===step?'step':'false');});$$('section.panel').forEach(p=>p.hidden=p.id!=='panel-'+step);render();}
async function refresh(){state.overview=await api('/api/status');if(state.run)state.run=await api('/api/run/'+state.run.meta.run_id);render();}
async function selectRun(id){state.run=await api('/api/run/'+id);state.reviewed=null;notice('');setStep(state.run.confirmation?'export':'diff');}
const noBatch=()=>'<div class="empty">请先导入资料，或从左侧选择已有批次。</div>';
function render(){if(!state.overview)return;const o=state.overview,c=o.counts,r=state.run,d=r?.diff;
$('#stats').innerHTML=[[c.reports,'学术报告'],[c.classified_reports,'纳入议题统计'],[c.topics,'当前细分议题'],[c.source_materials,'数据库来源文件']].map(([v,l])=>`<div class="stat"><b>${v.toLocaleString()}</b><span>${l}</span></div>`).join('');
$('#db-status').textContent='marketing.db · SHA256 '+o.database_sha256.slice(0,16)+'… · 本地运行';
$('#history').innerHTML=o.runs.length?o.runs.slice(0,8).map(x=>`<button class="history-item ${x.meta.run_id===r?.meta.run_id?'selected':''}" data-run="${esc(x.meta.run_id)}"><b>${esc(x.meta.original_filename)}</b><small>${esc(x.meta.run_id.slice(4,19))} · ${x.confirmed?'已确认':x.meta.status==='invalid'?'格式待整理':x.summary?.blocked?'待复核':'待确认'}</small></button>`).join(''):'<p class="muted">还没有导入记录。</p>';
$$('[data-run]').forEach(b=>b.onclick=()=>task(()=>selectRun(b.dataset.run)));
$('#records-link').hidden=!r;if(r)$('#records-link').href=r.record_url;
$('#diff-batch').textContent=r?'批次 '+r.meta.run_id+' · 资料日期 '+(r.meta.source_observed_on||'待核')+' · '+r.meta.original_filename:'';
$('#go-confirm').disabled=!d||!!d.blocked.length||!!r?.confirmation;
if(!r)$('#diff-content').innerHTML=noBatch();
else if(!d)$('#diff-content').innerHTML=`<div class="warning"><h3>原始资料已保存，格式需要整理</h3>${esc(r.meta.error)}</div><a href="${r.record_url}" target="_blank" rel="noopener">查看原文件与失败记录 ↗</a>`;
else{const s=d.summary;let html=`<div class="summary-grid">${[[s.agenda_items,'日程范围'],[s.changed_records,'变化记录'],[s.changed_fields,'变化字段'],[s.blocked,'待核问题']].map(([v,l])=>`<div class="summary-cell"><b>${v}</b>${l}</div>`).join('')}</div>`;
if(!s.changed_fields&&!s.blocked)html+='<div class="success-box"><strong>与当前数据库一致，无变化</strong><p>确认后会保存本次核对记录和更新前备份。现有报告、人物、分类和科研结论保持原值。</p></div>';
if(d.changes.length)html+='<h3 class="section-title">可以确认的日程字段</h3><div class="table-wrap"><table><thead><tr><th>记录 / 字段</th><th>更新前</th><th>更新后</th><th>原资料定位</th></tr></thead><tbody>'+d.changes.slice(0,100).map(x=>`<tr><td>${esc(x.entity_id)}<br>${esc(labels[x.field]||x.field)}</td><td class="before">${esc(x.before)}</td><td class="after">${esc(x.after)}</td><td>${esc(x.source_locator)}</td></tr>`).join('')+'</tbody></table></div>';
if(d.changes.length>100)html+='<p class="muted">页面展示前100条，完整字段差异见本批“变化清单.json”。</p>';
if(d.blocked.length)html+=`<div class="warning"><h3>${d.blocked.length}项变化需要另行复核，本批暂停写入</h3>处理后重新导入，所有原件和本次问题记录会保留。</div><div class="table-wrap"><table><thead><tr><th>记录 / 字段</th><th>原因</th><th>更新前</th><th>新资料</th></tr></thead><tbody>${d.blocked.slice(0,100).map(x=>`<tr><td>${esc(x.entity_id)}<br>${esc(x.field)}</td><td>${esc(x.message)}</td><td>${esc(typeof x.before==='object'?JSON.stringify(x.before):x.before)}</td><td>${esc(typeof x.after==='object'?JSON.stringify(x.after):x.after)}</td></tr>`).join('')}</tbody></table></div>`;
html+=`<p class="muted">${esc(d.scope)}</p><a href="${r.record_url}变化清单.json">下载完整变化清单 ↓</a>`;$('#diff-content').innerHTML=html;}
$('#confirm-run').disabled=true;
if(!r)$('#confirm-content').innerHTML=noBatch();
else if(r.confirmation){const cf=r.confirmation_file;$('#confirm-content').innerHTML=`<div class="success-box"><strong>${r.confirmation.status==='confirmed_no_change'?'已确认：无业务字段变化':'已确认更新'}</strong><p>确认时间：${esc(r.confirmation.confirmed_at)}</p><p>业务变化字段：${r.confirmation.changed_fields}；确认人：${esc(r.confirmation.confirmed_by)}</p>${cf?`<p><a href="/backup/${encodeURIComponent(cf.backup.split('/').pop())}">下载确认前数据库备份 ↓</a></p>`:''}</div><p class="muted">重复点击不会再次写入同一批次。可以继续核验并导出。</p><button class="secondary" data-next-export>继续核验导出 →</button>`;}
else if(!d||d.blocked.length)$('#confirm-content').innerHTML='<div class="warning">请先整理本批待核问题，再重新导入。</div>';
else{const stale=d.baseline_sha256!==o.database_sha256;$('#confirm-content').innerHTML=`<div class="success-box"><strong>${d.summary.changed_fields?'将确认 '+d.summary.changed_fields+' 个日程字段变化':'将确认本次核对结果：无变化'}</strong><p>先保存确认前数据库备份，再将更新与审计记录一并提交。</p><p>原始资料和变化清单均保留，可追溯到本批文件与原文位置。</p></div>${stale?'<div class="warning">数据库在导入后已变化。请重新导入，生成最新差异后再确认。</div>':''}${state.reviewed!==r.meta.run_id?'<p class="muted">先在“查看变化”中点击“已查看变化，进入确认”。</p>':''}<label class="check-line"><input type="checkbox" id="confirm-check" ${state.reviewed!==r.meta.run_id||stale?'disabled':''}><span>我已查看本批变化及来源，确认把这些字段或“无变化”核对记录保存到数据库。</span></label>`;const check=$('#confirm-check');if(check)check.onchange=()=>$('#confirm-run').disabled=!check.checked||state.busy;}
$$('[data-next-export]').forEach(b=>b.onclick=()=>setStep('export'));
$('#export-run').disabled=!r?.confirmation;
if(!r)$('#export-content').innerHTML=noBatch();
else if(!r.confirmation)$('#export-content').innerHTML='<div class="empty">这批资料还未确认。完成查看变化与确认后，即可核验导出。</div>';
else if(!r.verification)$('#export-content').innerHTML='<div class="scope-note"><strong>将检查哪些内容</strong><p>数据库完整性和外键、原始资料指纹、日程原文回读、议题统计范围、网页与JSON导出一致性。核验通过后替换本地会议网页，导出前文件也会保留。</p></div>';
else if(r.verification.result==='failed')$('#export-content').innerHTML=`<div class="warning"><h3>本次核验未通过</h3>${esc(r.verification.error)}</div><p class="muted">请检查本批记录，解决原因后重新核验。旧版网页和数据库确认前备份均保留。</p>`;
else{const v=r.verification;const isCurrent=v.database_sha256===o.database_sha256;$('#export-content').innerHTML=`<div class="success-box"><strong>核验通过，已生成本地会议网页</strong><p>${esc(v.checked_at)} · ${v.counts.reports}条学术报告 / ${v.counts.classified_reports}条纳入统计 / ${v.counts.topics}个议题</p><p>导出范围：当前已确认数据库；本次未对外发布。</p></div>${!isCurrent?'<div class="warning">数据库在这次导出后已有变化，请重新核验导出。</div>':''}<ul class="checks">${v.checks.map(x=>`<li>${esc(x)}</li>`).join('')}</ul><div class="hash">数据库 SHA256：${esc(v.database_sha256)}</div><p class="muted">本批原件、确认前数据库、导出前网页、新导出快照及核验结果均已保存。</p>`;}
}
$$('[data-step]').forEach(b=>b.onclick=()=>setStep(b.dataset.step));$$('[data-go]').forEach(b=>b.onclick=()=>setStep(b.dataset.go));
$('#refresh').onclick=()=>task(async()=>{await refresh();notice('状态已刷新。');});
$('#go-confirm').onclick=()=>{state.reviewed=state.run?.meta.run_id;notice('');setStep('confirm');};
async function finishImport(result){state.run=result;state.reviewed=null;await refresh();setStep('diff');notice(result.meta.status==='invalid'?'原件已保存，文件格式需要整理。':'原件已保存，变化清单已生成。',result.meta.status==='invalid');}
$('#import-sample').onclick=()=>task(async()=>{notice('正在保存CDS原件并比较，请稍候…');await finishImport(await api('/api/import-sample',{}));});
$('#import-file').onclick=()=>task(async()=>{const file=$('#source-file').files[0];if(!file)throw Error('请先选择CDS结构化JSON资料。');if(file.size>12*1024*1024)throw Error('请选择不超过12MB的JSON。');notice('正在保存原件并比较，请稍候…');const bytes=new Uint8Array(await file.arrayBuffer());let binary='';for(let i=0;i<bytes.length;i+=32768)binary+=String.fromCharCode(...bytes.subarray(i,i+32768));await finishImport(await api('/api/import',{content_base64:btoa(binary),filename:file.name,note:$('#note').value}));});
$('#confirm-run').onclick=()=>task(async()=>{if(!$('#confirm-check')?.checked||state.reviewed!==state.run?.meta.run_id)throw Error('请先查看变化并勾选确认。');notice('正在备份并保存本批确认记录…');await api('/api/confirm',{run_id:state.run.meta.run_id});await refresh();setStep('export');notice('本批已确认，更新记录与确认前备份已保存。');});
$('#export-run').onclick=()=>task(async()=>{notice('正在核验原资料、数据库与网页，请稍候…');try{await api('/api/verify-export',{run_id:state.run.meta.run_id});}finally{await refresh();}setStep('export');notice('核验通过，会议网页与本批导出记录已保存。');});
task(async()=>{await refresh();if(state.overview.runs.length)await selectRun(state.overview.runs[0].meta.run_id);});
