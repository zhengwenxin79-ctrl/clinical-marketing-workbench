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
    Returns:
      relevance_tier: '重点关注' | '常规关注' | '低优先级' | '剔除'
      reason: Explanatory rationale
      matched_keywords: list of matched keywords
      suggested_field: field_id
    """
    text = f"{item.get('conference_name', '')} {item.get('raw_content', '')} {item.get('summary', '')}".lower()
    
    # 1. Check negative noise
    for neg in NEGATIVE_NOISE_KEYWORDS:
        if neg in text:
            return {
                "relevance_tier": "低优先级",
                "reason": f"包含临床实践/护理/非科研关键词（{neg}），建议降低关注优先级",
                "matched_keywords": [neg],
                "passed_gating": False
            }

    # 2. Check positive research keywords
    matched_pos = [k for k in POSITIVE_RESEARCH_KEYWORDS if k in text]
    
    # 3. Check official tier
    tier_level = item.get("tier_level", "")
    is_top_tier = any(t in tier_level for t in ["国家重点", "国际顶级", "中华医学会", "中国医师协会"])

    if len(matched_pos) >= 2 or (len(matched_pos) >= 1 and is_top_tier):
        tier = "重点关注"
        reason = f"高价值临床科研会议：命中重点科研方向（{'、'.join(matched_pos[:3])}），具备清晰转化研究与组学/标志物合作切入点"
    elif len(matched_pos) >= 1 or is_top_tier:
        tier = "常规关注"
        reason = f"具备临床学术价值：涉及相关学科前沿进展，参会学者中有潜在合作PI团队"
    else:
        tier = "待确认"
        reason = "尚未提取到详尽日程或科研专题依据，保留基本信息待获取议程后二次定级"

    return {
        "relevance_tier": tier,
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
