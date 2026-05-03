from celery import Celery
import os

celery_app = Celery(
    "tasks",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/1"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/1"),
    include=["app.tasks.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,

    task_queues={
        'indexing': {'exchange': 'indexing', 'routing_key': 'indexing.#'},
        'upload': {'exchange': 'upload', 'routing_key': 'upload.#'},
        'generation': {'exchange': 'generation', 'routing_key': 'generation.#'},
    },

    task_routes={
        'app.tasks.tasks.index_documents_task': {'queue': 'indexing'},
        'app.tasks.tasks.upload_pickle_task': {'queue': 'upload'},
        'app.tasks.tasks.generate_answer_task': {'queue': 'generation'},
    }
)