import re
import torch
from pathlib import Path
from typing import List, Tuple
from sentence_transformers import SentenceTransformer
from .logger import logger
from .config import config, MODELS_DIR


class TextChunker:
    """Разбивает текст на оптимальные чанки для эмбеддингов"""

    def __init__(self, max_chunk_size: int = 1500, min_chunk_size: int = 300, overlap: int = 100):
        """
        Args:
            max_chunk_size: максимальный размер чанка в символах
            min_chunk_size: минимальный размер чанка в символах
            overlap: перекрытие между чанками (для сохранения контекста)
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap = overlap

    def split_into_paragraphs(self, text: str) -> List[str]:
        """Разбивает текст на абзацы"""
        # Ищем пустые строки (два и более переноса строки)
        paragraphs = re.split(r'\n\s*\n', text.strip())

        # Фильтруем пустые абзацы
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        # Если абзацев не найдено, разбиваем по одинарным переносам
        if len(paragraphs) <= 1:
            paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

        return paragraphs

    def merge_paragraphs_to_chunks(self, paragraphs: List[str]) -> List[str]:
        """
        Объединяет абзацы в чанки оптимального размера
        """
        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para_size = len(para)

            # Если абзац сам по себе больше max_size, разбиваем его
            if para_size > self.max_chunk_size:
                # Сохраняем текущий чанк если есть
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0

                # Разбиваем большой абзац на предложения
                sentences = re.split(r'(?<=[.!?])\s+', para)
                temp_chunk = []
                temp_size = 0

                for sent in sentences:
                    sent_size = len(sent)
                    if temp_size + sent_size > self.max_chunk_size and temp_chunk:
                        chunks.append(' '.join(temp_chunk))
                        # Добавляем перекрытие
                        overlap_text = temp_chunk[-1] if temp_chunk else ''
                        temp_chunk = [overlap_text, sent] if overlap_text else [sent]
                        temp_size = len(overlap_text) + sent_size if overlap_text else sent_size
                    else:
                        temp_chunk.append(sent)
                        temp_size += sent_size

                if temp_chunk:
                    chunks.append(' '.join(temp_chunk))

            # Если добавление абзаца превысит лимит
            elif current_size + para_size + 2 > self.max_chunk_size:
                # Сохраняем текущий чанк
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))

                # Начинаем новый чанк с перекрытием
                overlap_text = current_chunk[-1] if current_chunk else ''
                if overlap_text and len(overlap_text) <= self.overlap:
                    current_chunk = [overlap_text, para]
                    current_size = len(overlap_text) + para_size + 2
                else:
                    current_chunk = [para]
                    current_size = para_size
            else:
                # Добавляем абзац в текущий чанк
                current_chunk.append(para)
                current_size += para_size + 2

        # Добавляем последний чанк
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks

    def chunk_text(self, text: str) -> List[str]:
        """
        Основной метод: разбивает текст на чанки
        """
        paragraphs = self.split_into_paragraphs(text)
        chunks = self.merge_paragraphs_to_chunks(paragraphs)
        return chunks


class EmbeddingGenerator:
    """Генератор эмбеддингов с кэшированием модели и поддержкой GPU"""

    _instance = None
    _model = None
    _device = None

    def __new__(cls):
        """Singleton pattern - модель загружается только один раз"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            self._init_model()
        self.chunker = TextChunker()

    def _init_model(self):
        """Инициализация модели с автоматическим определением устройства"""
        try:
            # Определяем лучшее доступное устройство
            if torch.cuda.is_available():
                self._device = "cuda"
                logger.info(f"GPU доступен: {torch.cuda.get_device_name(0)}")
            elif torch.backends.mps.is_available():
                self._device = "mps"
                logger.info("MPS (Apple Silicon) доступен")
            else:
                self._device = "cpu"
                logger.info("Использую CPU")

            # Загружаем модель из кэша или скачиваем
            model_path = self._get_model_path()

            if model_path.exists():
                logger.info(f"Загружаю модель из кэша: {model_path}")
                self._model = SentenceTransformer(str(model_path))
            else:
                logger.info(f"Скачиваю модель: {config.EMBEDDING_MODEL}")
                self._model = SentenceTransformer(config.EMBEDDING_MODEL)
                self._save_model_to_cache(model_path)

            # Перемещаем на GPU если возможно
            self._model.to(self._device)

            # Прогрев модели
            logger.info("Прогреваю модель...")
            test_text = "test"
            self._model.encode(test_text)

            logger.info(f"Модель загружена на {self._device.upper()}")

        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            self._model = None
            self._device = "cpu"

    def _get_model_path(self) -> Path:
        """Возвращает путь для кэширования модели"""
        model_name = config.EMBEDDING_MODEL.replace('/', '_')
        return MODELS_DIR / model_name

    def _save_model_to_cache(self, path: Path):
        """Сохраняет модель в кэш"""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._model.save(str(path))
            logger.info(f"Модель сохранена в кэш: {path}")
        except Exception as e:
            logger.warning(f"Не удалось сохранить модель в кэш: {e}")

    def is_available(self) -> bool:
        return self._model is not None

    def get_device_info(self) -> dict:
        return {
            "device": self._device,
            "model_loaded": self._model is not None,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "model_name": config.EMBEDDING_MODEL
        }

    def generate_embeddings_for_chunks(self, chunks: List[str]) -> List[List[float]]:
        """
        Генерирует эмбеддинги ДЛЯ КАЖДОГО ЧАНКА ОТДЕЛЬНО

        Args:
            chunks: список текстовых чанков

        Returns:
            список эмбеддингов (по одному на каждый чанк)
        """
        if not self._model:
            raise RuntimeError("Модель эмбеддингов не загружена")

        if not chunks:
            return []

        # Генерируем эмбеддинги батчами для оптимизации
        batch_size = 32
        all_embeddings = []

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            batch_embeddings = self._model.encode(batch, show_progress_bar=False)
            all_embeddings.extend(batch_embeddings.tolist())

        return all_embeddings

    def generate_single_embedding(self, text: str) -> List[float]:
        """Генерирует один эмбеддинг для текста"""
        if not self._model:
            raise RuntimeError("Модель эмбеддингов не загружена")

        embedding = self._model.encode([text], show_progress_bar=False)
        return embedding[0].tolist()


