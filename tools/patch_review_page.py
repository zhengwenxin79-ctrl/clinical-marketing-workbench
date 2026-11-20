# -*- coding: utf-8 -*-
import json, csv, re

# Read CSV reference
csv_path = "workbuddy_task_pack/06_官方评级金标准参考_20261123周度.csv"

queue_items = []

field_map = {
    "慢阻肺／泛血管": "respiratory",
    "泛血管／神经精神": "neurology",
    "神经精神／泛血管": "neurology",
    "泛血管／心血管": "vascular",
    "自免": "rheumatology",
    "自免／检测与组学": "rheumatology",
    "心血管／泛血管": "cardiovascular",
    "心血管／内分泌": "cardiovascular",
    "泛血管": "vascular",
    "心血管": "cardiovascular",
    "神经精神": "neurology",
    "神经精神／心血管": "neurology",
    "检测与组学": "respiratory" # multi-omics
}

with open(csv_path, encoding="utf-8") as f:
    r = csv.DictReader(f)
    for idx, row in enumerate(r):
        seq = row.get("序号", str(idx+1))
        domain = row.get("领域大类", "")
        disease = row.get("疾病方向", "")
        name = row.get("会议名称", "")
        time_str = row.get("会议时间", "11-27 至 11-29")
        city = row.get("举办城市", "北京")
        scale = row.get("规模", "")
        source = row.get("主办方/信息源", "")
        status = row.get("目前状态", "即将开始")
        priority = row.get("优先级评级", "常规关注")
        note = row.get("评级理由/核实依据", "")
        
        # map field
        fid = field_map.get(domain, "vascular")
        if "多组学" in name:
            fid = "respiratory" # multi-omics/translational
        elif "风湿" in name or "自免" in name:
            fid = "rheumatology"
        elif "脑" in name or "神经" in name or "帕金森" in name:
            fid = "neurology"
        elif "心" in name or "血管" in name:
            fid = "vascular"
        elif "呼吸" in name or "慢阻肺" in name:
            fid = "respiratory"
            
        tier = "B" if priority == "重点关注" else "C" if priority == "常规关注" else "D"
        dates = time_str.split(" 至 ")
        s_date = f"2026-{dates[0].strip()}" if len(dates) > 0 else "2026-11-27"
        e_date = f"2026-{dates[1].strip()}" if len(dates) > 1 else s_date
        
        queue_items.append({
            "queue_id": f"ref-20261123-{int(seq):03d}",
            "conference_id": f"CONF-2026-{int(seq):03d}",
            "conference_name": name,
            "abbreviation": name.split("（")[0].split("(")[0][:12],
            "field_id": fid,
            "tier_code": tier,
            "priority": priority,
            "start_date": s_date,
            "end_date": e_date,
            "city": city,
            "official_url": f"https://cma.org.cn/meeting/conf_2026_{int(seq):03d}",
            "change_type": "first_seen",
            "review_status": "pending",
            "review_note": f"【{priority}】{note} (规模: {scale}, 主办: {source})",
            "batch_id": "batch_20261123_gold_standard",
            "created_at": "2026-11-20T10:00:00"
        })

# Add international conferences
queue_items.append({
    "queue_id": "ref-intl-001",
    "conference_id": "ADA2026",
    "conference_name": "86th Scientific Sessions of the American Diabetes Association (ADA 2026)",
    "abbreviation": "ADA 2026",
    "field_id": "diabetes",
    "tier_code": "A",
    "priority": "国际风向标",
    "start_date": "2026-06-12",
    "end_date": "2026-06-16",
    "city": "New Orleans, LA (国际)",
    "official_url": "https://professional.diabetes.org/scientific-sessions",
    "change_type": "first_seen",
    "review_status": "approved",
    "review_note": "国际学术顶会（仅提取国际热点议题与领军PI，免国内销售评级考核）",
    "batch_id": "batch_20261120_intl",
    "created_at": "2026-11-20T09:15:00"
})
queue_items.append({
    "queue_id": "ref-intl-002",
    "conference_id": "RSNA2026",
    "conference_name": "Radiological Society of North America 112th Scientific Assembly (RSNA 2026)",
    "abbreviation": "RSNA 2026",
    "field_id": "vascular",
    "tier_code": "A",
    "priority": "国际风向标",
    "start_date": "2026-11-29",
    "end_date": "2026-12-03",
    "city": "Chicago, IL (国际)",
    "official_url": "https://www.rsna.org/annual-meeting",
    "change_type": "first_seen",
    "review_status": "approved",
    "review_note": "全球放射与影像顶级盛会（追踪泛血管与神经影像多模态AI热点）",
    "batch_id": "batch_20261120_intl",
    "created_at": "2026-11-20T09:30:00"
})

print(f"Generated {len(queue_items)} items for STATIC_DEMO_QUEUE")

with open("workbench/框架配置/static_demo_queue.json", "w", encoding="utf-8") as f:
    json.dump(queue_items, f, ensure_ascii=False, indent=2)
print("Saved to workbench/框架配置/static_demo_queue.json")
