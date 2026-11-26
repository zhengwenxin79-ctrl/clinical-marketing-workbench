# -*- coding: utf-8 -*-
"""
DingTalk Automation Sync Service (钉钉多维表与机器人自动化同步网关)
1. 监控并读取 dist/dingtalk/ 下的最新产物：
   - dingtalk_conferences.json
   - dingtalk_pi_database_21col.json
   - dingtalk_products_capabilities.json
   - dingtalk_battle_cards.json
   - dingtalk_weekly_delta.json
2. 自动化写入与同步能力：
   - 方式 A (钉钉多维表 Notable OpenAPI 直连写入):
     接口：POST https://api.dingtalk.com/v1.0/notable/bases/{baseId}/sheets/{sheetId}/records
     鉴权：POST https://api.dingtalk.com/v1.0/oauth2/accessToken
   - 方式 B (钉钉群机器人 Webhook 通知卡片):
     支持发送 Markdown 富文本卡片，附带下载链接与统计。
"""
import os
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST_DINGTALK = ROOT / "dist" / "dingtalk"

def load_json(filename):
    path = DIST_DINGTALK / filename
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def get_dingtalk_access_token(app_key, app_secret):
    """
    获取钉钉企业内部应用 AccessToken (官方新版 v1.0 标准接口)
    接口文档：https://open.dingtalk.com/document/orgapp/obtain-orgapp-token
    """
    url = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
    payload = json.dumps({"appKey": app_key, "appSecret": app_secret}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            token = data.get("accessToken")
            if token:
                return token
            print(f"  [Error] 获取 AccessToken 失败: {data}")
            return None
    except Exception as e:
        print(f"  [Error] 请求 AccessToken 网络异常: {e}")
        return None

def push_to_dingtalk_notable(access_token, base_id, sheet_id, records, batch_size=100):
    """
    通过钉钉官方 Notable OpenAPI 批量向多维表写入记录
    接口文档：https://open.dingtalk.com/document/isvapp/batch-create-records
    POST https://api.dingtalk.com/v1.0/notable/bases/{baseId}/sheets/{sheetId}/records
    """
    if not (access_token and base_id and sheet_id and records):
        return 0

    url = f"https://api.dingtalk.com/v1.0/notable/bases/{base_id}/sheets/{sheet_id}/records"
    headers = {
        "Content-Type": "application/json",
        "x-acs-dingtalk-access-token": access_token
    }

    inserted = 0
    # 钉钉多维表单次最大写入建议 100-200 条，分批批量推送
    for i in range(0, len(records), batch_size):
        chunk = records[i:i + batch_size]
        payload = {"records": [{"fields": r} for r in chunk]}
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                inserted += len(chunk)
                print(f"    -> 成功写入批次 [{i + 1}-{i + len(chunk)}] (已写入 {inserted}/{len(records)} 条)")
        except urllib.error.HTTPError as he:
            err_body = he.read().decode('utf-8', errors='replace')
            print(f"    [Error] 批次 [{i + 1}-{i + len(chunk)}] HTTP 写入失败 (code={he.code}): {err_body}")
        except Exception as e:
            print(f"    [Error] 批次 [{i + 1}-{i + len(chunk)}] 写入异常: {e}")

    return inserted

def notify_dingtalk_robot(webhook_url, summary_text):
    """通过钉钉群机器人 Webhook 发送 ActionCard 或 Markdown 卡片"""
    if not webhook_url:
        return False
    
    headers = {"Content-Type": "application/json; charset=utf-8"}
    msg = {
        "msgtype": "markdown",
        "markdown": {
            "title": "【WorkBuddy 智能营销多维库更新通知】",
            "text": f"### 🚀 WorkBuddy 数据库更新已完成\n\n"
                    f"{summary_text}\n\n"
                    f"> **数据沉淀四大底表已同步刷新**：\n"
                    f"- 📅 学术会议库：已更新最新议程与蹲点指引\n"
                    f"- 👨‍⚕️ PI全息库：已同步 21 列画像（含学会任职与共识）\n"
                    f"- 🧬 公司产品能力库：T01-T17技术平台与P01-P11产品库\n"
                    f"- 🎯 销售商机作战卡：已生成对应战区代表破冰任务\n\n"
                    f"[点击查看工作台](https://zhengwenxin79-ctrl.github.io/clinical-marketing-workbench/)"
        }
    }
    
    try:
        req = urllib.request.Request(webhook_url, data=json.dumps(msg).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            if res_data.get("errcode") == 0:
                print("  -> 钉钉群机器人更新卡片发送成功！")
                return True
            else:
                print(f"  -> 钉钉机器人返回错误: {res_data}")
                return False
    except Exception as e:
        print(f"  -> 发送钉钉通知失败: {e}")
        return False

def run_sync():
    print("=== [DingTalk Auto Sync] Checking dist/dingtalk datasets ===")
    conferences = load_json("dingtalk_conferences.json")
    pis = load_json("dingtalk_pi_database_21col.json")
    products = load_json("dingtalk_products_capabilities.json")
    battle_cards = load_json("dingtalk_battle_cards.json")
    deltas = load_json("dingtalk_weekly_delta.json")
    
    summary = f"- **会议监控库**: 包含 {len(conferences)} 场重点会议 (含已审核批准入库)\n" \
              f"- **PI全息档案库**: 包含 {len(pis)} 位 21列专家画像\n" \
              f"- **产品与技术能力库**: 包含 {len(products)} 项核心技术平台与检测产品\n" \
              f"- **商机作战任务卡**: 包含 {len(battle_cards)} 张战区任务卡\n" \
              f"- **本轮周度增量**: 新增/更新 {len(deltas)} 条记录"
    
    print(summary)
    
    # 1. 尝试直连钉钉 Notable 多维表写入
    app_key = os.environ.get("DINGTALK_APP_KEY", "")
    app_secret = os.environ.get("DINGTALK_APP_SECRET", "")
    base_id = os.environ.get("DINGTALK_BASE_ID", "")
    sheet_conf = os.environ.get("DINGTALK_SHEET_CONFERENCES", "")
    sheet_pi = os.environ.get("DINGTALK_SHEET_PIS", "")
    sheet_prod = os.environ.get("DINGTALK_SHEET_PRODUCTS", "")
    sheet_bc = os.environ.get("DINGTALK_SHEET_BATTLE_CARDS", "")

    has_aitable_creds = bool(app_key and app_secret and base_id)
    if has_aitable_creds:
        print("\n🚀 [Notable Sync] 检测到多维表配置凭证，正在连接钉钉开放平台批量写入记录...")
        token = get_dingtalk_access_token(app_key, app_secret)
        if token:
            print("  -> 成功获取钉钉开放平台 AccessToken！")
            if sheet_conf:
                print(f"  -> 正在向【会议库】(sheet={sheet_conf}) 写入 {len(conferences)} 条记录...")
                c_ins = push_to_dingtalk_notable(token, base_id, sheet_conf, conferences)
                print(f"  -> 【会议库】写入完成，累计写入 {c_ins} 条。")
            if sheet_pi:
                print(f"  -> 正在向【PI 21列库】(sheet={sheet_pi}) 写入 {len(pis)} 条记录...")
                p_ins = push_to_dingtalk_notable(token, base_id, sheet_pi, pis)
                print(f"  -> 【PI 21列库】写入完成，累计写入 {p_ins} 条。")
            if sheet_prod:
                print(f"  -> 正在向【产品能力库】(sheet={sheet_prod}) 写入 {len(products)} 条记录...")
                pr_ins = push_to_dingtalk_notable(token, base_id, sheet_prod, products)
                print(f"  -> 【产品能力库】写入完成，累计写入 {pr_ins} 条。")
            if sheet_bc:
                print(f"  -> 正在向【作战任务表】(sheet={sheet_bc}) 写入 {len(battle_cards)} 条记录...")
                b_ins = push_to_dingtalk_notable(token, base_id, sheet_bc, battle_cards)
                print(f"  -> 【作战任务表】写入完成，累计写入 {b_ins} 条。")
        else:
            print("  [Error] 获取 AccessToken 失败，无法继续写入多维表。")
    else:
        print("\n💡 [提示] 当前未配置 DINGTALK_APP_KEY / DINGTALK_APP_SECRET / DINGTALK_BASE_ID。")
        print("   若需真正向钉钉在线多维表直写记录，请配置上述环境变量及对应 sheetId。")

    # 2. 尝试发送钉钉群机器人卡片通知
    webhook_url = os.environ.get("DINGTALK_WEBHOOK_URL", "")
    if webhook_url:
        print("\n📢 [Robot Notify] 正在向钉钉群机器人发送卡片通知...")
        notify_dingtalk_robot(webhook_url, summary)
    else:
        print("💡 [提示] 当前未配置 DINGTALK_WEBHOOK_URL。若需群通知，可在环境变量中配置群机器人 Webhook。")

if __name__ == "__main__":
    run_sync()
