"""只读取并复制本地CDS材料；无网络调用，原文件不改写。"""
from pathlib import Path
import argparse,hashlib,json,shutil

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--project',type=Path,required=True);args=ap.parse_args();root=args.root.resolve();project=args.project.resolve();pilot=project/'热点量化试评_2026-11-16/CDS三维议题试评_v0.2';raw=pilot.parent/'原始材料';work=pilot/'会前重点议题榜_工作资料';out=root/'原始资料/CDS2026';out.mkdir(parents=True,exist_ok=True)
 if (out/'资料清单.json').exists():raise SystemExit('资料清单已存在；本准备脚本不覆盖既有快照。请直接运行导入或复核脚本。')
 source=json.loads((pilot/'会前重点议题数据.json').read_text());checks=json.loads((work/'讲者简介核查.json').read_text());url_by_name={x['raw_file']:x['url'] for x in checks if x.get('raw_file')};entries=[]
 def copy(p,rel,kind,url=None,reading='结构化资料'):
  target=out/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target);assert sha(p)==sha(target)
  entries.append(dict(path=target.relative_to(root).as_posix(),sha256=sha(target),bytes=target.stat().st_size,kind=kind,source_url=url,reading_level=reading,source_observed_on='2026-11-16',original_path=str(p),original_sha256=sha(p),generated=False))
 copy(raw/'CDS_详细日程_2026-11-16.html','官方日程/CDS_详细日程_2026-11-16.html','official_agenda_html','https://cds26.tiemeeting.com/CN/Program/Details','官方日程题名')
 copy(raw/'CDS_全日程结构化.json','官方日程/CDS_全日程结构化.json','structured_agenda','https://cds26.tiemeeting.com/CN/Program/Details')
 for name in ['议题定义.json','逐报告归类与计分.json','讲者简介核查.json','学术带头人依据.json','专家识别规则.json']:
  copy(work/name,'处理依据/'+name,'local_review_snapshot')
 for name in ['CDS标志物题名复核.json','CDS标志物逐报告复核台账.json']:
  copy(pilot/'领域与Biomarker_工作资料'/name,'处理依据/'+name,'local_title_review')
 for p in sorted((work/'讲者简介原始页').iterdir()):
  if p.is_file():copy(p,'官方简介/'+p.name,'official_profile_html' if p.suffix.lower()=='.html' else 'derived_profile_text',url_by_name.get(p.name) or url_by_name.get(p.stem+'.html'),'官方会议简介' if p.suffix.lower()=='.html' else '既有提取文本')
 # 单独抽取CDS所需映射；不把整个混合ADA/论文台账当作CDS数据导入。
 mapping=dict(source_original_path=str(pilot/'会前重点议题数据.json'),source_sha256=sha(pilot/'会前重点议题数据.json'),source_observed_on=source['meta']['as_of'],people=[{k:p[k] for k in ['id','key','name','institution','profile_url','profile_status','profile_origin','profile_has_bio','leader_level','leader_basis','source_note']} for p in source['people']],meta={k:source['meta'][k] for k in ['as_of','agenda_date','scope']})
 cal=project/'会议与论文研究台_v2/src/weekly-meetings.json';c=next(x for x in json.loads(cal.read_text())['meetings'] if x['id']=='cds-2026')
 mapping['conference_calendar_record']=c;mapping['calendar_original_path']=str(cal);mapping['calendar_sha256']=sha(cal)
 p=out/'处理依据/CDS_导入映射快照.json';p.parent.mkdir(parents=True,exist_ok=True);dump(p,mapping)
 entries.append(dict(path=p.relative_to(root).as_posix(),sha256=sha(p),bytes=p.stat().st_size,kind='cds_only_import_mapping',source_url=None,reading_level='从既有本地资料抽取；不是新核查',source_observed_on='2026-11-16',original_path=str(pilot/'会前重点议题数据.json'),original_sha256=mapping['source_sha256'],generated=True))
 entries.sort(key=lambda e:e['path']);payload=dict(version=1,prepared_on='2026-11-17',source_observed_on='2026-11-16',scope='仅CDS2026；原始文件保留，复制件用于迁移和回溯',new_collection=False,files=entries)
 payload['fingerprint']=hashlib.sha256(json.dumps(entries,ensure_ascii=False,sort_keys=True).encode()).hexdigest();dump(out/'资料清单.json',payload);print(json.dumps(dict(copied_materials=len(entries),fingerprint=payload['fingerprint'],new_collection=False),ensure_ascii=False))
if __name__=='__main__':main()
