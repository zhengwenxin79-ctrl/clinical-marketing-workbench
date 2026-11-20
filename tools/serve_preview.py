"""Optional loopback-only static preview; no writes, collectors or maintenance APIs."""
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from functools import partial
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=8767);a=ap.parse_args();root=Path(__file__).resolve().parents[1]
print(f'http://127.0.0.1:{a.port}/打开工作台.html',flush=True)
with ThreadingHTTPServer(('127.0.0.1',a.port),partial(SimpleHTTPRequestHandler,directory=str(root))) as s:
 try:s.serve_forever()
 except KeyboardInterrupt:pass
