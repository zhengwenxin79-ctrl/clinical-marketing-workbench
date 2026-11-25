with open('clinical-marketing-antigravity-20261119/workbench/领域工作台/src/template.html', 'r', encoding='utf-8') as f:
    text = f.read()

pos_root = text.find('x-data="workbenchApp()"')
print('x-data="workbenchApp()" at line:', text[:pos_root].count('\n') + 1)

# 统计此后的 <div> 和 </div> 闭合情况
div_count = 0
for idx, line in enumerate(text[pos_root:].splitlines()):
    div_count += line.count('<div')
    div_count -= line.count('</div>')
    if div_count == 0:
        print('x-data root closed at relative line:', idx + 1, 'actual line:', text[:pos_root].count('\n') + 1 + idx)
        break
