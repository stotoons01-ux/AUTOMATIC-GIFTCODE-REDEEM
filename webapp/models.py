import sqlite3
from datetime import datetime
from typing import List, Optional

DB_PATH = None

def init_db(db_path: str):
    global DB_PATH
    DB_PATH = db_path
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id TEXT UNIQUE
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_ids TEXT,
        status TEXT,
        created_at TEXT,
        finished_at TEXT,
        result_csv TEXT
    )
    ''')
    conn.commit()
    conn.close()

def get_conn():
    if not DB_PATH:
        raise RuntimeError('DB not initialized')
    return sqlite3.connect(DB_PATH)

def add_player(player_id: str):
    conn = get_conn()
    try:
        conn.execute('INSERT OR IGNORE INTO players(player_id) VALUES (?)', (player_id,))
        conn.commit()
    finally:
        conn.close()

def list_players() -> List[str]:
    conn = get_conn()
    try:
        cur = conn.execute('SELECT player_id FROM players ORDER BY id')
        return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()

def create_job(player_ids: str) -> int:
    conn = get_conn()
    try:
        now = datetime.utcnow().isoformat()
        cur = conn.execute('INSERT INTO jobs(player_ids, status, created_at) VALUES (?, ?, ?)', (player_ids, 'queued', now))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def list_jobs():
    conn = get_conn()
    try:
        cur = conn.execute('SELECT id, player_ids, status, created_at, finished_at, result_csv FROM jobs ORDER BY id DESC')
        rows = cur.fetchall()
        jobs = []
        for r in rows:
            jobs.append({
                'id': r[0], 'player_ids': r[1], 'status': r[2], 'created_at': r[3], 'finished_at': r[4], 'result_csv': r[5]
            })
        return jobs
    finally:
        conn.close()

def get_job(job_id: int) -> Optional[dict]:
    conn = get_conn()
    try:
        cur = conn.execute('SELECT id, player_ids, status, created_at, finished_at, result_csv FROM jobs WHERE id=?', (job_id,))
        r = cur.fetchone()
        if not r:
            return None
        return {'id': r[0], 'player_ids': r[1], 'status': r[2], 'created_at': r[3], 'finished_at': r[4], 'result_csv': r[5]}
    finally:
        conn.close()

def update_job_status(job_id: int, status: str, finished_at: str = None, result_csv: str = None):
    conn = get_conn()
    try:
        if finished_at and result_csv:
            conn.execute('UPDATE jobs SET status=?, finished_at=?, result_csv=? WHERE id=?', (status, finished_at, result_csv, job_id))
        elif finished_at:
            conn.execute('UPDATE jobs SET status=?, finished_at=? WHERE id=?', (status, finished_at, job_id))
        else:
            conn.execute('UPDATE jobs SET status=? WHERE id=?', (status, job_id))
        conn.commit()
    finally:
        conn.close()
