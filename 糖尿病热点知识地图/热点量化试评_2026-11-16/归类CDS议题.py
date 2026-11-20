from pathlib import Path
import json,re,collections
p=Path(__file__).resolve().parent;themes=json.loads((p/'主题分组.json').read_text());d=json.loads((p/'原始材料/CDS_全日程结构化.json').read_text());counts=collections.Counter();un=[];manual=json.loads((p/'CDS分类校正.json').read_text())
for r in d['items']:
 if r['kind'] not in ['大会报告','专题报告','论文发言'] or not r['code']:continue
 m=[t for t in themes if re.search(t['pattern'],r['title'],re.I)]
 if r['code'] in manual['excluded_education']:r['theme_id']=None;r['excluded_reason']='科研写作/数据库方法培训；单列不入主题榜';continue
 if r['code'] in manual['left_unclassified']:r['theme_id']=None;un.append((r['code'],r['title']));continue
 if r['code'] in manual['overrides']:
  r['theme_id']=manual['overrides'][r['code']]['theme_id'];r['secondary_theme_ids']=[x['id'] for x in m if x['id']!=r['theme_id']];r['classification_basis']='AI编辑校正：'+manual['overrides'][r['code']]['reason'];counts[r['theme_id']]+=1;continue
 if m:r['theme_id']=m[0]['id'];r['secondary_theme_ids']=[x['id'] for x in m[1:]];r['classification_basis']='标题关键词；按主题配置顺序给出主归属，重叠主题另列';counts[m[0]['id']]+=1
 else:r['theme_id']=None;un.append((r['code'],r['title']))
(p/'CDS_逐报告分类.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');print('COUNTS',counts,'unmapped',len(un));print('UNMAPPED',un[:35])
for t in themes:
 rows=[r for r in d['items'] if r.get('theme_id')==t['id']];print('\n',t['name'],len(rows),collections.Counter(r['kind'] for r in rows));print([(r['code'],r['title']) for r in rows[:3]])
