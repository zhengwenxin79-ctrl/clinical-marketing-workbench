#!/usr/bin/env python3
"""Generate a coverage plan and audit an agent-written meeting ledger. No network I/O."""
import argparse
import copy
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[1] / "references" / "registry.json"
GRADES = {"重点关注", "常规关注", "低优先级", "待确认"}
DISPOSITIONS = {"weekly_confirmed", "weekly_pending", "reserve", "excluded", "duplicate"}
FINAL_ROLES = {"organizer_notice", "official_conference_site", "authorized_platform_notice"}
IDENTITY_ROLES = FINAL_ROLES | {"annual_plan"}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_date(value):
    if not value or not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def overlaps(start, end, window_start, window_end):
    return bool(start and end and start <= window_end and end >= window_start)


def make_plan(start, end, as_of=None, previous=None, registry=None):
    registry = registry or read_json(REGISTRY)
    first, last = parse_date(start), parse_date(end)
    if not first or not last or first > last:
        raise ValueError("起止日期必须为有效YYYY-MM-DD，且开始不晚于结束")
    cutoff = as_of or datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    if not parse_date(cutoff):
        raise ValueError("as-of必须为有效YYYY-MM-DD")
    tasks = []

    def add(task_id, label, topics, queries, **extra):
        tasks.append({"id": task_id, "label": label, "required_topics": topics,
                      "suggested_queries": queries, "status": "pending", "attempts": [],
                      "checked_topics": [], "extent_complete": False, "candidate_ids": [],
                      "documents": [], "enumerations": [], "gap_action": "", **extra})

    years = sorted({first.year, (last + timedelta(days=registry["lookahead_days"])).year})
    year_words = str(years[0]) if len(years) == 1 else "(" + " OR ".join(map(str, years)) + ")"
    for family in registry["national_families"]:
        for domain in registry["domains"]:
            queries = []
            for topic in domain["topics"]:
                queries.extend([f'{family["name"]} {topic} {year_words} (年会 OR 学术会议 OR 医师大会)',
                                f'{family["name"]} {topic} 年会 会议通知'])
            add(f'national:{family["id"]}:{domain["id"]}', f'{family["name"]} / {domain["name"]}',
                domain["topics"], queries, family=family["id"], domain=domain["id"])
    for domain in registry["domains"]:
        add(f'other:{domain["id"]}', f'其他全国专题组织 / {domain["name"]}', ["其他组织及品牌会"],
            [f'{domain["name"]} {year_words} (学会 OR 专业委员会) (年会 OR 论坛)',
             f'({" OR ".join(domain["aliases"])}) {year_words} 学术会议'], domain=domain["id"])
    for region in registry["regional_scopes"]:
        add(f'regional:{region["id"]}', f'{region["name"]}相关组织', ["医学会", "医师协会"],
            [f'{region["name"]}{org} {year_words} (会议计划 OR 年会 OR 学术活动)' for org in ["医学会", "医师协会"]],
            covered_cities=region["cities"])
    for group in registry["platform_groups"]:
        add(f'platform:{group["id"]}', group["name"], group["topics"], [], entry_ids=group["entry_ids"])
    for domain in registry["domains"]:
        add(f'open:{domain["id"]}', f'开放补漏 / {domain["name"]}', ["新组织或独立会名"],
            [f'{topic} {year_words} (会议通知 OR 邀请函 OR 征文)' for topic in domain["topics"]])
    add("carryover", "上轮储备与未解决项", ["储备", "待核实", "人工意见"], [])
    add("series", "核心会议系列反查", ["本届去向", "新增系列"], [])
    add("misses", "已知漏项与独立对照", ["已知漏项", "新增对照"], [])
    run = {
        "meta": {"skill_version": "1.0", "registry_version": registry["version"],
                 "start": first.isoformat(), "end": last.isoformat(), "as_of": cutoff,
                 "timezone": "Asia/Shanghai", "discovery_end": (last + timedelta(days=registry["lookahead_days"])).isoformat()},
        "coverage": tasks, "evidence": [], "candidates": [],
        "series_checks": [{"series_id": s["id"], "status": "pending", "candidate_ids": [],
                           "evidence_ids": [], "coverage_task_ids": [], "note": ""}
                          for s in registry["core_series_seeds"]],
        "benchmark_checks": [], "run_notes": []}
    if previous:
        previous = read_json(previous) if isinstance(previous, (str, Path)) else previous
        kept = []
        for item in previous.get("candidates", []):
            future = parse_date(item.get("main_end"))
            if item.get("disposition") in {"reserve", "weekly_pending"} or item.get("manual_review") or (future and future >= first):
                current = copy.deepcopy(item)
                current["previous_disposition"] = current.get("disposition")
                current["previous_discovery_task_ids"] = current.get("discovery_task_ids", [])
                current["discovery_task_ids"] = ["carryover"]
                current["needs_recheck"] = True
                current["carried_manual_review"] = copy.deepcopy(current.get("manual_review"))
                current["disposition"] = "weekly_pending" if overlaps(parse_date(current.get("main_start")), future, first, last) else "reserve"
                kept.append(current)
        run["candidates"] = kept
        run["evidence"] = copy.deepcopy(previous.get("evidence", []))
        next(t for t in tasks if t["id"] == "carryover")["candidate_ids"] = [c["id"] for c in kept]
    return run


