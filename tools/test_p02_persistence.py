"""P02 Persistence & Data Migration Test Suite.
Validates:
1. Strict JSON schema validation and error reporting.
2. Diff preview accuracy (add, update, identical).
3. Idempotent import & non-destructive merging.
4. Export round-trip fidelity.
5. Research database (marketing.db) remains 100% untouched.
"""
from pathlib import Path
import hashlib, json, sqlite3, sys
import migrate_sales_data as msd

ROOT = Path(__file__).resolve().parents[1]
TEST_DB = ROOT / "handoff/acceptance/P02/test_sales_business.db"
RESEARCH_DB = ROOT / "workbench/数据库/marketing.db"
BASELINE_PATH = ROOT / "handoff/baseline.json"

def test_p02_pipeline():
    print("=== [P02 Test 1] Schema validation & error detection ===")
    bad_data = {
        "schema": "wrong-schema",
        "version": 2,
        "recommendations": [
            {"id": "", "title": "No ID"},
            {"id": "R1", "title": "", "status": "unknown_status"}
        ],
        "feedback": [
            {"id": "F1", "recommendation_id": "", "contact_status": "invalid_status"}
        ]
    }
    errors = msd.validate_json_data(bad_data)
    assert len(errors) >= 5, f"Expected at least 5 validation errors, got {len(errors)}: {errors}"
    print(f"  -> Successfully caught {len(errors)} deliberate schema violations.")

    print("\n=== [P02 Test 2] Clean DB setup & initial import ===")
    if TEST_DB.exists():
        TEST_DB.unlink()
    conn = msd.get_db(TEST_DB)

    sample_data = {
        "schema": "clinical-sales-export:v1",
        "version": 1,
        "exported_at": "2026-11-20T10:00:00Z",
        "scope": "test data",
        "recommendations": [
            {
                "id": "REC-T01",
                "domain_id": "diabetes",
                "topic_id": "TOPIC_01",
                "title": "DKD早期标志物临床转化交流",
                "research_question": "DKD早期诊断与微量白蛋白相关性",
                "reason": "学术报告显示该团队在寻找外周血验证方案",
                "participation": "提供多组学检测及生信支持",
                "conditions": "需要至少50例临床血浆标本",
                "suggested_action": "约见内分泌科主任",
                "assignee_id": "demo-sales-a",
                "due_date": "2026-11-25",
                "status": "assigned",
                "is_demo": False,
                "links": [{"kind": "report", "id": "REP_001"}],
                "expert_keys": ["EXPERT_01"],
                "capability_ids": ["T10"],
                "created_at": "2026-11-20T10:00:00Z",
                "updated_at": "2026-11-20T10:00:00Z"
            }
        ],
        "feedback": [
            {
                "id": "FB-T01",
                "recommendation_id": "REC-T01",
                "author_id": "demo-sales-a",
                "contact_status": "contacted",
                "contact_date": "2026-11-20",
                "contact_name": "张主任",
                "institution": "第一附属医院",
                "need": "希望验证新型血清标志物",
                "cohort": "已储备100例随访样本",
                "support": "需要设计定制PCR面板",
                "next_action": "下周二提供初步技术方案",
                "next_owner_id": "demo-sales-a",
                "next_date": "2026-11-27",
                "is_demo": False,
                "created_at": "2026-11-20T10:15:00Z",
                "reviewed_at": None,
                "review_note": ""
            }
        ],
        "favorites": [
            {
                "actor_id": "demo-sales-a",
                "person_key": "EXPERT_01",
                "created_at": "2026-11-20T10:05:00Z"
            }
        ],
        "recommendation_feedback": [
            {
                "id": "RQ-T01",
                "recommendation_id": "REC-T01",
                "author_id": "demo-sales-a",
                "value": "useful",
                "stage": "after_contact",
                "reasons": ["clear_direction", "helpful_entry"],
                "note": "切入点非常准确，主任很感兴趣",
                "needs": "希望补充该标志物的文献总结",
                "is_demo": False,
                "created_at": "2026-11-20T10:20:00Z",
                "recommendation_updated_at": "2026-11-20T10:00:00Z",
                "recommendation_snapshot": {"title": "DKD早期标志物临床转化交流"}
            }
        ]
    }

    # Test initial diff
    diff = msd.diff_data(sample_data, conn)
    assert len(diff["recs_to_add"]) == 1
    assert len(diff["fb_to_add"]) == 1
    assert len(diff["favs_to_add"]) == 1
    assert len(diff["qf_to_add"]) == 1
    print("  -> Diff preview verified: 1 rec, 1 fb, 1 fav, 1 qf to add.")

    # Import
    res = msd.import_data(sample_data, conn, "test_file.json", "sha_dummy")
    assert res["recs_added"] == 1
    assert res["fb_added"] == 1
    assert res["favs_added"] == 1
    assert res["qf_added"] == 1
    print("  -> Initial import succeeded.")

    print("\n=== [P02 Test 3] Idempotency & Repeat Import ===")
    diff_again = msd.diff_data(sample_data, conn)
    assert len(diff_again["recs_to_add"]) == 0
    assert len(diff_again["recs_to_update"]) == 0
    assert diff_again["recs_identical"] == 1
    assert diff_again["fb_identical"] == 1
    assert diff_again["favs_identical"] == 1
    assert diff_again["qf_identical"] == 1

    res_again = msd.import_data(sample_data, conn)
    assert res_again["recs_added"] == 0
    assert res_again["recs_updated"] == 0
    print("  -> Idempotent re-import verified: 0 additions, 0 updates, 100% deduplicated.")

    print("\n=== [P02 Test 4] Incremental updates ===")
    updated_data = json.loads(json.dumps(sample_data))
    updated_data["recommendations"][0]["title"] = "DKD早期标志物临床转化交流 (已更新)"
    updated_data["recommendations"][0]["updated_at"] = "2026-11-20T11:00:00Z"
    updated_data["feedback"][0]["review_note"] = "市场部已复核，支持方案编写"
    updated_data["feedback"][0]["reviewed_at"] = "2026-11-20T11:30:00Z"

    diff_upd = msd.diff_data(updated_data, conn)
    assert len(diff_upd["recs_to_update"]) == 1
    assert len(diff_upd["fb_to_update"]) == 1
    res_upd = msd.import_data(updated_data, conn)
    assert res_upd["recs_updated"] == 1
    assert res_upd["fb_updated"] == 1
    print("  -> Incremental update verified.")

    print("\n=== [P02 Test 5] Export round-trip fidelity ===")
    exported = msd.export_to_dict(conn)
    assert exported["schema"] == "clinical-sales-export:v1"
    assert len(exported["recommendations"]) == 1
    assert exported["recommendations"][0]["title"] == "DKD早期标志物临床转化交流 (已更新)"
    assert exported["recommendations"][0]["links"] == [{"kind": "report", "id": "REP_001"}]
    assert exported["feedback"][0]["review_note"] == "市场部已复核，支持方案编写"
    assert exported["favorites"][0]["person_key"] == "EXPERT_01"
    assert exported["recommendation_feedback"][0]["value"] == "useful"
    print("  -> Export round-trip fidelity verified.")

    conn.close()

    print("\n=== [P02 Test 6] Research database conservation check ===")
    base = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    expected_hash = base["database_sha256"]
    actual_hash = hashlib.sha256(RESEARCH_DB.read_bytes()).hexdigest()
    assert actual_hash == expected_hash, f"Research DB corrupted! Expected {expected_hash}, got {actual_hash}"
    print(f"  -> Research DB (marketing.db) strictly untouched: {actual_hash}")

    print("\n=== ALL P02 PERSISTENCE TESTS PASSED ===")

if __name__ == "__main__":
    test_p02_pipeline()
