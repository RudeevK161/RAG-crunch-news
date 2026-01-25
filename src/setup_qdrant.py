import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models
import json
from typing import List, Dict
import os
from tqdm import tqdm
from scipy import sparse


class QdrantLocalSetup:
    def __init__(self, host="localhost", port=6333):
        self.client = QdrantClient(host=host, port=port)
        print(f"Подключение к Qdrant: {host}:{port}")

    def create_collection(self,
                          collection_name: str = "ai_articles",
                          vector_size: int = 1024,
                          distance: str = "Cosine"):
        """
        Создание коллекции
        """
        collections = self.client.get_collections()
        existing_names = [c.name for c in collections.collections]

        if collection_name in existing_names:
            print(f"Коллекция '{collection_name}' уже существует")
            return False

        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=self._get_distance(distance)
            ),
            optimizers_config=models.OptimizersConfigDiff(
                indexing_threshold=20000,
                memmap_threshold=20000
            )
        )
        print(f"Коллекция '{collection_name}' создана (vector_size={vector_size}, distance={distance})")
        return True

    def _get_distance(self, distance: str) -> models.Distance:
        """Преобразование строки в тип Distance"""
        distance_map = {
            "Cosine": models.Distance.COSINE,
            "Euclidean": models.Distance.EUCLID,
            "Dot": models.Distance.DOT
        }
        return distance_map.get(distance, models.Distance.COSINE)

    def upload_sparse_embeddings(self,
                                 collection_name: str,
                                 sparse_matrix,
                                 articles: List[Dict],
                                 batch_size: int = 100):
        """
        Загрузка SPARSE эмбеддингов в Qdrant

        Args:
            collection_name: имя коллекции
            sparse_matrix: scipy sparse матрица (n_articles, vector_size)
            articles: список статей с метаданными
            batch_size: размер батча для загрузки
        """
        # Конвертируем sparse в dense батчами для экономии памяти
        print(f"Начало загрузки {len(articles)} статей в коллекцию '{collection_name}'...")

        points = []

        for i in tqdm(range(len(articles)), desc="Загрузка статей"):
            # Получаем i-ю строку как dense вектор
            if sparse.issparse(sparse_matrix):
                # Для sparse матрицы конвертируем строку в dense
                embedding = sparse_matrix[i].toarray().flatten().tolist()
            else:
                # Уже dense
                embedding = sparse_matrix[i].tolist()

            article = articles[i]
            payload = {
                'id': article.get('id', str(i)),
                'title': article.get('title', ''),
                'text': article.get('text', '')[:2000],  # Ограничиваем длину
                'published_time': article.get('published_time', ''),
                'source': 'TechCrunch',
                'url': article.get('url', ''),
                'category': article.get('category', ''),
                'author': article.get('author', '')
            }

            payload = {k: v for k, v in payload.items() if v}

            point = models.PointStruct(
                id=payload['id'],
                vector=embedding,
                payload=payload
            )
            points.append(point)

            if len(points) >= batch_size:
                self.client.upsert(
                    collection_name=collection_name,
                    points=points,
                    wait=True
                )
                points = []

        if points:
            self.client.upsert(
                collection_name=collection_name,
                points=points,
                wait=True
            )

        print(f"Успешно загружено {len(articles)} статей")
        collection_info = self.client.get_collection(collection_name)
        print(f"   Векторов в коллекции: {collection_info.points_count}")

    def upload_dense_embeddings(self,
                                collection_name: str,
                                embeddings: np.ndarray,
                                articles: List[Dict],
                                batch_size: int = 100):
        """
        Загрузка DENSE эмбеддингов в Qdrant

        Args:
            collection_name: имя коллекции
            embeddings: numpy массив (n_articles, vector_size)
            articles: список статей с метаданными
            batch_size: размер батча для загрузки
        """
        if len(embeddings) != len(articles):
            raise ValueError(f"Количество эмбеддингов ({len(embeddings)}) не равно количеству статей ({len(articles)})")

        print(f"Начало загрузки {len(articles)} статей в коллекцию '{collection_name}'...")

        points = []

        for i, (embedding, article) in enumerate(tqdm(zip(embeddings, articles),
                                                      total=len(articles),
                                                      desc="Загрузка статей")):
            payload = {
                'id': article.get('id', str(i)),
                'title': article.get('title', ''),
                'text': article.get('text', '')[:2000],
                'published_time': article.get('published_time', ''),
                'source': 'TechCrunch',
                'url': article.get('url', ''),
                'category': article.get('category', ''),
                'author': article.get('author', '')
            }

            payload = {k: v for k, v in payload.items() if v}

            point = models.PointStruct(
                id=payload['id'],
                vector=embedding.tolist(),
                payload=payload
            )
            points.append(point)

            if len(points) >= batch_size:
                self.client.upsert(
                    collection_name=collection_name,
                    points=points,
                    wait=True
                )
                points = []

        if points:
            self.client.upsert(
                collection_name=collection_name,
                points=points,
                wait=True
            )

        print(f"Успешно загружено {len(articles)} статей")
        collection_info = self.client.get_collection(collection_name)
        print(f"   Векторов в коллекции: {collection_info.points_count}")

    def create_indexes(self, collection_name: str):
        try:
            self.client.create_payload_index(
                collection_name=collection_name,
                field_name="published_time",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            print("Индекс по published_time создан")
        except Exception as e:
            print(f"Ошибка создания индекса published_time: {e}")

        try:
            self.client.create_payload_index(
                collection_name=collection_name,
                field_name="category",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            print("Индекс по category создан")
        except Exception as e:
            print(f"Ошибка создания индекса category: {e}")

        try:
            self.client.create_payload_index(
                collection_name=collection_name,
                field_name="author",
                field_schema=models.PayloadSchemaType.KEYWORD
            )
            print("Индекс по author создан")
        except Exception as e:
            print(f"Ошибка создания индекса author: {e}")

    def test_search(self, collection_name: str, query_vector: List[float], k: int = 5):
        print(f"\nТестовый поиск (k={k}):")
        search_result = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=k
        )

        for i, hit in enumerate(search_result, 1):
            print(f"{i}. [{hit.score:.3f}] {hit.payload.get('title', 'Без названия')}")
            print(f"   ID: {hit.id}, Дата: {hit.payload.get('published_time', 'неизвестна')}")

        return search_result


def main():
    setup = QdrantLocalSetup()
    collection_name = "ai_trends_bm25_4"
    vector_size = 60846

    setup.create_collection(
        collection_name=collection_name,
        vector_size=vector_size,
        distance="Cosine"
    )

    try:
        with open('techcrunch_ai_5488_articles_20260112_1535.json', 'r', encoding='utf-8') as f:
            articles = json.load(f)
        #embeddings = np.load('dense_embeddings_qwen.npy')
        embeddings = sparse.load_npz('bm25_matrix.npz')
        setup.upload_sparse_embeddings(collection_name, embeddings, articles)

        print(f"Готово! Qdrant запущен с коллекцией '{collection_name}'")
        print(f"REST API: http://localhost:6333")
        print(f"gRPC API: http://localhost:6334")
    except Exception as e:
        print(f"Ошибка загрузки данных: {e}")
        print("Создана пустая коллекция. Загрузите данные позже.")


if __name__ == "__main__":
    main()