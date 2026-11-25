#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# WorkBuddy / CodeBuddy CLI 真实自动执行信箱网关 (Mailbox IPC + Headless CLI Runner)
# 收到网页派单后立即在后台真实拉起 codebuddy -p 执行专属 Skill，实时回传进度与产出文件

import os
import sys
import json
import time
import shutil
import threading
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAILBOX_DIR = os.path.join(BASE_DIR, 'workbench', 'agent_mailbox')
INBOX_DIR = os.path.join(MAILBOX_DIR, 'inbox')
OUTBOX_DIR = os.path.join(MAILBOX_DIR, 'outbox')

TASK_FILE = os.path.join(INBOX_DIR, 'task.json')
PROGRESS_FILE = os.path.join(OUTBOX_DIR, 'progress.json')
RESULT_FILE = os.path.join(OUTBOX_DIR, 'latest_result.json')

# 通用 Skill 路径候选列表（优先使用 D:\Users\ 标准安装目录）
D_USERS_SKILL_PATH = r"D:\Users\skills\conference-collection-rating\SKILL.md"
PROJECT_SKILL_PATH = os.path.join(BASE_DIR, 'skills', 'conference-collection-rating', 'SKILL.md')
LEGACY_LOCAL_SKILL_PATH = r"C:\Users\geneplus\WorkBuddy\2026-11-06-16-31-58\_input\会议收集评级\SKILL.md"

_run_lock = threading.Lock()
_is_running = False
_current_task_id = None


def get_active_skill_path():
    """获取当前可用的 Skill 路径"""
    if os.path.exists(D_USERS_SKILL_PATH):
        return D_USERS_SKILL_PATH
    if os.path.exists(PROJECT_SKILL_PATH):
        return os.path.abspath(PROJECT_SKILL_PATH)
    if os.path.exists(LEGACY_LOCAL_SKILL_PATH):
        return LEGACY_LOCAL_SKILL_PATH
    return D_USERS_SKILL_PATH


def find_codebuddy_cli():
    """查找本机安装的官方 codebuddy.cmd / codebuddy 可执行文件"""
    candidates = [
        os.path.join(os.path.expanduser('~'), 'bin', 'codebuddy.cmd'),
        os.path.join(os.environ.get('APPDATA', ''), 'npm', 'codebuddy.cmd'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'npm', 'codebuddy.cmd'),
        r"C:\Program Files\nodejs\codebuddy.cmd",
    ]
    for p in candidates:
        if p and os.path.exists(p):
            return p
    which_hit = shutil.which('codebuddy') or shutil.which('codebuddy.cmd')
    return which_hit


def ensure_dirs():
    os.makedirs(INBOX_DIR, exist_ok=True)
    os.makedirs(OUTBOX_DIR, exist_ok=True)


def write_progress(data):
    ensure_dirs()
    tmp_file = PROGRESS_FILE + '.tmp'
    with open(tmp_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, PROGRESS_FILE)


def read_progress():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "status": "idle",
        "percent": 0,
        "message": "信箱空闲，等待网页派发采集任务",
        "active_skill_path": get_active_skill_path(),
        "cli_ready": bool(find_codebuddy_cli()),
        "logs": []
    }


def extract_cli_summary(stdout_text):
    """从 codebuddy --output-format json 的输出中提取最终回复文本"""
    if not stdout_text:
        return ""
    try:
        parsed = json.loads(stdout_text)
        if isinstance(parsed, list):
            for item in reversed(parsed):
                if isinstance(item, dict) and item.get('type') == 'result' and item.get('result'):
                    return str(item.get('result'))
            for item in reversed(parsed):
                if isinstance(item, dict) and item.get('role') == 'assistant':
                    parts = item.get('content') or []
                    texts = [p.get('text', '') for p in parts if isinstance(p, dict) and p.get('text')]
                    if texts:
                        return "\n".join(texts)
        elif isinstance(parsed, dict):
            return str(parsed.get('result') or parsed.get('message') or stdout_text[:1000])
    except Exception:
        pass
    return stdout_text.strip()[-1500:]


