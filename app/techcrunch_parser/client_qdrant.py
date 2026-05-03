import time
from typing import List, Set, Dict
from qdrant_client import QdrantClient as QClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from .logger import logger
from .config import config


class QdrantClient:
    def __init__(self):
        self.client = None
        self._connect()

    def _connect(self):
        try:
            self.client = QClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT, timeout=10)
            self.client.get_collections()
            logger.info(f"Qdrant подключен")
            self._ensure_collection()
        except Exception as e:
            logger.warning(f"Qdrant недоступен: {e}")
            self.client = None

    def _ensure_collection(self):
        if not self.client:
            return
        try:
            collections = self.client.get_collections().collections
            if config.QDRANT_COLLECTION not in [c.name for c in collections]:
                self.client.create_collection(
                    collection_name=config.QDRANT_COLLECTION,
                    vectors_config=VectorParams(size=config.VECTOR_SIZE, distance=Distance.COSINE)
                )
                logger.info(f"Коллекция {config.QDRANT_COLLECTION} создана")
        except Exception as e:
            logger.error(f"Ошибка создания коллекции: {e}")

    def is_available(self) -> bool:
        return self.client is not None

    def get_existing_article_ids(self, limit: int = 10000) -> Set[str]:
        """Получает ID существующих СТАТЕЙ (не чанков) из Qdrant"""
        if not self.client:
            return set()
        try:
            scroll_result = self.client.scroll(
                collection_name=config.QDRANT_COLLECTION,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            article_ids = set()
            for point in scroll_result[0]:
                if 'document_id' in point.payload:
                    article_ids.add(point.payload['document_id'])
            logger.info(f"Загружено {len(article_ids)} ID статей из Qdrant")
            return article_ids
        except Exception as e:
            logger.error(f"Ошибка загрузки ID: {e}")
            return set()

    def save_chunks(self, points: List[Dict], embeddings: List[List[float]]) -> int:
        """
        Сохраняет чанки статей в Qdrant
        КАЖДЫЙ чанк - отдельная точка со своим эмбеддингом

        Args:
            points: список словарей с данными чанков
            embeddings: список эмбеддингов (по одному на каждый чанк)
        """
        if not self.client or not points:
            return 0

        if len(points) != len(embeddings):
            logger.error(f"Несоответствие: {len(points)} точек, {len(embeddings)} эмбеддингов")
            return 0

        # Создаем точки для Qdrant
        qdrant_points = []
        for point_data, embedding in zip(points, embeddings):
            # Генерируем уникальный ID для чанка
            point_id = abs(hash(point_data['chunk_id'])) % (2 ** 31 - 1)

            qdrant_points.append(PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "chunk_id": point_data['chunk_id'],
                    "document_id": point_data['document_id'],
                    "title": point_data['title'],
                    "url": point_data['url'],
                    "published_date": point_data['published_date'],
                    "chunk_index": point_data['chunk_index'],
                    "total_chunks": point_data['total_chunks'],
                    "text": point_data['chunk_text'],
                    "chunk_length": point_data['chunk_length'],
                    "processing_timestamp": point_data.get('processing_timestamp', '')
                }
            ))

        # Сохраняем батчами
        batch_size = 50
        saved = 0

        for i in range(0, len(qdrant_points), batch_size):
            batch = qdrant_points[i:i + batch_size]
            try:
                self.client.upsert(
                    collection_name=config.QDRANT_COLLECTION,
                    points=batch,
                    wait=False
                )
                saved += len(batch)
                logger.info(f"  Сохранено {saved}/{len(qdrant_points)} чанков")
                time.sleep(0.3)
            except Exception as e:
                logger.error(f"Ошибка сохранения батча: {e}")

        # Выводим статистику
        articles_saved = len(set(p['document_id'] for p in points))
        total_chunks = len(points)
        logger.info(f"Сохранено {articles_saved} статей ({total_chunks} чанков) в Qdrant")

        return saved