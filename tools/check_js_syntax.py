import re

with open('clinical-marketing-antigravity-20261119/workbench/领域工作台/src/app.js', 'r', encoding='utf-8') as f:
    text = f.read()

stack = []
in_str = None
in_comment = None
escaped = False

for idx, ch in enumerate(text):
    if in_comment == 'single':
        if ch == '\n':
            in_comment = None
        continue
    elif in_comment == 'multi':
        if ch == '/' and text[idx-1] == '*':
            in_comment = None
        continue

    if in_str:
        if escaped:
            escaped = False
        elif ch == '\\':
            escaped = True
        elif ch == in_str:
            in_str = None
        continue

    # 正则表达式简易识别
    if ch == '/' and idx + 1 < len(text):
        if text[idx+1] == '/':
            in_comment = 'single'
            continue
        elif text[idx+1] == '*':
            in_comment = 'multi'
            continue
        # 简单判断是否是正则字面量
        prev_non_space = text[:idx].rstrip()
        if prev_non_space and prev_non_space[-1] in '(=[,:!&|?{};':
            in_str = '/'
            escaped = False
            continue

    if ch in ('"', "'", '`'):
        in_str = ch
        escaped = False
        continue

    if ch in '({[':
        stack.append((ch, idx, text[:idx].count('\n') + 1))
    elif ch in ')}]':
        if not stack:
            line_no = text[:idx].count('\n') + 1
            print(f'Unmatched closing {ch} at line {line_no}')
            break
        last, l_idx, l_line = stack.pop()
        expected = {'(': ')', '{': '}', '[': ']'}[last]
        if ch != expected:
            line_no = text[:idx].count('\n') + 1
            print(f'Line {line_no}: Mismatched closing {ch}, opened with {last} at line {l_line}')
            break

print('Stack remaining:', len(stack))
for s, i, l in stack:
    print(f'Unclosed {s} at line {l}: {repr(text[i:i+40])}')
