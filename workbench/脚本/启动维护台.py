"""仅在127.0.0.1开放的数据库维护台；Ctrl+C结束，不安装自启。"""
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit, unquote, quote
import argparse
import base64
import html
import json
import mimetypes
import secrets
import sys

from 维护数据库 import (ROOT, MAX_UPLOAD, SOURCE_PATH, MaintenanceError, overview,
                     get_run, import_source, confirm, verify_export)


def serve(root, port):
    root = Path(root).resolve()
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        server_version = 'CDSMaintenance/1'

        def send(self, data, mime='application/json; charset=utf-8', status=200, attachment=None):
            if not isinstance(data, bytes):
                data = data.encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Referrer-Policy', 'no-referrer')
            if attachment:
                self.send_header('Content-Disposition', "attachment; filename*=UTF-8''" + quote(attachment))
                self.send_header('Content-Security-Policy', "sandbox; default-src 'none'")
            else:
                self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def json(self, value, status=200):
            self.send(json.dumps(value, ensure_ascii=False), status=status)

        def valid_host(self):
            return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}

        def file(self, path, attachment=False):
            if not path.is_file():
                return self.json({'error': '文件不存在。'}, 404)
            self.send(path.read_bytes(), mimetypes.guess_type(str(path))[0] or 'application/octet-stream', attachment=path.name if attachment else None)

        def do_GET(self):
            if not self.valid_host():
                return self.json({'error': '只接受本机访问。'}, 403)
            try:
                route = unquote(urlsplit(self.path).path)
                if route == '/api/status':
                    return self.json(dict(overview(root), token=token))
                if route.startswith('/api/run/'):
                    return self.json(get_run(root, route.rsplit('/', 1)[-1]))
                if route == '/api/sample':
                    return self.file(root / SOURCE_PATH, attachment=True)
                if route in ('/', '/index.html'):
                    return self.file(root / '维护台/index.html')
                if route in ('/app.js', '/style.css'):
                    return self.file(root / '维护台' / route[1:])
                if route in ('/meeting', '/meeting/'):
                    return self.file(root / '会议视图/index.html')
                # 原始资料只允许下载，防止归档HTML脚本与本机写入API处于同源。
                if route.startswith('/原始资料/') or route.startswith('/维护记录/'):
                    p = (root / route[1:]).resolve()
                    if p.is_relative_to(root / '原始资料') or p.is_relative_to(root / '维护记录/批次'):
                        return self.file(p, attachment=True)
                if route.startswith('/backup/'):
                    p = (root / '备份/维护台' / route[len('/backup/'):]).resolve()
                    if p.is_relative_to(root / '备份/维护台'):
                        return self.file(p, attachment=True)
                if route.startswith('/records/'):
                    parts = route[len('/records/'):].split('/', 1)
                    run = get_run(root, parts[0])
                    folder = root / '维护记录/批次' / parts[0]
                    if len(parts) > 1 and parts[1]:
                        p = (folder / parts[1]).resolve()
                        if p.is_relative_to(folder):
                            return self.file(p, attachment=True)
                    links = ''.join('<li><a href="' + quote(str(p.relative_to(folder)), safe='/') + '">' + html.escape(str(p.relative_to(folder))) + '</a></li>' for p in sorted(folder.rglob('*')) if p.is_file())
                    body = '<!doctype html><meta charset="utf-8"><title>本批维护记录</title><style>body{font:16px/1.9 system-ui;max-width:900px;margin:40px auto;padding:0 20px;color:#213650}a{color:#286bc1}</style><a href="/">返回维护台</a><h1>' + html.escape(parts[0]) + '</h1><p>原始资料、变化清单与每次操作记录。点击文件下载查看。</p><ul>' + links + '</ul>'
                    return self.send(body, 'text/html; charset=utf-8')
                return self.json({'error': '页面不存在。'}, 404)
            except (MaintenanceError, OSError, ValueError) as e:
                return self.json({'error': str(e)}, 400)

        def do_POST(self):
            origin = self.headers.get('Origin')
            if not self.valid_host() or self.headers.get('X-Maintenance-Token') != token or (origin and origin not in {f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'}):
                return self.json({'error': '请求未通过本地维护校验，请从维护台操作。'}, 403)
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= MAX_UPLOAD * 4 // 3 + 10000:
                    return self.json({'error': '请求为空或超过12MB文件上限。'}, 413)
                if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    return self.json({'error': '只接受JSON请求。'}, 415)
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise MaintenanceError('请求格式不正确。')
                route = urlsplit(self.path).path
                if route == '/api/import-sample':
                    result = import_source(root, (root / SOURCE_PATH).read_bytes(), Path(SOURCE_PATH).name, '用已有CDS资料试跑；未重新联网采集。')
                elif route == '/api/import':
                    if not all(isinstance(data.get(k, ''), str) for k in ('content_base64', 'filename', 'note')):
                        raise MaintenanceError('上传字段格式不正确。')
                    try:
                        content = base64.b64decode(data.get('content_base64', ''), validate=True)
                    except ValueError as e:
                        raise MaintenanceError('上传文件编码无效。') from e
                    result = import_source(root, content, data.get('filename', 'CDS日程.json'), data.get('note', ''))
                elif route == '/api/confirm':
                    result = confirm(root, data.get('run_id', ''), '维护台人工确认')
                elif route == '/api/verify-export':
                    result = verify_export(root, data.get('run_id', ''))
                else:
                    return self.json({'error': '操作不存在。'}, 404)
                return self.json(result)
            except (MaintenanceError, OSError, ValueError, TypeError) as e:
                return self.json({'error': str(e)}, 400)
            except Exception as e:
                print('维护操作失败：' + repr(e), file=sys.stderr)
                return self.json({'error': '操作未完成，请查看终端和本批维护记录。'}, 500)

        def log_message(self, format, *args):
            # 不输出上传内容或维护令牌。
            print(self.log_date_time_string() + ' ' + (format % args), file=sys.stderr)

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print(f'数据库维护台：http://127.0.0.1:{server.server_port}/', flush=True)
    print('仅在本机运行。关闭本终端或按Ctrl+C停止；没有定时任务和自启。', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--port', type=int, default=8789)
    args = ap.parse_args()
    try:
        serve(args.root, args.port)
    except OSError as e:
        print('无法启动维护台：' + str(e) + '。如端口被占用，请加 --port 8790 重试。', file=sys.stderr)
        raise SystemExit(1)
