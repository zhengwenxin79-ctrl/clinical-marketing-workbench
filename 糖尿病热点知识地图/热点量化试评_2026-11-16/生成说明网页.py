"""Render this pilot's simple Markdown notes as standalone UTF-8 reading pages.

Uses only the standard library. Markdown remains the source of truth for notes;
HTML copies are for browser navigation, including local file:// viewing.
"""
from pathlib import Path
import html
import json
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
NOTES = ['重点议题榜_简版.md', '量化口径_v0.1.md', '原始材料索引.md']
LINKS = {name: str(Path(name).with_suffix('.html')) for name in NOTES}
LINKS['来源覆盖与缺口.json'] = '来源覆盖与缺口.html'


def inline(text):
    tokens = []

    def stash(value):
        tokens.append(value)
        return f'\x00{len(tokens)-1}\x00'

    def link(match):
        label, url = match.groups()
        url = LINKS.get(url, url)
        scheme = urlsplit(url).scheme
        if scheme not in ('', 'https', 'http'):
            return stash(html.escape(label))
        attrs = ' target="_blank" rel="noopener"' if scheme else ''
        if url.endswith('.csv'):
            attrs += ' download'
        return stash(f'<a href="{html.escape(url, quote=True)}"{attrs}>{html.escape(label)}</a>')

    text = re.sub(r'`([^`]+)`', lambda m: stash('<code>'+html.escape(m[1])+'</code>'), text)
    text = re.sub(r'\[([^\]]+)\]\(([^\s)]+)\)', link, text)
    text = html.escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    return re.sub(r'\x00(\d+)\x00', lambda m: tokens[int(m[1])], text)


def markdown(text):
    lines = text.splitlines()
    if lines and lines[0] == '---':
        end = lines.index('---', 1)
        lines = lines[end+1:]
    out, i = [], 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        heading = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading:
            level = len(heading[1])
            out.append(f'<h{level}>{inline(heading[2])}</h{level}>')
            i += 1
        elif line.startswith('|') and i+1 < len(lines) and re.fullmatch(r'[|:\-\s]+', lines[i+1]):
            cells = lambda s: [inline(c.strip()) for c in s.strip().strip('|').split('|')]
            headers = cells(line)
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append('<tr>'+''.join('<td>'+c+'</td>' for c in cells(lines[i]))+'</tr>')
                i += 1
            out.append('<div class="table-wrap" role="region" aria-label="数据表格" tabindex="0"><table><thead><tr>'+''.join('<th>'+c+'</th>' for c in headers)+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>')
        elif re.match(r'^(?:- |\d+\. )', line):
            ordered = bool(re.match(r'^\d+\. ', line))
            pattern = r'^\d+\. ' if ordered else r'^- '
            items = []
            while i < len(lines) and re.match(pattern, lines[i].strip()):
                items.append('<li>'+inline(re.sub(pattern, '', lines[i].strip()))+'</li>')
                i += 1
            tag = 'ol' if ordered else 'ul'
            out.append(f'<{tag}>'+''.join(items)+f'</{tag}>')
        else:
            paragraph = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r'^(?:#|\||- |\d+\. )', lines[i].strip()):
                paragraph.append(lines[i].strip())
                i += 1
            out.append('<p>'+inline(' '.join(paragraph))+'</p>')
    return '\n'.join(out)


def page(title, body, source):
    nav = ''.join(f'<a href="{LINKS[n]}">{label}</a>' for n, label in zip(NOTES, ['简版报告', '评分口径', '原始材料']))
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}｜临床科研热点工作台</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#f1f4f8;color:#172b4d;font:16px/1.85 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif}}header{{background:#142b49;color:#fff;padding:24px max(20px,calc((100vw - 1120px)/2))}}header small{{color:#c8d7ec}}header h1{{margin:4px 0;font-size:25px;line-height:1.5}}nav{{display:flex;flex-wrap:wrap;gap:12px 22px;margin-top:12px}}header a{{color:#dceaff}}a{{color:#24578e;text-decoration:none}}a:hover{{text-decoration:underline}}main{{max-width:1160px;padding:24px 20px;margin:auto}}article{{background:#fff;border:1px solid #d6e0ed;border-radius:8px;padding:28px 32px}}article h1{{font-size:24px;margin:0 0 16px}}h2{{font-size:20px;margin:30px 0 12px}}h3{{font-size:18px}}p{{margin:12px 0;overflow-wrap:anywhere}}li{{margin:8px 0;overflow-wrap:anywhere}}.table-wrap{{overflow:auto;margin:18px 0}}table{{border-collapse:collapse;width:100%;min-width:680px;font-size:14px;line-height:1.8}}th,td{{text-align:left;vertical-align:top;border-bottom:1px solid #d6e0ed;padding:12px;overflow-wrap:anywhere}}th{{background:#edf3fb;min-width:70px}}code,pre{{font:14px/1.7 ui-monospace,SFMono-Regular,Menlo,monospace}}code{{background:#edf3fb;padding:2px 4px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;margin:12px 0}}details{{border-bottom:1px solid #d6e0ed;padding:12px 0}}summary{{cursor:pointer;color:#24578e;font-weight:600}}footer{{max-width:1120px;margin:0 auto 24px;padding:0 20px;color:#647b98;font-size:13px}}@media(max-width:650px){{header h1{{font-size:22px}}main{{padding:16px 12px}}article{{padding:20px 16px}}article h1{{font-size:22px}}h2{{font-size:19px}}}}
</style></head><body><header><small>临床科研热点工作台 · 本地试评 · 2026.11.16</small><h1>{html.escape(title)}</h1><nav><a href="重点议题榜_待复核.html">← 返回交互榜单</a>{nav}</nav></header><main><article>{body}</article></main><footer>待导师与专业复核 · <a href="{html.escape(source)}" download>下载原始文件</a></footer></body></html>'''


def generate():
    for name in NOTES:
        text = (ROOT/name).read_text(encoding='utf-8')
        title = next(re.sub(r'^#\s+', '', s) for s in text.splitlines() if s.startswith('# '))
        (ROOT/LINKS[name]).write_text(page(title, markdown(text), name), encoding='utf-8')
    audit = json.loads((ROOT/'来源覆盖与缺口.json').read_text(encoding='utf-8'))
    body = '<h1>来源覆盖与缺口</h1><p>按字段展开核对本轮读取范围与缺口；字段及数值沿用原始审计记录。</p>'
    for key, value in audit.items():
        body += '<details><summary>'+html.escape(key)+'</summary><pre>'+html.escape(json.dumps(value, ensure_ascii=False, indent=2))+'</pre></details>'
    (ROOT/'来源覆盖与缺口.html').write_text(page('来源覆盖与缺口', body, '来源覆盖与缺口.json'), encoding='utf-8')


if __name__ == '__main__':
    generate()
    print('Generated four standalone UTF-8 reading pages.')
