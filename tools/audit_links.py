from pathlib import Path
import re, glob, os

ROOT = Path("clinical-marketing-antigravity-20261119")
WORKBENCH = ROOT / "workbench"

# Scan all html and js files
links = set()
for p in WORKBENCH.glob("**/*"):
    if p.suffix in (".html", ".js", ".json"):
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        # find references like ../xxx or xxx.html
        found = re.findall(r'[\'"](\.\./[^\'"]+|\b[a-zA-Z0-9_\u4e00-\u9fa5\-]+\.html[^\'"]*)[\'"]', text)
        for l in found:
            # clean hash and query
            clean = l.split("?")[0].split("#")[0]
            if clean and not clean.startswith("http"):
                links.add((p.relative_to(ROOT).as_posix(), l, clean))

print(f"Total potential links scanned: {len(links)}")
# Group by destination directory
dest_dirs = set()
for src, full, clean in links:
    if clean.startswith("../"):
        parts = clean.split("/")
        if len(parts) > 1:
            dest_dirs.add(parts[1])

print("Destination directories referenced via ../ :", dest_dirs)
for d in dest_dirs:
    target = WORKBENCH / d
    exists = target.exists()
    print(f"  workbench/{d}: exists={exists}")
