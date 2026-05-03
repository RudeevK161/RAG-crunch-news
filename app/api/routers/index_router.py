from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
import json
from datetime import datetime

from app.tasks.tasks import index_documents_task
from app.tasks.redis_client import redis_client
from app.api.schemas.task import TaskResponse
from app.core.search_config import search_config


router = APIRouter()


@router.post("/index", response_model=TaskResponse)
async def index_documents(
        file: UploadFile = File(..., description="JSON файл с документами"),
        collection_name: str = Form(search_config.QDRANT_COLLECTION),
        max_docs: Optional[int] = Form(None),
        force_recreate: bool = Form(True)
):
    """
    Индексация документов в Qdrant (асинхронно через Celery)
    """
    try:
        content = await file.read()
        data = json.loads(content)

        task = index_documents_task.delay(
            data=data,
            collection_name=collection_name,
            max_docs=max_docs,
            force_recreate=force_recreate
        )

        redis_client.set_task_status(
            task_id=task.id,
            status="pending",
            task_type="index",
            collection_name=collection_name,
            created_at=datetime.now().isoformat(),
            filename=file.filename,
            total_docs=len(data) if isinstance(data, list) else 1
        )

        return TaskResponse(
            task_id=task.id,
            status="pending",
            message=f"Задача индексации поставлена в очередь. Документов: {len(data) if isinstance(data, list) else 1}"
        )

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Неверный JSON формат")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")