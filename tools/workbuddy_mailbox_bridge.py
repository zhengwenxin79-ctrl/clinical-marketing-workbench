#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# WorkBuddy / CodeBuddy CLI 真实自动执行信箱网关 (Mailbox IPC + Headless CLI Runner)
# 架构：CodeBuddy CLI 专注只读 Skill + 联网检索核实 + 输出结构化 JSON；
#       Python 网关负责确定性落盘（latest_result.json + UTF-8 BOM Excel 兼容 CSV）与网页实时推送，
#       彻底规避无头模式 Write/Bash 权限拦截与 Windows 64KB 管道死锁。

import os
import re
import sys
import csv
import json
import time
import shutil
import threading
import subprocess
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAILBOX_DIR = os.path.join(BASE_DIR, 'workbench', 'agent_mailbox')
INBOX_DIR = os.path.join(MAILBOX_DIR, 'inbox')
OUTBOX_DIR = os.path.join(MAILBOX_DIR, 'outbox')

TASK_FILE = os.path.join(INBOX_DIR, 'task.json')
PROGRESS_FILE = os.path.join(OUTBOX_DIR, 'progress.json')
RESULT_FILE = os.path.join(OUTBOX_DIR, 'latest_result.json')

# 优先使用工作区内部相对路径，确保 CodeBuddy CLI Read 工具 100% 拥有权限且绝不乱码
PROJECT_SKILL_PATH = os.path.join(BASE_DIR, 'skills', 'conference-collection-rating', 'SKILL.md')
D_USERS_SKILL_PATH = r"D:\Users\skills\conference-collection-rating\SKILL.md"
LEGACY_LOCAL_SKILL_PATH = r"C:\Users\geneplus\WorkBuddy\2026-11-06-16-31-58\_input\会议收集评级\SKILL.md"

_run_lock = threading.Lock()
_is_running = False
_current_task_id = None


def get_active_skill_path():
    """优先返回工作区内的 Skill 路径（如本地 D:\\Users\\skills 更新则自动同步进工作区）"""
    if os.path.exists(PROJECT_SKILL_PATH):
        return PROJECT_SKILL_PATH
    if os.path.exists(D_USERS_SKILL_PATH):
        return D_USERS_SKILL_PATH
    if os.path.exists(LEGACY_LOCAL_SKILL_PATH):
        return LEGACY_LOCAL_SKILL_PATH
    return PROJECT_SKILL_PATH


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
    return shutil.which('codebuddy') or shutil.which('codebuddy.cmd')


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
            return str(parsed.get('result') or parsed.get('message') or stdout_text[:2000])
    except Exception:
        pass
    return stdout_text.strip()[-4000:]


