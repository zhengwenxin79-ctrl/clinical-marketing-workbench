# -*- coding: utf-8 -*-
import json, re

html_path = "workbench/领域工作台/会议审核入库.html"
with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

# Load generated static items
with open("workbench/框架配置/static_demo_queue.json", "r", encoding="utf-8") as f:
    static_items = json.load(f)

json_str = json.dumps(static_items, ensure_ascii=False, indent=2)

# 1. Replace STATIC_DEMO_QUEUE
pattern = r"const STATIC_DEMO_QUEUE = \[.*?\];"
replacement = f"const STATIC_DEMO_QUEUE = {json_str};"
new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# 2. Update fallbackToStaticQueue to use demo_review_queue_v4 and clear obsolete v1/v2
pattern_fallback = r"function fallbackToStaticQueue\(\)\s*\{[\s\S]*?\n\}"
new_fallback = """function fallbackToStaticQueue() {
  try {
    localStorage.removeItem("demo_review_queue_v2");
    localStorage.removeItem("demo_review_queue");
    const cached = localStorage.getItem("demo_review_queue_v4");
    if (cached) {
      currentQueue = JSON.parse(cached);
      return;
    }
  } catch (e) {
    console.warn("Failed to load cached demo queue:", e);
  }
  currentQueue = JSON.parse(JSON.stringify(STATIC_DEMO_QUEUE));
  try {
    localStorage.setItem("demo_review_queue_v4", JSON.stringify(currentQueue));
  } catch (e) {}
}"""
new_content = re.sub(pattern_fallback, new_fallback, new_content)

# 3. Update localStorage key in reviewItem
new_content = new_content.replace('localStorage.setItem("demo_review_queue_v2"', 'localStorage.setItem("demo_review_queue_v4"')

# 4. Add resetQueueToGoldStandard function if not present
if "function resetQueueToGoldStandard" not in new_content:
    reset_func = """
function resetQueueToGoldStandard() {
  if (confirm("是否重置当前沙盒数据为官方金标准 17 场会议批次？已做的人工审核操作将被恢复。")) {
    localStorage.removeItem("demo_review_queue_v4");
    currentQueue = JSON.parse(JSON.stringify(STATIC_DEMO_QUEUE));
    try {
      localStorage.setItem("demo_review_queue_v4", JSON.stringify(currentQueue));
    } catch(e) {}
    updateStats();
    renderQueue();
    alert("✅ 已成功重置为官方金标准批次（6 场重点关注、5 场常规关注、6 场低优先级）！");
  }
}
"""
    new_content = new_content.replace('function simulateNewBatch() {', reset_func + '\nfunction simulateNewBatch() {')

# 5. Add Reset button into toolbar if not present
if "resetQueueToGoldStandard()" not in new_content:
    old_btn = '<button class="btn btn-outline" onclick="simulateNewBatch()">'
    new_btn = '<button class="btn btn-outline" onclick="resetQueueToGoldStandard()">🔄 重置金标准批次</button>\n        <button class="btn btn-outline" onclick="simulateNewBatch()">'
    new_content = new_content.replace(old_btn, new_btn)

with open(html_path, "w", encoding="utf-8") as f:
    f.write(new_content)

print(f"Patched {html_path} successfully!")
