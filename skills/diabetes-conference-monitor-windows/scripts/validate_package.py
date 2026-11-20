# Windows transfer edition: explicit UTF-8 and portable runtime.
"""Validate WorkBuddy-specific frontmatter, local references and package hashes offline."""
import hashlib
import json
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {'name', 'display_name', 'display_name_en', 'description', 'description_zh', 'description_en', 'version', 'author'}

def validate(root=ROOT):
    content = (root / 'SKILL.md').read_text(encoding='utf-8')
    match = re.match('^---\\n(.*?)\\n---\\n', content, re.S)
    if not match:
        raise ValueError('SKILL.md frontmatter missing')
    front = {}
    for line in match[1].splitlines():
        key, value = line.split(':', 1)
        front[key] = json.loads(value.strip())
    if not REQUIRED.issubset(front):
        raise ValueError('Required WorkBuddy metadata missing')
    if not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*', front['name']) or len(front['name']) > 64:
        raise ValueError('Invalid skill name')
    if root.name != front['name']:
        raise ValueError('Directory and skill names differ')
    for field in REQUIRED:
        if not isinstance(front[field], str) or not front[field].strip():
            raise ValueError('Empty or non-string field: ' + field)
    for ref in re.findall('@((?:references|scripts)/[^\\s。]+)', content):
        if not (root / ref).is_file():
            raise ValueError('Unresolved reference: ' + ref)
    manifest = json.loads((root / 'package-manifest.json').read_text(encoding='utf-8'))
    for name, sha in manifest['files'].items():
        path = root / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError('File hash mismatch: ' + name)
    for path in (root / 'scripts').glob('*.py'):
        compile(path.read_text(encoding='utf-8'), str(path), 'exec')
    return {'status': 'valid', 'format': 'WorkBuddy', 'name': front['name'], 'version': front['version'], 'files_checked': len(manifest['files']), 'network_requests': 0, 'schedule_created': False}
if __name__ == '__main__':
    try:
        print(json.dumps(validate(), ensure_ascii=False, indent=2))
    except (ValueError, OSError) as e:
        raise SystemExit(str(e))
