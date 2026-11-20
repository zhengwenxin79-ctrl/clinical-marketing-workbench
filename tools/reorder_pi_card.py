from pathlib import Path

path = Path("clinical-marketing-antigravity-20261119/workbench/领域工作台/src/sales.js")
content = path.read_text(encoding="utf-8")
lines = content.splitlines(keepends=True)

# 1. Locate the PI block (lines 87-90 in 1-based index, i.e. 86-90 in 0-based)
pi_block_text = """   <div class="sales-detail-block" style="background:#f8fafc;border:1px solid #e2e8f0;border-left:4px solid #0f243e;padding:14px 18px;border-radius:7px;margin-bottom:16px;">
     <h3 style="display:flex;align-items:center;gap:6px;color:#0f243e;margin-top:0;"><span>👨‍⚕️</span> 目标 PI 履历画像与客情档案</h3>
     ${r.expert_keys.length?r.expert_keys.map(k=>{const p=E.get(k);return p?window.PIRecommendations.profile({D,p,c:window.PIRecommendations.build(D).find(c=>c.person.key===k),esc,link,hash,compact:true,isFavorite:(S.favorites||[]).some(f=>f.actor_id===(role==='sales'?salesId:role)&&f.person_key===k)}):'';}).join(''):'<p class="muted">未绑定特定人物，可与该科室科研副主任或青年PI开展接洽。</p>'}
   </div>
"""

# Let's find lines 86 to 91 in 0-based indexing:
old_pi_start = None
old_pi_end = None
for i, l in enumerate(lines):
    if "目标 PI 履历画像与客情档案" in l:
        old_pi_start = i - 1 # <div class="sales-detail-block">
        for j in range(i, len(lines)):
            if lines[j].strip() == "</div>":
                old_pi_end = j + 1
                break
        break

print(f"Old PI block found at lines {old_pi_start+1} to {old_pi_end}")

# Check if there is an empty line after old PI block
if old_pi_end < len(lines) and lines[old_pi_end].strip() == "":
    old_pi_end += 1

# Remove old PI block
lines_removed = lines[:old_pi_start] + lines[old_pi_end:]

# Now find where break-ice block begins
break_ice_div = None
for i, l in enumerate(lines_removed):
    if "建议破冰话术" in l:
        # line before that is <div style="display:flex...
        # line before that is <div class="sales-detail-block" style="background:#f0fdf4...
        for k in range(i-1, -1, -1):
            if "sales-detail-block" in lines_removed[k]:
                break_ice_div = k
                break
        break

print(f"Break-ice div starts at line {break_ice_div+1}")

# Insert PI block right before break_ice_div
final_lines = lines_removed[:break_ice_div] + [pi_block_text + "\n"] + lines_removed[break_ice_div:]

path.write_text("".join(final_lines), encoding="utf-8")
print("SUCCESS: Successfully reordered sales.js!")
