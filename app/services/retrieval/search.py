import numpy as np
import logging
from datetime import datetime
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import torch

from app.core.search_config import search_config


logger = logging.getLogger("techcrunch_search")
logger.setLevel(logging.INFO)

_embedding_model = None


def _get_embedding_model(model_name: str):
    """Загружает модель один раз, потом возвращает из глобальной переменной"""
    global _embedding_model
    if _embedding_model is None:
        print(f"[retriever] Loading embedding model: {model_name}")
        _embedding_model = SentenceTransformer(model_name)
        if torch.cuda.is_available():
            _embedding_model.to("cuda")
    return _embedding_model


def retriever(
        query: str,
        collection_name: str = None,
        model_name: str = None,
        top_k: int = 10,
        freshness_weight: float = 0.2,
        relevance_weight: float = 1.0,
        max_days: int = 120
) -> List[Dict[str, Any]]:
    """
    Поиск статей с учетом релевантности и свежести

    Args:
        query: поисковый запрос
        collection_name: коллекция в Qdrant (по умолчанию из config)
        model_name: модель эмбеддингов (по умолчанию из config)
        top_k: количество результатов
        freshness_weight: вес свежести (0-1)
        relevance_weight: вес релевантности (0-1)
        max_days: период учета свежести в днях
    """

    collection_name = collection_name or search_config.QDRANT_COLLECTION
    model_name = model_name or search_config.EMBEDDING_MODEL
    freshness_weight = freshness_weight or search_config.DEFAULT_FRESHNESS_WEIGHT
    relevance_weight = relevance_weight or search_config.DEFAULT_RELEVANCE_WEIGHT
    top_k = top_k or search_config.DEFAULT_TOP_K

    logger.info(f"Поиск: {query[:50]}... | top_k={top_k}")

    client = QdrantClient(host=search_config.QDRANT_HOST, port=search_config.QDRANT_PORT, timeout=10)

    model = _get_embedding_model(model_name)
    if torch.cuda.is_available():
        model.to("cuda")

    query_embedding = model.encode(query).tolist()

    search_result = client.query_points(
        collection_name=collection_name,
        query=query_embedding,
        limit=top_k * 2,
        with_payload=True
    )

    results = []
    now = datetime.now()

    for point in search_result.points:
        relevance = point.score

        freshness = 0.5
        published = point.payload.get("published_time")
        if published:
            try:
                if isinstance(published, dict):
                    published = published.get("raw")

                days = (now - datetime.strptime(published, "%Y-%m-%d")).days
                freshness = np.exp(-days / max_days)
            except Exception as e:
                print(f"Ошибка парсинга даты {published}: {e}")
                freshness = 0.5

        combined = relevance_weight * relevance + freshness_weight * freshness

        results.append({
            'title': point.payload.get('title', ''),
            'url': point.payload.get('url', ''),
            'published_date': published,
            'text_preview': point.payload.get('text', '')[:350],
            'score': combined,
            'relevance': relevance,
            'freshness': freshness
        })

    results.sort(key=lambda x: x['score'], reverse=True)
    logger.info(f"Найдено: {len(results)} результатов")

    return results[:top_k]