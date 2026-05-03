from typing import List, Dict, Any, Union, Optional
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
import logging

from app.core.generation_config import generation_config
from app.core.search_config import search_config
from src.dense.data_prep import TextChunker

logger = logging.getLogger(__name__)


def index_documents_to_qdrant_dense(
        data: Union[List[Dict], Dict],
        collection_name: str,
        batch_size: int = 100,
        max_docs: Optional[int] = None,
        force_recreate: bool = True
) -> Dict[str, Any]:

    client = QdrantClient(
        host=generation_config.QDRANT_HOST,
        port=generation_config.QDRANT_PORT
    )

    model = SentenceTransformer(generation_config.EMBEDDING_MODEL)
    embedding_size = generation_config.EMBEDDING_SIZE
    chunk_size = search_config.CHUNK_SIZE
    chunk_overlap = search_config.CHUNK_SIZE_OVERLAP
    chunker = TextChunker(max_chunk_size=chunk_size, overlap=chunk_overlap)

    if force_recreate:
        try:
            client.delete_collection(collection_name)
            logger.info(f"Удалена старая коллекция {collection_name}")
        except Exception as e:
            logger.warning(f"Коллекция не существовала: {e}")

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=embedding_size,
            distance=Distance.COSINE
        )
    )
    logger.info(f"Коллекция {collection_name} создана с размером {embedding_size}")

    # Подготовка документов
    docs = data if isinstance(data, list) else data.get('documents', data.get('articles', [data]))
    docs = docs[:max_docs] if max_docs else docs
    logger.info(f"Документов для обработки: {len(docs)}")

    points = []
    chunk_counter = 0

    for doc_idx, doc in enumerate(docs):
        doc_id = doc.get('id') or doc.get('_id') or f"doc_{doc_idx}"
        title = doc.get('title', '')
        text = doc.get('text', '')

        if not text:
            continue

        chunks = chunker.chunk_text(text)

        for i, chunk_text in enumerate(chunks):
            full_chunk = f"Заголовок: {title}\n{chunk_text}" if title else chunk_text

            points.append({
                "id": chunk_counter,
                "text": full_chunk,
                "payload": {
                    "doc_id": str(doc_id),
                    "title": str(title)[:200],
                    "text": full_chunk[:1000],
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
            })
            chunk_counter += 1

    logger.info(f"Создано {len(points)} чанков")

    success = 0

    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]

        try:
            texts = [p["text"] for p in batch]
            embeddings = model.encode(texts, show_progress_bar=False)

            qdrant_points = []
            for j, point in enumerate(batch):
                qdrant_points.append(PointStruct(
                    id=point["id"],
                    vector=embeddings[j].tolist(),
                    payload=point["payload"]
                ))

            client.upsert(collection_name=collection_name, points=qdrant_points, wait=True)
            success += len(batch)
            logger.info(f"Загружено {success}/{len(points)} точек")

        except Exception as e:
            logger.error(f"Ошибка батча: {e}")
            for point in batch:
                try:
                    embedding = model.encode([point["text"]], show_progress_bar=False)[0]
                    qdrant_point = PointStruct(
                        id=point["id"],
                        vector=embedding.tolist(),
                        payload=point["payload"]
                    )
                    client.upsert(collection_name=collection_name, points=[qdrant_point], wait=True)
                    success += 1
                    logger.info(f"Загружено {success}/{len(points)} точек")
                except Exception as e2:
                    logger.error(f"Точка {point['id']} не загружена: {e2}")

    logger.info(f"Загружено {success}/{len(points)} чанков")
    return {"total": len(points), "success": success, "collection": collection_name}