"""Hooks for the Builder container's Gunicorn workers."""

from threading import Thread


def post_worker_init(worker):
    from nofos.readability_scratch import run_sweeper

    Thread(target=run_sweeper, name="readability-scratch-cleanup", daemon=True).start()
