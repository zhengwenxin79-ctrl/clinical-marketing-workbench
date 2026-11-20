"""Conference Staging, Diff Analysis, Review & Weekly Updates Management Tool.
Strictly operates on independent conference_updates.db.
Leaves core research database (marketing.db) untouched.
"""
from pathlib import Path
import argparse, datetime, hashlib, json, secrets, sqlite3, sys
try:
    import open_conference_discovery
except ImportError:
    from tools import open_conference_discovery

ROOT = Path(__file__).resolve().parents[1]
UPDATES_DB_PATH = ROOT / "workbench/数据库/conference_updates.db"
CHANGE_LOG_PATH = ROOT / "workbench/框架配置/会议更新记录.json"
RESEARCH_DB = ROOT / "workbench/数据库/marketing.db"

def get_db(db_path=UPDATES_DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn

def init_schema(conn):
    c = conn.cursor()
    # 1. Raw staging table for crawled conference data
    c.execute("""
    CREATE TABLE IF NOT EXISTS raw_conference_staging (
        raw_id TEXT PRIMARY KEY,
        batch_id TEXT NOT NULL,
        conference_name TEXT NOT NULL,
        abbreviation TEXT,
        field_id TEXT NOT NULL,
        start_date TEXT,
        end_date TEXT,
        city TEXT,
        tier_level TEXT,
        source_url TEXT,
        raw_content TEXT,
        crawled_at TEXT NOT NULL
    )
    """)

    # 2. Review queue for market staff
    c.execute("""
    CREATE TABLE IF NOT EXISTS conference_review_queue (
        queue_id TEXT PRIMARY KEY,
        raw_id TEXT NOT NULL,
        conference_id TEXT NOT NULL,
        change_type TEXT NOT NULL, -- first_seen, source_update, duplicate
        review_status TEXT NOT NULL, -- pending, approved, rejected
        reviewed_by TEXT,
        reviewed_at TEXT,
        review_note TEXT,
        field_id TEXT NOT NULL,
        conference_name TEXT NOT NULL,
        abbreviation TEXT,
        tier_code TEXT DEFAULT 'B', -- A, B, C, D
        start_date TEXT,
        end_date TEXT,
        city TEXT,
        official_url TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(raw_id) REFERENCES raw_conference_staging(raw_id)
    )
    """)

    # 3. Approved weekly events
    c.execute("""
    CREATE TABLE IF NOT EXISTS weekly_update_events (
        event_id TEXT PRIMARY KEY,
        conference_id TEXT NOT NULL,
        event_kind TEXT NOT NULL, -- first_seen, source_update
        summary TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        source_published_on TEXT,
        source_url TEXT,
        review_status TEXT NOT NULL, -- approved
        field_id TEXT NOT NULL
    )
    """)

    # 4. Monitored conference anchors (19 orgs, 28 series, 12 international anchors)
    c.execute("""
    CREATE TABLE IF NOT EXISTS conference_anchors (
        anchor_id TEXT PRIMARY KEY,
        anchor_kind TEXT NOT NULL, -- organization, core_series, international_anchor, channel
        anchor_name TEXT NOT NULL,
        field_id TEXT,
        tier_level TEXT,
        aliases_json TEXT,
        entry_url TEXT,
        metadata_json TEXT
    )
    """)

    # Ensure tier_code exists in conference_review_queue
    cols = [col[1] for col in c.execute("PRAGMA table_info(conference_review_queue)").fetchall()]
    if "tier_code" not in cols:
        c.execute("ALTER TABLE conference_review_queue ADD COLUMN tier_code TEXT DEFAULT 'B'")

    conn.commit()

def sync_anchors_to_db(conn=None):
    if conn is None:
        conn = get_db()
    c = conn.cursor()
    anchors_json_path = ROOT / "workbench/框架配置/会议监控锚点库.json"
    if not anchors_json_path.is_file():
        anchors_json_path = ROOT / "workbench/框架配置/会议监控靶点库.json"
    if not anchors_json_path.is_file():
        return 0

    data = json.loads(anchors_json_path.read_text(encoding="utf-8"))
    count = 0

    # 1. Organizations
    for org in data.get("organizations", []):
        c.execute("""
        INSERT OR REPLACE INTO conference_anchors (
            anchor_id, anchor_kind, anchor_name, field_id, tier_level, aliases_json, entry_url, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            org["id"], "organization", org["name"], org.get("field_id"), org.get("type"),
            json.dumps([org.get("wechat_channel", "")], ensure_ascii=False),
            org.get("official_entry", ""),
            json.dumps(org, ensure_ascii=False)
        ))
        count += 1

    # 2. Core series
    for ser in data.get("core_series", []):
        c.execute("""
        INSERT OR REPLACE INTO conference_anchors (
            anchor_id, anchor_kind, anchor_name, field_id, tier_level, aliases_json, entry_url, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ser["id"], "core_series", ser["name"], ser.get("field_id"), ser.get("tier"),
            json.dumps(ser.get("aliases", []), ensure_ascii=False),
            "",
            json.dumps(ser, ensure_ascii=False)
        ))
        count += 1

    # 3. International anchors
    for anchor in data.get("international_anchors", []):
        c.execute("""
        INSERT OR REPLACE INTO conference_anchors (
            anchor_id, anchor_kind, anchor_name, field_id, tier_level, aliases_json, entry_url, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            anchor["id"], "international_anchor", anchor["name"], anchor.get("field_id"), anchor.get("tier"),
            json.dumps([anchor.get("abbr", "")], ensure_ascii=False),
            anchor.get("url", ""),
            json.dumps(anchor, ensure_ascii=False)
        ))
        count += 1

    conn.commit()
    return count

def sync_targets_to_db(conn=None):
    return sync_anchors_to_db(conn)

def ingest_crawled_conferences(items, batch_id=None, conn=None):
    if conn is None:
        conn = get_db()
    c = conn.cursor()
    if not batch_id:
        batch_id = "BATCH-" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Load existing catalog conferences to check for duplicates and changes
    snapshot_path = ROOT / "workbench/领域工作台/领域数据快照.json"
    known_conferences = {}
    if snapshot_path.is_file():
        snapshot_data = json.loads(snapshot_path.read_text(encoding="utf-8"))
        for entry in snapshot_data.get("catalog", {}).get("entries", []):
            known_conferences[entry["conference_id"]] = entry
            if entry.get("name_original"):
                known_conferences[entry["name_original"]] = entry

    # Also load already queued conferences
    for row in c.execute("SELECT conference_id, conference_name FROM conference_review_queue").fetchall():
        known_conferences[row["conference_id"]] = dict(row)
        known_conferences[row["conference_name"]] = dict(row)

    results = {
        "batch_id": batch_id,
        "total": len(items),
        "first_seen": 0,
        "source_update": 0,
        "duplicate": 0,
        "queued": []
    }

    for item in items:
        raw_id = "RAW-" + secrets.token_hex(6)
        name = item.get("conference_name") or item.get("name_original") or "未命名学术会议"
        field_id = item.get("field_id") or "cardiovascular"
        abbr = item.get("abbreviation") or "".join([w[0].upper() for w in name.split() if w])[:6] or "CONF"
        cid = item.get("conference_id") or (abbr + "-" + str(datetime.datetime.now().year))
        
        # Save raw staging
        c.execute("""
        INSERT INTO raw_conference_staging (
            raw_id, batch_id, conference_name, abbreviation, field_id,
            start_date, end_date, city, tier_level, source_url, raw_content, crawled_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            raw_id, batch_id, name, abbr, field_id,
            item.get("start_date"), item.get("end_date"), item.get("city"),
            item.get("tier_level", "行业重点会议"), item.get("source_url", ""),
            json.dumps(item, ensure_ascii=False), now_str
        ))

        # Diff determination
        if cid in known_conferences or name in known_conferences:
            # Match found: check if date or url is updated
            existing = known_conferences.get(cid) or known_conferences.get(name)
            if existing.get("start_date") != item.get("start_date") or existing.get("city") != item.get("city"):
                change_type = "source_update"
                results["source_update"] += 1
            else:
                change_type = "duplicate"
                results["duplicate"] += 1
        else:
            change_type = "first_seen"
            results["first_seen"] += 1

        # Deduce Tier code (A, B, C, D)
        tier_raw = str(item.get("tier") or item.get("tier_code") or item.get("tier_level") or "").strip().upper()
        if "A" in tier_raw or "INTERNATIONAL" in tier_raw or "国际" in tier_raw:
            tier_code = "A"
        elif "B" in tier_raw or "NATIONAL" in tier_raw or "全国" in tier_raw:
            tier_code = "B"
        elif "C" in tier_raw or "REGIONAL" in tier_raw or "区域" in tier_raw or "省" in tier_raw:
            tier_code = "C"
        elif "D" in tier_raw or "TOPIC" in tier_raw or "专题" in tier_raw:
            tier_code = "D"
        else:
            if cid in {"ADA2026", "EASD2026", "ACC2026", "ESC2026", "EULAR2026", "ISTH2026"}:
                tier_code = "A"
            elif any(k in name for k in ("中华医学会", "中国医师协会", "CSCO", "全国", "年会")):
                tier_code = "B"
            elif any(k in name for k in ("省", "市", "华东", "华北", "华南", "西部")):
                tier_code = "C"
            else:
                tier_code = "B"

        # Enqueue for review (duplicates are marked rejected by default)
        queue_id = "REV-" + secrets.token_hex(6)
        if change_type == "duplicate":
            status = "rejected"
            note = "完全相同会议日程，自动去重"
        else:
            status = "pending"
            eval_res = open_conference_discovery.evaluate_conference_relevance(item)
            note = f"【Skill初评：{eval_res['relevance_tier']}】{eval_res['reason']}"
        c.execute("""
        INSERT INTO conference_review_queue (
            queue_id, raw_id, conference_id, change_type, review_status,
            reviewed_by, reviewed_at, review_note, field_id, conference_name,
            abbreviation, tier_code, start_date, end_date, city, official_url, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            queue_id, raw_id, cid, change_type, status,
            "system" if change_type == "duplicate" else None,
            now_str if change_type == "duplicate" else None,
            note, field_id, name, abbr, tier_code, item.get("start_date"),
            item.get("end_date"), item.get("city"), item.get("official_url") or item.get("source_url"),
            now_str
        ))
        results["queued"].append({
            "queue_id": queue_id,
            "conference_name": name,
            "change_type": change_type,
            "status": status
        })

    conn.commit()
    return results

def review_queue_item(queue_id, action, reviewed_by="market_admin", note="", tier_code=None, conn=None):
    if conn is None:
        conn = get_db()
    c = conn.cursor()
    row = c.execute("SELECT * FROM conference_review_queue WHERE queue_id = ?", (queue_id,)).fetchone()
    if not row:
        return {"success": False, "error": f"Queue item {queue_id} not found"}

    status = "approved" if action == "approve" else "rejected"
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    final_tier = tier_code or dict(row).get("tier_code") or "B"

    c.execute("""
    UPDATE conference_review_queue SET
        review_status = ?, reviewed_by = ?, reviewed_at = ?, review_note = ?, tier_code = ?
    WHERE queue_id = ?
    """, (status, reviewed_by, now_str, note, final_tier, queue_id))

    # If approved, generate weekly update event
    if status == "approved":
        row_d = dict(row)
        event_id = "EVT-" + secrets.token_hex(6)
        summary = f"市场部复核通过新学术会议：{row_d['conference_name']}" if row_d['change_type'] == "first_seen" else f"会议日程更新：{row_d['conference_name']}"
        c.execute("""
        INSERT OR REPLACE INTO weekly_update_events (
            event_id, conference_id, event_kind, summary, observed_at,
            source_published_on, source_url, review_status, field_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id, row_d["conference_id"], row_d["change_type"], summary,
            now_str, row_d.get("start_date"), row_d.get("official_url"), "approved", row_d["field_id"]
        ))

    conn.commit()
    return {"success": True, "queue_id": queue_id, "status": status}

def sync_weekly_change_log(conn=None):
    """Sync approved weekly events into workbench/框架配置/会议更新记录.json, activating the frontend."""
    if conn is None:
        conn = get_db()
    c = conn.cursor()
    
    events = []
    for row in c.execute("SELECT * FROM weekly_update_events WHERE review_status = 'approved' ORDER BY observed_at DESC"):
        events.append({
            "event_id": row["event_id"],
            "conference_id": row["conference_id"],
            "event_kind": row["event_kind"],
            "summary": row["summary"],
            "observed_at": row["observed_at"],
            "source_published_on": row["source_published_on"],
            "source_url": row["source_url"],
            "review_status": "approved",
            "field_id": row["field_id"]
        })

    # Prepare active change log
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    change_log = {
        "version": "conference-change-log:v1",
        "connection_status": "connected" if events else "not_connected",
        "timezone": "Asia/Shanghai",
        "last_synced_at": now_str,
        "events": events,
        "checks": [
            {
                "checked_at": now_str,
                "status": "complete",
                "notes": f"会议更新库已成功同步 {len(events)} 条经市场部审核批准的会议事件。"
            }
        ],
        "rules": {
            "first_seen": "已复核通过的新收录会议",
            "source_update": "已复核通过的会议日程变更",
            "verified_by": "市场部人工审核复核"
        }
    }

    CHANGE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHANGE_LOG_PATH.write_text(json.dumps(change_log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return change_log

def main():
    parser = argparse.ArgumentParser(description="Conference Staging and Review Management Tool")
    parser.add_argument("--init", action="store_true", help="Initialize conference_updates.db")
    parser.add_argument("--ingest", type=Path, help="Ingest crawled conferences from JSON")
    parser.add_argument("--list-pending", action="store_true", help="List all pending items in review queue")
    parser.add_argument("--approve", type=str, help="Approve queue_id")
    parser.add_argument("--reject", type=str, help="Reject queue_id")
    parser.add_argument("--sync", action="store_true", help="Sync approved events to 会议更新记录.json")
    parser.add_argument("--sync-anchors", "--sync-targets", dest="sync_anchors", action="store_true", help="Sync anchors from 会议监控锚点库.json into conference_anchors table")
    args = parser.parse_args()

    conn = get_db()
    if args.init:
        print(f"Initialized database at: {UPDATES_DB_PATH}")
        cnt = sync_anchors_to_db(conn)
        print(f"Synced {cnt} conference anchors into database.")
    elif args.sync_anchors:
        cnt = sync_anchors_to_db(conn)
        print(f"Synced {cnt} conference anchors (organizations, core series, international anchors) into conference_anchors table.")
    elif args.ingest:
        items = json.loads(args.ingest.read_text(encoding="utf-8"))
        res = ingest_crawled_conferences(items, conn=conn)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    elif args.list_pending:
        c = conn.cursor()
        rows = c.execute("SELECT queue_id, conference_id, conference_name, field_id, change_type, start_date, city FROM conference_review_queue WHERE review_status = 'pending'").fetchall()
        print(json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2))
    elif args.approve:
        res = review_queue_item(args.approve, "approve", conn=conn)
        print(json.dumps(res, ensure_ascii=False))
        sync_weekly_change_log(conn)
    elif args.reject:
        res = review_queue_item(args.reject, "reject", conn=conn)
        print(json.dumps(res, ensure_ascii=False))
    elif args.sync:
        res = sync_weekly_change_log(conn)
        print(f"Synced {len(res['events'])} approved events to 会议更新记录.json (status: {res['connection_status']})")
    conn.close()

if __name__ == "__main__":
    main()
