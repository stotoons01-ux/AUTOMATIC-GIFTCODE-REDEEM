from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
import os
from pathlib import Path
import sys
# Ensure project root is on sys.path so `import webapp.*` works when running this file directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from webapp.models import init_db, get_conn, add_player, list_players, create_job, list_jobs, get_job, update_job_status
from webapp.tasks import start_worker, enqueue_job

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'jobs_data'
DATA_DIR.mkdir(exist_ok=True)

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret')

    # init DB
    init_db(str(BASE_DIR / 'app.db'))

    # start background worker
    start_worker()

    @app.route('/')
    def index():
        players = list_players()
        return render_template('index.html', players=players)

    @app.route('/add_player', methods=['POST'])
    def add_player_route():
        pid = request.form.get('player_id', '').strip()
        if pid:
            add_player(pid)
            flash(f'Added player {pid}')
        return redirect(url_for('index'))

    @app.route('/apply', methods=['POST'])
    def apply():
        # selected player ids from form
        selected = request.form.getlist('player')
        if not selected:
            flash('No players selected')
            return redirect(url_for('index'))
        job_id = create_job(','.join(selected))
        enqueue_job(job_id, selected)
        flash(f'Job {job_id} created')
        return redirect(url_for('jobs'))

    @app.route('/jobs')
    def jobs():
        jobs = list_jobs()
        return render_template('jobs.html', jobs=jobs)

    @app.route('/job/<int:job_id>')
    def job_detail(job_id):
        job = get_job(job_id)
        if not job:
            flash('Job not found')
            return redirect(url_for('jobs'))
        return render_template('job_detail.html', job=job)

    @app.route('/jobs_data/<path:filename>')
    def jobs_data(filename):
        return send_from_directory(str(DATA_DIR), filename)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
