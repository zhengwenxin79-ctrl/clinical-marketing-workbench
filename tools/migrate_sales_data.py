"""P02 Sales business data migration and persistence tool.
Validates, diffs, backups, and idempotently imports/exports sales records
between clinical-sales-export:v1 JSON and independent sales_business.db.
Strictly does NOT modify or touch the research database (marketing.db).
"""
from pathlib import Path
import argparse, datetime, hashlib, json, shutil, sqlite3, sys

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "workbench/数据库/sales_business.db"
RESEARCH_DB = ROOT / "workbench/数据库/marketing.db"

SCHEMA_VERSION = "clinical-sales-export:v1"
ALLOWED_STATUS = {"draft", "assigned", "in_progress", "archived"}
ALLOWED_CONTACT = {"not_contacted", "contacted", "waiting", "paused"}
ALLOWED_QUALITY_VALUES = {"useful", "partly_useful", "not_useful", "not_assessed"}
ALLOWED_STAGES = {"before_contact", "after_contact"}

def get_db(db_path=DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn

def init_schema(conn):
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS business_recommendations (
        id TEXT PRIMARY KEY,
        domain_id TEXT NOT NULL,
        topic_id TEXT,
        title TEXT NOT NULL,
        research_question TEXT,
        reason TEXT,
        participation TEXT,
        conditions TEXT,
        suggested_action TEXT,
        assignee_id TEXT,
        due_date TEXT,
        status TEXT NOT NULL,
        is_demo INTEGER DEFAULT 0,
        origin TEXT,
        candidate_id TEXT,
        provenance TEXT,
        links_json TEXT,
        expert_keys_json TEXT,
        capability_ids_json TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS business_feedback (
        id TEXT PRIMARY KEY,
        recommendation_id TEXT NOT NULL,
        author_id TEXT NOT NULL,
        contact_status TEXT NOT NULL,
        contact_date TEXT,
        contact_name TEXT,
        institution TEXT,
        need TEXT,
        cohort TEXT,
        support TEXT,
        next_action TEXT,
        next_owner_id TEXT,
        next_date TEXT,
        is_demo INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        reviewed_at TEXT,
        review_note TEXT,
        FOREIGN KEY(recommendation_id) REFERENCES business_recommendations(id)
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS business_favorites (
        actor_id TEXT NOT NULL,
        person_key TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (actor_id, person_key)
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS business_recommendation_feedback (
        id TEXT PRIMARY KEY,
        recommendation_id TEXT NOT NULL,
        author_id TEXT NOT NULL,
        value TEXT NOT NULL,
        stage TEXT NOT NULL,
        reasons_json TEXT,
        note TEXT,
        needs TEXT,
        is_demo INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        recommendation_updated_at TEXT,
        recommendation_snapshot_json TEXT,
        FOREIGN KEY(recommendation_id) REFERENCES business_recommendations(id)
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS import_audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        imported_at TEXT NOT NULL,
        source_file TEXT,
        file_sha256 TEXT,
        recs_added INTEGER,
        recs_updated INTEGER,
        feedback_added INTEGER,
        feedback_updated INTEGER,
        favorites_added INTEGER,
        quality_feedback_added INTEGER,
        quality_feedback_updated INTEGER
    )
    """)
    conn.commit()

def validate_json_data(data):
    errors = []
    if not isinstance(data, dict):
        return ["Root must be a JSON object"]
    
    schema = data.get("schema")
    if schema != SCHEMA_VERSION:
        errors.append(f"Invalid schema: expected '{SCHEMA_VERSION}', got '{schema}'")
    
    version = data.get("version")
    if version != 1:
        errors.append(f"Invalid version: expected 1, got {version}")
        
    for k in ["recommendations", "feedback"]:
        if k not in data or not isinstance(data[k], list):
            errors.append(f"Missing or invalid '{k}' array")
            
    recs = data.get("recommendations", [])
    seen_rec_ids = set()
    for i, r in enumerate(recs):
        prefix = f"recommendations[{i}]"
        rid = r.get("id")
        if not rid:
            errors.append(f"{prefix}: missing 'id'")
        elif rid in seen_rec_ids:
            errors.append(f"{prefix}: duplicate id '{rid}'")
        seen_rec_ids.add(rid)
        
        if not r.get("title"):
            errors.append(f"{prefix}: missing 'title'")
        if r.get("status") and r["status"] not in ALLOWED_STATUS:
            errors.append(f"{prefix}: invalid status '{r['status']}'")
            
    fbs = data.get("feedback", [])
    seen_fb_ids = set()
    for i, f in enumerate(fbs):
        prefix = f"feedback[{i}]"
        fid = f.get("id")
        if not fid:
            errors.append(f"{prefix}: missing 'id'")
        elif fid in seen_fb_ids:
            errors.append(f"{prefix}: duplicate id '{fid}'")
        seen_fb_ids.add(fid)
        
        if not f.get("recommendation_id"):
            errors.append(f"{prefix}: missing 'recommendation_id'")
        if f.get("contact_status") and f["contact_status"] not in ALLOWED_CONTACT:
            errors.append(f"{prefix}: invalid contact_status '{f['contact_status']}'")

    favs = data.get("favorites", [])
    if favs and not isinstance(favs, list):
        errors.append("Invalid 'favorites' array")
    else:
        for i, fav in enumerate(favs):
            if not fav.get("actor_id") or not fav.get("person_key"):
                errors.append(f"favorites[{i}]: missing actor_id or person_key")

    qfs = data.get("recommendation_feedback", [])
    if qfs and not isinstance(qfs, list):
        errors.append("Invalid 'recommendation_feedback' array")
    else:
        seen_qf_ids = set()
        for i, q in enumerate(qfs):
            prefix = f"recommendation_feedback[{i}]"
            qid = q.get("id")
            if not qid:
                errors.append(f"{prefix}: missing 'id'")
            elif qid in seen_qf_ids:
                errors.append(f"{prefix}: duplicate id '{qid}'")
            seen_qf_ids.add(qid)
            
            if q.get("value") not in ALLOWED_QUALITY_VALUES:
                errors.append(f"{prefix}: invalid quality value '{q.get('value')}'")
            if q.get("stage") not in ALLOWED_STAGES:
                errors.append(f"{prefix}: invalid stage '{q.get('stage')}'")

    return errors

def diff_data(data, conn):
    c = conn.cursor()
    diff = {
        "recs_to_add": [],
        "recs_to_update": [],
        "recs_identical": 0,
        "fb_to_add": [],
        "fb_to_update": [],
        "fb_identical": 0,
        "favs_to_add": [],
        "favs_identical": 0,
        "qf_to_add": [],
        "qf_to_update": [],
        "qf_identical": 0,
    }
    
    # Recommendations diff
    existing_recs = {row["id"]: row for row in c.execute("SELECT * FROM business_recommendations")}
    for r in data.get("recommendations", []):
        rid = r["id"]
        if rid not in existing_recs:
            diff["recs_to_add"].append(rid)
        else:
            old = existing_recs[rid]
            # check if updated_at is newer
            new_updated = r.get("updated_at", "")
            old_updated = old["updated_at"]
            if new_updated > old_updated or (r.get("title") != old["title"] or r.get("status") != old["status"]):
                diff["recs_to_update"].append(rid)
            else:
                diff["recs_identical"] += 1
                
    # Feedback diff
    existing_fb = {row["id"]: row for row in c.execute("SELECT * FROM business_feedback")}
    for f in data.get("feedback", []):
        fid = f["id"]
        if fid not in existing_fb:
            diff["fb_to_add"].append(fid)
        else:
            old = existing_fb[fid]
            if f.get("reviewed_at") != old["reviewed_at"] or f.get("next_action") != old["next_action"]:
                diff["fb_to_update"].append(fid)
            else:
                diff["fb_identical"] += 1
                
    # Favorites diff
    existing_favs = {(row["actor_id"], row["person_key"]) for row in c.execute("SELECT actor_id, person_key FROM business_favorites")}
    for fav in data.get("favorites", []):
        pair = (fav["actor_id"], fav["person_key"])
        if pair not in existing_favs:
            diff["favs_to_add"].append(pair)
        else:
            diff["favs_identical"] += 1
            
    # Quality feedback diff
    existing_qf = {row["id"]: row for row in c.execute("SELECT * FROM business_recommendation_feedback")}
    for q in data.get("recommendation_feedback", []):
        qid = q["id"]
        if qid not in existing_qf:
            diff["qf_to_add"].append(qid)
        else:
            old = existing_qf[qid]
            if q.get("value") != old["value"] or q.get("note") != old["note"]:
                diff["qf_to_update"].append(qid)
            else:
                diff["qf_identical"] += 1
                
    return diff

def import_data(data, conn, source_file="manual", file_sha256=""):
    diff = diff_data(data, conn)
    c = conn.cursor()
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # 1. Recommendations
    recs_added = 0
    recs_updated = 0
    for r in data.get("recommendations", []):
        rid = r["id"]
        if rid in diff["recs_to_add"]:
            c.execute("""
            INSERT INTO business_recommendations (
                id, domain_id, topic_id, title, research_question, reason, participation,
                conditions, suggested_action, assignee_id, due_date, status, is_demo, origin,
                candidate_id, provenance, links_json, expert_keys_json, capability_ids_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rid, r.get("domain_id", "diabetes"), r.get("topic_id"), r.get("title", ""),
                r.get("research_question"), r.get("reason"), r.get("participation"),
                r.get("conditions"), r.get("suggested_action"), r.get("assignee_id"),
                r.get("due_date"), r.get("status", "draft"), 1 if r.get("is_demo") else 0,
                r.get("origin"), r.get("candidate_id"), r.get("provenance"),
                json.dumps(r.get("links", []), ensure_ascii=False),
                json.dumps(r.get("expert_keys", []), ensure_ascii=False),
                json.dumps(r.get("capability_ids", []), ensure_ascii=False),
                r.get("created_at", now_str), r.get("updated_at", now_str)
            ))
            recs_added += 1
        elif rid in diff["recs_to_update"]:
            c.execute("""
            UPDATE business_recommendations SET
                domain_id = ?, topic_id = ?, title = ?, research_question = ?, reason = ?,
                participation = ?, conditions = ?, suggested_action = ?, assignee_id = ?,
                due_date = ?, status = ?, is_demo = ?, origin = ?, candidate_id = ?,
                provenance = ?, links_json = ?, expert_keys_json = ?, capability_ids_json = ?,
                updated_at = ?
            WHERE id = ?
            """, (
                r.get("domain_id", "diabetes"), r.get("topic_id"), r.get("title", ""),
                r.get("research_question"), r.get("reason"), r.get("participation"),
                r.get("conditions"), r.get("suggested_action"), r.get("assignee_id"),
                r.get("due_date"), r.get("status", "draft"), 1 if r.get("is_demo") else 0,
                r.get("origin"), r.get("candidate_id"), r.get("provenance"),
                json.dumps(r.get("links", []), ensure_ascii=False),
                json.dumps(r.get("expert_keys", []), ensure_ascii=False),
                json.dumps(r.get("capability_ids", []), ensure_ascii=False),
                r.get("updated_at", now_str), rid
            ))
            recs_updated += 1
            
    # 2. Feedback
    fb_added = 0
    fb_updated = 0
    for f in data.get("feedback", []):
        fid = f["id"]
        if fid in diff["fb_to_add"]:
            c.execute("""
            INSERT INTO business_feedback (
                id, recommendation_id, author_id, contact_status, contact_date, contact_name,
                institution, need, cohort, support, next_action, next_owner_id, next_date,
                is_demo, created_at, reviewed_at, review_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fid, f.get("recommendation_id"), f.get("author_id"),
                f.get("contact_status", "not_contacted"), f.get("contact_date"),
                f.get("contact_name"), f.get("institution"), f.get("need"),
                f.get("cohort"), f.get("support"), f.get("next_action"),
                f.get("next_owner_id"), f.get("next_date"), 1 if f.get("is_demo") else 0,
                f.get("created_at", now_str), f.get("reviewed_at"), f.get("review_note")
            ))
            fb_added += 1
        elif fid in diff["fb_to_update"]:
            c.execute("""
            UPDATE business_feedback SET
                contact_status = ?, contact_date = ?, contact_name = ?, institution = ?,
                need = ?, cohort = ?, support = ?, next_action = ?, next_owner_id = ?,
                next_date = ?, reviewed_at = ?, review_note = ?
            WHERE id = ?
            """, (
                f.get("contact_status", "not_contacted"), f.get("contact_date"),
                f.get("contact_name"), f.get("institution"), f.get("need"),
                f.get("cohort"), f.get("support"), f.get("next_action"),
                f.get("next_owner_id"), f.get("next_date"), f.get("reviewed_at"),
                f.get("review_note"), fid
            ))
            fb_updated += 1
            
    # 3. Favorites
    favs_added = 0
    for fav in data.get("favorites", []):
        pair = (fav["actor_id"], fav["person_key"])
        if pair in diff["favs_to_add"]:
            c.execute("""
            INSERT OR IGNORE INTO business_favorites (actor_id, person_key, created_at)
            VALUES (?, ?, ?)
            """, (fav["actor_id"], fav["person_key"], fav.get("created_at", now_str)))
            favs_added += 1
            
    # 4. Recommendation Quality Feedback
    qf_added = 0
    qf_updated = 0
    for q in data.get("recommendation_feedback", []):
        qid = q["id"]
        if qid in diff["qf_to_add"]:
            c.execute("""
            INSERT INTO business_recommendation_feedback (
                id, recommendation_id, author_id, value, stage, reasons_json, note,
                needs, is_demo, created_at, recommendation_updated_at, recommendation_snapshot_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                qid, q.get("recommendation_id"), q.get("author_id"), q.get("value"),
                q.get("stage", "before_contact"),
                json.dumps(q.get("reasons", []), ensure_ascii=False),
                q.get("note"), q.get("needs"), 1 if q.get("is_demo") else 0,
                q.get("created_at", now_str), q.get("recommendation_updated_at"),
                json.dumps(q.get("recommendation_snapshot", {}), ensure_ascii=False)
            ))
            qf_added += 1
        elif qid in diff["qf_to_update"]:
            c.execute("""
            UPDATE business_recommendation_feedback SET
                value = ?, stage = ?, reasons_json = ?, note = ?, needs = ?,
                recommendation_updated_at = ?, recommendation_snapshot_json = ?
            WHERE id = ?
            """, (
                q.get("value"), q.get("stage", "before_contact"),
                json.dumps(q.get("reasons", []), ensure_ascii=False),
                q.get("note"), q.get("needs"), q.get("recommendation_updated_at"),
                json.dumps(q.get("recommendation_snapshot", {}), ensure_ascii=False),
                qid
            ))
            qf_updated += 1

    # Record audit log
    c.execute("""
    INSERT INTO import_audit_logs (
        imported_at, source_file, file_sha256, recs_added, recs_updated,
        feedback_added, feedback_updated, favorites_added, quality_feedback_added,
        quality_feedback_updated
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        now_str, str(source_file), file_sha256, recs_added, recs_updated,
        fb_added, fb_updated, favs_added, qf_added, qf_updated
    ))
    
    conn.commit()
    return {
        "status": "success",
        "recs_added": recs_added,
        "recs_updated": recs_updated,
        "recs_identical": diff["recs_identical"],
        "fb_added": fb_added,
        "fb_updated": fb_updated,
        "fb_identical": diff["fb_identical"],
        "favs_added": favs_added,
        "favs_identical": diff["favs_identical"],
        "qf_added": qf_added,
        "qf_updated": qf_updated,
        "qf_identical": diff["qf_identical"],
    }

def export_to_dict(conn):
    c = conn.cursor()
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    recs = []
    for row in c.execute("SELECT * FROM business_recommendations ORDER BY created_at ASC"):
        d = dict(row)
        d["is_demo"] = bool(d["is_demo"])
        d["links"] = json.loads(d.pop("links_json") or "[]")
        d["expert_keys"] = json.loads(d.pop("expert_keys_json") or "[]")
        d["capability_ids"] = json.loads(d.pop("capability_ids_json") or "[]")
        recs.append(d)
        
    fbs = []
    for row in c.execute("SELECT * FROM business_feedback ORDER BY created_at ASC"):
        d = dict(row)
        d["is_demo"] = bool(d["is_demo"])
        fbs.append(d)
        
    favs = []
    for row in c.execute("SELECT * FROM business_favorites ORDER BY created_at ASC"):
        favs.append(dict(row))
        
    qfs = []
    for row in c.execute("SELECT * FROM business_recommendation_feedback ORDER BY created_at ASC"):
        d = dict(row)
        d["is_demo"] = bool(d["is_demo"])
        d["reasons"] = json.loads(d.pop("reasons_json") or "[]")
        d["recommendation_snapshot"] = json.loads(d.pop("recommendation_snapshot_json") or "{}")
        qfs.append(d)
        
    return {
        "schema": SCHEMA_VERSION,
        "version": 1,
        "exported_at": now_str,
        "scope": "业务数据库持久化导出；演示与真实条目按is_demo区分",
        "recommendations": recs,
        "feedback": fbs,
        "favorites": favs,
        "recommendation_feedback": qfs
    }

def main():
    parser = argparse.ArgumentParser(description="P02 Sales business data migration and persistence tool")
    parser.add_argument("--validate", type=Path, help="Validate export JSON against schema")
    parser.add_argument("--diff", type=Path, help="Preview differences between file and database")
    parser.add_argument("--import-file", type=Path, help="Idempotently import JSON file to sales_business.db")
    parser.add_argument("--backup", action="store_true", help="Backup existing sales_business.db before importing")
    parser.add_argument("--export-file", type=Path, help="Export sales_business.db into JSON format")
    args = parser.parse_args()

    conn = get_db()
    
    if args.validate:
        data = json.loads(args.validate.read_text(encoding="utf-8"))
        errors = validate_json_data(data)
        if errors:
            print(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False, indent=2))
            sys.exit(1)
        print(json.dumps({"valid": True, "recs": len(data.get("recommendations", [])), "feedback": len(data.get("feedback", [])), "favorites": len(data.get("favorites", [])), "quality_feedback": len(data.get("recommendation_feedback", []))}, ensure_ascii=False))
        
    elif args.diff:
        data = json.loads(args.diff.read_text(encoding="utf-8"))
        errors = validate_json_data(data)
        if errors:
            print(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False, indent=2))
            sys.exit(1)
        diff = diff_data(data, conn)
        print(json.dumps({"valid": True, "diff": diff}, ensure_ascii=False, indent=2))
        
    elif args.import_file:
        data = json.loads(args.import_file.read_text(encoding="utf-8"))
        errors = validate_json_data(data)
        if errors:
            print(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False, indent=2))
            sys.exit(1)
        if args.backup and DB_PATH.is_file():
            backup_path = DB_PATH.with_suffix(f".bak_{int(datetime.datetime.now().timestamp())}.db")
            shutil.copyfile(DB_PATH, backup_path)
            print(f"Backup created at: {backup_path.name}")
        h = hashlib.sha256(args.import_file.read_bytes()).hexdigest()
        result = import_data(data, conn, source_file=args.import_file.name, file_sha256=h)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif args.export_file:
        out = export_to_dict(conn)
        args.export_file.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": "exported", "path": str(args.export_file), "counts": {k: len(out[k]) for k in ["recommendations", "feedback", "favorites", "recommendation_feedback"]}}, ensure_ascii=False))

    conn.close()

if __name__ == "__main__":
    main()