def audit(run, registry=None):
    registry = registry or read_json(REGISTRY)
    errors, gaps, warnings = [], [], []

    def error(code, message):
        errors.append({"code": code, "message": message})

    def gap(code, message):
        gaps.append({"code": code, "message": message})

    def index(items, label):
        found = {}
        for item in items:
            if not isinstance(item, dict) or not item.get("id"):
                error("MISSING_ID", f"{label}缺id或格式错误")
                continue
            if item["id"] in found:
                error("DUPLICATE_ID", f'{label}重复id: {item["id"]}')
            found[item["id"]] = item
        return found

    if not isinstance(run, dict):
        return {"status": "error", "exit_code": 1, "errors": [{"code": "FORMAT", "message": "台账必须是JSON对象"}], "gaps": [], "warnings": []}
    meta = run.get("meta", {})
    first, last, cutoff = (parse_date(meta.get(k)) for k in ("start", "end", "as_of"))
    if not first or not last or not cutoff or first > last:
        return {"status": "error", "exit_code": 1, "errors": [{"code": "WINDOW", "message": "meta缺有效目标周或截止日"}], "gaps": [], "warnings": []}
    expected = {t["id"]: t for t in make_plan(meta["start"], meta["end"], meta["as_of"], registry=registry)["coverage"]}
    for key in ("coverage", "evidence", "candidates", "series_checks", "benchmark_checks"):
        if not isinstance(run.get(key, []), list):
            return {"status": "error", "exit_code": 1, "errors": [{"code": "FORMAT", "message": f"{key}必须是数组"}], "gaps": [], "warnings": []}
    tasks = index(run.get("coverage", []), "来源任务")
    evidence = index(run.get("evidence", []), "证据")
    candidates = index(run.get("candidates", []), "候选")
    complete = 0
    for task_id, template in expected.items():
        task = tasks.get(task_id)
        if not task:
            gap("MISSING_COVERAGE", f'缺必查任务: {task_id}')
            continue
        state = task.get("status")
        if state not in {"pending", "partial", "blocked", "complete"}:
            error("TASK_STATUS", f'{task_id}: 无效来源状态')
        if state != "complete":
            gap("INCOMPLETE_COVERAGE", f'{task_id}: {state}; {task.get("gap_action", "未写下一步")}')
            continue
        valid = True
        attempts = task.get("attempts", [])
        if not attempts or any(not isinstance(a, dict) or not (a.get("url") or a.get("query")) or not parse_date(a.get("checked_at")) or not a.get("result") for a in attempts):
            error("UNSUPPORTED_COMPLETE", f'{task_id}: 标已完成却无有效实际访问/查询记录')
            valid = False
        missing_topics = set(template["required_topics"]) - set(task.get("checked_topics", []))
        if missing_topics:
            gap("TOPIC_GAP", f'{task_id}: 未覆盖子方向 {sorted(missing_topics)}')
            valid = False
        if task.get("extent_complete") is not True:
            gap("EXTENT_GAP", f'{task_id}: 列表/章节范围未确认完成')
            valid = False
        for doc in task.get("documents", []):
            total = doc.get("page_count")
            if not isinstance(total, int) or total < 1 or not doc.get("url"):
                error("PDF_METADATA", f'{task_id}: PDF缺页数或来源')
                valid = False
                continue
            processed = set(doc.get("processed_pages", []))
            excluded = {int(k) for k, v in doc.get("excluded_pages", {}).items() if str(k).isdigit() and v}
            if set(range(1, total + 1)) - processed - excluded:
                gap("PDF_PAGE_GAP", f'{task_id}: {doc["url"]} 有未读或未解释页面')
                valid = False
            if set(doc.get("image_pages", [])) - set(doc.get("ocr_pages", [])) - excluded:
                gap("OCR_GAP", f'{task_id}: 图片页未OCR/人工核对')
                valid = False
        for listing in task.get("enumerations", []):
            total, items = listing.get("total_items"), listing.get("items", [])
            if not listing.get("url") or not isinstance(total, int) or total < 0 or not isinstance(items, list):
                error("INDEX_METADATA", f'{task_id}: 目录条目清单格式错误')
                valid = False
                continue
            if len(items) != total:
                gap("INDEX_ITEM_GAP", f'{task_id}: 目录有{total}条，仅登记{len(items)}条')
                valid = False
            item_ids = set()
            for item in items:
                item_id = item.get("source_item_id")
                if not item_id or item_id in item_ids or not item.get("title"):
                    error("INDEX_ITEM_ID", f'{task_id}: 源条目缺身份或重复')
                item_ids.add(item_id)
                if item.get("kind") == "conference":
                    cid = item.get("candidate_id")
                    if cid not in candidates or cid not in task.get("candidate_ids", []):
                        gap("RAW_ITEM_UNACCOUNTED", f'{task_id}: 会议条目{item_id}未进入候选台账')
                        valid = False
                elif item.get("kind") != "nonconference" or not item.get("reason"):
                    error("INDEX_ITEM_REASON", f'{task_id}: 非会议条目{item_id}缺说明')
        if valid:
            complete += 1
    for eid, e in evidence.items():
        if not e.get("url") or not e.get("publisher") or not e.get("role") or not parse_date(e.get("accessed_at")):
            error("EVIDENCE_METADATA", f'{eid}: 缺来源、发布者、角色或访问日期')
        if not isinstance(e.get("claims", {}), dict):
            error("EVIDENCE_CLAIMS", f'{eid}: claims必须是对象')
        published = parse_date(e.get("published_at"))
        if published and published > cutoff:
            error("AFTER_CUTOFF", f'{eid}: 发布日期晚于本轮截止日')
        if not published:
            warnings.append(f'{eid}: 未知发布日期，需人工判断时效')
    valid_domains = {d["id"] for d in registry["domains"]}
    active_series = {}
    for cid, c in candidates.items():
        domains = c.get("domains", [])
        if not c.get("name") or not isinstance(domains, list) or not set(domains) <= valid_domains:
            error("CANDIDATE_IDENTITY", f'{cid}: 缺名称或领域格式错误')
        if not domains and not (c.get("disposition") == "excluded" and c.get("disposition_reason")) and not (c.get("priority") == "待确认" and c.get("business_fit") == "unclear"):
            error("DOMAIN_UNEXPLAINED", f'{cid}: 领域未知应待确认，范围外应说明排除，不能虚填六大类')
        if c.get("business_fit") not in {"relevant", "mixed_relevant", "unclear", "low"}:
            error("BUSINESS_FIT", f'{cid}: 业务相关性状态无效')
        if c.get("format") not in {"onsite", "online", "hybrid", "unknown"}:
            error("MEETING_FORMAT", f'{cid}: 会议形式状态无效')
        if not isinstance(c.get("edition_year"), int) or not isinstance(c.get("formal_national_annual"), bool):
            error("EDITION_FORMAT", f'{cid}: 缺本届年份或正式年会布尔状态')
        disposition = c.get("disposition")
        if disposition not in DISPOSITIONS:
            error("DISPOSITION", f'{cid}: 候选缺有效去向')
        if c.get("priority") not in GRADES:
            error("PRIORITY", f'{cid}: 缺有效关注等级')
        if not c.get("reason"):
            error("NO_REASON", f'{cid}: 缺判断理由')
        if disposition in {"reserve", "excluded", "duplicate"} and not c.get("disposition_reason"):
            error("NO_DISPOSITION_REASON", f'{cid}: 缺去向说明')
        if disposition == "duplicate":
            target = c.get("duplicate_of")
            if target not in candidates or target == cid or candidates[target].get("disposition") == "duplicate":
                error("DUPLICATE_TARGET", f'{cid}: 缺有效主记录，或重复形成链/循环')
        sid = c.get("series_id")
        if sid and disposition != "duplicate":
            key = (sid, c.get("edition_year"))
            if key in active_series:
                error("SAME_EDITION_DUPLICATE", f'{cid}和{active_series[key]}为同系列同届；改期不能另建一场')
            active_series[key] = cid
        source_keys = ("date_evidence_ids", "identity_evidence_ids", "content_evidence_ids", "discovery_evidence_ids", "occurrence_evidence_ids")
        refs = set()
        for key in source_keys:
            refs.update(c.get(key, []))
        if not refs:
            error("NO_EVIDENCE", f'{cid}: 缺任何发现或事实来源')
        for eid in refs:
            if eid not in evidence:
                error("MISSING_EVIDENCE", f'{cid}: 引用不存在的证据{eid}')
        found_by = c.get("discovery_task_ids", [])
        if not found_by:
            error("NO_DISCOVERY_TRACE", f'{cid}: 缺发现任务关联')
        for tid in found_by:
            if tid not in tasks or cid not in tasks[tid].get("candidate_ids", []):
                error("DISCOVERY_LINK", f'{cid}: 与任务{tid}关联不一致')
        identity = [evidence[e] for e in c.get("identity_evidence_ids", []) if e in evidence]
        if c.get("formal_national_annual"):
            proof = any(e.get("role") in IDENTITY_ROLES and e.get("claims", {}).get("formal_national_annual") is True
                        and e.get("edition_year") == c.get("edition_year") for e in identity)
            if not proof:
                error("NATIONAL_IDENTITY", f'{cid}: 正式全国年会身份缺官方证据')
            if domains and c.get("business_fit") != "low" and not c.get("operational_only"):
                if c.get("priority") != "重点关注":
                    error("NATIONAL_DOWNGRADED", f'{cid}: 相关正式全国年会不应因缺日程、名单、人数或非覆盖城市降级')
                if disposition == "excluded" and c.get("date_status") != "cancelled":
                    error("NATIONAL_DROPPED", f'{cid}: 相关核心会不能静默排除，改期应进入储备')
        if c.get("business_fit") == "low" or c.get("operational_only"):
            if not c.get("content_evidence_ids"):
                error("CONTENT_EXCLUSION_EVIDENCE", f'{cid}: 低相关/纯操作判断需内容证据')
            if c.get("priority") == "重点关注" and not c.get("manual_review"):
                error("LOW_FIT_PROMOTED", f'{cid}: 明确低相关不能仅因级别或人数重点推荐')
        start, end = parse_date(c.get("main_start")), parse_date(c.get("main_end"))
        if start and end and start > end:
            error("DATE_ORDER", f'{cid}: 主会起止日期倒置')
        ds = c.get("date_status")
        if ds not in {"confirmed", "planned", "conflict", "unknown", "cancelled"}:
            error("DATE_STATUS", f'{cid}: 日期状态无效')
        selected = [evidence[e] for e in c.get("date_evidence_ids", []) if e in evidence]
        if ds == "confirmed":
            official = [e for e in selected if e.get("role") in FINAL_ROLES
                        and e.get("status", "active") == "active" and e.get("edition_year") == c.get("edition_year")]
            if not start or not end or not official:
                error("UNCONFIRMED_FINAL_DATE", f'{cid}: 最终日期不能仅用计划、采购、聚合摘要等确认')
            required_fields = ["main_start", "main_end"]
            if c.get("format") != "online":
                required_fields.append("city")
            for field in required_fields:
                if not c.get(field) or not any(e.get("claims", {}).get(field) == c.get(field) for e in official):
                    error("DATE_FIELD_EVIDENCE", f'{cid}: {field}缺对应本届正式证据')
            for e in evidence.values():
                if e.get("candidate_id") == cid and e.get("role") in FINAL_ROLES and e.get("status", "active") == "active":
                    if any(k in e.get("claims", {}) and e["claims"][k] != c.get(k) for k in required_fields):
                        error("ACTIVE_SCHEDULE_CONFLICT", f'{cid}: 有未解决的有效正式通知冲突，不能写已确认')
        if disposition == "weekly_confirmed":
            if ds != "confirmed" or not overlaps(start, end, first, last):
                error("WEEKLY_WINDOW", f'{cid}: 本周已确认清单含计划/冲突日期或周外会议')
            if c.get("needs_recheck"):
                error("STALE_CARRYOVER", f'{cid}: 上轮储备尚未复核')
        if disposition == "weekly_pending" and ds == "confirmed" and start and end and not overlaps(start, end, first, last):
            error("PENDING_OUTSIDE_WINDOW", f'{cid}: 已确认在周外，应转储备')
        if c.get("meeting_status") == "已结束":
            occurred = any(evidence[e].get("role") in FINAL_ROLES | {"hospital_report"}
                           and evidence[e].get("edition_year") == c.get("edition_year")
                           and evidence[e].get("claims", {}).get("held") is True
                           for e in c.get("occurrence_evidence_ids", []) if e in evidence)
            if not occurred:
                error("ENDED_FROM_PLAN", f'{cid}: 缺实际举办证据，不能仅凭计划日期写已结束')
        if c.get("carried_manual_review") and c.get("manual_review") != c["carried_manual_review"] and not c.get("manual_review_change_reason"):
            error("MANUAL_REVIEW_OVERWRITTEN", f'{cid}: 人工意见被覆盖且无说明')
    for tid, task in tasks.items():
        for cid in task.get("candidate_ids", []):
            if cid not in candidates or tid not in candidates[cid].get("discovery_task_ids", []):
                error("ORPHAN_DISCOVERY", f'{tid}: 候选{cid}缺记录或反向关联')
    series_checks = {s.get("series_id"): s for s in run.get("series_checks", []) if isinstance(s, dict)}
    for seed in registry["core_series_seeds"]:
        check = series_checks.get(seed["id"], {})
        if check.get("status") == "linked":
            ids = check.get("candidate_ids", [])
            if not ids or any(cid not in candidates or candidates[cid].get("series_id") != seed["id"] for cid in ids):
                error("SERIES_LINK", f'{seed["id"]}: 本届去向没有连到对应系列的候选')
        else:
            gap("UNRESOLVED_SERIES", f'{seed["id"]}: {check.get("status", "未登记")}; {check.get("note", "未说明本届去向")}')
    for benchmark in run.get("benchmark_checks", []):
        if not isinstance(benchmark, dict) or not benchmark.get("name"):
            error("BENCHMARK_FORMAT", "独立核对项缺名称")
            continue
        cid = benchmark.get("candidate_id")
        if cid not in candidates:
            gap("KNOWN_MEETING_MISSING", f'{benchmark["name"]}: 独立已知会议未进入候选池')
    counts = {key: sum(c.get("disposition") == key for c in candidates.values()) for key in sorted(DISPOSITIONS)}
    code = 1 if errors else 2 if gaps else 0
    return {"status": "error" if errors else "partial" if gaps else "review_ready",
            "exit_code": code, "coverage_completed": complete, "coverage_required": len(expected),
            "candidate_count": len(candidates), "dispositions": counts,
            "errors": errors, "gaps": gaps, "warnings": warnings,
            "limit": "只检查声明台账的一致性和必查范围，不能证明实际检索日志真实、证据原文正确或全国会议已找全。"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--start", required=True)
    init.add_argument("--end", required=True)
    init.add_argument("--as-of")
    init.add_argument("--previous")
    init.add_argument("--output", required=True)
    check = sub.add_parser("audit")
    check.add_argument("run_file")
    check.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        if args.command == "init":
            if Path(args.output).exists():
                raise ValueError("输出文件已存在，请换本轮新文件名，避免覆盖历史台账")
            run = make_plan(args.start, args.end, args.as_of, args.previous)
            write_json(args.output, run)
            print(f'已创建{len(run["coverage"])}项待执行覆盖任务及{len(run["series_checks"])}个系列反查项；尚未联网检索。')
            return 0
        report = audit(read_json(args.run_file))
        write_json(args.output, report)
        print(json.dumps({k: report[k] for k in ("status", "exit_code", "coverage_completed", "coverage_required", "candidate_count") if k in report}, ensure_ascii=False))
        return report["exit_code"]
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"输入/格式错误: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
