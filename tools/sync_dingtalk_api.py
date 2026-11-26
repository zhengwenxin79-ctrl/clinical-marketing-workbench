# -*- coding: utf-8 -*-
"""
DingTalk AI表格（多维表）同步网关
=====================================================================
读取 dist/dingtalk/ 下四套产物，通过钉钉官方 Notable OpenAPI 直写在线多维表。

接口依据（官方文档）：
  获取 token : POST https://api.dingtalk.com/v1.0/oauth2/accessToken
  新增记录   : POST https://api.dingtalk.com/v1.0/notable/bases/{baseId}/sheets/{sheetIdOrName}/records
  必填查询参数: operatorId（操作人 unionId）
  幂等参数   : clientToken（UUID v4，相同值重复请求不会重复写入）

用法：
  python -X utf8 tools/sync_dingtalk_api.py --print-fields   # 打印四张表需要的字段名
  python -X utf8 tools/sync_dingtalk_api.py --dry-run        # 离线自检，不发网络请求
  python -X utf8 tools/sync_dingtalk_api.py                  # 真正写入钉钉

配置（优先级：环境变量 > 项目根目录 .env，.env 已被 gitignore）：
  DINGTALK_APP_KEY / DINGTALK_APP_SECRET  企业内部应用凭证
  DINGTALK_BASE_ID                        AI表格文档 baseId（从表格 URL 或文档信息面板获取）
  DINGTALK_OPERATOR_ID                   操作人 unionId（必填，否则钉钉拒绝写入）
  DINGTALK_SHEET_CONFERENCES / _PIS / _PRODUCTS / _BATTLE_CARDS
                                          四张数据表的 sheetId 或 sheetName，未填则用下方默认表名
  DINGTALK_WEBHOOK_URL                   可选，群机器人通知卡片

应用需开通权限：AI表格应用写权限。
"""
import os
import sys
import csv
import json
import uuid
import hashlib
import argparse
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST_DINGTALK = ROOT / "dist" / "dingtalk"
DOTENV_FILE = ROOT / ".env"
STATE_FILE = DIST_DINGTALK / ".sync_state.json"

DEFAULT_SHEETS = {
    "conferences": "会议全景库",
    "pis": "PI全息画像库",
    "products": "产品能力库",
    "battle_cards": "商机作战卡",
}

DATASETS = [
    ("conferences", "会议全景库", "dingtalk_conferences.json"),
    ("pis", "PI全息画像库", "dingtalk_pi_database_21col.json"),
    ("products", "产品能力库", "dingtalk_products_capabilities.json"),
    ("battle_cards", "商机作战卡", "dingtalk_battle_cards.json"),
]

NUMERIC_FIELDS = {"序号", "合计总分"}


# ---------------------------------------------------------------- config ---
def load_dotenv():
    """读取项目根目录 .env；不覆盖已存在的环境变量。"""
    if not DOTENV_FILE.is_file():
        return
    for raw in DOTENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


def load_config():
    load_dotenv()
    cfg = {
        "app_key": os.environ.get("DINGTALK_APP_KEY", ""),
        "app_secret": os.environ.get("DINGTALK_APP_SECRET", ""),
        "base_id": os.environ.get("DINGTALK_BASE_ID", ""),
        "operator_id": os.environ.get("DINGTALK_OPERATOR_ID", ""),
        "webhook": os.environ.get("DINGTALK_WEBHOOK_URL", ""),
        "sheets": {},
    }
    env_names = {
        "conferences": "DINGTALK_SHEET_CONFERENCES",
        "pis": "DINGTALK_SHEET_PIS",
        "products": "DINGTALK_SHEET_PRODUCTS",
        "battle_cards": "DINGTALK_SHEET_BATTLE_CARDS",
    }
    for key, env_name in env_names.items():
        cfg["sheets"][key] = os.environ.get(env_name, "") or DEFAULT_SHEETS[key]
    return cfg


def missing_config(cfg):
    missing = []
    for label, key in [
        ("DINGTALK_APP_KEY", "app_key"),
        ("DINGTALK_APP_SECRET", "app_secret"),
        ("DINGTALK_BASE_ID", "base_id"),
        ("DINGTALK_OPERATOR_ID", "operator_id"),
    ]:
        if not cfg[key]:
            missing.append(label)
    return missing


