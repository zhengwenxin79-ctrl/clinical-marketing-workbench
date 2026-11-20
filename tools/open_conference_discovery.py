"""Open Conference Discovery & Relevance Ranking Engine.
Dual-Track Architecture:
Track 1: Fixed Target Tracking (19 CMA/CMDA organizations, 28 core series, 12 international anchors).
Track 2: Open Web Search Matrix (Disease keyword x Translational keyword x Event keyword x Sales city).

Filters out commercial noise (e.g., nursing, supply chain, routine clinical training)
and scores clinical research value according to the 吉因加《会议收集评级》Skill.
"""
from pathlib import Path
import datetime, json, re, sys

ROOT = Path(__file__).resolve().parents[1]
ANCHORS_CONFIG = ROOT / "workbench/框架配置/会议监控锚点库.json"
TARGETS_CONFIG = ANCHORS_CONFIG # Alias for backward compatibility

# High-value clinical research keywords (Positive anchors)
POSITIVE_RESEARCH_KEYWORDS = [
    "标志物", "biomarker", "分子标志物", "多组学", "转录组", "蛋白质组", "代谢组",
    "基因测序", "全外显子", "ctDNA", "cfDNA", "单细胞", "空间组学",
    "早期诊断", "早筛", "分子分型", "疾病分型", "发病机制", "耐药机制",
    "多中心队列", "前瞻性队列", "临床研究", "临床试验", "科研转化", "转化医学",
    "靶点发现", "预后评估", "风险预测", "精准诊疗", "免疫微环境"
]

# Negative noise keywords (Negative filter - auto-downgraded or discarded)
NEGATIVE_NOISE_KEYWORDS = [
    "护理操作", "护理技术", "护士长培训", "常规病例交流", "基层巡讲", "操作培训",
    "耗材推销", "经销商大会", "设备采购", "医院物价管理", "医疗纠纷防范",
    "中医养生", "针灸推拿普及", "康复理疗实操"
]

def load_targets():
    if not TARGETS_CONFIG.is_file():
        raise FileNotFoundError(f"Missing {TARGETS_CONFIG}")
    return json.loads(TARGETS_CONFIG.read_text(encoding="utf-8"))

def generate_search_queries(target_year=None):
    if not target_year:
        target_year = datetime.datetime.now().year
    targets = load_targets()
    matrix = targets.get("discovery_matrix", {}).get("dimensions", {})
    queries = []

    # 1. Track 1: Fixed Core Series specific queries
    for s in targets.get("core_series", []):
        queries.append({
            "track": "fixed_series",
            "field_id": s["field_id"],
            "series_id": s["id"],
            "query": f"{s['name']} {target_year} 日程 通知 会议网站",
            "tier": s.get("tier", "national_core")
        })

    # 2. Track 1: International Anchors queries
    for a in targets.get("international_anchors", []):
        queries.append({
            "track": "international_anchor",
            "field_id": a["field_id"],
            "anchor_id": a["id"],
            "query": f"{a['name']} {target_year} scientific program abstracts",
            "tier": a.get("tier", "international_top")
        })

    # 3. Track 2: Open Discovery Matrix (Domain x Translational x City)
    disease_kw = matrix.get("disease_keywords", {})
    trans_kw = ["多组学", "标志物", "临床转化", "队列研究", "精准医学"]
    suffixes = ["学术年会", "高峰论坛", "全国学术会议", "研讨会"]
    cities = targets.get("discovery_matrix", {}).get("sales_cities", [])[:5] # Top 5 sales cities

    for field_id, diseases in disease_kw.items():
        for d in diseases[:3]: # Top 3 disease topics per domain
            for t in trans_kw[:2]:
                q_str = f"{d} {t} {suffixes[0]} {target_year}"
                queries.append({
                    "track": "open_matrix",
                    "field_id": field_id,
                    "disease": d,
                    "keyword": t,
                    "query": q_str,
                    "tier": "open_discovery"
                })

    return queries

def evaluate_conference_relevance(item):
    """Evaluates raw conference info against 《会议收集评级》Skill criteria.
    Business Logic:
      - Domestic conferences (国内会议): Evaluated against commercial clinical research conversion criteria
        (重点关注 / 常规关注 / 低优先级 / 待确认), aiming at BD PI visits and clinical research sponsorship.
      - International conferences (国际会议): Treated strictly as '前沿学术风向标', focusing ONLY on
        hot topics, biomarker breakthroughs, and leading international PIs (no domestic BD event logistics).
    Returns:
      relevance_tier: '重点关注' | '常规关注' | '国际风向标(议题/PI)' | '低优先级' | '剔除'
      reason: Explanatory rationale
      matched_keywords: list of matched keywords
      suggested_field: field_id
    """
    cid = item.get("conference_id", "").upper()
    tier_raw = str(item.get("tier") or item.get("tier_code") or item.get("tier_level") or "").strip().upper()
    text = f"{item.get('conference_name', '')} {item.get('raw_content', '')} {item.get('summary', '')}".lower()

    is_international = (
        "A" in tier_raw or "INTERNATIONAL" in tier_raw or "国际核心" in tier_raw or "国际顶级" in tier_raw or
        cid in {"ADA2026", "EASD2026", "ACC2026", "ESC2026", "EULAR2026", "ISTH2026", "RSNA2026", "ASCO2026"}
    )

    # 1. Check International Anchor Mode
    if is_international:
        return {
            "relevance_tier": "国际前沿风向标",
            "track_mode": "international_benchmark",
            "reason": "国际学术风向标：不设国内销售线下跑会排期；专门提取国际最新学术议题、突破性临床研究结果与国际顶级PI带头人，输入知识图谱与学术背书",
            "matched_keywords": ["国际核心", "学术风向标"],
            "passed_gating": True
        }
    
    # 2. Domestic Conference Evaluation
    # 2.1 Check negative noise
    for neg in NEGATIVE_NOISE_KEYWORDS:
        if neg in text:
            return {
                "relevance_tier": "低优先级",
                "track_mode": "domestic_market",
                "reason": f"包含临床实践/护理/非科研关键词（{neg}），建议降低关注优先级",
                "matched_keywords": [neg],
                "passed_gating": False
            }

    # 2.2 Check positive research keywords
    matched_pos = [k for k in POSITIVE_RESEARCH_KEYWORDS if k in text]
    is_top_national = any(t in tier_raw or t in text for t in ["b", "国家级", "全国", "中华医学会", "中国医师协会", "csco"])

    if len(matched_pos) >= 2 or (len(matched_pos) >= 1 and is_top_national):
        tier = "重点关注"
        reason = f"高价值国内临床科研会议：命中核心转化方向（{'、'.join(matched_pos[:3])}），具备明确的组学/标志物科研合作切入点，建议取日程深拆PI"
    elif len(matched_pos) >= 1 or is_top_national:
        tier = "常规关注"
        reason = f"国内重要专科学术会议：具备临床学术价值，供覆盖区域属地销售代表（BD）选择性参会与拜访PI"
    else:
        tier = "待确认"
        reason = "尚未提取到详尽日程或科研专题依据，保留基本信息待获取议程后二次定级"

    return {
        "relevance_tier": tier,
        "track_mode": "domestic_market",
        "reason": reason,
        "matched_keywords": matched_pos,
        "passed_gating": True
    }

if __name__ == "__main__":
    queries = generate_search_queries()
    print(f"Total search queries generated: {len(queries)}")
    print(f"Sample Fixed Query: {queries[0]}")
    print(f"Sample International Query: {queries[28]}")
    print(f"Sample Open Discovery Query: {queries[40]}")
