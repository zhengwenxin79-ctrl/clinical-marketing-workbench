# -*- coding: utf-8 -*-
"""
DingTalk Automation Sync Service (钉钉多维表与机器人自动化同步网关)
1. 监控并读取 dist/dingtalk/ 下的最新产物：
   - dingtalk_conferences.json
   - dingtalk_pi_database_21col.json
   - dingtalk_products_capabilities.json
   - dingtalk_battle_cards.json
   - dingtalk_weekly_delta.json
2. 支持两种自动化同步方式：
   - Mode A (群机器人通知卡片): 通过钉钉群 Webhook 实时推送更新卡片，附带下载链接与统计。
   - Mode B (钉钉多维表 OpenAPI 直连写入): 调用钉钉开放平台接口批量追加/更新记录到线上多维表。
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

def notify_dingtalk_robot(webhook_url, summary_text, details=None):
    """通过钉钉群机器人 Webhook 发送 ActionCard 或 Markdown 卡片"""
    if not webhook_url:
        print("  [Notice] DINGTALK_WEBHOOK_URL 未设置，跳过群机器人通知。")
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
                    f"- 👨‍⚕️ PI全息库：已同步21列画像（含学会任职与共识）\n"
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
                print("  -> 钉钉机器人通知发送成功！")
                return True
            else:
                print(f"  -> 钉钉机器人返回错误: {res_data}")
                return False
    except Exception as e:
        print(f"  -> 发送钉钉通知失败: {e}")
        return False

def push_to_dingtalk_aitable(app_key, app_secret, file_id, table_id, records):
    """
    通过钉钉官方 OpenAPI 批量写入多维表格记录
    接口文档：https://open.dingtalk.com/document/orgapp/add-multiple-records
    """
    if not (app_key and app_secret and file_id and table_id):
        print("  [Notice] 钉钉 OpenAPI 配置未完全设置 (AppKey/Secret/FileId/TableId)，跳过直接写入。")
        return False
    
    # 1. 获取 access_token
    token_url = f"https://oapi.dingtalk.com/gettoken?appkey={app_key}&appsecret={app_secret}"
    try:
        with urllib.request.urlopen(token_url, timeout=10) as resp:
            token_res = json.loads(resp.read().decode("utf-8"))
            access_token = token_res.get("access_token")
            if not access_token:
                print(f"  -> 获取 access_token 失败: {token_res}")
                return False
        
        # 2. 批量写入记录
        write_url = f"https://api.dingtalk.com/v1.0/storage/spaces/files/{file_id}/tables/{table_id}/records"
        headers = {
            "Content-Type": "application/json",
            "x-acs-dingtalk-access-token": access_token
        }
        payload = {"records": [{"fields": r} for r in records]}
        req = urllib.request.Request(write_url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            print(f"  -> 成功写入钉钉多维表格 {len(records)} 条记录！")
            return True
    except Exception as e:
        print(f"  -> 调用钉钉 OpenAPI 异常: {e}")
        return False

def run_sync():
    print("=== [DingTalk Auto Sync] Checking dist/dingtalk datasets ===")
    conferences = load_json("dingtalk_conferences.json")
    pis = load_json("dingtalk_pi_database_21col.json")
    products = load_json("dingtalk_products_capabilities.json")
    battle_cards = load_json("dingtalk_battle_cards.json")
    deltas = load_json("dingtalk_weekly_delta.json")
    
    summary = f"- **会议监控库**: 包含 {len(conferences)} 场重点会议\n" \
              f"- **PI全息档案库**: 包含 {len(pis)} 位 21列专家画像\n" \
              f"- **产品与技术能力库**: 包含 {len(products)} 项核心技术/产品\n" \
              f"- **商机作战任务卡**: 包含 {len(battle_cards)} 张战区任务卡\n" \
              f"- **本轮周度增量**: 新增/更新 {len(deltas)} 条记录"
    
    print(summary)
    
    webhook_url = os.environ.get("DINGTALK_WEBHOOK_URL", "")
    if webhook_url:
        notify_dingtalk_robot(webhook_url, summary)
    else:
        print("💡 提示：如需在 WorkBuddy 更新后自动向钉钉群推送通知卡片，可在环境变量中配置 DINGTALK_WEBHOOK_URL。")

if __name__ == "__main__":
    run_sync()
