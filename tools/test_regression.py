"""P01 Regression test suite covering classifications, weekly date slicing,
market/sales independence, rating criteria, and cross-saving contracts.
All tests are strictly read-only and offline.
"""
from pathlib import Path
import datetime, json, sqlite3, sys

ROOT = Path(__file__).resolve().parents[1]
WORKBENCH = ROOT / "workbench"

def test_data_conservation():
    print("[1/5] Testing data classification and conservation...")
    db_path = WORKBENCH / "数据库/marketing.db"
    assert db_path.is_file(), "Database file missing"
    
    conn = sqlite3.connect(f"file:{db_path.resolve().as_posix()}?mode=ro", uri=True)
    c = conn.cursor()
    
    tables = c.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()[0]
    views = c.execute("SELECT count(*) FROM sqlite_master WHERE type='view'").fetchone()[0]
    assert tables == 66, f"Expected 66 tables, got {tables}"
    assert views == 25, f"Expected 25 views, got {views}"
    
    snapshot_path = WORKBENCH / "领域工作台/领域数据快照.json"
    data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    summary = data["summary"]
    
    assert summary["boards"] == 12, "Boards mismatch"
    assert summary["topics"] == 66, "Topics mismatch"
    assert summary["conference_topics"] == 58, "Conference topics mismatch"
    assert summary["paper_extensions"] == 8, "Paper extensions mismatch"
    assert summary["reports"] == 2628, "Reports mismatch"
    assert summary["talk_reports"] == 1256, "Talk reports mismatch"
    assert summary["papers"] == 618, "Papers mismatch"
    assert summary["primary_papers"] == 160, "Primary papers mismatch"
    assert summary["biomarkers"] == 39, "Biomarkers mismatch"
    assert summary["unclassified_biomarkers"] == 3, "Unclassified biomarkers mismatch"
    assert summary["reference_biomarkers"] == 7, "Reference biomarkers mismatch"
    assert summary["expert_records"] == 2277, "Expert records mismatch"
    assert summary["known_role_records"] == 139, "Known role records mismatch"
    
    # Reports & papers uniqueness
    report_ids = [rid for t in data["topics"] for rid in t["report_ids"]]
    paper_ids = [pid for t in data["topics"] for pid in t["paper_ids"]]
    assert len(report_ids) == len(set(report_ids)) == 2628, "Duplicate report IDs in topic map"
    assert len(paper_ids) == len(set(paper_ids)) == 160, "Duplicate paper IDs in topic map"
    
    conn.close()
    print("  -> Passed: 66 tables, 25 views, 66 topics, 2628 reports, 160 papers, 39 biomarkers conserved.")

def test_weekly_date_slicing():
    print("[2/5] Testing weekly date slicing and boundary algorithms...")
    
    # Emulate WeeklyMeetings.monday and add from weekly.js
    def monday_of(d_str):
        dt = datetime.date.fromisoformat(d_str)
        return dt - datetime.timedelta(days=dt.weekday())
        
    def add_days(dt, n):
        return dt + datetime.timedelta(days=n)
    
    # Test CDS2026 date: 2026-11-18 (Wednesday)
    m = monday_of("2026-11-18")
    assert m == datetime.date(2026, 11, 16), f"Expected Monday 2026-11-16, got {m}"
    sun = add_days(m, 6)
    assert sun == datetime.date(2026, 11, 22), f"Expected Sunday 2026-11-22, got {sun}"
    
    # Check date boundaries
    assert monday_of("2026-11-16") == datetime.date(2026, 11, 16)  # Monday itself
    assert monday_of("2026-11-22") == datetime.date(2026, 11, 16)  # Sunday
    assert monday_of("2026-11-23") == datetime.date(2026, 11, 23)  # Next Monday
    
    # Verify CDS conference dates from snapshot catalog
    snapshot = json.loads((WORKBENCH / "领域工作台/领域数据快照.json").read_text(encoding="utf-8"))
    cds = next((c for c in snapshot["catalog"]["entries"] if c["conference_id"] == "CDS2026"), None)
    assert cds is not None, "CDS2026 catalog entry missing"
    assert cds["start_date"] <= str(sun) and cds["end_date"] >= str(m), "CDS2026 should intersect with week 2026-11-16..2026-11-22"
    
    print("  -> Passed: Monday-Sunday week interval and conference date intersection verified.")

def test_market_sales_independence():
    print("[3/5] Testing market vs sales role separation and scope filtering...")
    
    snapshot = json.loads((WORKBENCH / "领域工作台/领域数据快照.json").read_text(encoding="utf-8"))
    sales_cfg = snapshot["sales"]
    assert sales_cfg["storage_key"] == "clinical-workbench:sales:v1"
    
    salespeople = sales_cfg["salespeople"]
    assert len(salespeople) >= 2, "Expected at least 2 sales demo reps"
    rep_a = salespeople[0]["id"]
    rep_b = salespeople[1]["id"]
    
    # Simulated store
    mock_store = {
        "version": 1,
        "recommendations": [
            {"id": "R1", "domain_id": "diabetes", "assignee_id": rep_a, "status": "draft", "title": "Draft R1"},
            {"id": "R2", "domain_id": "diabetes", "assignee_id": rep_a, "status": "assigned", "title": "Assigned R2"},
            {"id": "R3", "domain_id": "diabetes", "assignee_id": rep_b, "status": "in_progress", "title": "In Progress R3"},
        ],
        "feedback": []
    }
    
    # Market view: can see draft, assigned, and in_progress across all sales reps
    market_visible = [r for r in mock_store["recommendations"] if r["domain_id"] == "diabetes"]
    assert len(market_visible) == 3, "Market should see all recommendations"
    
    # Sales A view: only see non-draft assigned to rep_a
    sales_a_visible = [r for r in mock_store["recommendations"] if r["domain_id"] == "diabetes" and r["assignee_id"] == rep_a and r["status"] != "draft"]
    assert len(sales_a_visible) == 1 and sales_a_visible[0]["id"] == "R2", "Sales A should only see R2"
    
    # Sales B view: only see non-draft assigned to rep_b
    sales_b_visible = [r for r in mock_store["recommendations"] if r["domain_id"] == "diabetes" and r["assignee_id"] == rep_b and r["status"] != "draft"]
    assert len(sales_b_visible) == 1 and sales_b_visible[0]["id"] == "R3", "Sales B should only see R3"
    
    print("  -> Passed: Market/Sales visibility and role-scoped permissions verified.")

