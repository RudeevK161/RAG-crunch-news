from qdrant_client import models
from fastapi import APIRouter, HTTPException
import logging
import os

from src.setup_qdrant import *
from src.bm25.bm25_utils import get_qdrant_client

logger = logging.getLogger(__name__)
sys.path.append(os.path.join(os.path.dirname(__file__), '../..', '..'))

router = APIRouter()


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