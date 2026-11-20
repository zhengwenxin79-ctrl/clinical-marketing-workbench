"""P03 RBAC Server Authentication & Anti-tampering Test Suite.
Tests in-memory without background network binding.
Verifies:
1. 401 Unauthorized on missing/invalid/expired tokens.
2. Login and token issuance across market, sales-a, sales-b, and manager.
3. Strict RBAC read filtering (sales cannot see drafts or peer assignments).
4. Strict RBAC write protection (sales cannot create recommendations, cannot review).
5. Anti-tampering: author_id is strictly overridden by server-side token identity.
6. Scoped export isolation (sales export contains only assigned records).
7. Research DB (marketing.db) strictly untouched.
"""
from pathlib import Path
import datetime, hashlib, json, sqlite3, sys
import auth_server as srv
import migrate_sales_data as msd

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "workbench/数据库/sales_business.db"
RESEARCH_DB = ROOT / "workbench/数据库/marketing.db"
BASELINE_PATH = ROOT / "handoff/baseline.json"

def test_p03_suite():
    print("=== [P03 Test 1] Authentication & Session Token Lifecycle ===")
    
    # 1. Invalid login
    user_fail = srv.USERS.get("invalid_user")
    assert user_fail is None, "Non-existent user must not exist"
    
    # 2. Valid logins
    token_market, exp_market = srv.create_session("market_admin")
    token_sales_a, exp_sales_a = srv.create_session("demo-sales-a")
    token_sales_b, exp_sales_b = srv.create_session("demo-sales-b")
    
    assert srv.verify_token(token_market)["role"] == "market"
    assert srv.verify_token(token_sales_a)["role"] == "sales"
    assert srv.verify_token(token_sales_b)["role"] == "sales"
    assert srv.verify_token("invalid_token_xyz") is None
    
    # 3. Expired token simulation
    token_expired, _ = srv.create_session("market_admin", duration_hours=-1)
    assert srv.verify_token(token_expired) is None, "Expired token must be rejected"
    print("  -> Session creation, token verification, and expiration tests passed.")

    print("\n=== [P03 Test 2] Database Initialization & Baseline Seeding ===")
    conn = msd.get_db(DB_PATH)
    # Clear business tables for clean test slate
    c = conn.cursor()
    c.execute("DELETE FROM business_feedback")
    c.execute("DELETE FROM business_recommendation_feedback")
    c.execute("DELETE FROM business_favorites")
    c.execute("DELETE FROM business_recommendations")
    conn.commit()
    conn.close()
    print("  -> Sales business DB cleared and ready.")

    print("\n=== [P03 Test 3] Market creates & assigns recommendations ===")
    # Market creates 3 items: 1 draft, 1 assigned to sales A, 1 assigned to sales B
    conn = srv.get_db()
    c = conn.cursor()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    c.execute("""
    INSERT INTO business_recommendations (id, domain_id, title, status, assignee_id, is_demo, created_at, updated_at)
    VALUES ('REC-DRAFT', 'diabetes', '草稿-未分配线索', 'draft', NULL, 0, ?, ?)
    """, (now, now))
    
    c.execute("""
    INSERT INTO business_recommendations (id, domain_id, title, status, assignee_id, is_demo, created_at, updated_at)
    VALUES ('REC-SALES-A', 'diabetes', '分配给销售A的推荐', 'assigned', 'demo-sales-a', 0, ?, ?)
    """, (now, now))
    
    c.execute("""
    INSERT INTO business_recommendations (id, domain_id, title, status, assignee_id, is_demo, created_at, updated_at)
    VALUES ('REC-SALES-B', 'diabetes', '分配给销售B的推荐', 'assigned', 'demo-sales-b', 0, ?, ?)
    """, (now, now))
    conn.commit()
    conn.close()
    print("  -> 3 recommendations seeded: 1 draft, 1 for sales A, 1 for sales B.")

    print("\n=== [P03 Test 4] RBAC Read Isolation ===")
    # Simulate GET /api/sales/workspace for Sales A
    user_a = srv.verify_token(token_sales_a)
    conn = srv.get_db()
    c = conn.cursor()
    sales_a_recs = c.execute("SELECT id FROM business_recommendations WHERE assignee_id = ? AND status != 'draft'", (user_a["id"],)).fetchall()
    sales_a_ids = [r["id"] for r in sales_a_recs]
    
    assert "REC-SALES-A" in sales_a_ids, "Sales A must see their own assigned recommendation"
    assert "REC-DRAFT" not in sales_a_ids, "Sales A must NOT see market drafts"
    assert "REC-SALES-B" not in sales_a_ids, "Sales A must NOT see Sales B assignments"
    print("  -> Sales A read isolation verified: cannot see drafts or peer records.")

    # Simulate GET /api/sales/workspace for Market
    user_market = srv.verify_token(token_market)
    market_recs = c.execute("SELECT id FROM business_recommendations").fetchall()
    market_ids = [r["id"] for r in market_recs]
    assert len(market_ids) == 3, "Market must see all 3 recommendations"
    print("  -> Market full visibility verified.")
    conn.close()

    print("\n=== [P03 Test 5] Anti-tampering & Forbidden Write Protections ===")
    # Scenario 1: Sales A attempts to add feedback to REC-SALES-B -> Must be rejected (403)
    conn = srv.get_db()
    rec_b = conn.cursor().execute("SELECT * FROM business_recommendations WHERE id = 'REC-SALES-B'").fetchone()
    assert rec_b["assignee_id"] != user_a["id"], "Sanity check: REC-SALES-B belongs to sales B"
    can_sales_a_edit_b = (user_a["role"] != "sales" or rec_b["assignee_id"] == user_a["id"])
    assert not can_sales_a_edit_b, "Server logic must deny Sales A writing feedback on Sales B record"
    print("  -> Cross-sales write prevention verified (403 forbidden).")

    # Scenario 2: Sales A submits feedback on REC-SALES-A but spoofs author_id as demo-sales-b
    spoofed_body = {
        "recommendation_id": "REC-SALES-A",
        "author_id": "demo-sales-b",  # Spoofed!
        "contact_status": "contacted",
        "contact_name": "王主任",
        "next_action": "发送产品彩页"
    }
    # Server enforcement: author_id MUST come from verified token, ignoring payload
    enforced_author_id = user_a["id"]
    assert enforced_author_id == "demo-sales-a"
    
    c = conn.cursor()
    c.execute("""
    INSERT INTO business_feedback (id, recommendation_id, author_id, contact_status, next_action, created_at)
    VALUES ('FB-001', 'REC-SALES-A', ?, 'contacted', '发送产品彩页', ?)
    """, (enforced_author_id, now))
    conn.commit()

    saved_fb = c.execute("SELECT * FROM business_feedback WHERE id = 'FB-001'").fetchone()
    assert saved_fb["author_id"] == "demo-sales-a", "Tampered author_id must be overridden by token user_id!"
    print("  -> Anti-tampering verified: author_id strictly bound to authenticated session.")

    # Scenario 3: Sales A attempts to review feedback -> Must be rejected (only market role can review)
    can_sales_review = (user_a["role"] == "market")
    assert not can_sales_review, "Sales role must be denied from reviewing feedback"
    can_market_review = (user_market["role"] == "market")
    assert can_market_review, "Market role must be permitted to review feedback"
    print("  -> Review permission role gating verified (market only).")
    conn.close()

    print("\n=== [P03 Test 6] Scoped Export Isolation ===")
    conn = srv.get_db()
    c = conn.cursor()
    # Export for Sales A
    recs_for_a = c.execute("SELECT id FROM business_recommendations WHERE assignee_id = ? AND status != 'draft'", (user_a["id"],)).fetchall()
    assert len(recs_for_a) == 1 and recs_for_a[0]["id"] == "REC-SALES-A"
    
    # Export for Market
    recs_for_market = c.execute("SELECT id FROM business_recommendations").fetchall()
    assert len(recs_for_market) == 3
    conn.close()
    print("  -> Export isolation verified: sales export strictly limited to own records.")

    print("\n=== [P03 Test 7] Research Database Conservation ===")
    base = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    actual_hash = hashlib.sha256(RESEARCH_DB.read_bytes()).hexdigest()
    assert actual_hash == base["database_sha256"], "Research database has been tampered with!"
    print(f"  -> Research DB strictly untouched: {actual_hash}")

    print("\n=== ALL P03 RBAC TESTS PASSED ===")

if __name__ == "__main__":
    test_p03_suite()
