from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
import uuid
import time
from sentence_transformers import SentenceTransformer

from app.core.generation_config import generation_config
from app.core.search_config import search_config


_semantic_model = None


def _get_semantic_model():
    """Загружает семантическую модель один раз, потом возвращает из глобальной переменной"""
    global _semantic_model
    if _semantic_model is None:
        print(f"[semantic_cache] Loading semantic model: {generation_config.SEM_MODEL_NAME}")
        _semantic_model = SentenceTransformer(generation_config.SEM_MODEL_NAME)
    return _semantic_model


def embed(text: str):
    model = _get_semantic_model()
    return model.encode(text, normalize_embeddings=True)


class SemanticCache:

    def __init__(self):
        self.client = QdrantClient(host=search_config.QDRANT_HOST, port=search_config.QDRANT_PORT)

        self._init_collection()

    def _init_collection(self):
        collections = self.client.get_collections().collections

        if generation_config.SEM_COLLECTION_NAME not in [c.name for c in collections]:
            self.client.create_collection(
                collection_name=generation_config.SEM_COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=generation_config.SEM_VECTOR_SIZE,
                    distance=Distance.COSINE
                )
            )

    def search(self, query, threshold=0.85):
        vector = embed(query)

        result = self.client.query_points(
            collection_name=generation_config.SEM_COLLECTION_NAME,
            query=vector,
            limit=1,
            with_payload=True
        )

        if result.points and len(result.points) > 0:
            hit = result.points[0]
            if hit.score >= threshold:
                return hit.payload["answer"], hit.score

        return None, None

    def save(self, query, answer):
        vector = embed(query)

        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={
                "query": query,
                "answer": answer,
                "timestamp": time.time()
            }
        )

        self.client.upsert(
            collection_name=generation_config.SEM_COLLECTION_NAME,
            points=[point]
        )


semantic_cache = SemanticCache()