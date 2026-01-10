"""Celery worker entrypoint."""

from app.celery_app import celery_app

if __name__ == "__main__":
    celery_app.worker_main([
        "worker",
        "--loglevel=info",
        "--concurrency=1",  # One task per worker
        "--pool=solo",  # Use solo pool for simplicity
    ])
