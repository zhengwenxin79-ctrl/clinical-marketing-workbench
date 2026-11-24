# -*- coding: utf-8 -*-
"""
Export DingTalk-compatible database packages:
1. dingtalk_full_baseline.csv / .json: Full baseline of PIs, 4D ratings, ongoing projects, and battle cards.
2. dingtalk_weekly_delta.csv / .json: Weekly incremental additions (natural week W48).
"""
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
SNAPSHOT_PATH = ROOT / "workbench/领域工作台/领域数据快照.json"

REPS = [
    {
        "id": "sales_east_zhang",
        "name": "张敏",
        "region": "华东战区",
        "kw": re.compile(r"上海|瑞金|中山|华山|第六人民|仁济|复旦|同济|江苏|南京|鼓楼|浙江|杭州|浙大|安徽|中国科学技术大学|山东|齐鲁|厦门|福建")
    },
    {
        "id": "sales_north_li",
        "name": "李娜",
        "region": "华北战区",
        "kw": re.compile(r"北京|协和|北大|北京大学|宣武|天坛|阜外|安贞|中日友好|解放军总医院|301|天津|河北|山西|中国医学科学院")
    },
    {
        "id": "sales_south_wang",
        "name": "王强",
        "region": "华南战区",
        "kw": re.compile(r"广东|广州|深圳|中山大学|南方医|广医|湖南|长沙|湘雅|中南大学|湖北|武汉|同济|协和|四川|华西|重庆|贵州")
    }
]

def get_rep_for_inst(inst):
    for r in REPS:
        if r["kw"].search(inst):
            return r["name"], r["region"]
    return "张敏", "华东战区"

