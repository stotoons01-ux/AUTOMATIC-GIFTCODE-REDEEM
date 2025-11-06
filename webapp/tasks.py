import threading
import queue
import time
from pathlib import Path
from webapp.models import update_job_status
import automation
import os

JOB_QUEUE = queue.Queue()
WORKER_THREAD = None

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / 'jobs_data'
OUT_DIR.mkdir(exist_ok=True)

def enqueue_job(job_id, player_list):
    JOB_QUEUE.put((job_id, player_list))

def worker_loop():
    while True:
        try:
            job_id, player_list = JOB_QUEUE.get()
            print(f"Worker picked job {job_id} for players: {player_list}")
            update_job_status(job_id, 'running')
            job_dir = OUT_DIR / f'job_{job_id}'
            job_dir.mkdir(exist_ok=True)

            # run apply automation
            try:
                res = automation.apply_player_ids(player_list, out_dir=str(job_dir))
                result_csv = res.get('status_csv')
                update_job_status(job_id, 'done', finished_at=time.strftime('%Y-%m-%dT%H:%M:%SZ'), result_csv=result_csv)
            except Exception as e:
                update_job_status(job_id, 'error', finished_at=time.strftime('%Y-%m-%dT%H:%M:%SZ'), result_csv=str(e))

        except Exception as e:
            print('Worker loop error:', e)
        finally:
            time.sleep(0.5)

def start_worker():
    global WORKER_THREAD
    if WORKER_THREAD and WORKER_THREAD.is_alive():
        return
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()
    WORKER_THREAD = t
    return t
