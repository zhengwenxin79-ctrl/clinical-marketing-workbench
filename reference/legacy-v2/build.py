from pathlib import Path
import hashlib
import json
import zipfile
import argparse

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description='Build standalone workbench, optionally from a review draft.')
parser.add_argument('--weekly-data', type=Path)
parser.add_argument('--output-dir', type=Path)
args = parser.parse_args()
output = args.output_dir.resolve() if args.output_dir else root
if args.weekly_data and output == root:
    parser.error('Draft data requires a separate --output-dir; formal website is not overwritten.')
output.mkdir(parents=True, exist_ok=True)
(output / 'dist').mkdir(exist_ok=True)
weekly_path = args.weekly_data or root / 'src/weekly-meetings.json'
data = json.loads((root / 'src/data.snapshot.json').read_text())
template = (root / 'src/index.template.html').read_text()
html = template.replace('__STYLE__', (root / 'src/styles.css').read_text())
html = html.replace('__DATA__', json.dumps(data, ensure_ascii=False).replace('</', '<\\/'))
html = html.replace('__BIOMARKERS__', (root / 'src/biomarkers.catalog.json').read_text().replace('</', '<\\/'))
html = html.replace('__PAPER_EVIDENCE__', (root / 'src/paper-evidence.json').read_text().replace('</', '<\\/'))
html = html.replace('__TRANSLATION_REVIEW__', (root / 'src/translation-review.json').read_text().replace('</', '<\\/'))
html = html.replace('__WEEKLY_MEETINGS__', weekly_path.read_text().replace('</', '<\\/'))
html = html.replace('__FIELD_CONFIG__', (root / 'src/fields.config.json').read_text().replace('</', '<\\/'))
html = html.replace('__APP__', (root / 'src/app.js').read_text() + '\n' + (root / 'src/biomarkers.js').read_text() + '\n' + (root / 'src/conference-cloud.js').read_text() + '\n' + (root / 'src/paper-cloud.js').read_text() + '\n' + (root / 'src/translation.js').read_text() + '\n' + (root / 'src/fields.js').read_text() + '\n' + (root / 'src/weekly-meetings.js').read_text() + '\nsetRoute();')
assert 'obsidian:' not in html.lower() and '/Users/' not in html
(output / 'index.html').write_text(html)
(output / 'dist/index.html').write_text(html)
readme = (root / 'README.md').read_text()
if args.weekly_data:
    readme = '# 待复核采集版本\n\n本网页含自动采集的会议候选；首次发现不等于主办方发布日期。正式首页未覆盖，检查范围和失败来源见页面状态。原研究数据保持原快照。\n\n' + readme
if output != root:
    (output / 'README.md').write_text(readme)
with zipfile.ZipFile(output / '会议与论文研究台_v2_分享包.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    z.write(output / 'index.html', 'research-workbench-v2/index.html')
    z.writestr('research-workbench-v2/README.md', readme)
print('Built standalone V2; research cutoff:', data['cutoff'])
print('SHA256:', hashlib.sha256(html.encode()).hexdigest())
