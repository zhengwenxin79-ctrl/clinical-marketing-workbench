"""Portable directory mutex and executable lookup. No scheduler or external packages."""
import json
import os
import shutil
import socket
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

def curl_executable():
    return shutil.which('curl.exe' if os.name=='nt' else 'curl')

@contextmanager
def project_lock(root):
    directory=Path(root)/'monitoring/.collector.lock.d'
    try:directory.mkdir()
    except FileExistsError:
        raise BlockingIOError('Another collection may be running. Inspect monitoring/.collector.lock.d; remove a stale lock only after confirming all collectors have stopped.')
    token=uuid.uuid4().hex
    owner=directory/'owner.json'
    try:
        owner.write_text(json.dumps({'token':token,'pid':os.getpid(),'computer':socket.gethostname(),'started_at_utc':datetime.now(timezone.utc).isoformat()},ensure_ascii=False),encoding='utf-8')
        yield
    finally:
        if owner.exists() and json.loads(owner.read_text(encoding='utf-8')).get('token')==token:
            owner.unlink();directory.rmdir()
        elif directory.exists() and not any(directory.iterdir()):directory.rmdir()
