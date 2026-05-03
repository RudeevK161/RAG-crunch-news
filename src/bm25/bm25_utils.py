from qdrant_client.models import PointStruct, SparseVectorParams, SparseIndexParams
from typing import Optional, List, Dict, Any, Union
from qdrant_client import QdrantClient, models
from datetime import datetime
import math
from collections import Counter
import re
import os
import time
import logging


logger = logging.getLogger(__name__)

try:
    from fastembed import SparseTextEmbedding
    FASTEMBED_AVAILABLE = True
    logger.info("Fastembed доступен, используем реальную реализацию")
except ImportError:
    FASTEMBED_AVAILABLE = False
    logger.warning("Fastembed не установлен, используем эмуляцию через BM25")

os.environ["HF_HUB_TIMEOUT"] = "600"
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "600"


class BM25SparseEmbedding:
    """
    Эмуляция SparseTextEmbedding через BM25
    Создаёт разреженные векторы в том же формате, что и fastembed
    """

    def __init__(self, model_name: str = "Qdrant/bm25"):
        self.model_name = model_name
        self.vocab = {}
        self.documents = []
        logger.info(f"Инициализирован эмулятор SparseTextEmbedding с моделью {model_name}")

    def _tokenize(self, text: str) -> List[str]:
        """Простая токенизация текста"""
        # Приводим к нижнему регистру и удаляем знаки препинания
        text = re.sub(r'[^\w\s]', '', text.lower())
        return text.split()

    def _build_vocabulary(self, texts: List[str]):
        """Строит словарь уникальных токенов"""
        all_tokens = set()
        for text in texts:
            tokens = self._tokenize(text)
            all_tokens.update(tokens)

        # Сортируем для стабильности
        sorted_tokens = sorted(all_tokens)
        self.vocab = {token: idx for idx, token in enumerate(sorted_tokens)}
        logger.info(f"📚 Построен словарь из {len(self.vocab)} токенов")

    def embed(self, texts: List[str]) -> List[Dict[int, float]]:
        """
        Создаёт разреженные эмбеддинги в формате fastembed

        Возвращает список словарей, где:
        - ключ: индекс токена в словаре
        - значение: вес (TF-IDF или BM25 score)
        """
        if not self.vocab:
            self._build_vocabulary(texts)

        doc_count = len(texts)
        doc_freqs = [Counter(self._tokenize(text)) for text in texts]

        idf = {}
        for token, idx in self.vocab.items():
            containing_docs = sum(1 for freq in doc_freqs if token in freq)
            idf[token] = math.log((doc_count - containing_docs + 0.5) / (containing_docs + 0.5) + 1)

        sparse_embeddings = []

        for i, text in enumerate(texts):
            tokens = self._tokenize(text)
            token_freq = Counter(tokens)

            sparse_vector = {}
            for token, freq in token_freq.items():
                if token in self.vocab:
                    tf = freq / len(tokens)
                    sparse_vector[self.vocab[token]] = tf * idf.get(token, 1.0)

            sparse_embeddings.append(sparse_vector)

        return sparse_embeddings

    def embed_query(self, query: str) -> Dict[int, float]:
        """
        Создаёт разреженный эмбеддинг для одного запроса
        """
        return self.embed([query])[0]


class SparseTextEmbeddingWrapper:
    """
    Обёртка, которая выбирает реальную реализацию или эмуляцию
    """

    def __init__(self, model_name: str = "Qdrant/bm25"):
        self.model_name = model_name

        if FASTEMBED_AVAILABLE:
            # Используем реальную реализацию
            self.model = SparseTextEmbedding(model_name)
            self.is_emulated = False
            logger.info(f"Используется реальный SparseTextEmbedding с моделью {model_name}")
        else:
            # Используем эмуляцию
            self.model = BM25SparseEmbedding(model_name)
            self.is_emulated = True
            logger.info(f"Используется эмуляция SparseTextEmbedding с моделью {model_name}")

    def embed(self, texts: List[str]) -> List[Dict[int, float]]:
        """
        Возвращает разреженные эмбеддинги в формате {индекс: вес}
        """
        if self.is_emulated:
            return self.model.embed(texts)
        else:
            return list(self.model.embed(texts))

    def embed_query(self, query: str) -> Dict[int, float]:
        """
        Возвращает разреженный эмбеддинг для одного запроса
        """
        if self.is_emulated:
            return self.model.embed_query(query)
        else:
            return list(self.model.embed([query]))[0]



def split_text(text: str, chunk_size: int = 1500, chunk_overlap: int = 150) -> List[str]:
    """
    Разбивает текст на чанки с перекрытием
    """
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start = end - chunk_overlap if end < len(text) else len(text)
    return chunks


def get_qdrant_client():
    """Создание клиента Qdrant с правильными параметрами"""
    host = os.getenv("QDRANT_HOST", "qdrant")
    port = int(os.getenv("QDRANT_PORT", 6333))

    logger.info(f"Connecting to Qdrant at {host}:{port}")

    # Пробуем подключиться несколько раз
    for attempt in range(5):
        try:
            client = QdrantClient(
                host=host,
                port=port,
                timeout=30,
                prefer_grpc=False  # Используем HTTP
            )
            # Проверяем соединение
            client.get_collections()
            logger.info(f"Successfully connected to Qdrant on attempt {attempt + 1}")
            return client
        except Exception as e:
            logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt < 4:
                time.sleep(3)

    raise Exception(f"Could not connect to Qdrant at {host}:{port}")


