#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WorkBuddy Local Assistant API 桥接服务
用于接收网页前端的抓取请求，并通过官方 OpenAPI 全自动静默下发给本地 WorkBuddy 客户端执行。
零第三方依赖（纯 Python 标准库），跨平台兼容。
"""

import os
import sys
import json
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

# 配置文件保存路径（存放在 workbench/框架配置/ 目录下）
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', 'workbench', '框架配置', 'workbuddy_api_config.json'
)

DEFAULT_CRAWL_PROMPT = """你是一个临床科研营销情报自动化 Agent。请在当前工作空间执行以下自动化任务：
1. 检查并抓取本周最新的临床学术会议（重点关注糖尿病与代谢、神经精神、心血管等领域），提取议题与讲者名单。
2. 运行构建脚本同步数据：
   python tools/export_pages.py
3. 检查自动化回归测试：
   python tools/test_regression.py
4. 提交并推送到远端仓库。
"""

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"access_token": "", "client_id": "", "enabled": False}

def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

class WorkBuddyBridgeHandler(BaseHTTPRequestHandler):
    def _set_cors_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_cors_headers(200)

    def do_GET(self):
        if self.path.startswith('/api/workbuddy/status'):
            cfg = load_config()
            token = cfg.get('access_token', '')
            if not token:
                self._set_cors_headers(200)
                self.wfile.write(json.dumps({
                    "configured": False,
                    "online": False,
                    "message": "未配置 WorkBuddy OpenAPI Access Token"
                }).encode('utf-8'))
                return

            # 查询官方 OpenAPI 检测本地助手是否在线
            api_url = 'https://www.workbuddy.cn/openapi/v2/localassistant'
            req = urllib.request.Request(
                api_url,
                headers={
                    'Authorization': f'Bearer {token}',
                    'User-Agent': 'Clinical-Marketing-Workbench-Bridge/1.0'
                }
            )
            try:
                with urllib.request.urlopen(req, timeout=5) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    self._set_cors_headers(200)
                    self.wfile.write(json.dumps({
                        "configured": True,
                        "online": res_data.get('data', {}).get('online', True),
                        "raw": res_data
                    }).encode('utf-8'))
            except urllib.error.HTTPError as e:
                self._set_cors_headers(200)
                self.wfile.write(json.dumps({
                    "configured": True,
                    "online": False,
                    "error_code": e.code,
                    "message": f"Token 校验失败或权限不足 (HTTP {e.code})"
                }).encode('utf-8'))
            except Exception as e:
                self._set_cors_headers(200)
                self.wfile.write(json.dumps({
                    "configured": True,
                    "online": False,
                    "message": f"连接 WorkBuddy 云端服务超时或异常: {str(e)}"
                }).encode('utf-8'))
        else:
            self._set_cors_headers(404)
            self.wfile.write(json.dumps({"error": "Not Found"}).encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
        try:
            body = json.loads(post_data.decode('utf-8'))
        except Exception:
            body = {}

        if self.path == '/api/workbuddy/config':
            # 保存 Token 配置
            cfg = load_config()
            cfg['access_token'] = body.get('access_token', '').strip()
            cfg['enabled'] = bool(cfg['access_token'])
            save_config(cfg)
            self._set_cors_headers(200)
            self.wfile.write(json.dumps({
                "success": True,
                "message": "WorkBuddy 鉴权 Token 已成功保存至本地！",
                "configured": cfg['enabled']
            }).encode('utf-8'))

        elif self.path == '/api/workbuddy/trigger':
            # 向 WorkBuddy 本地助手发送静默任务
            cfg = load_config()
            token = cfg.get('access_token', '').strip()
            if not token:
                self._set_cors_headers(400)
                self.wfile.write(json.dumps({
                    "success": False,
                    "message": "请先在工作台中配置 WorkBuddy OpenAPI Access Token！"
                }).encode('utf-8'))
                return

            prompt = body.get('prompt') or DEFAULT_CRAWL_PROMPT
            api_url = 'https://www.workbuddy.cn/openapi/v2/localassistant/message'
            payload = json.dumps({
                "content": prompt,
                "msg_type": "text"
            }).encode('utf-8')

            req = urllib.request.Request(
                api_url,
                data=payload,
                headers={
                    'Authorization': f'Bearer {token}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'Clinical-Marketing-Workbench-Bridge/1.0'
                },
                method='POST'
            )

            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    self._set_cors_headers(200)
                    self.wfile.write(json.dumps({
                        "success": True,
                        "message": "已成功向 WorkBuddy 客户端下发全自动抓取任务！",
                        "response": res_data
                    }).encode('utf-8'))
            except urllib.error.HTTPError as e:
                err_content = e.read().decode('utf-8')
                self._set_cors_headers(e.code)
                self.wfile.write(json.dumps({
                    "success": False,
                    "message": f"WorkBuddy OpenAPI 响应失败 (HTTP {e.code}): {err_content}"
                }).encode('utf-8'))
            except Exception as e:
                self._set_cors_headers(500)
                self.wfile.write(json.dumps({
                    "success": False,
                    "message": f"任务下发超时或网络异常: {str(e)}"
                }).encode('utf-8'))
        else:
            self._set_cors_headers(404)
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode('utf-8'))

    def log_message(self, format, *args):
        # 保持安静输出
        pass

def run(port=8899):
    server_address = ('127.0.0.1', port)
    httpd = HTTPServer(server_address, WorkBuddyBridgeHandler)
    print(f"=== WorkBuddy 本地 OpenAPI 桥接服务已在 127.0.0.1:{port} 启动 ===")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已平稳关闭。")

if __name__ == '__main__':
    port = 8899
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run(port)
