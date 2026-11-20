"""P03 Light-weight authenticated HTTP server & RBAC service.
Built with Python standard library.
Enforces real server-side authentication (Bearer Token) and role-based
access control (RBAC) across two roles: market (市场部) and sales (销售代表).
- Market (市场部): full visibility across all views, creates & assigns leads, reviews feedback.
- Sales (销售代表): isolated per representative, only sees and acts on own assigned leads.
Guarantees anti-tampering: author_id is strictly derived from server token.
Strictly touches only sales_business.db, leaving marketing.db pristine.
"""
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
import datetime, hashlib, hmac, json, os, secrets, sqlite3, sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import manage_conference_updates
DB_PATH = ROOT / "workbench/数据库/sales_business.db"
SECRET_KEY = secrets.token_hex(32)

USERS = {
    "market": {
        "id": "market",
        "name": "市场部人员",
        "role": "market",
        "password_hash": hashlib.sha256("market123".encode()).hexdigest(),
        "description": "市场部全权账号：可查看所有界面（学术事实、PI推荐、分配记录、全销售反馈与复盘）"
    },
    "market_admin": {
        "id": "market_admin",
        "name": "市场专员-李明",
        "role": "market",
        "password_hash": hashlib.sha256("market123".encode()).hexdigest(),
        "description": "市场部人员"
    },
    "demo-sales-a": {
        "id": "demo-sales-a",
        "name": "销售代表-张强(华北)",
        "role": "sales",
        "password_hash": hashlib.sha256("sales123".encode()).hexdigest(),
        "description": "销售代表A：仅查看并跟进分配给本人的线索"
    },
    "demo-sales-b": {
        "id": "demo-sales-b",
        "name": "销售代表-陈丽(华南)",
        "role": "sales",
        "password_hash": hashlib.sha256("sales123".encode()).hexdigest(),
        "description": "销售代表B：仅查看并跟进分配给本人的线索"
    }
}

ACTIVE_SESSIONS = {}

def create_session(user_id, duration_hours=24):
    token = secrets.token_urlsafe(32)
    expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=duration_hours)
    ACTIVE_SESSIONS[token] = {
        "user_id": user_id,
        "expires_at": expires
    }
    return token, expires

def verify_token(token):
    if not token or token not in ACTIVE_SESSIONS:
        return None
    session = ACTIVE_SESSIONS[token]
    if datetime.datetime.now(datetime.timezone.utc) > session["expires_at"]:
        del ACTIVE_SESSIONS[token]
        return None
    return USERS.get(session["user_id"])

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

class RBACRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_json(self, status_code, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def get_auth_user(self):
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            return verify_token(token)
        return None

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return None

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/"):
            return self.handle_api_get(path, parse_qs(parsed.query))
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/"):
            return self.handle_api_post(path)
        self.send_json(404, {"error": "Not Found"})

    def handle_api_get(self, path, query):
        if path == "/api/auth/me":
            user = self.get_auth_user()
            if not user:
                return self.send_json(401, {"error": "Unauthorized / Session Expired"})
            return self.send_json(200, {"user": {"id": user["id"], "name": user["name"], "role": user["role"]}})

        user = self.get_auth_user()
        if not user:
            return self.send_json(401, {"error": "Authentication required"})

        if path == "/api/sales/workspace":
            conn = get_db()
            c = conn.cursor()
            
            # RBAC Isolation
            if user["role"] == "sales":
                recs_query = "SELECT * FROM business_recommendations WHERE assignee_id = ? AND status != 'draft' ORDER BY updated_at DESC"
                recs_rows = c.execute(recs_query, (user["id"],)).fetchall()
                allowed_rec_ids = {r["id"] for r in recs_rows}
                
                fb_rows = [r for r in c.execute("SELECT * FROM business_feedback ORDER BY created_at DESC").fetchall() if r["recommendation_id"] in allowed_rec_ids]
                fav_rows = c.execute("SELECT * FROM business_favorites WHERE actor_id = ?", (user["id"],)).fetchall()
                qf_rows = [r for r in c.execute("SELECT * FROM business_recommendation_feedback ORDER BY created_at DESC").fetchall() if r["recommendation_id"] in allowed_rec_ids]
            else: # market or manager
                recs_rows = c.execute("SELECT * FROM business_recommendations ORDER BY updated_at DESC").fetchall()
                fb_rows = c.execute("SELECT * FROM business_feedback ORDER BY created_at DESC").fetchall()
                fav_rows = c.execute("SELECT * FROM business_favorites ORDER BY created_at DESC").fetchall()
                qf_rows = c.execute("SELECT * FROM business_recommendation_feedback ORDER BY created_at DESC").fetchall()

            conn.close()

            def clean_rec(r):
                d = dict(r)
                d["is_demo"] = bool(d["is_demo"])
                d["links"] = json.loads(d.pop("links_json") or "[]")
                d["expert_keys"] = json.loads(d.pop("expert_keys_json") or "[]")
                d["capability_ids"] = json.loads(d.pop("capability_ids_json") or "[]")
                return d

            def clean_qf(q):
                d = dict(q)
                d["is_demo"] = bool(d["is_demo"])
                d["reasons"] = json.loads(d.pop("reasons_json") or "[]")
                d["recommendation_snapshot"] = json.loads(d.pop("recommendation_snapshot_json") or "{}")
                return d

            return self.send_json(200, {
                "user": {"id": user["id"], "name": user["name"], "role": user["role"]},
                "recommendations": [clean_rec(r) for r in recs_rows],
                "feedback": [dict(f) for f in fb_rows],
                "favorites": [dict(f) for f in fav_rows],
                "recommendation_feedback": [clean_qf(q) for q in qf_rows]
            })

        if path == "/api/sales/export":
            # Scoped export
            conn = get_db()
            c = conn.cursor()
            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            if user["role"] == "sales":
                recs_rows = c.execute("SELECT * FROM business_recommendations WHERE assignee_id = ? AND status != 'draft'", (user["id"],)).fetchall()
                allowed_rec_ids = {r["id"] for r in recs_rows}
                fb_rows = [r for r in c.execute("SELECT * FROM business_feedback").fetchall() if r["recommendation_id"] in allowed_rec_ids]
                fav_rows = c.execute("SELECT * FROM business_favorites WHERE actor_id = ?", (user["id"],)).fetchall()
                qf_rows = [r for r in c.execute("SELECT * FROM business_recommendation_feedback").fetchall() if r["recommendation_id"] in allowed_rec_ids]
                scope_label = f"销售代表个人记录导出（{user['name']}）"
            else:
                recs_rows = c.execute("SELECT * FROM business_recommendations").fetchall()
                fb_rows = c.execute("SELECT * FROM business_feedback").fetchall()
                fav_rows = c.execute("SELECT * FROM business_favorites").fetchall()
                qf_rows = c.execute("SELECT * FROM business_recommendation_feedback").fetchall()
                scope_label = f"全量业务协同记录导出（{user['role']}授权）"

            conn.close()

            def rec_to_dict(r):
                d = dict(r)
                d["is_demo"] = bool(d["is_demo"])
                d["links"] = json.loads(d.pop("links_json") or "[]")
                d["expert_keys"] = json.loads(d.pop("expert_keys_json") or "[]")
                d["capability_ids"] = json.loads(d.pop("capability_ids_json") or "[]")
                return d

            def qf_to_dict(q):
                d = dict(q)
                d["is_demo"] = bool(d["is_demo"])
                d["reasons"] = json.loads(d.pop("reasons_json") or "[]")
                d["recommendation_snapshot"] = json.loads(d.pop("recommendation_snapshot_json") or "{}")
                return d

            return self.send_json(200, {
                "schema": "clinical-sales-export:v1",
                "version": 1,
                "exported_at": now_str,
                "scope": scope_label,
                "exported_by": {"id": user["id"], "role": user["role"]},
                "recommendations": [rec_to_dict(r) for r in recs_rows],
                "feedback": [dict(f) for f in fb_rows],
                "favorites": [dict(f) for f in fav_rows],
                "recommendation_feedback": [qf_to_dict(q) for q in qf_rows]
            })

        if path == "/api/conference/queue":
            if user["role"] != "market":
                return self.send_json(403, {"error": "权限拒绝：仅市场部人员可查看会议审核入库队列"})
            status_filter = query.get("status", [None])[0]
            field_filter = query.get("field_id", [None])[0]
            conn = manage_conference_updates.get_db()
            c = conn.cursor()
            q = "SELECT * FROM conference_review_queue WHERE 1=1"
            params = []
            if status_filter and status_filter != "all":
                q += " AND review_status = ?"
                params.append(status_filter)
            if field_filter and field_filter != "all":
                q += " AND field_id = ?"
                params.append(field_filter)
            q += " ORDER BY created_at DESC"
            rows = [dict(r) for r in c.execute(q, params).fetchall()]
            conn.close()
            return self.send_json(200, {"total": len(rows), "items": rows})

        if path == "/api/conference/weekly-events":
            conn = manage_conference_updates.get_db()
            c = conn.cursor()
            rows = [dict(r) for r in c.execute("SELECT * FROM weekly_update_events ORDER BY observed_at DESC").fetchall()]
            conn.close()
            return self.send_json(200, {"total": len(rows), "events": rows})

        return self.send_json(404, {"error": "API route not found"})

    def handle_api_post(self, path):
        body = self.read_json_body()
        if body is None:
            return self.send_json(400, {"error": "Malformed JSON body"})

        if path == "/api/auth/login":
            username = body.get("username", "").strip()
            password = body.get("password", "")
            user = USERS.get(username)
            if not user or user["password_hash"] != hashlib.sha256(password.encode()).hexdigest():
                return self.send_json(401, {"error": "用户名或密码错误"})

            token, expires = create_session(user["id"])
            return self.send_json(200, {
                "token": token,
                "expires_at": expires.isoformat(),
                "user": {"id": user["id"], "name": user["name"], "role": user["role"]}
            })

        user = self.get_auth_user()
        if not user:
            return self.send_json(401, {"error": "Authentication required"})

        if path == "/api/auth/logout":
            auth_header = self.headers.get("Authorization", "")
            token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""
            if token in ACTIVE_SESSIONS:
                del ACTIVE_SESSIONS[token]
            return self.send_json(200, {"status": "logged_out"})

        conn = get_db()
        c = conn.cursor()
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if path == "/api/sales/recommendations":
            # Only market can create/assign recommendations
            if user["role"] != "market":
                conn.close()
                return self.send_json(403, {"error": "权限拒绝：仅市场部人员可创建或分配推荐"})

            rid = body.get("id") or ("REC-" + secrets.token_hex(6))
            title = body.get("title", "").strip()
            if not title:
                conn.close()
                return self.send_json(400, {"error": "标题不能为空"})

            assignee_id = body.get("assignee_id")
            status = body.get("status", "draft")
            if status == "assigned" and not assignee_id:
                conn.close()
                return self.send_json(400, {"error": "分配状态必须指定负责销售"})

            # Upsert
            existing = c.execute("SELECT id FROM business_recommendations WHERE id = ?", (rid,)).fetchone()
            if existing:
                c.execute("""
                UPDATE business_recommendations SET
                    domain_id = ?, topic_id = ?, title = ?, research_question = ?, reason = ?,
                    participation = ?, conditions = ?, suggested_action = ?, assignee_id = ?,
                    due_date = ?, status = ?, is_demo = ?, origin = ?, candidate_id = ?,
                    provenance = ?, links_json = ?, expert_keys_json = ?, capability_ids_json = ?,
                    updated_at = ?
                WHERE id = ?
                """, (
                    body.get("domain_id", "diabetes"), body.get("topic_id"), title,
                    body.get("research_question"), body.get("reason"), body.get("participation"),
                    body.get("conditions"), body.get("suggested_action"), assignee_id,
                    body.get("due_date"), status, 1 if body.get("is_demo") else 0,
                    body.get("origin"), body.get("candidate_id"), body.get("provenance"),
                    json.dumps(body.get("links", []), ensure_ascii=False),
                    json.dumps(body.get("expert_keys", []), ensure_ascii=False),
                    json.dumps(body.get("capability_ids", []), ensure_ascii=False),
                    now_str, rid
                ))
            else:
                c.execute("""
                INSERT INTO business_recommendations (
                    id, domain_id, topic_id, title, research_question, reason, participation,
                    conditions, suggested_action, assignee_id, due_date, status, is_demo, origin,
                    candidate_id, provenance, links_json, expert_keys_json, capability_ids_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rid, body.get("domain_id", "diabetes"), body.get("topic_id"), title,
                    body.get("research_question"), body.get("reason"), body.get("participation"),
                    body.get("conditions"), body.get("suggested_action"), assignee_id,
                    body.get("due_date"), status, 1 if body.get("is_demo") else 0,
                    body.get("origin"), body.get("candidate_id"), body.get("provenance"),
                    json.dumps(body.get("links", []), ensure_ascii=False),
                    json.dumps(body.get("expert_keys", []), ensure_ascii=False),
                    json.dumps(body.get("capability_ids", []), ensure_ascii=False),
                    now_str, now_str
                ))
            conn.commit()
            conn.close()
            return self.send_json(200, {"status": "saved", "id": rid})

        if path == "/api/sales/feedback":
            # Sales adds contact feedback
            rid = body.get("recommendation_id")
            rec = c.execute("SELECT * FROM business_recommendations WHERE id = ?", (rid,)).fetchone()
            if not rec:
                conn.close()
                return self.send_json(404, {"error": "推荐不存在"})

            if user["role"] == "sales" and rec["assignee_id"] != user["id"]:
                conn.close()
                return self.send_json(403, {"error": "越权拒绝：该推荐未分配给当前销售账号"})

            fid = body.get("id") or ("FB-" + secrets.token_hex(6))
            # STRICT ANTI-TAMPERING: author_id is ALWAYS current authenticated user ID
            author_id = user["id"]

            c.execute("""
            INSERT INTO business_feedback (
                id, recommendation_id, author_id, contact_status, contact_date, contact_name,
                institution, need, cohort, support, next_action, next_owner_id, next_date,
                is_demo, created_at, reviewed_at, review_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fid, rid, author_id, body.get("contact_status", "contacted"),
                body.get("contact_date"), body.get("contact_name"), body.get("institution"),
                body.get("need"), body.get("cohort"), body.get("support"),
                body.get("next_action"), body.get("next_owner_id", author_id),
                body.get("next_date"), 1 if rec["is_demo"] else 0,
                now_str, None, ""
            ))
            # Update recommendation status to in_progress
            if rec["status"] == "assigned":
                c.execute("UPDATE business_recommendations SET status = 'in_progress', updated_at = ? WHERE id = ?", (now_str, rid))

            conn.commit()
            conn.close()
            return self.send_json(200, {"status": "saved", "id": fid, "author_id": author_id})

        if path == "/api/sales/quality-feedback":
            # Recommendation quality evaluation
            rid = body.get("recommendation_id")
            rec = c.execute("SELECT * FROM business_recommendations WHERE id = ?", (rid,)).fetchone()
            if not rec:
                conn.close()
                return self.send_json(404, {"error": "推荐不存在"})

            if user["role"] == "sales" and rec["assignee_id"] != user["id"]:
                conn.close()
                return self.send_json(403, {"error": "越权拒绝：只能评价分配给本人的推荐"})

            qid = body.get("id") or ("RQ-" + secrets.token_hex(6))
            author_id = user["id"]
            val = body.get("value")
            if val not in {"useful", "partly_useful", "not_useful", "not_assessed"}:
                conn.close()
                return self.send_json(400, {"error": "评价取值非法"})

            snapshot = {
                "title": rec["title"],
                "reason": rec["reason"],
                "origin": rec["origin"] or "manual"
            }

            c.execute("""
            INSERT INTO business_recommendation_feedback (
                id, recommendation_id, author_id, value, stage, reasons_json, note,
                needs, is_demo, created_at, recommendation_updated_at, recommendation_snapshot_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                qid, rid, author_id, val, body.get("stage", "before_contact"),
                json.dumps(body.get("reasons", []), ensure_ascii=False),
                body.get("note", ""), body.get("needs", ""), 1 if rec["is_demo"] else 0,
                now_str, rec["updated_at"], json.dumps(snapshot, ensure_ascii=False)
            ))
            conn.commit()
            conn.close()
            return self.send_json(200, {"status": "saved", "id": qid, "author_id": author_id})

        if path == "/api/sales/feedback/review":
            # Market marks feedback reviewed
            if user["role"] != "market":
                conn.close()
                return self.send_json(403, {"error": "权限拒绝：仅市场部人员可复核跟进"})

            fid = body.get("feedback_id")
            note = body.get("review_note", "").strip()
            c.execute("UPDATE business_feedback SET reviewed_at = ?, review_note = ? WHERE id = ?", (now_str, note, fid))
            conn.commit()
            conn.close()
            return self.send_json(200, {"status": "reviewed", "feedback_id": fid})

        if path == "/api/sales/favorites/toggle":
            pkey = body.get("person_key")
            if not pkey:
                conn.close()
                return self.send_json(400, {"error": "缺少 person_key"})

            actor_id = user["id"]
            existing = c.execute("SELECT * FROM business_favorites WHERE actor_id = ? AND person_key = ?", (actor_id, pkey)).fetchone()
            if existing:
                c.execute("DELETE FROM business_favorites WHERE actor_id = ? AND person_key = ?", (actor_id, pkey))
                saved = False
            else:
                c.execute("INSERT INTO business_favorites (actor_id, person_key, created_at) VALUES (?, ?, ?)", (actor_id, pkey, now_str))
                saved = True
            conn.commit()
            conn.close()
            return self.send_json(200, {"saved": saved, "person_key": pkey, "actor_id": actor_id})

        if path == "/api/conference/review":
            if user["role"] != "market":
                conn.close()
                return self.send_json(403, {"error": "权限拒绝：仅市场部人员可执行会议审核"})
            conn.close()
            queue_id = body.get("queue_id")
            action = body.get("action")
            note = body.get("note", "")
            if not queue_id or action not in ("approve", "reject"):
                return self.send_json(400, {"error": "缺少 queue_id 或 action 取值非法 (approve/reject)"})
            res = manage_conference_updates.review_queue_item(queue_id, action, reviewed_by=user["id"], note=note)
            if res.get("success"):
                manage_conference_updates.sync_weekly_change_log()
            return self.send_json(200 if res.get("success") else 400, res)

        if path == "/api/conference/ingest":
            if user["role"] != "market":
                conn.close()
                return self.send_json(403, {"error": "权限拒绝：仅市场部人员可提交采集批次入库"})
            conn.close()
            items = body.get("items", [])
            batch_id = body.get("batch_id")
            if not isinstance(items, list) or not items:
                return self.send_json(400, {"error": "items 必须是非空数组"})
            res = manage_conference_updates.ingest_crawled_conferences(items, batch_id=batch_id)
            return self.send_json(200, res)

        conn.close()
        return self.send_json(404, {"error": "API route not found"})

def run_server(port=8768):
    server = ThreadingHTTPServer(("127.0.0.1", port), RBACRequestHandler)
    print(f"RBAC Server started on http://127.0.0.1:{port}", flush=True)
    return server

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8768)
    args = parser.parse_args()
    s = run_server(args.port)
    try:
        s.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        s.server_close()
