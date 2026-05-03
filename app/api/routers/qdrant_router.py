from qdrant_client import models
import sys
import os
import uuid
from fastapi import APIRouter, Form, UploadFile, File, HTTPException
import logging
from datetime import datetime

from src.setup_qdrant import *
from app.tasks.tasks import upload_pickle_task
from app.tasks.redis_client import redis_client
from src.bm25.bm25_utils import get_qdrant_client

logger = logging.getLogger(__name__)
sys.path.append(os.path.join(os.path.dirname(__file__), '../..', '..'))

router = APIRouter()


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


@router.get("/collections")
async def list_collections():
    """Получить список всех коллекций"""
    try:
        qdrant = get_qdrant_client()
        collections = qdrant.get_collections()

        result = []
        for coll in collections.collections:
            try:
                info = qdrant.get_collection(coll.name)
                result.append({
                    "name": coll.name,
                    "points": info.points_count,
                    "vector_size": info.config.params.vectors.size if info.config.params.vectors else 0
                })
            except Exception as e:
                result.append({
                    "name": coll.name,
                    "points": None,
                    "vector_size": None,
                    "error": f"Не удалось получить полную информацию: {str(e)}"
                })

        return {"collections": result}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка сервера при получении списка коллекций: {str(e)}"
        )


@router.get("/collections/{collection_name}")
async def get_collection(collection_name: str):
    """Получить информацию о коллекции"""
    try:
        qdrant = get_qdrant_client()
        info = qdrant.get_collection(collection_name)
        return {
            "name": collection_name,
            "points_count": info.points_count,
            "status": info.status,
            "vectors_config": str(info.config.params.vectors)
        }
    except Exception as e:
        raise HTTPException(404, f"Коллекция не найдена: {str(e)}")


@router.post("/collections/{collection_name}")
async def create_collection(
        collection_name: str,
        vector_size: int,
        distance: str = "Cosine"
):
    """Создать новую коллекцию"""
    try:
        dist_map = {
            "Cosine": models.Distance.COSINE,
            "Euclidean": models.Distance.EUCLID,
            "Dot": models.Distance.DOT
        }
        qdrant = get_qdrant_client()
        qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=dist_map.get(distance, models.Distance.COSINE)
            )
        )
        return {"message": f"Коллекция '{collection_name}' создана"}
    except Exception as e:
        raise HTTPException(400, f"Ошибка создания: {str(e)}")


@router.delete("/collections/{collection_name}")
async def delete_collection(collection_name: str):
    """Удалить коллекцию"""
    try:
        qdrant = get_qdrant_client()
        qdrant.delete_collection(collection_name)
        return {"message": f"Коллекция '{collection_name}' удалена"}
    except Exception as e:
        raise HTTPException(404, f"Ошибка удаления: {str(e)}")