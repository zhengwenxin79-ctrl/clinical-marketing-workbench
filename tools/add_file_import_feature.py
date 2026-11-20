# -*- coding: utf-8 -*-
html_path = "workbench/领域工作台/会议审核入库.html"
with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update toolbar buttons
old_toolbar_buttons = """      <div style="display:flex; gap:10px;">
        <button class="btn btn-outline" onclick="simulateNewBatch()">📥 导入/模拟新抓取批次</button>
        <button class="btn btn-primary" onclick="loadQueueData()">🔄 刷新列表</button>
      </div>"""

new_toolbar_buttons = """      <div style="display:flex; gap:10px; align-items:center;">
        <input type="file" id="batch-file-input" accept=".json,.csv" style="display:none;" onchange="handleFileImport(event)" />
        <button class="btn btn-outline" onclick="document.getElementById('batch-file-input').click()">📁 导入交付文件 (JSON/CSV)</button>
        <button class="btn btn-outline" onclick="resetQueueToGoldStandard()">🔄 重置金标准批次</button>
        <button class="btn btn-primary" onclick="loadQueueData()">🔄 刷新列表</button>
      </div>"""

if old_toolbar_buttons in content:
    content = content.replace(old_toolbar_buttons, new_toolbar_buttons)
else:
    print("Warning: old toolbar buttons not matched exactly, replacing via regex...")
    import re
    content = re.sub(r'<div style="display:flex; gap:10px;">\s*<button.*?simulateNewBatch[\s\S]*?loadQueueData.*?</div>', new_toolbar_buttons, content)

# 2. Add handleFileImport function
file_import_func = """
function handleFileImport(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function(e) {
    try {
      const text = e.target.result;
      let newItems = [];
      if (file.name.endsWith('.json')) {
        const parsed = JSON.parse(text);
        const rawList = parsed.items || (Array.isArray(parsed) ? parsed : []);
        newItems = rawList.map((item, idx) => {
          const name = item.conference_name || item.name || "未命名学术会议";
          const pri = item.priority || (item.tier_code === 'B' ? '重点关注' : item.tier_code === 'C' ? '常规关注' : item.tier_code === 'A' ? '国际风向标' : '低优先级');
          const tier = item.tier_code || (pri === '重点关注' ? 'B' : pri === '常规关注' ? 'C' : pri === '国际风向标' ? 'A' : 'D');
          return {
            queue_id: item.queue_id || ("imp-" + Date.now() + "-" + idx),
            conference_id: item.conference_id || ("CONF-IMP-" + idx),
            conference_name: name,
            abbreviation: item.abbreviation || item.abbr || name.slice(0, 16),
            field_id: item.field_id || "vascular",
            tier_code: tier,
            priority: pri,
            start_date: item.start_date || "2026-11-27",
            end_date: item.end_date || item.start_date || "2026-11-29",
            city: item.city || "待定",
            official_url: item.official_url || item.source_url || "#",
            change_type: item.change_type || "first_seen",
            review_status: "pending",
            review_note: item.review_note || item.note || `【${pri}】WorkBuddy交付导入`,
            batch_id: parsed.batch_id || file.name,
            created_at: new Date().toISOString()
          };
        });
      } else if (file.name.endsWith('.csv')) {
        const lines = text.split(/\\r?\\n/).filter(l => l.trim());
        if (lines.length > 1) {
          const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''));
          for (let i = 1; i < lines.length; i++) {
            const cols = lines[i].split(',').map(c => c.trim().replace(/^"|"$/g, ''));
            if (cols.length < 3) continue;
            const row = {};
            headers.forEach((h, idx) => { row[h] = cols[idx] || ''; });
            const name = row['会议名称'] || cols[3] || '未命名会议';
            const pri = row['优先级'] || row['优先级评级'] || '常规关注';
            const loc = row['会议地点'] || row['举办城市'] || cols[5] || '待定';
            const city = loc.includes('·') ? loc.split('·')[0].trim() : loc.slice(0, 4);
            newItems.push({
              queue_id: "csv-" + Date.now() + "-" + i,
              conference_id: "CONF-CSV-" + i,
              conference_name: name,
              abbreviation: name.slice(0, 16),
              field_id: (name.includes("多组学") || name.includes("呼吸")) ? "respiratory" : "vascular",
              tier_code: pri === '重点关注' ? 'B' : pri === '常规关注' ? 'C' : 'D',
              priority: pri,
              start_date: "2026-11-27",
              end_date: "2026-11-29",
              city: city,
              official_url: "#",
              change_type: "first_seen",
              review_status: "pending",
              review_note: `【${pri}】` + (row['备注'] || 'CSV交付导入'),
              batch_id: file.name,
              created_at: new Date().toISOString()
            });
          }
        }
      }

      if (!newItems.length) {
        alert("未能从文件中解析出有效的会议记录，请确认格式为标准 JSON 或 CSV！");
        return;
      }

      currentQueue = [...newItems, ...currentQueue];
      try {
        localStorage.setItem("demo_review_queue_v4", JSON.stringify(currentQueue));
      } catch (e) {}
      updateStats();
      renderQueue();
      alert(`🎉 成功从 ${file.name} 导入 ${newItems.length} 场学术会议！\\n已实时加载至待审核列表。`);
    } catch (err) {
      alert("解析文件失败：" + err.message);
    }
  };
  reader.readAsText(file, "utf-8");
  event.target.value = "";
}
"""

if "function handleFileImport" not in content:
    content = content.replace("function resetQueueToGoldStandard() {", file_import_func + "\nfunction resetQueueToGoldStandard() {")

with open(html_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Added file import feature to {html_path} successfully!")