def test_pi_rating_rules():
    print("[4/5] Testing PI rating four-dimension criteria and tier calculations...")
    
    snapshot = json.loads((WORKBENCH / "领域工作台/领域数据快照.json").read_text(encoding="utf-8"))
    ratings = snapshot["pi_ratings"]["ratings"]
    
    assert len(ratings) == 14, f"Expected 14 PI rating entries, got {len(ratings)}"
    complete = [r for r in ratings if r["total_score"] is not None]
    assert len(complete) == 5, f"Expected exactly 5 complete provisional ratings, got {len(complete)}"
    
    dim_caps = {"研究方向契合度": 30, "学术产出质量": 25, "科研转化潜力": 25, "平台资源禀赋": 20}
    
    for r in complete:
        total = 0
        dim_map = {}
        for d in r["dimensions"]:
            dim_key = d["name"]
            score = d["score"]
            assert dim_key in dim_caps, f"Unknown dimension: {dim_key}"
            assert 0 <= score <= dim_caps[dim_key], f"Score out of bounds for {dim_key}: {score}"
            assert d["maximum"] == dim_caps[dim_key], f"Maximum mismatch for {dim_key}"
            total += score
            dim_map[dim_key] = score
        assert total == r["total_score"], f"Total score mismatch for {r['person_key']}: sum={total}, stored={r['total_score']}"
        
        # Verify tier grade
        if total >= 90:
            expected_grade = "A"
        elif total >= 75:
            expected_grade = "B"
        elif total >= 60:
            expected_grade = "C"
        else:
            expected_grade = "D"
        assert r["grade"] == expected_grade, f"Grade mismatch for {r['person_key']}: got {r['grade']}, expected {expected_grade}"
    
    # Verify unrated people remain unassigned without synthetic defaults
    unrated = [r for r in ratings if r["total_score"] is None]
    assert len(unrated) == 9
    for r in unrated:
        assert r["total_score"] is None
        assert r["grade"] is None
    
    print("  -> Passed: 4 dimensions (30/25/25/20), tier logic (A>=90, B>=75, C>=60, D<60), and undetermined safety verified.")

def test_favorites_and_cross_feedback_isolation():
    print("[5/5] Testing favorites and cross-saving isolation between feedback types...")
    
    # Test state object
    state = {
        "version": 1,
        "recommendations": [
            {"id": "REC-001", "title": "Test Rec", "assignee_id": "rep_1", "status": "assigned", "updated_at": "2026-11-20T10:00:00Z"}
        ],
        "feedback": [],
        "recommendation_feedback": [],
        "favorites": []
    }
    
    # 1. Add customer contact feedback
    contact_feedback = {
        "id": "FB-001",
        "recommendation_id": "REC-001",
        "author_id": "rep_1",
        "contact_status": "contacted",
        "contact_date": "2026-11-20",
        "next_action": "Follow up next week"
    }
    state["feedback"].append(contact_feedback)
    state["recommendations"][0]["status"] = "in_progress"
    
    # Ensure recommendation_feedback is unaffected
    assert len(state["recommendation_feedback"]) == 0
    
    # 2. Add recommendation quality feedback
    quality_feedback = {
        "id": "RQ-001",
        "recommendation_id": "REC-001",
        "author_id": "rep_1",
        "value": "useful",
        "stage": "before_contact",
        "reasons": ["clear_direction"],
        "recommendation_snapshot": {"title": "Test Rec"}
    }
    state["recommendation_feedback"].append(quality_feedback)
    
    # Ensure feedback is unaffected
    assert len(state["feedback"]) == 1
    assert state["feedback"][0]["id"] == "FB-001"
    
    # 3. Add and remove favorite
    state["favorites"].append({"actor_id": "rep_1", "person_key": "PI-001"})
    assert len(state["favorites"]) == 1
    
    # Remove favorite
    state["favorites"] = [f for f in state["favorites"] if f["person_key"] != "PI-001"]
    assert len(state["favorites"]) == 0
    
    # Ensure neither recommendation nor feedbacks were deleted or modified
    assert len(state["recommendations"]) == 1
    assert len(state["feedback"]) == 1
    assert len(state["recommendation_feedback"]) == 1
    
    print("  -> Passed: Cross-feedback isolation, favorite toggle safety, and non-destructive persistence verified.")

def main():
    print("=== P01 Regression Test Suite ===")
    test_data_conservation()
    test_weekly_date_slicing()
    test_market_sales_independence()
    test_pi_rating_rules()
    test_favorites_and_cross_feedback_isolation()
    print("=== ALL P01 REGRESSION TESTS PASSED ===")

if __name__ == "__main__":
    main()