def index_documents_to_qdrant(
        data: Union[List[Dict], Dict],
        collection_name: str,
        chunk_size: int = 1500,
        chunk_overlap: int = 150,
        batch_size: int = 100,
        max_docs: Optional[int] = None,
        force_recreate: bool = True
) -> Dict[str, Any]:
    """
    Индексация документов в Qdrant с BM25

    Args:
        data: Загруженные данные (список документов или словарь с документами)
        collection_name: Имя коллекции
        qdrant_host: Хост Qdrant
        qdrant_port: Порт Qdrant
        chunk_size: Размер чанка
        chunk_overlap: Перекрытие чанков
        batch_size: Размер батча для загрузки
        max_docs: Максимум документов для обработки
        force_recreate: Пересоздать коллекцию
    """

    client = get_qdrant_client()
    model = SparseTextEmbeddingWrapper("Qdrant/bm25")

    if force_recreate:
        try:
            client.delete_collection(collection_name)
            print(f"Удалена старая коллекция {collection_name}")
        except:
            pass

    client.create_collection(
        collection_name=collection_name,
        vectors_config={},
        sparse_vectors_config={
            "bm25": SparseVectorParams(index=SparseIndexParams(on_disk=False))
        }
    )
    print(f"Коллекция {collection_name} создана")

    docs = data if isinstance(data, list) else data.get('documents', data.get('articles', [data]))
    docs = docs[:max_docs] if max_docs else docs
    print(f"Документов для обработки: {len(docs)}")

    points = []
    chunk_counter = 0

    for doc_idx, doc in enumerate(docs):
        doc_id = doc.get('id') or doc.get('_id') or f"doc_{doc_idx}"
        title = doc.get('title', '')
        text = doc.get('text', '')

        if not text:
            continue

        raw_chunks = split_text(text, chunk_size, chunk_overlap)

        for i, raw_chunk in enumerate(raw_chunks):
            chunk_text = f"Заголовок: {title}\n{raw_chunk}" if title else raw_chunk
            sparse = list(model.embed(chunk_text))[0]

            points.append(PointStruct(
                id=chunk_counter,
                vector={
                    "bm25": {
                        "indices": sparse.indices.tolist(),
                        "values": sparse.values.tolist()
                    }
                },
                payload={
                    "doc_id": str(doc_id),
                    "title": str(title)[:200],
                    "text": chunk_text[:1000],
                    "chunk_index": i
                }
            ))
            chunk_counter += 1

    print(f"Загрузка {len(points)} точек...")
    success = 0

    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        try:
            client.upsert(collection_name=collection_name, points=batch, wait=True)
            success += len(batch)
            print(f"Загружено {success}/{len(points)} точек", end="\r")
        except Exception as e:
            print(f"\nОшибка батча: {e}")
            for point in batch:
                try:
                    client.upsert(collection_name=collection_name, points=[point], wait=True)
                    success += 1
                    print(f"Загружено {success}/{len(points)} точек", end="\r")
                except:
                    print(f"\n  Точка {point.id} не загружена")

    print(f"\nЗагружено {success}/{len(points)} чанков")
    return {"total": len(points), "success": success}


def search_bm25(
    query: str,
    collection_name: str,
    qdrant_host: str = "localhost",
    qdrant_port: int = 6333,
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """
    Поиск с учетом релевантности и свежести (скор = 0.7*релевантность + 0.3*свежесть)
    """
    client = QdrantClient(host=qdrant_host, port=qdrant_port)
    model = SparseTextEmbeddingWrapper("Qdrant/bm25")

    query_sparse = list(model.embed(query))[0]
    query_vector = {
        "bm25": {
            "indices": query_sparse.indices.tolist(),
            "values": query_sparse.values.tolist()
        }
    }


    search_result = client.query_points(
        collection_name=collection_name,
        query=models.Document(text=query, model="Qdrant/bm25"),
        limit=top_k * 2,
        with_payload=True,
        search_params=models.SearchParams(
            hnsw_ef=128,
            exact=False
        ),
        score_threshold=0.0
    )

    results = list(search_result.points)

    now = datetime.now()
    max_days = 365

    for hit in results:
        published = hit.payload.get('published_time')
        if published:
            try:
                pub_date = datetime.strptime(published, "%Y-%m-%d")

                days_old = (now - pub_date).days
                freshness = max(0, 1 - days_old / max_days)
                hit.score = 0.7 * hit.score + 0.3 * freshness
            except:
                pass

    results.sort(key=lambda x: x.score, reverse=True)

    return [
        {
            'id': hit.id,
            'score': hit.score,
            'title': hit.payload.get('title', ''),
            'text': hit.payload.get('text', '')[:200],
            'published_time': hit.payload.get('published_time'),
            'doc_id': hit.payload.get('doc_id', ''),
            'chunk_index': hit.payload.get('chunk_index', 0)
        }
        for hit in results[:top_k]
    ]