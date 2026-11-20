from pathlib import Path
import json,re,math,hashlib,importlib.util
R=Path('/Users/zwx/Documents/文献阅读/BrainHao-Study/wenxin/糖尿病热点知识地图/热点量化试评_2026-11-16/CDS三维议题试评_v0.2');W=R/'会前重点议题榜_工作资料';d=json.loads((R/'会前重点议题数据.json').read_text());a=json.loads((R.parent/'原始材料/CDS_全日程结构化.json').read_text());raw=[r for r in a['items'] if r['kind'] in ['大会报告','专题报告','论文发言']];rp={r['code']:r for r in d['reports']};ps={p['id']:p for p in d['people']};checks=[]
def ck(v,n):
 assert v,n
 checks.append(n)
ck(len(raw)==len(rp)==606,'完整606条报告编号去重且覆盖')
ck({r['code'] for r in raw}==set(rp),'没有漏项或新增报告')
for r in raw:
 for k in ['title','people','date','time','kind','session_id','source_url']:ck(r[k]==rp[r['code']][k],r['code']+'保留'+k)
ranked=[r for r in d['reports'] if r['scope']=='入榜'];outs=[r for r in d['reports'] if r['scope']!='入榜'];ck(len(ranked)==579 and len(outs)==27,'579入榜27单列合计606')
ck(len(d['topics'])==44 and len(d['parents'])==12,'44具体议题12主题')
flat=[c for t in d['topics'] for c in t['report_codes']];ck(len(flat)==len(set(flat))==579,'一个报告仅一个主议题')
for t in d['topics']:
 rs=[rp[c] for c in t['report_codes']];leaders=[ps[i] for i in t['leader_ids']]
 ck(all(r['topic_id']==t['id'] for r in rs),t['id']+'主归属一致')
 ck(t['report_count']==len(rs),t['id']+'报告量')
 ck(t['session_count']==len({r['session_id'] for r in rs}),t['id']+'专题量')
 ck(len(leaders)==len(set(t['leader_ids'])),t['id']+'专家去重')
 ck(t['leader_units']==sum(p['leader_weight'] for p in leaders),t['id']+'角色加权单位复算')
 for p in leaders:ck(any(c in t['report_codes'] for c in p['reports']),t['id']+p['name']+'真实讲题关联')
 vals=[]
 for c,k in zip(t['components'],['report_count','leader_units','session_count','key_units']):
  ck(c['maximum']==max(x[k] for x in d['topics']),t['id']+'全榜归一化分母'+k)
  ck(c['raw']==t[k],t['id']+'原始量'+k);v=c['weight']*math.log1p(c['raw'])/math.log1p(c['maximum']);ck(round(v,2)==c['score'],t['id']+'分项得分'+k);vals.append(v)
 ck(round(sum(vals),1)==t['score'],t['id']+'总分复算')
 ck(round(sum(v for i,v in enumerate(vals) if i!=1)/.7,1)==t['agenda_only_score'],t['id']+'去专家项对照复算')
 ck(t['rank']==1+sum(x['score']>t['score'] for x in d['topics']),t['id']+'并列名次')
for p in d['people']:
 ck('grade' not in p and 'total_score' not in p,p['id']+'不使用客户评级')
 if p['leader_weight'] is not None:ck(bool(p['leader_basis']) and p['profile_has_bio'] or '国际糖尿病联盟' in p['institution'],p['id']+'角色有来源依据')
ck(len([p for p in d['people'] if p['name']=='肖新华'])==2,'同名肖新华按单位分开')
ck(any(p['is_plenary'] and p['name']=='Minna Woo' and p['leader_weight'] is None for p in d['people']),'简介不足仍展示大会主讲，不强行认定身份')
spec=importlib.util.spec_from_file_location('builder',R/'生成会前重点议题榜.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
for text in ['内分泌科主任医师','上海市内分泌科主任医师','中华医学会糖尿病学分会委员、上海市糖尿病学会副主任委员']:
 lvl,w,b=mod.qualify({'name':'回归检查','institution':'测试机构','text':'简历：\n'+text+'\n学术任务如下'})
 ck(w!=3,'不将普通全国委员跨顿号升级全国主委：'+text)
 if text=='内分泌科主任医师':ck(w is None,'主任医师不误作科主任')
page=(R/'index.html').read_text();embedded=json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>',page,re.S)[1]);ck(embedded==d,'页面与数据同步')
for needle in ['客户机会强度','客户加权分','综合评分卡','PI评级与缺口']:ck(needle not in page,'页面收起'+needle)
protected=json.loads((W/'未发布文件基线.json').read_text())
for x in protected:ck(hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()==x['sha256'],'原框架/正式文件未改：'+x['path'].split('/')[-1])
ck((R/'客户资料存档_2026-11-16.html').read_bytes()==(W/'改版前快照/index.html').read_bytes(),'旧客户页面完整存档')
res=dict(result='passed',assertions=len(checks),checks=checks,scope=d['meta']['scope'],protected_files=protected,head_rows=[dict(rank=t['rank'],topic=t['name'],score=t['score'],reports=t['report_count'],leaders=t['leader_count'],sessions=t['session_count']) for t in d['topics'][:10]])
(R/'会前榜数据核验.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in res.items() if k in ['result','assertions','head_rows']},ensure_ascii=False,indent=2))
