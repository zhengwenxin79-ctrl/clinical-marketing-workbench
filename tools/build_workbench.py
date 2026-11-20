"""Build only in an isolated copy, preserving the shipped workbench."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,os
R=Path(__file__).resolve().parents[1];source=R/'workbench';dest=R/'handoff/acceptance/build-preview/workbench'
if dest.exists():shutil.rmtree(dest)
dest.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(source,dest,ignore=shutil.ignore_patterns('__pycache__','node_modules'))
refs=R/'糖尿病热点知识地图';target=dest.parent/'糖尿病热点知识地图'
if target.exists():shutil.rmtree(target)
shutil.copytree(refs,target,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before=h(source/'数据库/marketing.db')
for script in ['生成领域工作台.py','核验领域框架.py']:
 cp=subprocess.run([sys.executable,str(dest/'脚本'/script)],cwd=dest,capture_output=True,text=True,encoding='utf-8',env={**os.environ,'PYTHONUTF8':'1'});print(cp.stdout.strip())
 if cp.returncode:print(cp.stderr);sys.exit(cp.returncode)
snapshot=json.loads((dest/'领域工作台/领域数据快照.json').read_text(encoding='utf-8'))
from urllib.parse import unquote
for rating in snapshot['pi_ratings']['ratings']:
 assert (dest/'领域工作台'/unquote(rating['source_url'].split('#')[0])).resolve().is_file()
assert h(source/'数据库/marketing.db')==before==h(dest/'数据库/marketing.db')
print(json.dumps({'result':'passed','database_unchanged':True,'preview':str(dest/'领域工作台/index.html')},ensure_ascii=False))
