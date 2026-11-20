// 以独立SQL计数核对三榜及板块，另外验证地域数量不平衡、缺侧与补充会议。
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),out=path.join(root,'会议总入口');
const data=JSON.parse(fs.readFileSync(path.join(out,'领域热点数据快照.json'),'utf8'));
const expected=JSON.parse(fs.readFileSync(path.join(out,'领域热点数据核验.json'),'utf8')).expected;
const sandbox={document:{getElementById:()=>({textContent:JSON.stringify(data)})},window:{addEventListener:()=>{}}};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(path.join(out,'src/hotspots.js'),'utf8'),sandbox);
const calculate=sandbox.window.DomainHotspots.calculate;
const state=(cohort,rank)=>({year:'2026',cohort,rank,region:rank==='overall'?'all':rank,board:'',q:'',sort:'overall'});
const close=(a,b)=>{if(a===null||b===null)assert.equal(a,b);else assert(Math.abs(a-b)<1e-9,`${a} != ${b}`);};
let assertions=0;
for(const cohort of ['talks','posters','all'])for(const rank of ['overall','domestic','international']){
 const s=state(cohort,rank),m=calculate(s),eligible=data.conferences.filter(c=>['main','trial'].includes(c.admission.status)&&expected[c.conference_id][cohort].denominator>0);
 const mean=(topicIds,region)=>{const cs=eligible.filter(c=>c.region===region);return cs.length?cs.reduce((sum,c)=>{const e=expected[c.conference_id][cohort];return sum+100*topicIds.reduce((n,id)=>n+(e.counts[id]||0),0)/e.denominator;},0)/cs.length:null;};
 const check=(t,ids)=>{const domestic=mean(ids,'domestic'),international=mean(ids,'international');close(t.domestic,domestic);close(t.international,international);close(t.overall,domestic===null||international===null?null:(domestic+international)/2);assertions+=3;};
 m.topics.forEach(t=>check(t,[t.topic_id]));
 m.boards.forEach(b=>check(b,data.topics.filter(t=>t.board_id===b.board_id).map(t=>t.topic_id)));
 const scores=m.boards.map(b=>b[rank]??-1);assert(scores.every((v,i)=>!i||v<=scores[i-1]+1e-10));
 // 搜索或点选板块不会改变板块均值与排序。
 const filtered=calculate({...s,board:data.boards[0].board_id,q:'test-no-match'});
 assert.equal(JSON.stringify(filtered.boards.map(b=>[b.board_id,b[rank]])),JSON.stringify(m.boards.map(b=>[b.board_id,b[rank]])));
}
function fixture(domesticCopies,internationalCopies){
 const cloned=JSON.parse(JSON.stringify(data));cloned.conferences=[];cloned.reports=[];
 for(const [region,copies] of [['domestic',domesticCopies],['international',internationalCopies]]){
  const original=data.conferences.find(c=>c.region===region);
  for(let i=0;i<copies;i++){const cid=original.conference_id+'-fixture-'+i;cloned.conferences.push({...original,conference_id:cid});cloned.reports.push(...data.reports.filter(r=>r.conference_id===original.conference_id).map(r=>({...r,report_id:r.report_id+'-fixture-'+i,conference_id:cid})));}
 }
 return cloned;
}
const baseline=calculate(state('talks','overall'));
const imbalanced=calculate(state('talks','overall'),fixture(8,2));
for(const t of baseline.topics){const other=imbalanced.topics.find(x=>x.topic_id===t.topic_id);close(t.overall,other.overall);assertions++;}
assert.equal(JSON.stringify(baseline.topics.map(t=>t.topic_id)),JSON.stringify(imbalanced.topics.map(t=>t.topic_id)));
assert.equal(JSON.stringify(baseline.boards.map(b=>b.board_id)),JSON.stringify(imbalanced.boards.map(b=>b.board_id)));
const oneSide=fixture(0,2),missing=calculate(state('talks','overall'),oneSide);
assert.equal(missing.topics.length,0);assert(missing.boards.every(b=>b.overall===null));
assert(calculate(state('talks','international'),oneSide).topics.length>0);
const supplement=fixture(1,1);supplement.conferences.filter(c=>c.region==='international').forEach(c=>c.admission={status:'supplement',basis:'fixture'});
assert.equal(calculate(state('talks','overall'),supplement).topics.length,0);
const unknown=fixture(1,1);unknown.conferences.filter(c=>c.region==='international').forEach(c=>delete c.admission);
assert.equal(calculate(state('talks','overall'),unknown).topics.length,0);
const result={result:'passed',numeric_assertions:assertions,checks:['现有SQL计数：三报告范围×三榜，逐议题及逐板块核对国内/国际/50-50均值','研究板块按当前榜关注度降序；板块/搜索筛选不改变板块计算','合成测试8场国内/2场国际：综合值和议题/板块排序保持1:1基线结果','缺少任一地域时综合榜留空，地域榜仍可用','仅补充或未评估会议不参与榜单'],new_collection:false,published:false};
fs.writeFileSync(path.join(out,'领域热点计算核验.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
