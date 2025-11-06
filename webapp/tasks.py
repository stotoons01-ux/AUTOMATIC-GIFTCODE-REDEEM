import threading
import time
import json
import os
from pathlib import Path
from webapp.models import update_job_status
import automation

try:
    import redis
except Exception:
    redis = None

JOB_QUEUE_ENABLED = True
REDIS_URL = os.environ.get('REDIS_URL')

WORKER_THREAD = None

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / 'jobs_data'
OUT_DIR.mkdir(exist_ok=True)


def get_redis_client():
    if not REDIS_URL:
        return None
    if redis is None:
        raise RuntimeError('redis package not installed')
    return redis.from_url(REDIS_URL)


def enqueue_job(job_id, player_list):
    """Enqueue a job. If REDIS_URL is set, push to Redis list; otherwise the in-process queue is used."""
    client = get_redis_client()
    payload = {'job_id': job_id, 'player_list': list(player_list)}
    if client:
        # push to Redis list 'wos_jobs'
        client.lpush('wos_jobs', json.dumps(payload))
    else:
        # fallback: write a file flag (simple local queue) — put into OUT_DIR/incoming
        qdir = OUT_DIR / 'incoming'
        qdir.mkdir(exist_ok=True)
        path = qdir / f'job_{job_id}.json'
        path.write_text(json.dumps(payload))


def _pop_redis_job(block=True, timeout=0):
    client = get_redis_client()
    if not client:
        return None
    # BRPOP blocks and returns (list_name, data)
    item = client.brpop('wos_jobs', timeout=timeout)
    if not item:
        return None
    _, data = item
    return json.loads(data)


def _pop_file_job():
    qdir = OUT_DIR / 'incoming'
    qdir.mkdir(exist_ok=True)
    files = sorted(qdir.glob('job_*.json'))
    if not files:
        return None
    p = files[0]
    payload = json.loads(p.read_text())
    try:
        p.unlink()
    except Exception:
        pass
    return payload


def worker_loop():
    client = get_redis_client()
    print('Worker loop started; REDIS_URL=' + str(REDIS_URL))
    while True:
        try:
            payload = None
            if client:
                payload = _pop_redis_job(block=True, timeout=5)
            else:
                payload = _pop_file_job()

            if not payload:
                time.sleep(0.5)
                continue

            job_id = payload.get('job_id')
            player_list = payload.get('player_list', [])
            print(f"Worker picked job {job_id} for players: {player_list}")
            update_job_status(job_id, 'running')
            job_dir = OUT_DIR / f'job_{job_id}'
            job_dir.mkdir(exist_ok=True)

            # run apply automation
            try:
                # run headless by default on remote worker
                res = automation.apply_player_ids(player_list, out_dir=str(job_dir), headless=True)
                # if automation detected a captcha/overlay, mark job as blocked and save screenshot path
                if res and res.get('captcha'):
                    msg = res.get('message')
                    ss = res.get('apply_screenshot')
                    # store a path relative to OUT_DIR when possible so the web route can serve it
                    rel = None
                    try:
                        if ss:
                            rel = str(Path(ss).relative_to(OUT_DIR))
                    except Exception:
                        rel = None
                    update_job_status(job_id, 'blocked', finished_at=time.strftime('%Y-%m-%dT%H:%M:%SZ'), result_csv=rel or msg)
                else:
                    result_csv = None
                    if res:
                        result_csv = res.get('status_csv')
                    # convert to relative path if the CSV lives under OUT_DIR
                    rel = None
                    try:
                        if result_csv:
                            rel = str(Path(result_csv).relative_to(OUT_DIR))
                    except Exception:
                        rel = None
                    update_job_status(job_id, 'done', finished_at=time.strftime('%Y-%m-%dT%H:%M:%SZ'), result_csv=rel or result_csv)
            except Exception as e:
                update_job_status(job_id, 'error', finished_at=time.strftime('%Y-%m-%dT%H:%M:%SZ'), result_csv=str(e))

        except Exception as e:
            print('Worker loop error:', e)
            time.sleep(1.0)


def start_worker():
    global WORKER_THREAD
    if WORKER_THREAD and WORKER_THREAD.is_alive():
        return
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()
    WORKER_THREAD = t
    return t
