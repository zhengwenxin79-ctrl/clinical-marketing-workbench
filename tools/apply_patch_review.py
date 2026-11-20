# -*- coding: utf-8 -*-
import json, re

html_path = "workbench/领域工作台/会议审核入库.html"
with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

# Load generated static items
with open("workbench/框架配置/static_demo_queue.json", "r", encoding="utf-8") as f:
    static_items = json.load(f)

json_str = json.dumps(static_items, ensure_ascii=False, indent=2)

# Replace STATIC_DEMO_QUEUE
# From 'const STATIC_DEMO_QUEUE = [' up to '];'
pattern = r"const STATIC_DEMO_QUEUE = \[.*?\];"
replacement = f"const STATIC_DEMO_QUEUE = {json_str};"

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Ensure fallbackToStaticQueue uses localStorage
old_fallback = """function fallbackToStaticQueue() {
  if (!currentQueue || currentQueue.length === 0) {
    currentQueue = JSON.parse(JSON.stringify(STATIC_DEMO_QUEUE));
  }
}"""

new_fallback = """function fallbackToStaticQueue() {
  try {
    const cached = localStorage.getItem("demo_review_queue_v2");
    if (cached) {
      currentQueue = JSON.parse(cached);
      return;
    }
  } catch (e) {
    console.warn("Failed to load cached demo queue:", e);
  }
  currentQueue = JSON.parse(JSON.stringify(STATIC_DEMO_QUEUE));
  try {
    localStorage.setItem("demo_review_queue_v2", JSON.stringify(currentQueue));
  } catch (e) {}
}"""

if old_fallback in new_content:
    new_content = new_content.replace(old_fallback, new_fallback)
else:
    print("Warning: old_fallback not matched exactly, checking regex...")
    pattern_fallback = r"function fallbackToStaticQueue\(\)\s*\{[\s\S]*?\n\}"
    new_content = re.sub(pattern_fallback, new_fallback, new_content)

# Ensure reviewItem updates localStorage in static mode
old_review_static = """    item.review_status = action === "approve" ? "approved" : "rejected";
    item.tier_code = chosenTier;
    item.tier = chosenTier;
    item.reviewed_by = "market_user";
    item.reviewed_at = new Date().toISOString();
    if (note) item.review_note = (item.review_note ? item.review_note + " | " : "") + note;
    updateStats();
    renderQueue();"""

new_review_static = """    item.review_status = action === "approve" ? "approved" : "rejected";
    item.tier_code = chosenTier;
    item.tier = chosenTier;
    item.reviewed_by = "market_user";
    item.reviewed_at = new Date().toISOString();
    if (note) item.review_note = (item.review_note ? item.review_note + " | " : "") + note;
    try {
      localStorage.setItem("demo_review_queue_v2", JSON.stringify(currentQueue));
    } catch (e) {}
    updateStats();
    renderQueue();"""

if old_review_static in new_content:
    new_content = new_content.replace(old_review_static, new_review_static)
else:
    print("Warning: old_review_static not matched exactly")

with open(html_path, "w", encoding="utf-8") as f:
    f.write(new_content)

print(f"Patched {html_path} successfully!")