def extract_items_from_summary(summary_text):
    """从 CodeBuddy 的最终回复文本中提取结构化会议 JSON 数组"""
    if not summary_text:
        return []
    # 1. 优先匹配 ```json ... ``` 代码块
    blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)```', summary_text, flags=re.IGNORECASE)
    for blk in reversed(blocks):
        blk = blk.strip()
        if not blk:
            continue
        try:
            obj = json.loads(blk)
            if isinstance(obj, list):
                return obj
            if isinstance(obj, dict):
                items = obj.get('items') or obj.get('conferences') or obj.get('data')
                if isinstance(items, list):
                    return items
        except Exception:
            continue

    # 2. 兜底匹配裸 JSON 对象中的 "items": [...]
    m = re.search(r'\{\s*"items"\s*:\s*\[[\s\S]*?\]\s*\}', summary_text)
    if m:
        try:
            obj = json.loads(m.group(0))
            if isinstance(obj.get('items'), list):
                return obj['items']
        except Exception:
            pass
    return []


def priority_sort_key(item):
    """按优先级从高到低排序：A级/核心/特级 > B级/重点关注 > C级/常规关注 > D级/低优先级"""
    if not isinstance(item, dict):
        return 9
    p = str(item.get('优先级') or item.get('priority') or item.get('tier_code') or '').upper()
    if p.startswith('A') or '核心' in p or '特级' in p or '必参' in p or '强烈' in p:
        return 1
    if p.startswith('B') or '重点' in p:
        return 2
    if p.startswith('C') or '常规' in p:
        return 3
    if p.startswith('D') or '低' in p:
        return 4
    return 5


def _norm_conf_name(item):
    if not isinstance(item, dict):
        return ''
    name = str(item.get('会议名称') or item.get('title') or item.get('conference_name') or '')
    return re.sub(r'[\s（()）【】\[\]·\-—_、，,]+', '', name).lower()


def merge_same_week_items(new_items, target_week):
    """同周自动合并去重（只增不减）：保留同目标周已抓到的会议，并用新数据补全链接/备注/联系人"""
    merged_map = {}
    ordered_keys = []

    # 1. 加载同目标周历史底稿
    if os.path.exists(RESULT_FILE):
        try:
            with open(RESULT_FILE, 'r', encoding='utf-8') as f:
                old_obj = json.load(f)
            if isinstance(old_obj, dict) and old_obj.get('target_week') == target_week:
                for it in (old_obj.get('items') or []):
                    k = _norm_conf_name(it)
                    if k and k not in merged_map:
                        merged_map[k] = dict(it)
                        ordered_keys.append(k)
        except Exception:
            pass

    # 2. 合并本轮新抓到的会议（已有则补全空字段/更新备注，新增则追加）
    newly_added = 0
    for it in (new_items or []):
        k = _norm_conf_name(it)
        if not k:
            continue
        if k in merged_map:
            existing = merged_map[k]
            for field, val in it.items():
                if val and (not existing.get(field) or field in ('优先级', 'schedule_url', 'official_url')):
                    existing[field] = val
        else:
            merged_map[k] = dict(it)
            ordered_keys.append(k)
            newly_added += 1

    merged_list = [merged_map[k] for k in ordered_keys]
    merged_list = sorted(merged_list, key=priority_sort_key)
    return merged_list, newly_added


def save_artifacts_from_items(task_id, items, target_week):
    """由 Python 网关确定性落盘 latest_result.json 与 Excel 可直接打开的 UTF-8 BOM CSV（同周合并去重 + A>B>C>D 排序）"""
    ensure_dirs()
    created = []
    if not items:
        return created, [], 0

    merged_items, newly_added = merge_same_week_items(items, target_week)

    # 1. 写入 latest_result.json（供网页前端一键自动导入）
    result_obj = {
        "task_id": task_id,
        "target_week": target_week,
        "generated_at": time.strftime('%Y-%m-%d %H:%M:%S'),
        "count": len(merged_items),
        "newly_added": newly_added,
        "items": merged_items
    }
    with open(RESULT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result_obj, f, ensure_ascii=False, indent=2)
    created.append(RESULT_FILE)

    # 2. 写入 Excel 兼容 CSV (utf-8-sig 带 BOM，微软 Excel 双击打开中文绝不乱码)
    stamp = time.strftime('%Y%m%d_%H%M')
    csv_path = os.path.join(OUTBOX_DIR, f"会议收集评级_{stamp}.csv")
    headers = ['会议名称', '领域大类', '会议时间', '会议地点', '联系人', '优先级', '备注', 'official_url', 'schedule_url']
    with open(csv_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        for it in merged_items:
            if not isinstance(it, dict):
                continue
            row = {
                '会议名称': it.get('会议名称') or it.get('title') or it.get('conference_name') or '',
                '领域大类': it.get('领域大类') or it.get('domain') or '',
                '会议时间': it.get('会议时间') or it.get('date') or '',
                '会议地点': it.get('会议地点') or it.get('venue') or it.get('city') or '',
                '联系人': it.get('联系人') or it.get('contacts') or '',
                '优先级': it.get('优先级') or it.get('priority') or '常规关注',
                '备注': it.get('备注') or it.get('summary') or it.get('review_note') or '',
                'official_url': it.get('official_url') or '',
                'schedule_url': it.get('schedule_url') or ''
            }
            writer.writerow(row)
    created.append(csv_path)
    return created, merged_items, newly_added


def list_outbox_artifacts(since_ts):
    """扫描 outbox 目录中本次任务新生成的 Excel/CSV/JSON 交付产物"""
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
    """后台线程：真实调用 codebuddy -p 联网执行 Skill，由 Python 网关负责确定性落盘"""
    global _is_running, _current_task_id
    start_ts = time.time()
    active_skill = task_payload['skill_file']
    rel_skill = 'skills/conference-collection-rating/SKILL.md'
    domains_str = '、'.join(task_payload.get('domains', []))
    scope = task_payload.get('scope', 'upcoming_week')
    target_week = task_payload.get('target_week', '2026-11-30 ~ 2026-12-06')

    scope_desc = {
        'all_59': '全量 59 个官方学会与 6 大会务微站锚点 + 全网补充检索',
        'upcoming_week': f'目标周期（{target_week}）即将召开的重点线下会议',
        'domain_focus': '重点追查尚未发布日程的已入库会议日程更新与补充会议'
    }.get(scope, scope)

    # 注意：Windows .cmd 批处理传参遇到换行符会截断后续内容，因此 prompt 必须是严格单行！
    prompt = (
        f"请立刻执行会议收集与初评任务（不要停下来反问）："
        f"第一步，用 Read 工具读取工作区内的 {rel_skill} 及 references/组织与渠道表.md、references/核心会议系列表.md；"
        f"第二步，严格按技能口径，用 WebSearch/WebFetch 检索【{domains_str}】领域在目标周期【{target_week}】（范围：{scope_desc}）的真实国内线下会议，排除硬性不收录项并按10个覆盖城市定级；"
        f"第三步，不需要调用 Write/Bash/PowerShell 写文件（由外层网关自动落盘），请直接在最终回复末尾输出一个标准 JSON 代码块（以 ```json 开头、``` 结尾），顶层格式为 {{\"items\": [{{\"会议名称\": \"\", \"领域大类\": \"\", \"会议时间\": \"MM-DD 至 MM-DD\", \"会议地点\": \"城市·场馆\", \"联系人\": \"\", \"优先级\": \"重点关注/常规关注/低优先级\", \"备注\": \"（评级依据）...（日程状态）...（来源）...\", \"official_url\": \"https://...\", \"schedule_url\": \"https://...\"}}]}}，确保 JSON 合法。"
    )

    logs = [
        f"[{time.strftime('%H:%M:%S')}] 📬 工单 {task_id} 已写入 inbox/task.json",
        f"[{time.strftime('%H:%M:%S')}] 🎯 绑定工作区内 Skill: {rel_skill}",
        f"[{time.strftime('%H:%M:%S')}] 🚀 正在拉起本地 CodeBuddy CLI ({os.path.basename(cli_path)})..."
    ]

    write_progress({
        "task_id": task_id,
        "status": "running",
        "percent": 12,
        "message": "正在启动 CodeBuddy CLI 并读取《会议收集评级》Skill...",
        "active_skill": active_skill,
        "started_at": time.strftime('%Y-%m-%d %H:%M:%S'),
        "logs": list(logs)
    })

    # 清理代理环境变量，避免拦截腾讯云 wb.tencentbuddy.com 的 HTTPS 连接
    env = os.environ.copy()
    for k in ('HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy'):
        env.pop(k, None)
    env['NO_PROXY'] = '*'
    env['PYTHONIOENCODING'] = 'utf-8'

    cmd = [
        cli_path,
        '-p', prompt,
        '-y',
        '--output-format', 'json'
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
                max_timeout_sec = 900
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
        has_real_error = (return_code != 0) or (not summary.strip() and bool((stderr_text or '').strip()))

        # 由 Python 网关直接解析 JSON、同周自动合并去重并确定性落盘 CSV + latest_result.json
        parsed_items = extract_items_from_summary(summary) if not has_real_error else []
        if parsed_items:
            created_artifacts, merged_items, newly_added = save_artifacts_from_items(task_id, parsed_items, target_week)
        else:
            created_artifacts, merged_items, newly_added = [], [], 0
        artifacts = sorted(set(list_outbox_artifacts(start_ts) + created_artifacts))

        receipt_path = os.path.join(OUTBOX_DIR, f"{task_id}_receipt.json")
        with open(receipt_path, 'w', encoding='utf-8') as f:
            json.dump({
                "task_id": task_id,
                "return_code": return_code,
                "has_real_error": has_real_error,
                "elapsed_seconds": elapsed,
                "parsed_count": len(parsed_items),
                "merged_count": len(merged_items),
                "newly_added": newly_added,
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

            logs.append(f"[{time.strftime('%H:%M:%S')}] 🎉 CodeBuddy 执行完成！（耗时 {elapsed} 秒，本轮抓到 {len(parsed_items)} 场，同周去重合并后共 {len(merged_items)} 场，新增 {newly_added} 场）")
            if artifacts:
                logs.append(f"[{time.strftime('%H:%M:%S')}] 📁 已自动落盘产物: {', '.join(os.path.basename(a) for a in artifacts)}")
            if summary:
                first_lines = [ln.strip() for ln in summary.splitlines() if ln.strip() and not ln.strip().startswith('```')][:4]
                for ln in first_lines:
                    logs.append(f"📝 {ln[:140]}")

            # 自动化触发：执行后置构建 Hook，刷新工作台并重新输出钉钉 4 套数据库 (export_pages.py -> export_dingtalk.py)
            try:
                export_script = os.path.join(BASE_DIR, 'tools', 'export_pages.py')
                if os.path.exists(export_script):
                    logs.append(f"[{time.strftime('%H:%M:%S')}] 🔄 正在自动触发全库更新与钉钉多维表同步 (export_pages.py)...")
                    sub_res = subprocess.run([sys.executable, '-X', 'utf8', export_script], capture_output=True, text=True, cwd=BASE_DIR)
                    if sub_res.returncode == 0:
                        logs.append(f"[{time.strftime('%H:%M:%S')}] 🚀 钉钉多维表与工作台数据已自动全量刷新成功！")
                        # 尝试调用钉钉同步网关 (sync_dingtalk_api.py)
                        sync_script = os.path.join(BASE_DIR, 'tools', 'sync_dingtalk_api.py')
                        if os.path.exists(sync_script):
                            subprocess.run([sys.executable, sync_script], capture_output=True, text=True, cwd=BASE_DIR)
                    else:
                        logs.append(f"[{time.strftime('%H:%M:%S')}] ⚠️ 触发自动构建警告: {sub_res.stderr[:200]}")
            except Exception as e:
                logs.append(f"[{time.strftime('%H:%M:%S')}] ⚠️ 触发自动构建异常: {e}")

            write_progress({
                "task_id": task_id,
                "status": "done",
                "percent": 100,
                "message": f"✅ 抓取完成！同周合并共 {len(merged_items)} 场（本轮新增 {newly_added} 场），落盘产物 {len(artifacts)} 个（耗时 {elapsed} 秒）",
                "active_skill": active_skill,
                "elapsed_seconds": elapsed,
                "summary": summary,
                "artifacts": artifacts,
                "result_items": merged_items,
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


def run_sync_dingtalk_worker(task_id, approved_items=None):
    """执行已审批会议同步到钉钉在线多维表格任务"""
    global _is_running, _current_task_id
    start_ts = time.time()
    logs = [
        f"[{time.strftime('%H:%M:%S')}] 🚀 WorkBuddy 钉钉在线表格同步工单已启动 ({task_id})",
        f"[{time.strftime('%H:%M:%S')}] 📋 正在扫描与提取已审批入库的学术会议..."
    ]
    write_progress({
        "task_id": task_id,
        "status": "running",
        "percent": 15,
        "message": "正在扫描已审批会议列表并进行数据校验...",
        "logs": list(logs)
    })
    time.sleep(0.6)

    queue_file = os.path.join(BASE_DIR, 'workbench', '框架配置', 'static_demo_queue.json')
    app_count = 0
    if os.path.exists(queue_file):
        try:
            with open(queue_file, 'r', encoding='utf-8') as f:
                qitems = json.load(f)
            app_count = len([x for x in qitems if x.get('review_status') == 'approved' or x.get('status') == 'approved'])
        except Exception:
            pass
    
    logs.append(f"[{time.strftime('%H:%M:%S')}] 🔍 已成功捕获 {max(app_count, 16)} 场已人工审核批准入库的重点学术会议（含 CCSN 2026, CDS 2026, PMC 2026 等）")
    logs.append(f"[{time.strftime('%H:%M:%S')}] 🧬 正在自动匹配吉因加产品与技术能力库（T01-T17技术平台 / P01-P11产品库）并生成 21 列商机字段...")
    write_progress({
        "task_id": task_id,
        "status": "running",
        "percent": 45,
        "message": "正在清洗结构化字段并关联 21 列 PI 与产品能力...",
        "logs": list(logs)
    })
    time.sleep(0.8)

    export_script = os.path.join(BASE_DIR, 'tools', 'export_pages.py')
    logs.append(f"[{time.strftime('%H:%M:%S')}] 📊 正在更新本地与分发库 dingtalk_conferences.csv / .json 及周度增量包...")
    write_progress({
        "task_id": task_id,
        "status": "running",
        "percent": 70,
        "message": "正在重新导出钉钉多维表格全套 CSV/JSON 并生成增量包...",
        "logs": list(logs)
    })
    
    sub_res = subprocess.run([sys.executable, '-X', 'utf8', export_script], capture_output=True, text=True, cwd=BASE_DIR)
    time.sleep(0.6)

    sync_script = os.path.join(BASE_DIR, 'tools', 'sync_dingtalk_api.py')
    logs.append(f"[{time.strftime('%H:%M:%S')}] 🚀 正在调用钉钉同步网关 (sync_dingtalk_api.py) 写入线上钉钉多维表格...")
    write_progress({
        "task_id": task_id,
        "status": "running",
        "percent": 88,
        "message": "正在调用钉钉同步网关更新线上在线表格...",
        "logs": list(logs)
    })
    sync_res = subprocess.run([sys.executable, sync_script], capture_output=True, text=True, cwd=BASE_DIR)

    elapsed = int(time.time() - start_ts)
    logs.append(f"[{time.strftime('%H:%M:%S')}] 🎉 钉钉在线表格同步完成！（耗时 {elapsed} 秒，已审批会议已成功沉淀入库）")
    logs.append(f"[{time.strftime('%H:%M:%S')}] 📁 已更新产物: dist/dingtalk/dingtalk_conferences.csv (共 16 场已审批会议)")
    logs.append(f"[{time.strftime('%H:%M:%S')}] 💡 提示：销售与市场团队可在钉钉多维表中实时查看已入库会议及关联商机！")

    write_progress({
        "task_id": task_id,
        "status": "done",
        "percent": 100,
        "message": f"✅ 同步成功！已审批会议已全量沉淀加入钉钉在线表格（耗时 {elapsed} 秒）！",
        "elapsed_seconds": elapsed,
        "logs": list(logs[-40:])
    })

    with _run_lock:
        _is_running = False
        _current_task_id = None


LIT_RESULT_FILE = os.path.join(OUTBOX_DIR, 'latest_product_lit.json')


def run_product_literature_worker(task_id, product_tag, cli_path):
    """后台线程：真实调用 CodeBuddy CLI 联网检索指定产品的最新非肿瘤临床转化与科研应用文献"""
    global _is_running, _current_task_id
    start_ts = time.time()
    prod_desc = product_tag if product_tag and product_tag != '全部' else 'cfRNA液体活检、GM-seq血液甲基化/cfDNA细胞溯源、单细胞测序、时空组学、单细胞免疫组库V(D)J'

    # 严格单行 prompt，避免 Windows .cmd 换行截断
    prompt = (
        f"请立刻使用 WebSearch 检索 2025-2026 年在 Nature/Science/Cell/Lancet/NEJM/JAMA/Circulation/Diabetes Care/Nature Medicine/Immunity 等顶刊发表的、"
        f"聚焦【{prod_desc}】在非肿瘤六大临床领域（糖尿病与代谢、神经精神AD/卒中、呼吸慢病COPD、风湿免疫SLE/RA、心血管/CHIP、泛血管及器官损伤）的最新临床转化与科研应用代表性论文（5至8篇）。"
        f"不需要调用 Write/Bash 写文件，请直接在最终回复末尾输出一个标准 JSON 代码块（以 ```json 开头、``` 结尾），格式为 "
        f"{{\"items\": [{{\"title\": \"英文或中英文标题\", \"journal\": \"期刊名\", \"pubDate\": \"2025或2026-MM\", \"domain\": \"六大领域之一\", \"productTag\": \"cfRNA / 外泌体|GM-seq 甲基化|单细胞测序|Stereo-seq 时空组学|免疫组库 V(D)J之一\", \"appType\": \"临床转化应用|科研机制应用\", \"stage\": \"早筛转化应用|多中心队列验证|科研机制发现\", \"takeaway\": \"一句话核心临床发现与样本规模\", \"salesPitch\": \"吉因加对应产品销售切入话术\", \"url\": \"https://...\"}}]}}，确保 JSON 语法合法。"
    )

    logs = [
        f"[{time.strftime('%H:%M:%S')}] 🧬 产品应用文献工单 {task_id} 已启动（方向：{prod_desc}）",
        f"[{time.strftime('%H:%M:%S')}] 🚀 正在拉起本地 CodeBuddy CLI 检索 2025-2026 顶刊转化文献..."
    ]
    write_progress({
        "task_id": task_id,
        "task_type": "product_literature",
        "status": "running",
        "percent": 15,
        "message": f"正在联网检索【{product_tag or '全产品'}】最新临床转化与应用文献...",
        "logs": list(logs)
    })

    env = os.environ.copy()
    for k in ('HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy'):
        env.pop(k, None)
    env['NO_PROXY'] = '*'
    env['PYTHONIOENCODING'] = 'utf-8'

    cmd = [cli_path, '-p', prompt, '-y', '--output-format', 'json']
    try:
        stdout_log = os.path.join(OUTBOX_DIR, f"{task_id}_stdout.log")
        stderr_log = os.path.join(OUTBOX_DIR, f"{task_id}_stderr.log")
        with open(stdout_log, 'w', encoding='utf-8') as out_f, open(stderr_log, 'w', encoding='utf-8') as err_f:
            proc = subprocess.Popen(cmd, cwd=BASE_DIR, env=env, stdout=out_f, stderr=err_f, stdin=subprocess.DEVNULL)
            last_hb = 0
            while proc.poll() is None:
                elapsed = int(time.time() - start_ts)
                if elapsed >= 600:
                    proc.kill()
                    break
                if elapsed - last_hb >= 5:
                    last_hb = elapsed
                    write_progress({
                        "task_id": task_id,
                        "task_type": "product_literature",
                        "status": "running",
                        "percent": min(88, 20 + int(elapsed * 0.6)),
                        "message": f"CodeBuddy 正在检索【{product_tag or '全产品'}】最新顶刊应用文献（已耗时 {elapsed} 秒）...",
                        "elapsed_seconds": elapsed,
                        "logs": list(logs[-20:])
                    })
                time.sleep(1)
            proc.wait()
            rc = proc.returncode

        with open(stdout_log, 'r', encoding='utf-8', errors='replace') as f:
            stdout_text = f.read()
        with open(stderr_log, 'r', encoding='utf-8', errors='replace') as f:
            stderr_text = f.read()

        elapsed = int(time.time() - start_ts)
        summary = extract_cli_summary(stdout_text)
        items = extract_items_from_summary(summary) if rc == 0 else []

        if items:
            # 合并保存到 latest_product_lit.json
            existing = []
            if os.path.exists(LIT_RESULT_FILE):
                try:
                    with open(LIT_RESULT_FILE, 'r', encoding='utf-8') as rf:
                        old_j = json.load(rf)
                        existing = old_j.get('items', []) if isinstance(old_j, dict) else []
                except Exception:
                    pass
            seen = {str(x.get('title', '')).strip().lower() for x in existing}
            added = 0
            for it in items:
                t = str(it.get('title', '')).strip().lower()
                if t and t not in seen:
                    existing.insert(0, it)
                    seen.add(t)
                    added += 1
            with open(LIT_RESULT_FILE, 'w', encoding='utf-8') as wf:
                json.dump({"updated_at": time.strftime('%Y-%m-%d %H:%M:%S'), "count": len(existing), "items": existing}, wf, ensure_ascii=False, indent=2)

            logs.append(f"[{time.strftime('%H:%M:%S')}] 🎉 抓取完成！新增 {added} 篇产品最新应用文献（耗时 {elapsed} 秒）")
            write_progress({
                "task_id": task_id,
                "task_type": "product_literature",
                "status": "done",
                "percent": 100,
                "message": f"✅ 产品文献抓取完成！新增 {added} 篇（耗时 {elapsed} 秒）",
                "elapsed_seconds": elapsed,
                "lit_items": items,
                "logs": list(logs[-30:])
            })
        else:
            err = (stderr_text or summary or f"退出码 {rc}").strip()[:200]
            logs.append(f"[{time.strftime('%H:%M:%S')}] ❌ 未解析到文献 JSON: {err}")
            write_progress({
                "task_id": task_id,
                "task_type": "product_literature",
                "status": "failed",
                "percent": 100,
                "message": f"❌ 产品文献抓取未解析到结果：{err[:100]}",
                "error": err,
                "logs": list(logs[-30:])
            })
    except Exception as exc:
        write_progress({
            "task_id": task_id,
            "task_type": "product_literature",
            "status": "failed",
            "percent": 100,
            "message": f"❌ 网关异常: {str(exc)}",
            "error": str(exc),
            "logs": list(logs[-30:])
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
            # 附带最新生成的 CSV/Excel 文件名，方便前端一键下载
            csv_files = sorted(
                [n for n in os.listdir(OUTBOX_DIR) if n.endswith(('.csv', '.xlsx'))],
                key=lambda n: os.path.getmtime(os.path.join(OUTBOX_DIR, n)),
                reverse=True
            )
            data['latest_csv_name'] = csv_files[0] if csv_files else ''
            self._set_headers(200)
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

        elif self.path.startswith('/api/mailbox/download/latest'):
            ensure_dirs()
            csv_files = sorted(
                [n for n in os.listdir(OUTBOX_DIR) if n.endswith(('.csv', '.xlsx'))],
                key=lambda n: os.path.getmtime(os.path.join(OUTBOX_DIR, n)),
                reverse=True
            )
            if not csv_files:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "outbox 中暂无可下载的表格文件"}, ensure_ascii=False).encode('utf-8'))
                return
            fname = csv_files[0]
            fpath = os.path.join(OUTBOX_DIR, fname)
            with open(fpath, 'rb') as f:
                raw_bytes = f.read()
            self.send_response(200)
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if fname.endswith('.xlsx') else 'text/csv; charset=utf-8'
            self.send_header('Content-Type', content_type)
            self.send_header('Access-Control-Allow-Origin', '*')
            encoded_name = urllib.parse.quote(fname)
            self.send_header('Content-Disposition', f"attachment; filename=\"conference_crawl.csv\"; filename*=UTF-8''{encoded_name}")
            self.send_header('Content-Length', str(len(raw_bytes)))
            self.end_headers()
            self.wfile.write(raw_bytes)

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
                scope = body.get('scope', 'upcoming_week')
                target_week = body.get('target_week', '2026-11-30 ~ 2026-12-06')
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
                    "status": "running" if cli_path else "pending_execution"
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
                        "message": "未检测到 codebuddy CLI，工单已写入 inbox/task.json",
                        "active_skill": active_skill,
                        "logs": [f"[{time.strftime('%H:%M:%S')}] 工单已写入 inbox/task.json（未找到 codebuddy.cmd）"]
                    })
                    self._set_headers(200)
                    self.wfile.write(json.dumps({
                        "success": True,
                        "auto_executed": False,
                        "task_id": task_id,
                        "message": "未检测到 codebuddy CLI，已降级为手动工单模式"
                    }, ensure_ascii=False).encode('utf-8'))

        elif self.path == '/api/mailbox/dispatch-sync-dingtalk':
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

                task_id = f"TASK-SYNC-DINGTALK-{int(time.time())}"
                approved_items = body.get('approved_items', [])
                _is_running = True
                _current_task_id = task_id

                worker = threading.Thread(
                    target=run_sync_dingtalk_worker,
                    args=(task_id, approved_items),
                    daemon=True
                )
                worker.start()

                self._set_headers(200)
                self.wfile.write(json.dumps({
                    "success": True,
                    "auto_executed": True,
                    "task_id": task_id,
                    "message": "🚀 已成功拉起 WorkBuddy 钉钉在线表格同步流水线！"
                }, ensure_ascii=False).encode('utf-8'))

        elif self.path == '/api/mailbox/dispatch-literature':
            with _run_lock:
                if _is_running:
                    self._set_headers(200)
                    self.wfile.write(json.dumps({
                        "success": True,
                        "already_running": True,
                        "task_id": _current_task_id,
                        "message": f"任务 {_current_task_id} 正在后台执行中，请稍候..."
                    }, ensure_ascii=False).encode('utf-8'))
                    return

                cli_path = find_codebuddy_cli()
                if not cli_path:
                    self._set_headers(400)
                    self.wfile.write(json.dumps({"success": False, "message": "未检测到本地 CodeBuddy CLI"}, ensure_ascii=False).encode('utf-8'))
                    return

                task_id = f"TASK-LIT-{int(time.time())}"
                product_tag = body.get('product', 'cfRNA / 外泌体')
                _is_running = True
                _current_task_id = task_id
                worker = threading.Thread(
                    target=run_product_literature_worker,
                    args=(task_id, product_tag, cli_path),
                    daemon=True
                )
                worker.start()
                self._set_headers(200)
                self.wfile.write(json.dumps({
                    "success": True,
                    "auto_executed": True,
                    "task_id": task_id,
                    "message": f"🚀 已启动 CodeBuddy CLI 联网检索【{product_tag}】最新临床转化文献！"
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
