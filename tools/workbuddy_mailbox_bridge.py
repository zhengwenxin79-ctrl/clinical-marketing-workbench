#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WorkBuddy 信箱机制（Mailbox IPC）调度中继服务
支持通用化 Skill 寻址：
1. 优先使用项目内置独立副本：`skills/conference-collection-rating/SKILL.md`（任何人拉取仓库即可直接使用）
2. 兼容本地 WorkBuddy 用户自定义安装路径：`C:\\Users\\...\\WorkBuddy\\...\\会议收集评级\\SKILL.md`
3. 自动生成跨机器兼容的相对路径/绝对路径工单
4. 零依赖，纯 Python 标准库
"""

import os
import sys
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAILBOX_DIR = os.path.join(BASE_DIR, 'workbench', 'agent_mailbox')
INBOX_DIR = os.path.join(MAILBOX_DIR, 'inbox')
OUTBOX_DIR = os.path.join(MAILBOX_DIR, 'outbox')

TASK_FILE = os.path.join(INBOX_DIR, 'task.json')
PROGRESS_FILE = os.path.join(OUTBOX_DIR, 'progress.json')
RESULT_FILE = os.path.join(OUTBOX_DIR, 'latest_result.json')

# 通用 Skill 路径候选列表（优先使用仓库内通用路径，兜底本地 WorkBuddy 路径）
PROJECT_SKILL_PATH = os.path.join(BASE_DIR, 'skills', 'conference-collection-rating', 'SKILL.md')
LEGACY_LOCAL_SKILL_PATH = r"C:\Users\geneplus\WorkBuddy\2026-11-06-16-31-58\_input\会议收集评级\SKILL.md"

def get_active_skill_path():
    """获取当前可用的 Skill 路径，确保无论在哪台机器上运行都能找到对应文件"""
    if os.path.exists(PROJECT_SKILL_PATH):
        return os.path.abspath(PROJECT_SKILL_PATH)
    if os.path.exists(LEGACY_LOCAL_SKILL_PATH):
        return LEGACY_LOCAL_SKILL_PATH
    return os.path.abspath(PROJECT_SKILL_PATH)

def ensure_dirs():
    os.makedirs(INBOX_DIR, exist_ok=True)
    os.makedirs(OUTBOX_DIR, exist_ok=True)

class MailboxBridgeHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        # 1. 查询当前进度 (Happy 式进度轮询)
        if self.path.startswith('/api/mailbox/progress'):
            ensure_dirs()
            if os.path.exists(PROGRESS_FILE):
                try:
                    with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    self._set_headers(200)
                    self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
                    return
                except Exception:
                    pass
            self._set_headers(200)
            self.wfile.write(json.dumps({
                "status": "idle",
                "percent": 0,
                "message": "信箱等待工单派发",
                "active_skill_path": get_active_skill_path(),
                "logs": []
            }, ensure_ascii=False).encode('utf-8'))

        # 2. 查询最新采集结果
        elif self.path.startswith('/api/mailbox/result'):
            if os.path.exists(RESULT_FILE):
                try:
                    with open(RESULT_FILE, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    self._set_headers(200)
                    self.wfile.write(json.dumps({"success": True, "data": data}, ensure_ascii=False).encode('utf-8'))
                    return
                except Exception:
                    pass
            self._set_headers(200)
            self.wfile.write(json.dumps({"success": False, "message": "暂无最新结果"}, ensure_ascii=False).encode('utf-8'))

        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not Found"}).encode('utf-8'))

    def do_POST(self):
        ensure_dirs()
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
        try:
            body = json.loads(post_data.decode('utf-8'))
        except Exception:
            body = {}

        if self.path == '/api/mailbox/dispatch':
            task_id = f"TASK-{int(time.time())}"
            scope = body.get('scope', 'all_59')
            target_week = body.get('target_week', '下周')
            domains = body.get('domains', ['内分泌', '心血管', '神经精神', '慢阻肺', '自免', '泛血管'])

            active_skill = get_active_skill_path()
            rel_skill = os.path.relpath(active_skill, BASE_DIR) if active_skill.startswith(BASE_DIR) else active_skill

            task_payload = {
                "task_id": task_id,
                "skill_name": "conference-collection-rating",
                "skill_file": active_skill,
                "skill_relative_file": rel_skill,
                "scope": scope,
                "target_week": target_week,
                "domains": domains,
                "created_at": time.strftime('%Y-%m-%d %H:%M:%S'),
                "status": "pending_execution",
                "instruction_for_workbuddy": f"请加载技能 [{rel_skill}]，严格按口径收集 {','.join(domains)} 领域的最新会议，排除硬性降档会议，输出 Excel 并将结果写入 latest_result.json"
            }

            with open(TASK_FILE, 'w', encoding='utf-8') as f:
                json.dump(task_payload, f, ensure_ascii=False, indent=2)

            initial_progress = {
                "task_id": task_id,
                "status": "dispatched",
                "percent": 5,
                "message": "工单已送达 inbox/task.json，等待 Agent 处理...",
                "active_skill": active_skill,
                "logs": [
                    f"[{time.strftime('%H:%M:%S')}] 工单 {task_id} 已写入信箱",
                    f"[{time.strftime('%H:%M:%S')}] 绑定通用 Skill 路径: {rel_skill}",
                    f"[{time.strftime('%H:%M:%S')}] 目标领域: {len(domains)} 大临床慢病方向"
                ]
            }
            with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
                json.dump(initial_progress, f, ensure_ascii=False, indent=2)

            self._set_headers(200)
            self.wfile.write(json.dumps({
                "success": True,
                "task_id": task_id,
                "message": "工单已成功写入 inbox！",
                "skill": "conference-collection-rating",
                "active_skill_path": active_skill,
                "copy_prompt": f"执行工单任务：请读取 workbench/agent_mailbox/inbox/task.json，严格按照已配置的技能《会议收集评级》（路径：{rel_skill}）执行全网深度会议与日程采集并产出结果。"
            }, ensure_ascii=False).encode('utf-8'))

        elif self.path == '/api/mailbox/update_progress':
            with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
                json.dump(body, f, ensure_ascii=False, indent=2)
            self._set_headers(200)
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))

        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not Found"}).encode('utf-8'))

    def log_message(self, format, *args):
        pass

def run(port=8899):
    ensure_dirs()
    active_skill = get_active_skill_path()
    server_address = ('127.0.0.1', port)
    httpd = HTTPServer(server_address, MailboxBridgeHandler)
    print(f"=== Mailbox IPC 信箱中继服务已在 127.0.0.1:{port} 启动 ===")
    print(f"  -> 当前激活的 Skill 路径: {active_skill}")
    print(f"  -> Inbox 目录: {INBOX_DIR}")
    print(f"  -> Outbox 目录: {OUTBOX_DIR}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n服务平稳停止。")

if __name__ == '__main__':
    port = 8899
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run(port)