class ArticleEmbeddingProcessor:
    """
    Обработчик статей: разбивает на чанки и генерирует эмбеддинг для КАЖДОГО чанка
    """

    def __init__(self):
        self.embedder = EmbeddingGenerator()

    def process_article(self, article: dict) -> Tuple[List[dict], List[List[float]]]:
        """
        Обрабатывает статью:
        1. Разбивает на чанки
        2. Для КАЖДОГО чанка генерирует свой эмбеддинг

        Args:
            article: словарь со статьей (должен содержать 'title', 'text', 'id' и т.д.)

        Returns:
            tuple: (список чанков-словарей для Qdrant, список эмбеддингов для этих чанков)
        """
        # 1. Разбиваем текст на чанки
        chunks = self.embedder.chunker.chunk_text(article['text'])

        if not chunks:
            # Если не удалось разбить, используем весь текст как один чанк
            chunks = [article['text'][:1500]]

        # 2. Добавляем заголовок к первому чанку для контекста
        if chunks:
            chunks[0] = f"Title: {article['title']}\n\n{chunks[0]}"

        # 3. Генерируем эмбеддинг для КАЖДОГО чанка (отдельно!)
        chunk_embeddings = self.embedder.generate_embeddings_for_chunks(chunks)

        # 4. Создаем точки для Qdrant (по одной на каждый чанк)
        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, chunk_embeddings)):
            point = {
                "chunk_id": f"{article['id']}_chunk_{i}",
                "document_id": article['id'],
                "title": article['title'],
                "url": article['url'],
                "published_date": article['published_date'],
                "chunk_index": i,
                "total_chunks": len(chunks),
                "chunk_text": chunk,
                "chunk_length": len(chunk),
                "processing_timestamp": article.get('parsed_at', '')
            }
            points.append(point)

        logger.debug(
            f"  Статья '{article['title'][:40]}...' → {len(chunks)} чанков, {len(chunk_embeddings)} эмбеддингов")

        return points, chunk_embeddings

    def process_articles_batch(self, articles: List[dict]) -> Tuple[List[dict], List[List[float]]]:
        """
        Обрабатывает батч статей

        Returns:
            tuple: (список всех точек, список всех эмбеддингов)
        """
        all_points = []
        all_embeddings = []

        for article in articles:
            try:
                points, embeddings = self.process_article(article)
                all_points.extend(points)
                all_embeddings.extend(embeddings)
            except Exception as e:
                logger.error(f"Ошибка обработки статьи {article.get('title', 'unknown')}: {e}")

        return all_points, all_embeddings