# ------------------------------------------------------------------ data ---
def load_json(filename):
    path = DIST_DINGTALK / filename
    if not path.exists():
        print(f"  [WARN] 缺少产物文件: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def coerce_fields(row):
    """把数值字段的中文字符串转成数字，以适配钉钉数字类型字段。"""
    out = {}
    for key, value in row.items():
        if key in NUMERIC_FIELDS and isinstance(value, str) and value.strip().isdigit():
            out[key] = int(value.strip())
        elif isinstance(value, (list, dict)):
            out[key] = json.dumps(value, ensure_ascii=False)
        else:
            out[key] = value
    return out


def load_state():
    if STATE_FILE.is_file():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_state(state):
    DIST_DINGTALK.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


# --------------------------------------------------------------- network ---
def get_dingtalk_access_token(app_key, app_secret):
    url = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
    payload = json.dumps({"appKey": app_key, "appSecret": app_secret}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        token = data.get("accessToken")
        if token:
            return token
        print(f"  [Error] 获取 AccessToken 失败: {data}")
    except urllib.error.HTTPError as he:
        print(f"  [Error] AccessToken HTTP {he.code}: {he.read().decode('utf-8', errors='replace')}")
    except Exception as e:
        print(f"  [Error] AccessToken 请求异常: {e}")
    return None


def list_sheets(token, base_id, operator_id):
    """列出 AI表格文档中的所有数据表，返回 [{id,name}]。"""
    query = urllib.parse.urlencode({"operatorId": operator_id})
    url = f"https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets?{query}"
    req = urllib.request.Request(url, headers={"x-acs-dingtalk-access-token": token}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        if isinstance(body, dict) and (body.get("errorCode") or body.get("errorMsg")):
            raise RuntimeError(f"钉钉返回业务错误: {body}")
        return body.get("value", [])
    except urllib.error.HTTPError as he:
        print(f"  [Error] 获取数据表列表 HTTP {he.code}: {he.read().decode('utf-8', errors='replace')[:600]}")
    except Exception as e:
        print(f"  [Error] 获取数据表列表失败: {e}")
    return None


def payload_signature(base_id, sheet, records):
    raw = json.dumps(records, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(f"{base_id}|{sheet}|".encode("utf-8") + raw).hexdigest()


def push_to_dingtalk_notable(token, base_id, sheet, records, operator_id,
                             batch_size=100, dry_run=False, state=None):
    """返回 (成功写入条数, 失败批次数)。state 用于复用 clientToken 实现幂等。"""
    if not records:
        print(f"    -> 【{sheet}】无数据，跳过。")
        return 0, 0
    if state is None:
        state = {}

    signature = payload_signature(base_id, sheet, records)
    state_key = f"{sheet}::{signature}"
    saved_tokens = state.get(state_key, [])
    reused = {str(item.get("index")): item.get("clientToken") for item in saved_tokens if isinstance(item, dict)}

    if dry_run:
        sample = json.dumps(coerce_fields(records[0]), ensure_ascii=False)[:160]
        print(f"    -> [DRY-RUN] {sheet}: {len(records)} 条 / {(len(records) + batch_size - 1) // batch_size} 批，")
        print(f"       URL: /v1.0/notable/bases/{base_id}/sheets/{urllib.parse.quote(sheet, safe='')}/records?operatorId={operator_id or '<未配置>'}")
        print(f"       样例字段: {sample}")
        return len(records), 0

    inserted, failed = 0, 0
    new_tokens = []
    for batch_index, start in enumerate(range(0, len(records), batch_size)):
        chunk = records[start:start + batch_size]
        client_token = reused.get(str(batch_index)) or str(uuid.uuid4())
        new_tokens.append({"index": batch_index, "clientToken": client_token})
        query = urllib.parse.urlencode({"operatorId": operator_id, "clientToken": client_token})
        url = (f"https://api.dingtalk.com/v1.0/notable/bases/{base_id}"
               f"/sheets/{urllib.parse.quote(sheet, safe='')}/records?{query}")
        payload = {"records": [{"fields": coerce_fields(r)} for r in chunk]}
        req = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-acs-dingtalk-access-token": token},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            if isinstance(body, dict) and (body.get("errorCode") or body.get("errorMsg")):
                raise RuntimeError(f"钉钉返回业务错误: {body}")
            row_ids = body.get("value", []) if isinstance(body, dict) else []
            inserted += len(chunk)
            print(f"    -> 【{sheet}】批次 {batch_index + 1}: 写入 {len(chunk)} 条，返回 {len(row_ids)} 个记录ID")
        except urllib.error.HTTPError as he:
            failed += 1
            print(f"    [Error] 【{sheet}】批次 {batch_index + 1} HTTP {he.code}: "
                  f"{he.read().decode('utf-8', errors='replace')[:600]}")
        except Exception as e:
            failed += 1
            print(f"    [Error] 【{sheet}】批次 {batch_index + 1} 失败: {e}")

    state[state_key] = new_tokens
    save_state(state)
    return inserted, failed


def notify_dingtalk_robot(webhook_url, summary_text):
    if not webhook_url:
        return False
    msg = {
        "msgtype": "markdown",
        "markdown": {
            "title": "【WorkBuddy 智能营销多维库更新通知】",
            "text": f"### WorkBuddy 数据库更新已完成\n\n{summary_text}\n\n"
                    "> 数据沉淀四大底表已同步刷新：\n"
                    "- 学术会议库：最新议程与蹲点指引\n"
                    "- PI全息库：21列画像\n"
                    "- 产品能力库：技术平台与检测产品\n"
                    "- 商机作战卡：战区破冰任务",
        },
    }
    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(msg, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            res = json.loads(resp.read().decode("utf-8"))
        if res.get("errcode") == 0:
            print("  -> 钉钉群机器人通知发送成功！")
            return True
        print(f"  -> 钉钉机器人返回错误: {res}")
    except Exception as e:
        print(f"  -> 发送钉钉通知失败: {e}")
    return False


# ------------------------------------------------------------------ main ---
def print_fields():
    print("钉钉四张数据表需要的字段名（顺序一致，字段名必须与表内字段完全相同）：")
    for _, label, filename in DATASETS:
        path = DIST_DINGTALK / filename.replace(".json", ".csv")
        if not path.is_file():
            print(f"\n[{label}] 缺少 {path.name}")
            continue
        with open(path, "r", encoding="utf-8-sig") as f:
            headers = next(csv.reader(f), [])
        print(f"\n[{label}] {len(headers)} 列")
        print("  " + " | ".join(headers))


def run_sync(args):
    cfg = load_config()
    bundles = [(key, label, load_json(filename)) for key, label, filename in DATASETS]
    deltas = load_json("dingtalk_weekly_delta.json")

    summary = (
        f"- **会议监控库**: {len(bundles[0][2])} 场重点会议（含已审核批准入库）\n"
        f"- **PI全息档案库**: {len(bundles[1][2])} 位 21列专家画像\n"
        f"- **产品与技术能力库**: {len(bundles[2][2])} 项技术平台与检测产品\n"
        f"- **商机作战任务卡**: {len(bundles[3][2])} 张战区任务卡\n"
        f"- **本轮周度增量**: {len(deltas)} 条"
    )
    print("=== [DingTalk Notable Sync] ===")
    print(summary)

    if args.print_fields:
        print_fields()
        return 0

    if args.list_sheets:
        token = get_dingtalk_access_token(cfg["app_key"], cfg["app_secret"])
        if not token:
            return 3
        sheets = list_sheets(token, cfg["base_id"], cfg["operator_id"])
        if sheets is None:
            return 3
        print(f"\nAI表格 baseId={cfg['base_id']} 下共 {len(sheets)} 张数据表：")
        for item in sheets:
            print(f"  - {item.get('name')}  (id={item.get('id')})")
        return 0

    dry_run = args.dry_run
    if not dry_run:
        missing = missing_config(cfg)
        if missing:
            print("\n[配置缺失] 以下环境变量未设置，无法写入钉钉：")
            for item in missing:
                print(f"  - {item}")
            print("请在项目根目录 .env 中填写（模板见 .env.example），或通过环境变量注入。")
            print("可用 --dry-run 先做离线自检。")
            return 2

        print("\n[Auth] 正在获取钉钉 AccessToken ...")
        token = get_dingtalk_access_token(cfg["app_key"], cfg["app_secret"])
        if not token:
            return 3
        print("  -> 获取成功。")
    else:
        token = ""
        print("\n[DRY-RUN] 以下为写入计划，不会发起任何网络请求：")

    state = load_state()
    total_inserted, total_failed = 0, 0
    for key, label, records in bundles:
        sheet = cfg["sheets"][key]
        print(f"\n  正在处理【{label}】-> sheet={sheet}, 记录={len(records)}")
        inserted, failed = push_to_dingtalk_notable(
            token, cfg["base_id"], sheet, records, cfg["operator_id"],
            batch_size=args.batch_size, dry_run=dry_run, state=state,
        )
        total_inserted += inserted
        total_failed += failed

    print(f"\n=== 汇总：计划/写入 {total_inserted} 条，失败批次 {total_failed} ===")
    if dry_run:
        print("DRY-RUN 完成。配置凭证后去掉 --dry-run 即可真正写入。")
        return 0

    if cfg["webhook"]:
        notify_dingtalk_robot(cfg["webhook"], summary)
    else:
        print("[提示] 未配置 DINGTALK_WEBHOOK_URL，跳过群通知。")

    if total_failed:
        print("[失败] 存在写入失败的批次，请检查日志后重试（相同数据会复用 clientToken，不会重复写入）。")
        return 3
    print("[完成] 四张表已同步到钉钉在线多维表。")
    return 0


def main():
    parser = argparse.ArgumentParser(description="钉钉 AI表格（多维表）四表同步网关")
    parser.add_argument("--dry-run", action="store_true", help="离线自检，验证产物与写入计划，不调用钉钉接口")
    parser.add_argument("--print-fields", action="store_true", help="打印四张表的字段名清单")
    parser.add_argument("--list-sheets", action="store_true", help="用凭证列出目标 AI表格 下的所有数据表（验证凭证与 baseId）")
    parser.add_argument("--batch-size", type=int, default=100, help="每批写入条数（默认 100）")
    args = parser.parse_args()
    sys.exit(run_sync(args))


if __name__ == "__main__":
    main()
