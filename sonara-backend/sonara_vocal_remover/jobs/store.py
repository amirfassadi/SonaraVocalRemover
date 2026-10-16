import json
import sqlite3
import time
from contextlib import contextmanager

TERMINAL = {'succeeded', 'failed', 'cancelled', 'expired', 'deleted'}

class Store:
    def __init__(self, root):
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / 'jobs.sqlite'
        with self.db() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, filename TEXT NOT NULL,
                state TEXT NOT NULL, created REAL NOT NULL, started REAL, finished REAL,
                model TEXT NOT NULL, device TEXT NOT NULL, error TEXT,
                cancel INTEGER NOT NULL DEFAULT 0, remove INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS heartbeat (id INTEGER PRIMARY KEY, ts REAL);
            ''')

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self, job_id, owner, filename, model, device, limit):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            count = db.execute("SELECT count(*) FROM jobs WHERE state IN ('uploading','queued')").fetchone()[0]
            if count >= limit:
                raise ValueError('queue_full')
            db.execute('INSERT INTO jobs(id,owner,filename,state,created,model,device) VALUES(?,?,?,?,?,?,?)',
                       (job_id, owner, filename, 'uploading', time.time(), json.dumps(model), device))

    def get(self, job_id, owner=None):
        with self.db() as db:
            row = db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
        if row is None or (owner is not None and row['owner'] != owner):
            return None
        result = dict(row)
        result['model'] = json.loads(result['model'])
        return result

    def enqueue(self, job_id):
        with self.db() as db:
            db.execute("UPDATE jobs SET state='queued' WHERE id=? AND state='uploading'", (job_id,))

    def claim(self):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT id FROM jobs WHERE state='queued' ORDER BY created LIMIT 1").fetchone()
            if row is None:
                return None
            db.execute("UPDATE jobs SET state='running',started=? WHERE id=?", (time.time(), row['id']))
        return self.get(row['id'])

    def finish(self, job_id, state, error=None):
        with self.db() as db:
            db.execute('UPDATE jobs SET state=?,finished=?,error=? WHERE id=?', (state, time.time(), error, job_id))

    def request_cancel(self, job_id, remove=False):
        with self.db() as db:
            db.execute('UPDATE jobs SET cancel=1,remove=max(remove,?) WHERE id=?', (int(remove), job_id))

    def tick(self):
        with self.db() as db:
            db.execute('INSERT OR REPLACE INTO heartbeat VALUES(1,?)', (time.time(),))

    def alive(self):
        with self.db() as db:
            row = db.execute('SELECT ts FROM heartbeat WHERE id=1').fetchone()
        return bool(row and time.time() - row['ts'] < 15)

    def rows(self):
        with self.db() as db:
            return [dict(row) for row in db.execute('SELECT id,state,created,finished,cancel,remove FROM jobs')]
