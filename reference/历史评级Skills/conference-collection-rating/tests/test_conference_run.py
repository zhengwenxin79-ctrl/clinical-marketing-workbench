"""Synthetic behavioral cases. No fixture represents a real conference or actual search."""
import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("conference_run", ROOT / "scripts" / "conference_run.py")
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


def fixture():
    registry = workflow.read_json(workflow.REGISTRY)
    run = workflow.make_plan("2026-11-02", "2026-11-08", "2026-11-05")
    for task in run["coverage"]:
        task.update(status="complete", checked_topics=task["required_topics"].copy(), extent_complete=True,
                    attempts=[{"query": "假设测试查询，未真实执行", "checked_at": "2026-11-05", "result": "仅为离线测试"}])
    for i, seed in enumerate(registry["core_series_seeds"]):
        cid, eid = f"synthetic-{i}", f"synthetic-notice-{i}"
        task_id = f'national:{seed["family"]}:{seed["domain"]}'
        run["evidence"].append({
            "id": eid, "candidate_id": cid, "url": f"https://example.invalid/{eid}",
            "publisher": "假设主办方", "role": "organizer_notice", "origin_id": eid,
            "published_at": "2026-10-15", "accessed_at": "2026-11-05", "edition_year": 2026,
            "claims": {"main_start": "2026-11-06", "main_end": "2026-11-08", "city": "北京", "formal_national_annual": True}})
        run["candidates"].append({
            "id": cid, "name": f"假设会议{i}（非真实会议）", "edition_year": 2026, "series_id": seed["id"],
            "domains": [seed["domain"]], "format": "onsite", "city": "北京",
            "main_start": "2026-11-06", "main_end": "2026-11-08", "date_status": "confirmed",
            "date_evidence_ids": [eid], "identity_evidence_ids": [eid],
            "formal_national_annual": True, "business_fit": "relevant", "operational_only": False,
            "priority": "重点关注", "reason": "测试用相关正式年会", "disposition": "weekly_confirmed",
            "disposition_reason": "测试窗口内", "discovery_task_ids": [task_id], "manual_review": None})
        next(t for t in run["coverage"] if t["id"] == task_id)["candidate_ids"].append(cid)
        check = run["series_checks"][i]
        check.update(status="linked", candidate_ids=[cid], evidence_ids=[eid])
    return run


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.run = fixture()

    def codes(self, run=None):
        report = workflow.audit(run or self.run)
        return {i["code"] for i in report["errors"] + report["gaps"]}

    def test_complete_synthetic_run_can_be_reviewed(self):
        self.assertEqual(workflow.audit(self.run)["status"], "review_ready")

    def test_medical_association_cannot_cover_physicians_association(self):
        self.run["coverage"] = [t for t in self.run["coverage"] if not t["id"].startswith("national:CMDA:")]
        report = workflow.audit(self.run)
        self.assertEqual(sum(g["code"] == "MISSING_COVERAGE" for g in report["gaps"]), 6)

    def test_neurology_search_does_not_cover_psychiatry(self):
        t = next(t for t in self.run["coverage"] if t["id"] == "national:CMDA:neuropsych")
        t["checked_topics"] = ["神经内科"]
        self.assertIn("TOPIC_GAP", self.codes())

    def test_unread_pdf_and_image_pages_are_gaps(self):
        self.run["coverage"][0]["documents"] = [{"url": "https://example.invalid/plan.pdf", "page_count": 3,
                                               "processed_pages": [1], "image_pages": [3], "ocr_pages": []}]
        self.assertTrue({"PDF_PAGE_GAP", "OCR_GAP"} <= self.codes())

    def test_completed_claim_needs_actual_query_log(self):
        self.run["coverage"][0]["attempts"] = []
        self.assertIn("UNSUPPORTED_COMPLETE", self.codes())

    def test_directory_cannot_keep_only_final_selected_items(self):
        self.run["coverage"][0]["enumerations"] = [{"url": "https://example.invalid/list", "total_items": 3,
            "items": [{"source_item_id": "news-1", "title": "非会议新闻", "kind": "nonconference", "reason": "组织人事通知"}]}]
        self.assertIn("INDEX_ITEM_GAP", self.codes())

    def test_seen_but_dropped_conference_is_exposed(self):
        self.run["coverage"][0]["enumerations"] = [{"url": "https://example.invalid/list", "total_items": 1,
            "items": [{"source_item_id": "meeting-x", "title": "已看到但遗漏的会议", "kind": "conference", "candidate_id": None}]}]
        self.assertIn("RAW_ITEM_UNACCOUNTED", self.codes())

    def test_national_meeting_can_remain_priority_without_agenda_or_dates(self):
        c = self.run["candidates"][0]
        c.update(main_start=None, main_end=None, city=None, date_status="unknown", disposition="weekly_pending",
                 date_evidence_ids=[], agenda_status="未发布", pi_list_status="未发布")
        e = self.run["evidence"][0]
        e["role"] = "annual_plan"
        e["claims"] = {"formal_national_annual": True}
        self.assertEqual(workflow.audit(self.run)["status"], "review_ready")
        c["priority"] = "常规关注"
        self.assertIn("NATIONAL_DOWNGRADED", self.codes())

    def test_procurement_is_not_final_schedule(self):
        self.run["evidence"][0]["role"] = "procurement_notice"
        self.assertIn("UNCONFIRMED_FINAL_DATE", self.codes())

    def test_reschedule_moves_event_out_of_week_and_into_reserve(self):
        c, old = self.run["candidates"][0], self.run["evidence"][0]
        old["status"] = "superseded"
        revised = copy.deepcopy(old)
        revised.update(id="new-notice", published_at="2026-11-01", status="active")
        revised["claims"].update(main_start="2026-12-04", main_end="2026-12-06")
        self.run["evidence"].append(revised)
        c.update(main_start="2026-12-04", main_end="2026-12-06", date_evidence_ids=["new-notice"])
        self.assertIn("WEEKLY_WINDOW", self.codes())
        c.update(disposition="reserve", disposition_reason="正式通知改期")
        self.assertEqual(workflow.audit(self.run)["status"], "review_ready")

    def test_unresolved_official_conflict_cannot_be_confirmed(self):
        e = copy.deepcopy(self.run["evidence"][0])
        e["id"] = "other-active-notice"
        e["claims"]["main_start"] = "2026-12-04"
        self.run["evidence"].append(e)
        self.assertIn("ACTIVE_SCHEDULE_CONFLICT", self.codes())

    def test_workshop_does_not_extend_main_meeting_into_week(self):
        c, e = self.run["candidates"][0], self.run["evidence"][0]
        c.update(main_start="2026-11-12", main_end="2026-11-14")
        e["claims"].update(main_start="2026-11-12", main_end="2026-11-14")
        c["sessions"] = [{"kind": "workshop", "start": "2026-11-06", "end": "2026-11-06"}]
        self.assertIn("WEEKLY_WINDOW", self.codes())

    def test_same_series_and_edition_not_new_event_after_date_change(self):
        c = copy.deepcopy(self.run["candidates"][0])
        c["id"] = "another-copy"
        self.run["candidates"].append(c)
        t = next(t for t in self.run["coverage"] if t["id"] == c["discovery_task_ids"][0])
        t["candidate_ids"].append(c["id"])
        self.assertIn("SAME_EDITION_DUPLICATE", self.codes())
        c.update(disposition="duplicate", duplicate_of="synthetic-0", disposition_reason="同届转载")
        self.assertNotIn("SAME_EDITION_DUPLICATE", self.codes())

    def test_future_publication_not_available_at_cutoff(self):
        self.run["evidence"][0]["published_at"] = "2026-11-10"
        self.assertIn("AFTER_CUTOFF", self.codes())

    def test_low_fit_national_meeting_can_be_lower_priority_with_content_evidence(self):
        c = self.run["candidates"][0]
        c.update(business_fit="low", operational_only=True, priority="低优先级", disposition="excluded",
                 disposition_reason="明确纯操作培训", content_evidence_ids=c["identity_evidence_ids"].copy())
        self.assertEqual(workflow.audit(self.run)["status"], "review_ready")

    def test_out_of_scope_meeting_is_kept_with_exclusion_reason(self):
        c = self.run["candidates"][0]
        c.update(domains=[], business_fit="low", priority="低优先级", disposition="excluded",
                 disposition_reason="目录条目不在本轮六领域", content_evidence_ids=c["identity_evidence_ids"].copy())
        self.assertEqual(workflow.audit(self.run)["status"], "review_ready")

    def test_unknown_domain_is_not_forced_into_six_categories(self):
        c = self.run["candidates"][0]
        c.update(domains=[], business_fit="unclear", priority="待确认")
        self.assertEqual(workflow.audit(self.run)["status"], "review_ready")

    def test_known_missing_meeting_is_not_hidden_by_good_existing_rows(self):
        self.run["benchmark_checks"] = [{"name": "独立核对的漏会样本", "candidate_id": None}]
        self.assertIn("KNOWN_MEETING_MISSING", self.codes())

    def test_elapsed_plan_does_not_prove_meeting_held(self):
        self.run["candidates"][0]["meeting_status"] = "已结束"
        self.assertIn("ENDED_FROM_PLAN", self.codes())

    def test_carryover_keeps_manual_opinion_and_requires_recheck(self):
        self.run["candidates"][0]["manual_review"] = {"priority": "重点关注", "reason": "人工判断"}
        next_run = workflow.make_plan("2026-11-09", "2026-11-15", "2026-11-05", previous=self.run)
        c = next_run["candidates"][0]
        self.assertEqual(c["manual_review"], c["carried_manual_review"])
        self.assertTrue(c["needs_recheck"])
        c["manual_review"] = {"priority": "低优先级"}
        self.assertIn("MANUAL_REVIEW_OVERWRITTEN", self.codes(next_run))

    def test_empty_plan_reports_gaps_not_success(self):
        report = workflow.audit(workflow.make_plan("2026-11-02", "2026-11-08", "2026-11-05"))
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["coverage_completed"], 0)
        self.assertGreater(len(report["gaps"]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
