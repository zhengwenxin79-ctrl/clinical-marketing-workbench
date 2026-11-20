# -*- coding: utf-8 -*-
import json, sqlite3, datetime

conn = sqlite3.connect("workbench/数据库/conference_updates.db")
c = conn.cursor()

with open("workbench/框架配置/static_demo_queue.json", "r", encoding="utf-8") as f:
    items = json.load(f)

print(f"Syncing {len(items)} gold standard items into conference_updates.db...")

for item in items:
    qid = item["queue_id"]
    cid = item["conference_id"]
    name = item["conference_name"]
    abbr = item.get("abbreviation", "")
    fid = item["field_id"]
    tier = item.get("tier_code", "B")
    s_date = item.get("start_date", "")
    e_date = item.get("end_date", "")
    city = item.get("city", "")
    url = item.get("official_url", "")
    ctype = item.get("change_type", "first_seen")
    status = item.get("review_status", "pending")
    note = item.get("review_note", "")
    now_str = item.get("created_at", datetime.datetime.now().isoformat())
    
    # upsert into raw_conference_staging
    raw_id = "raw-" + qid
    c.execute("""
    INSERT OR REPLACE INTO raw_conference_staging (
        raw_id, batch_id, conference_name, abbreviation, field_id,
        start_date, end_date, city, tier_level, source_url, raw_content, crawled_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        raw_id, item.get("batch_id", "batch_20261123_gold_standard"),
        name, abbr, fid, s_date, e_date, city, tier, url, note, now_str
    ))
    
    # upsert into conference_review_queue
    c.execute("""
    INSERT OR REPLACE INTO conference_review_queue (
        queue_id, raw_id, conference_id, change_type, review_status,
        reviewed_by, reviewed_at, review_note, field_id, conference_name,
        abbreviation, tier_code, start_date, end_date, city, official_url, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        qid, raw_id, cid, ctype, status,
        "market_user" if status != "pending" else None,
        now_str if status != "pending" else None,
        note, fid, name, abbr, tier, s_date, e_date, city, url, now_str
    ))

conn.commit()

# Verify counts in DB
counts = c.execute("SELECT tier_code, review_status, COUNT(*) FROM conference_review_queue GROUP BY tier_code, review_status").fetchall()
print("DB Review Queue Breakdown:")
for row in counts:
    print(f"  Tier {row[0]} | Status: {row[1]} | Count: {row[2]}")

conn.close()
print("Synced successfully!")
