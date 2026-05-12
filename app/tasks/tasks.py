import os
from datetime import datetime
import logging

from app.core.search_config import search_config
from app.tasks.celery_app import celery_app
from app.tasks.redis_client import redis_client
from app.services.generator.generation import rag_generator
from src.dense.dense_model import index_documents_to_qdrant_dense
from src.setup_qdrant import upload_pickle_to_qdrant

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.tasks.index_documents_task")
def index_documents_task(self, data, collection_name, max_docs, force_recreate):
    """
    Задача индексации документов
    """
    task_id = self.request.id

    try:
        redis_client.update_task_progress(
            task_id=task_id,
            progress=0,
            message="Начало индексации"
        )

        result = index_documents_to_qdrant_dense(
            data=data,
            collection_name=collection_name,
            max_docs=max_docs,
            force_recreate=force_recreate
        )

        redis_client.set_task_status(
            task_id=task_id,
            status="completed",
            completed_at=datetime.now().isoformat(),
            result=result
        )

        return result

    except Exception as e:
        logger.error(f"Indexing task {task_id} failed: {e}")

        redis_client.set_task_status(
            task_id=task_id,
            status="failed",
            error=str(e),
            failed_at=datetime.now().isoformat()
        )
        raise


@celery_app.task(bind=True, name="app.tasks.tasks.upload_pickle_task")
def upload_pickle_task(self, pickle_file_path: str, collection_name: str,
                       vector_size: int, distance: str, batch_size: int,
                       force_recreate: bool):
    """
    Асинхронная загрузка pickle файла в Qdrant
    Принимает ПУТЬ к файлу вместо содержимого
    """
    task_id = self.request.id
    logger.info(f"Starting upload task {task_id} for collection {collection_name}")
    logger.info(f"File path: {pickle_file_path}")

    try:
        if not os.path.exists(pickle_file_path):
            raise FileNotFoundError(f"Pickle file not found: {pickle_file_path}")

        file_size_mb = os.path.getsize(pickle_file_path) / (1024 * 1024)
        logger.info(f"Task {task_id}: processing {file_size_mb:.2f}MB file")

        redis_client.set_task_status(
            task_id,
            "processing",
            started_at=datetime.now().isoformat(),
            progress=0,
            message=f"Обработка файла {file_size_mb:.1f}MB"
        )

        redis_client.update_task_progress(task_id, 10, "Начало загрузки в Qdrant")

        result = upload_pickle_to_qdrant(
            pickle_path=pickle_file_path,
            collection=collection_name,
            vector_size=vector_size,
            distance=distance,
            batch_size=batch_size,
            qdrant_host=search_config.QDRANT_HOST,
            qdrant_port=search_config.QDRANT_PORT,
            force_recreate=force_recreate
        )

        redis_client.update_task_progress(task_id, 90, "Данные загружены")

        redis_client.set_task_status(
            task_id,
            "completed",
            completed_at=datetime.now().isoformat(),
            progress=100,
            result=result
        )

        logger.info(f"Upload task {task_id} completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Upload task {task_id} failed: {str(e)}", exc_info=True)
        redis_client.set_task_status(
            task_id,
            "failed",
            completed_at=datetime.now().isoformat(),
            error=str(e)
        )
        raise

    finally:
        if pickle_file_path and os.path.exists(pickle_file_path):
            try:
                os.unlink(pickle_file_path)
                logger.info(f"Task {task_id}: удален временный файл {pickle_file_path}")
            except Exception as e:
                logger.warning(f"Task {task_id}: не удалось удалить {pickle_file_path}: {e}")


@celery_app.task(bind=True, name="app.tasks.tasks.generate_answer_task")
def generate_answer_task(self, question: str, style: str = "detailed"):
    """
    Задача генерации ответа с автоматическим ретривалом
    """
    task_id = self.request.id

    try:
        redis_client.update_task_progress(
            task_id=task_id,
            progress=0,
            message="Начало генерации"
        )

        result = rag_generator.generate_with_retrieval(
            question=question,
            style=style
        )

        try:
            redis_client.client.hincrby("rag_metrics", "total_requests", 1)
            redis_client.client.hincrbyfloat("rag_metrics", "total_latency", result.get("latency_sec", 0))

            if result.get("cached"):
                redis_client.client.hincrby("rag_metrics", "cache_hits", 1)
            else:
                redis_client.client.hincrby("rag_metrics", "cache_misses", 1)

            redis_client.client.hset("rag_last_request", mapping={
                "timestamp": datetime.now().isoformat(),
                "question": question[:100],
                "style": style,
                "latency": result.get("latency_sec", 0),
                "cached": result.get("cached", False)
            })
        except Exception as e:
            logger.warning(f"Failed to save metrics: {e}")

        redis_client.set_task_status(
            task_id=task_id,
            status="completed",
            completed_at=datetime.now().isoformat(),
            result=result
        )

        return result

    except Exception as e:
        logger.error(f"Generation task {task_id} failed: {e}")

        redis_client.set_task_status(
            task_id=task_id,
            status="failed",
            error=str(e),
            failed_at=datetime.now().isoformat()
        )
        raise