def build_dingtalk_packages():
    print("=== [Export DingTalk] Building Baseline & Weekly Delta Packages ===")
    
    if not SNAPSHOT_PATH.is_file():
        print(f"Error: Snapshot not found at {SNAPSHOT_PATH}")
        return

    with open(SNAPSHOT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Collect all rated PIs
    ratings = (data.get("pi_ratings") or {}).get("ratings") or []
    experts = data.get("experts") or []
    reports = {r["report_id"]: r for r in (data.get("reports") or [])}

    # Curated High-Priority Battle Card enrichment
    CURATED = {
        "王卫庆": {
            "ongoing_project": "国家重点研发计划「四大慢病」代谢病精准分型专项在研 + 国家自然重点项目在研",
            "cohort_intent": "已冻存300例微血管并发症样本，拟Q4启动转录组+高通量血浆蛋白组(T10/T14)验证",
            "break_ice_script": "王主任您好！拜读了您在 CDS 2026 大会关于瑞金代谢大队列的报告。吉因加近期结合 6Dmarker 算法与高深度蛋白组协助多家医学中心发表顶刊，想约您汇报案例！",
            "checklist": "1.摸清拟启动微血管并发症队列样本类型; 2.确认随访终点; 3.了解生信驻场联合建模需求",
            "capabilities": "T10 队列多组学建模, T14 高通量蛋白组",
            "status": "跟进中",
            "weekly_new": True  # Belongs to current week's conference delta
        },
        "黄斌": {
            "ongoing_project": "安徽省自然科学基金青年项目《DKD早期损伤标志物筛选与外泌体转录组验证》在研（准备冲刺2027国自然面上）",
            "cohort_intent": "已冻存320例具备完整随访的DKD早期患者配对尿液与血浆标本，拟启动尿液外泌体转录组",
            "break_ice_script": "黄老师您好，听了您在 CDS 2026 口头报告 OR_003 非常精彩！针对您的省自然青年项目，吉因加有专门的尿液外泌体与外周血转录组转化包，想跟您对一下建库参数。",
            "checklist": "1.核实DKD配对尿液与血浆样本量; 2.确认省自然剩余检测经费预算; 3.寄送尿液外泌体质控SOP",
            "capabilities": "T03 转录组测序, T10 临床指标验证",
            "status": "已触达",
            "weekly_new": True
        },
        "张学礼": {
            "ongoing_project": "上海市级医院新兴前沿临床研究专项《微血管并发症多靶标筛查》在研",
            "cohort_intent": "共病队列配对血浆/尿液样本冻存完整，需微量体液超敏蛋白组支持",
            "break_ice_script": "张教授您好，关注到您在 CDS 2026 分享的微血管并发症多组学课题。吉因加在微量体液超敏蛋白组与转录组建库上有成熟实测数据，希望能为您提供初筛支持！",
            "checklist": "1.核实视网膜与肾病队列配对样本例数; 2.确认50~100例初筛预实验排期; 3.了解国自然申报规划",
            "capabilities": "T14 微量体液蛋白组, T03 外泌体转录组",
            "status": "待接触",
            "weekly_new": True
        },
        "吉训明": {
            "ongoing_project": "科技创新2030「脑科学与类脑研究」重大项目在研 + 国家百万减残工程急性卒中多中心临床队列",
            "cohort_intent": "国家级卒中多中心队列首批挑选200例急性卒中再灌注损伤配对血浆/脑脊液，需超敏蛋白组联检",
            "break_ice_script": "吉院士团队老师您好，借2026中国脑卒中大会在京召开契机请教！吉因加在外周血及脑脊液微量核酸与高深度蛋白组联检上有全国多中心临床经验，希望能提供支持！",
            "checklist": "1.现场对接分管学术秘书; 2.摸清液体活检首批筛选例数; 3.确认重点研发计划子课题合作意向",
            "capabilities": "T10 多中心队列验证, T14 脑脊液/血浆蛋白组",
            "status": "跟进中",
            "weekly_new": True
        },
        "陈荣昌": {
            "ongoing_project": "国家自然科学基金面上项目《慢阻肺早期气道微生态-宿主互作分子分型》在研 + 呼吸健康大队列子课题",
            "cohort_intent": "已收集180例慢阻肺早期进展患者配对诱导痰与外周血样本，认可同一份痰液双组学方案",
            "break_ice_script": "陈主任您好，在长沙 CACP 呼吸大会聆听了您关于慢阻肺分子分型的报告！吉因加打通了诱导痰/灌洗液同时做宏基因组+宿主转录组的流程，希望能提供支持！",
            "checklist": "1.拜访团队核心课题秘书; 2.核实诱导痰/BALF存量; 3.提供呼吸道双组学质控报告",
            "capabilities": "T03 宏基因组+宿主转录组, T10 队列验证",
            "status": "跟进中",
            "weekly_new": True
        },
        "苏茵": {
            "ongoing_project": "首都卫生发展科研专项《自身免疫病早期精准分型与靶向诊疗》在研",
            "cohort_intent": "现有 SLE/RA 患者活细胞冻存完整，需单细胞 TCR/BCR 免疫组库解析致病性克隆",
            "break_ice_script": "苏主任您好！祝贺北京风湿病学年会召开。看到今年设立了高分论文专场，特别契合吉因加在自免领域的 PBMC 单细胞+免疫组库方案，想在会后汇报案例！",
            "checklist": "1.摸清青年医师国自然申报选题; 2.确认SLE活细胞冻存数量; 3.邀约参加科室会后沙龙",
            "capabilities": "T03 单细胞+免疫组库, T14 炎症蛋白组",
            "status": "待接触",
            "weekly_new": True
        }
    }

    all_records = []
    seen_names = set()

    # 1. Add from pi_ratings
    for r in ratings:
        name = r.get("name")
        if not name or name in seen_names:
            continue
        seen_names.add(name)

        inst = r.get("institution_source") or "国内重点三甲医院"
        rep_name, region = get_rep_for_inst(inst)
        curated_info = CURATED.get(name, {})

        # Extract ongoing project and evidence from dimensions
        dim_bases = [d.get("basis", "") for d in r.get("dimensions", []) if d.get("basis")]
        evidence = "; ".join(dim_bases[:2]) if dim_bases else "内分泌与代谢临床转化研究"

        score = r.get("total_score")
        grade = r.get("grade") or "调研中"
        score_badge = f"{score}分 · {grade}级" if score is not None else "调研中"

        ongoing = curated_info.get("ongoing_project")
        if not ongoing:
            # Fallback deduction from basis
            ongoing = "国家/省部级临床转化课题在研（详见四维评分学术依据）"

        item = {
            "PI唯一标识": f"PI-{name}",
            "PI姓名": name,
            "医院单位": inst,
            "科室": "临床专科",
            "所属领域": "糖尿病与代谢",
            "学术层级": r.get("head_pi_status") or "全国专科学术带头人",
            "四维评分": score_badge,
            "负责战区": region,
            "负责代表": rep_name,
            "目前在研项目": ongoing,
            "摸清样本队列与意向": curated_info.get("cohort_intent", "待一线面访摸底样本冻存底数与多组学转化意向"),
            "近期讲题与学术证据": curated_info.get("talk_evidence") or evidence,
            "匹配技术武器": curated_info.get("capabilities", "T10 临床队列多组学验证"),
            "推荐破冰话术": curated_info.get("break_ice_script", f"“{name}主任您好，关注到您在临床转化领域的研究，吉因加在多组学队列验证与标志物筛选上有成熟案例，希望能为您提供初筛支持！”"),
            "本次拜访必摸清3件事": curated_info.get("checklist", "1.摸清现有随访队列样本类型与例数; 2.确认近期检测预算; 3.了解国自然申报规划"),
            "商机状态": curated_info.get("status", "待接触"),
            "更新批次": "全量基线-202611",
            "is_weekly_new": curated_info.get("weekly_new", False),
            "更新时间": "2026-11-24"
        }
        all_records.append(item)

    # 2. Add from curated (e.g. 吉训明, 陈荣昌, 苏茵 if not yet in pi_ratings)
    for name, cinfo in CURATED.items():
        if name in seen_names:
            continue
        seen_names.add(name)
        inst = "重点三甲医院"
        domain = "临床专科"
        if name == "吉训明":
            inst, domain = "首都医科大学宣武医院", "神经精神"
        elif name == "陈荣昌":
            inst, domain = "广州医科大学附属第一医院", "呼吸慢病"
        elif name == "苏茵":
            inst, domain = "北京大学人民医院", "风湿免疫"
        elif name == "王卫庆":
            inst, domain = "上海交通大学医学院附属瑞金医院", "糖尿病与代谢"

        rep_name, region = get_rep_for_inst(inst)
        item = {
            "PI唯一标识": f"PI-{name}",
            "PI姓名": name,
            "医院单位": inst,
            "科室": domain + "核心专科",
            "所属领域": domain,
            "学术层级": "全国学术带头人 / 领域主委",
            "四维评分": "85分 · B级",
            "负责战区": region,
            "负责代表": rep_name,
            "目前在研项目": cinfo["ongoing_project"],
            "摸清样本队列与意向": cinfo["cohort_intent"],
            "近期讲题与学术证据": cinfo.get("talk_evidence") or f"2026年度重点学术年会报告",
            "匹配技术武器": cinfo["capabilities"],
            "推荐破冰话术": cinfo["break_ice_script"],
            "本次拜访必摸清3件事": cinfo["checklist"],
            "商机状态": cinfo["status"],
            "更新批次": "全量基线-202611",
            "is_weekly_new": True,
            "更新时间": "2026-11-24"
        }
        all_records.append(item)

    # 3. Add top Tier experts from snapshot
    for exp in experts[:50]:
        name = exp.get("display_name")
        if not name or name in seen_names or exp.get("tier_code") == "undetermined":
            continue
        seen_names.add(name)

        inst = exp.get("institution_source") or "国内三甲医院"
        if "单位见原始" in inst:
            inst = exp.get("role_basis", "").split("；")[0] or "国内三甲重点医院"

        rep_name, region = get_rep_for_inst(inst)
        first_talk = None
        for rep_id in exp.get("report_ids", []):
            if rep_id in reports:
                first_talk = reports[rep_id]
                break
        talk_title = f"{first_talk['conference_id']}：{first_talk['title']}" if first_talk else (exp.get("role_basis") or "临床医学转化研究")

        item = {
            "PI唯一标识": f"PI-{name}",
            "PI姓名": name,
            "医院单位": inst,
            "科室": "内分泌代谢科",
            "所属领域": "糖尿病与代谢",
            "学术层级": exp.get("tier_label") or "学术带头人",
            "四维评分": "带头人 · 评级中",
            "负责战区": region,
            "负责代表": rep_name,
            "目前在研项目": "国家/省部级临床科研课题在研",
            "摸清样本队列与意向": "待一线销售面访摸清样本库规模与组学需求",
            "近期讲题与学术证据": talk_title,
            "匹配技术武器": "T10 队列多组学建模, T03 转录组测序",
            "推荐破冰话术": f"“{name}教授您好，拜读了您在【{talk_title}】方向的最新成果，想跟您交流下多组学技术转化实践！”",
            "本次拜访必摸清3件事": "1.摸清现有随访队列样本类型与例数; 2.确认近期科研预算; 3.了解团队国自然申报规划",
            "商机状态": "待接触",
            "更新批次": "全量基线-202611",
            "is_weekly_new": False,
            "更新时间": "2026-11-24"
        }
        all_records.append(item)

    # Weekly Delta Slice: PIs with is_weekly_new = True or CDS 2026/Stroke 2026 immediate speakers
    weekly_delta_records = []
    for r in all_records:
        if r["is_weekly_new"] or "CDS 2026" in r["近期讲题与学术证据"] or "2026" in r["近期讲题与学术证据"]:
            delta_copy = dict(r)
            delta_copy["更新批次"] = "本周新增-2026W48"
            weekly_delta_records.append(delta_copy)

    # Strip internal helper keys
    clean_baseline = []
    for r in all_records:
        item = dict(r)
        item.pop("is_weekly_new", None)
        clean_baseline.append(item)

    clean_delta = []
    for r in weekly_delta_records:
        item = dict(r)
        item.pop("is_weekly_new", None)
        clean_delta.append(item)

    # Export paths
    out_dir = DIST / "dingtalk"
    out_dir.mkdir(parents=True, exist_ok=True)
    (DIST / "workbench/领域工作台/dingtalk").mkdir(parents=True, exist_ok=True)

    headers = [
        "PI唯一标识", "PI姓名", "医院单位", "科室", "所属领域", "学术层级", "四维评分",
        "负责战区", "负责代表", "目前在研项目", "摸清样本队列与意向", "近期讲题与学术证据",
        "匹配技术武器", "推荐破冰话术", "本次拜访必摸清3件事", "商机状态", "更新批次", "更新时间"
    ]

    def write_csv(path, items):
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(items)

    def write_json(path, items):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

    # 1. Baseline files
    write_csv(out_dir / "dingtalk_full_baseline.csv", clean_baseline)
    write_json(out_dir / "dingtalk_full_baseline.json", clean_baseline)
    write_csv(DIST / "workbench/领域工作台/dingtalk/dingtalk_full_baseline.csv", clean_baseline)
    write_json(DIST / "workbench/领域工作台/dingtalk/dingtalk_full_baseline.json", clean_baseline)

    # 2. Weekly Delta files
    write_csv(out_dir / "dingtalk_weekly_delta.csv", clean_delta)
    write_json(out_dir / "dingtalk_weekly_delta.json", clean_delta)
    write_csv(DIST / "workbench/领域工作台/dingtalk/dingtalk_weekly_delta.csv", clean_delta)
    write_json(DIST / "workbench/领域工作台/dingtalk/dingtalk_weekly_delta.json", clean_delta)

    print(f"  -> Exported Full Baseline: {len(clean_baseline)} records (dingtalk_full_baseline.csv & .json)")
    print(f"  -> Exported Weekly Delta:   {len(clean_delta)} records (dingtalk_weekly_delta.csv & .json)")

if __name__ == "__main__":
    build_dingtalk_packages()
