from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
import json
from datetime import datetime
import os
import uuid

from app.tasks.tasks import index_documents_task
from app.tasks.redis_client import redis_client
from app.api.schemas.task import TaskResponse
from app.core.search_config import search_config
from app.tasks.tasks import upload_pickle_task


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


@router.post("/upload")
async def upload_simple(
        collection: str = Form(...),
        vector_size: int = Form(384),
        distance: str = Form("Cosine"),
        pickle_file: UploadFile = File(...),
        batch_size: int = Form(100),
        force_recreate: bool = Form(False)
):
    """
    Загрузка данных из pickle файла в Qdrant коллекцию
    """
    temp_path = None
    file_size = 0
    try:
        if not pickle_file.filename.endswith('.pkl'):
            raise HTTPException(
                status_code=400,
                detail="Файл должен иметь расширение .pkl"
            )

        temp_dir = "/tmp/celery_uploads"
        os.makedirs(temp_dir, exist_ok=True)

        unique_name = f"{uuid.uuid4()}_{pickle_file.filename}"
        temp_path = os.path.join(temp_dir, unique_name)

        with open(temp_path, "wb") as tmp:
            while chunk := await pickle_file.read(8192):
                tmp.write(chunk)
                file_size += len(chunk)

        task = upload_pickle_task.delay(
            pickle_file_path=temp_path,
            collection_name=collection,
            vector_size=vector_size,
            distance=distance,
            batch_size=batch_size,
            force_recreate=force_recreate
        )

        redis_client.set_task_status(
            task_id=task.id,
            status="pending",
            task_type="upload",
            collection_name=collection,
            filename=pickle_file.filename,
            file_size=file_size,
            vector_size=vector_size,
            distance=distance,
            batch_size=batch_size,
            created_at=datetime.now().isoformat()
        )

        return {
            "status": "accepted",
            "mode": "async",
            "task_id": task.id,
            "collection": collection,
            "filename": pickle_file.filename,
            "message": "Загрузка запущена асинхронно",
            "check_status_url": f"/api/v1/task/{task.id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки: {str(e)}")