def list_outbox_artifacts(since_ts):
    """扫描 outbox 目录中本次任务新生成的 Excel/CSV/JSON 文件"""
    found = []
    if not os.path.exists(OUTBOX_DIR):
        return found
    for name in os.listdir(OUTBOX_DIR):
        if name in ('progress.json', 'progress.json.tmp') or name.endswith(('_stdout.log', '_stderr.log', '_receipt.json')):
            continue
        full = os.path.join(OUTBOX_DIR, name)
        if os.path.isfile(full) and os.path.getmtime(full) >= since_ts - 2:
            found.append(full)
    return found


def run_codebuddy_worker(task_id, task_payload, cli_path):
    """后台线程：真实调用 codebuddy -p 执行会议采集与评级 Skill，并实时刷新进度"""
    global _is_running, _current_task_id
    start_ts = time.time()
    active_skill = task_payload['skill_file']
    domains_str = '、'.join(task_payload.get('domains', []))
    scope = task_payload.get('scope', 'all_59')
    target_week = task_payload.get('target_week', '下一自然周')

    scope_desc = {
        'all_59': '全量 59 个官方学会与 6 大会务微站锚点 + 全网补充检索',
        'upcoming_week': f'目标周期（{target_week}）即将召开的重点线下会议',
        'domain_focus': '重点追查尚未发布日程的已入库会议日程更新与补充会议'
    }.get(scope, scope)

    prompt = (
        f"请严格阅读并遵循技能文件 `{active_skill}`（及其同级 references 目录下的组织与渠道表、核心会议系列表）执行本次会议收集与初评任务。\n"
        f"本次工单编号：{task_id}\n"
        f"巡检范围：{scope_desc}\n"
        f"覆盖领域：{domains_str}\n"
        f"目标周期：{target_week}\n"
        f"交付要求：\n"
        f"1. 按技能口径完成会议收集、排除硬性不收录与降档项，并核实最新链接与日程状态；\n"
        f"2. 将结果 Excel（或 CSV）保存到 `{OUTBOX_DIR}` 目录，同时将结构化会议列表写入 `{RESULT_FILE}`（JSON 格式，包含 `items` 数组，每项尽量含 `会议名称`、`领域大类`、`会议时间`、`会议地点`、`联系人`、`优先级`、`备注`、`schedule_url`、`official_url` 字段）；\n"
        f"3. 完成后简要汇报本次收集的会议总数、重点关注场次以及输出文件路径。"
    )

    logs = [
        f"[{time.strftime('%H:%M:%S')}] 📬 工单 {task_id} 已写入 inbox/task.json",
        f"[{time.strftime('%H:%M:%S')}] 🎯 绑定专属技能: {active_skill}",
        f"[{time.strftime('%H:%M:%S')}] 🚀 正在拉起本地 CodeBuddy CLI ({os.path.basename(cli_path)})..."
    ]

    write_progress({
        "task_id": task_id,
        "status": "running",
        "percent": 12,
        "message": "正在启动 CodeBuddy CLI 并加载《会议收集评级》Skill...",
        "active_skill": active_skill,
        "started_at": time.strftime('%Y-%m-%d %H:%M:%S'),
        "logs": list(logs)
    })

    # 清理本地代理环境变量，避免拦截腾讯云 wb.tencentbuddy.com 的 HTTPS 连接
    env = os.environ.copy()
    for k in ('HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy'):
        env.pop(k, None)
    env['NO_PROXY'] = '*'
    env['PYTHONIOENCODING'] = 'utf-8'

    cmd = [
        cli_path,
        '-p', prompt,
        '--output-format', 'json',
        '--permission-mode', 'bypassPermissions'
    ]

    try:
        max_attempts = 2
        stdout_text, stderr_text, return_code = "", "", -1

        for attempt in range(1, max_attempts + 1):
            stdout_log_path = os.path.join(OUTBOX_DIR, f"{task_id}_stdout.log")
            stderr_log_path = os.path.join(OUTBOX_DIR, f"{task_id}_stderr.log")
            with open(stdout_log_path, 'w', encoding='utf-8') as out_f, open(stderr_log_path, 'w', encoding='utf-8') as err_f:
                proc = subprocess.Popen(
                    cmd,
                    cwd=BASE_DIR,
                    env=env,
                    stdout=out_f,
                    stderr=err_f,
                    stdin=subprocess.DEVNULL
                )

                attempt_tag = f"（第 {attempt}/{max_attempts} 次尝试）" if attempt > 1 else ""
                logs.append(f"[{time.strftime('%H:%M:%S')}] ✅ CodeBuddy 进程已启动 (PID: {proc.pid}){attempt_tag}，正在联网检索与筛选会议...")
                write_progress({
                    "task_id": task_id,
                    "status": "running",
                    "percent": 22,
                    "message": f"CodeBuddy 正在后台真实执行联网检索与初评（PID: {proc.pid}）{attempt_tag}...",
                    "active_skill": active_skill,
                    "pid": proc.pid,
                    "logs": list(logs)
                })

                last_heartbeat = 0
                max_timeout_sec = 900  # 15 分钟安全超时上限
                while proc.poll() is None:
                    elapsed = int(time.time() - start_ts)
                    if elapsed >= max_timeout_sec:
                        proc.kill()
                        logs.append(f"[{time.strftime('%H:%M:%S')}] ⚠️ 运行超过 {max_timeout_sec} 秒安全上限，已自动终止进程")
                        break
                    if elapsed - last_heartbeat >= 5:
                        last_heartbeat = elapsed
                        pct = min(88, 22 + int(elapsed * 0.4))
                        if elapsed in (10, 30, 60, 120, 180, 300, 480):
                            logs.append(f"[{time.strftime('%H:%M:%S')}] ⏳ Agent 正在持续执行中（已耗时 {elapsed} 秒），请耐心等待检索与评级完成...")
                        write_progress({
                            "task_id": task_id,
                            "status": "running",
                            "percent": pct,
                            "message": f"CodeBuddy 正在后台真实执行《会议收集评级》（已耗时 {elapsed} 秒）...",
                            "active_skill": active_skill,
                            "pid": proc.pid,
                            "elapsed_seconds": elapsed,
                            "logs": list(logs[-30:])
                        })
                    time.sleep(1)

                proc.wait()
                return_code = proc.returncode

            with open(stdout_log_path, 'r', encoding='utf-8', errors='replace') as f:
                stdout_text = f.read()
            with open(stderr_log_path, 'r', encoding='utf-8', errors='replace') as f:
                stderr_text = f.read()

            is_tls_502 = (not stdout_text.strip()) and ('502' in (stderr_text or '') or 'TLS' in (stderr_text or '') or 'disconnected' in (stderr_text or ''))

            if is_tls_502 and attempt < max_attempts:
                logs.append(f"[{time.strftime('%H:%M:%S')}] ⚠️ 腾讯云连接出现临时 TLS 波动 (502)，3 秒后自动重试...")
                write_progress({
                    "task_id": task_id,
                    "status": "running",
                    "percent": 20,
                    "message": "遇到临时网络波动 (502)，正在自动重试...",
                    "active_skill": active_skill,
                    "logs": list(logs[-30:])
                })
                time.sleep(3)
                continue
            break

        elapsed = int(time.time() - start_ts)
        summary = extract_cli_summary(stdout_text)
        artifacts = list_outbox_artifacts(start_ts)
        has_real_error = (return_code != 0) or (not summary.strip() and bool((stderr_text or '').strip()))

        # 保存完整执行回执
        receipt_path = os.path.join(OUTBOX_DIR, f"{task_id}_receipt.json")
        with open(receipt_path, 'w', encoding='utf-8') as f:
            json.dump({
                "task_id": task_id,
                "return_code": return_code,
                "has_real_error": has_real_error,
                "elapsed_seconds": elapsed,
                "summary": summary,
                "stderr": (stderr_text or '')[-1500:],
                "artifacts": artifacts,
                "finished_at": time.strftime('%Y-%m-%d %H:%M:%S')
            }, f, ensure_ascii=False, indent=2)

        if not has_real_error:
            task_payload['status'] = 'done'
            task_payload['finished_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
            with open(TASK_FILE, 'w', encoding='utf-8') as f:
                json.dump(task_payload, f, ensure_ascii=False, indent=2)

            logs.append(f"[{time.strftime('%H:%M:%S')}] 🎉 CodeBuddy 执行完成！（共耗时 {elapsed} 秒）")
            if artifacts:
                logs.append(f"[{time.strftime('%H:%M:%S')}] 📁 已生成产物文件: {', '.join(os.path.basename(a) for a in artifacts)}")
            if summary:
                first_lines = [ln.strip() for ln in summary.splitlines() if ln.strip()][:5]
                for ln in first_lines:
                    logs.append(f"📝 {ln[:140]}")

            parsed_items = []
            if os.path.exists(RESULT_FILE) and os.path.getmtime(RESULT_FILE) >= start_ts - 2:
                try:
                    with open(RESULT_FILE, 'r', encoding='utf-8') as rf:
                        rj = json.load(rf)
                        parsed_items = rj if isinstance(rj, list) else (rj.get('items') or rj.get('conferences') or [])
                except Exception:
                    pass

            write_progress({
                "task_id": task_id,
                "status": "done",
                "percent": 100,
                "message": f"✅ CodeBuddy 真实执行完成！（耗时 {elapsed} 秒，产物 {len(artifacts)} 个）",
                "active_skill": active_skill,
                "elapsed_seconds": elapsed,
                "summary": summary,
                "artifacts": artifacts,
                "result_items": parsed_items,
                "logs": list(logs[-40:])
            })
        else:
            err_msg = (stderr_text or summary or f"退出码 {return_code}").strip()[:350]
            logs.append(f"[{time.strftime('%H:%M:%S')}] ❌ CodeBuddy 执行中断/失败: {err_msg}")
            write_progress({
                "task_id": task_id,
                "status": "failed",
                "percent": 100,
                "message": f"❌ 执行失败（耗时 {elapsed} 秒）：{err_msg[:120]}",
                "active_skill": active_skill,
                "elapsed_seconds": elapsed,
                "error": err_msg,
                "logs": list(logs[-40:])
            })

    except Exception as exc:
        logs.append(f"[{time.strftime('%H:%M:%S')}] ❌ 拉起 CodeBuddy 异常: {str(exc)}")
        write_progress({
            "task_id": task_id,
            "status": "failed",
            "percent": 100,
            "message": f"❌ 网关拉起进程异常: {str(exc)}",
            "active_skill": active_skill,
            "error": str(exc),
            "logs": list(logs[-40:])
        })
    finally:
        with _run_lock:
            _is_running = False
            _current_task_id = None


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
        if self.path.startswith('/api/mailbox/health'):
            cli_path = find_codebuddy_cli()
            self._set_headers(200)
            self.wfile.write(json.dumps({
                "ok": True,
                "cli_ready": bool(cli_path),
                "cli_path": cli_path,
                "active_skill_path": get_active_skill_path(),
                "is_running": _is_running,
                "current_task_id": _current_task_id
            }, ensure_ascii=False).encode('utf-8'))

        elif self.path.startswith('/api/mailbox/progress'):
            ensure_dirs()
            data = read_progress()
            data['is_running'] = _is_running
            data['cli_ready'] = bool(find_codebuddy_cli())
            self._set_headers(200)
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

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
        global _is_running, _current_task_id
        ensure_dirs()
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b'{}'
        try:
            body = json.loads(post_data.decode('utf-8'))
        except Exception:
            body = {}

        if self.path == '/api/mailbox/dispatch':
            with _run_lock:
                if _is_running:
                    self._set_headers(200)
                    self.wfile.write(json.dumps({
                        "success": True,
                        "already_running": True,
                        "task_id": _current_task_id,
                        "message": f"任务 {_current_task_id} 正在后台执行中，已接管实时进度展示！"
                    }, ensure_ascii=False).encode('utf-8'))
                    return

                cli_path = find_codebuddy_cli()
                task_id = f"TASK-{int(time.time())}"
                scope = body.get('scope', 'all_59')
                target_week = body.get('target_week', '下周')
                domains = body.get('domains', ['内分泌', '心血管', '神经精神', '慢阻肺', '自免', '泛血管'])
                active_skill = get_active_skill_path()

                task_payload = {
                    "task_id": task_id,
                    "skill_name": "conference-collection-rating",
                    "skill_file": active_skill,
                    "scope": scope,
                    "target_week": target_week,
                    "domains": domains,
                    "created_at": time.strftime('%Y-%m-%d %H:%M:%S'),
                    "status": "running" if cli_path else "pending_execution",
                    "instruction_for_workbuddy": f"请加载技能 [{active_skill}]，严格按口径收集 {','.join(domains)} 领域的最新会议，排除硬性降档会议，输出 Excel 并将结果写入 latest_result.json"
                }

                with open(TASK_FILE, 'w', encoding='utf-8') as f:
                    json.dump(task_payload, f, ensure_ascii=False, indent=2)

                if cli_path:
                    _is_running = True
                    _current_task_id = task_id
                    worker = threading.Thread(
                        target=run_codebuddy_worker,
                        args=(task_id, task_payload, cli_path),
                        daemon=True
                    )
                    worker.start()
                    self._set_headers(200)
                    self.wfile.write(json.dumps({
                        "success": True,
                        "auto_executed": True,
                        "task_id": task_id,
                        "cli_path": cli_path,
                        "message": "🚀 已真实拉起本地 CodeBuddy CLI 自动执行《会议收集评级》！"
                    }, ensure_ascii=False).encode('utf-8'))
                else:
                    write_progress({
                        "task_id": task_id,
                        "status": "dispatched",
                        "percent": 5,
                        "message": "未检测到 codebuddy CLI，工单已写入 inbox/task.json，请手动在 WorkBuddy 中执行",
                        "active_skill": active_skill,
                        "logs": [f"[{time.strftime('%H:%M:%S')}] 工单已写入 inbox/task.json（未找到 codebuddy.cmd）"]
                    })
                    self._set_headers(200)
                    self.wfile.write(json.dumps({
                        "success": True,
                        "auto_executed": False,
                        "task_id": task_id,
                        "message": "未检测到 codebuddy CLI，已降级为手动工单模式",
                        "copy_prompt": f"执行工单任务：请读取 workbench/agent_mailbox/inbox/task.json，严格按照已配置的技能《会议收集评级》（路径：{active_skill}）执行全网深度会议与日程采集并产出结果。"
                    }, ensure_ascii=False).encode('utf-8'))

        elif self.path == '/api/mailbox/update_progress':
            write_progress(body)
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
    cli_path = find_codebuddy_cli()
    server_address = ('127.0.0.1', port)
    httpd = HTTPServer(server_address, MailboxBridgeHandler)
    print(f"=== Mailbox IPC + CodeBuddy CLI 自动执行网关已在 127.0.0.1:{port} 启动 ===")
    print(f"  -> CodeBuddy CLI: {cli_path or '未找到'}")
    print(f"  -> 激活 Skill 路径: {active_skill}")
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
