"""Automated Verification Suite for Conference Staging, Diff Deduplication & Weekly Updates.
Validates:
1. Independent DB schema & initialization (conference_updates.db).
2. Crawled conference batch ingestion & diffing (first_seen / source_update / duplicate).
3. Automated duplicate rejection & pending review queue.
4. RBAC review authorization (Market can review, Sales forbidden with 403).
5. Weekly update events publishing & sync to 会议更新记录.json (connection_status: connected).
6. Strict conservation of core research database marketing.db (SHA256 untouched).
"""
import datetime, hashlib, json, os, sqlite3, sys, threading, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import manage_conference_updates
import auth_server

RESEARCH_DB = ROOT / "workbench/数据库/marketing.db"
EXPECTED_DB_SHA256 = "645adc48a9af2eb67a9df04a0f4990fce706a5a4fcf2fe467c8e2372f0e78568"
UPDATES_DB = ROOT / "workbench/数据库/conference_updates.db"
CHANGE_LOG_PATH = ROOT / "workbench/框架配置/会议更新记录.json"

def calculate_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def http_json(method, url, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data, ensure_ascii=False).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))

def run_tests():
    print("=== [Conference Updates Test 1] Schema Initialization & Table Verification ===")
    conn = manage_conference_updates.get_db()
    c = conn.cursor()
    
    # Check tables
    tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "raw_conference_staging" in tables, "Missing raw_conference_staging table"
    assert "conference_review_queue" in tables, "Missing conference_review_queue table"
    assert "weekly_update_events" in tables, "Missing weekly_update_events table"
    print("  -> Passed: 3 core tables verified in conference_updates.db.")

    # Clean test data from review queue and staging for deterministic test run
    c.execute("DELETE FROM raw_conference_staging")
    c.execute("DELETE FROM conference_review_queue")
    c.execute("DELETE FROM weekly_update_events")
    conn.commit()

    print("\n=== [Conference Updates Test 2] Crawled Batch Ingestion & Diff Classification ===")
    mock_batch = [
        {
            # 1. Existing conference (CDS2026), updated date -> should be source_update
            "conference_id": "CDS2026",
            "conference_name": "中华医学会糖尿病学分会第二十八次全国学术会议 (CDS 2026 - Updated)",
            "abbreviation": "CDS",
            "field_id": "diabetes",
            "start_date": "2026-11-25", # Changed date
            "end_date": "2026-11-28",
            "city": "厦门市",
            "source_url": "https://cds2026.cma.org.cn/schedule-v2",
            "tier_level": "国家重点学术年会"
        },
        {
            # 2. Existing conference with identical dates/city -> should be duplicate
            "conference_id": "ADA2026",
            "conference_name": "American Diabetes Association 86th Scientific Sessions (ADA 2026)",
            "abbreviation": "ADA",
            "field_id": "diabetes",
            "start_date": "2026-06-05",
            "end_date": "2026-06-08",
            "city": "New Orleans, LA",
            "source_url": "https://diabetes.org/scientific-sessions",
            "tier_level": "国际顶级学会年会"
        },
        {
            # 3. Brand new conference -> should be first_seen
            "conference_id": "AHA-CARDIO-2026",
            "conference_name": "American Heart Association Scientific Sessions 2026",
            "abbreviation": "AHA",
            "field_id": "cardiovascular",
            "start_date": "2026-11-14",
            "end_date": "2026-11-16",
            "city": "Chicago, IL",
            "source_url": "https://professional.heart.org/scientific-sessions",
            "tier_level": "国际顶级学会年会"
        }
    ]

    res = manage_conference_updates.ingest_crawled_conferences(mock_batch, batch_id="TEST-BATCH-001", conn=conn)
    assert res["total"] == 3, f"Expected 3 items ingested, got {res['total']}"
    assert res["source_update"] >= 1, f"Expected at least 1 source_update, got {res['source_update']}"
    assert res["duplicate"] >= 1, f"Expected at least 1 duplicate, got {res['duplicate']}"
    assert res["first_seen"] >= 1, f"Expected at least 1 first_seen, got {res['first_seen']}"
    print(f"  -> Diff classification passed: {res['first_seen']} first_seen, {res['source_update']} source_update, {res['duplicate']} duplicate auto-deduplicated.")

    # Verify duplicate auto-rejection
    dup_row = c.execute("SELECT review_status, review_note FROM conference_review_queue WHERE conference_id = 'ADA2026'").fetchone()
    assert dup_row and dup_row["review_status"] == "rejected", "Duplicate should be auto-rejected"
    assert "去重" in dup_row["review_note"], "Duplicate should mention deduplication in note"
    print("  -> Passed: duplicate conference automatically set to 'rejected' without polluting pending queue.")

    print("\n=== [Conference Updates Test 3] Server RBAC & Review Permissions ===")
    port = 8792
    server = auth_server.ThreadingHTTPServer(("127.0.0.1", port), auth_server.RBACRequestHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    base_url = f"http://127.0.0.1:{port}"

    # Log in as Market and Sales
    status, market_login = http_json("POST", f"{base_url}/api/auth/login", {"username": "market", "password": "market123"})
    assert status == 200, "Market login failed"
    market_token = market_login["token"]

    status, sales_login = http_json("POST", f"{base_url}/api/auth/login", {"username": "demo-sales-a", "password": "sales123"})
    assert status == 200, "Sales login failed"
    sales_token = sales_login["token"]

    # 1. Sales tries to access review queue -> must get 403 Forbidden
    status, sales_queue = http_json("GET", f"{base_url}/api/conference/queue", token=sales_token)
    assert status == 403, f"Expected 403 for sales on conference queue, got {status}"
    print("  -> Passed: Sales representative strictly forbidden from accessing conference review queue (403).")

    # 2. Market accesses review queue -> gets list
    status, market_queue = http_json("GET", f"{base_url}/api/conference/queue?status=pending", token=market_token)
    assert status == 200, f"Market failed to get queue: {market_queue}"
    pending_items = market_queue["items"]
    assert len(pending_items) >= 2, f"Expected at least 2 pending items, got {len(pending_items)}"
    print(f"  -> Passed: Market retrieved pending queue with {len(pending_items)} items.")

    # 3. Sales tries to approve an item -> must get 403 Forbidden
    first_item = pending_items[0]
    status, sales_review = http_json("POST", f"{base_url}/api/conference/review", {
        "queue_id": first_item["queue_id"],
        "action": "approve"
    }, token=sales_token)
    assert status == 403, f"Expected 403 for sales reviewing conference, got {status}"
    print("  -> Passed: Sales representative strictly forbidden from reviewing conferences (403).")

    print("\n=== [Conference Updates Test 4] Market Approval & Weekly Events Sync ===")
    # 4. Market approves pending items
    for item in pending_items:
        status, review_res = http_json("POST", f"{base_url}/api/conference/review", {
            "queue_id": item["queue_id"],
            "action": "approve",
            "note": "市场部核验日程属实，准予入库发布"
        }, token=market_token)
        assert status == 200 and review_res.get("success"), f"Failed to approve {item['queue_id']}: {review_res}"

    print(f"  -> Passed: Market successfully approved {len(pending_items)} conference updates.")

    # Verify weekly update events in DB
    approved_events = c.execute("SELECT * FROM weekly_update_events WHERE review_status = 'approved'").fetchall()
    assert len(approved_events) >= 2, f"Expected at least 2 approved events, got {len(approved_events)}"
    print(f"  -> Passed: weekly_update_events table populated with {len(approved_events)} approved records.")

    # Verify sync to 会议更新记录.json
    assert CHANGE_LOG_PATH.is_file(), f"Missing {CHANGE_LOG_PATH}"
    log_data = json.loads(CHANGE_LOG_PATH.read_text(encoding="utf-8"))
    assert log_data["connection_status"] == "connected", f"Expected connection_status 'connected', got {log_data['connection_status']}"
    assert len(log_data["events"]) >= 2, f"Expected at least 2 events in JSON, got {len(log_data['events'])}"
    assert log_data["checks"][0]["status"] == "complete", "Checks status should be complete"
    print("  -> Passed: 会议更新记录.json transitioned to 'connected' with valid event schema.")

    # 5. Public / Sales can access weekly events
    status, events_resp = http_json("GET", f"{base_url}/api/conference/weekly-events", token=sales_token)
    assert status == 200 and len(events_resp["events"]) >= 2, "Sales should be able to view published weekly events"
    print("  -> Passed: Both Sales and Market can view approved weekly events via API.")

    server.shutdown()
    conn.close()

    print("\n=== [Conference Updates Test 5] Core Research DB Conservation Check ===")
    current_hash = calculate_sha256(RESEARCH_DB)
    assert current_hash == EXPECTED_DB_SHA256, f"RESEARCH DB TAMPERED!\nExpected: {EXPECTED_DB_SHA256}\nGot:      {current_hash}"
    print(f"  -> Passed: marketing.db strictly untouched: {current_hash}")

    print("\n=== ALL CONFERENCE UPDATES TESTS PASSED ===")

if __name__ == "__main__":
    run_tests()
