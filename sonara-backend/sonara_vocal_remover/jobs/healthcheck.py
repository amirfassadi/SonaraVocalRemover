"""Read-only container checks; no downloads or inference."""
import argparse
import json
import os
import sqlite3
import time
import urllib.request
from .settings import Settings


def worker_ready(root, now=None):
    try:
        with sqlite3.connect((root / 'jobs.sqlite').as_uri() + '?mode=ro', uri=True, timeout=2) as db:
            row = db.execute('SELECT ts FROM heartbeat WHERE id=1').fetchone()
        return bool(row and 0 <= (time.time() if now is None else now) - row[0] < 15)
    except sqlite3.Error:
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('service', choices=('api', 'worker'))
    args = parser.parse_args()
    if args.service == 'worker':
        raise SystemExit(0 if worker_ready(Settings().root) else 1)
    request = urllib.request.Request('http://127.0.0.1:8000/api/health/ready', headers={
        'x-sonara-token': os.environ.get('SONARA_API_TOKEN', ''), 'x-sonara-owner': '0' * 32})
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            ok = response.status == 200 and json.load(response).get('ready') is True
    except (OSError, ValueError):
        ok = False
    raise SystemExit(0 if ok else 1)

if __name__ == '__main__':
    main()
