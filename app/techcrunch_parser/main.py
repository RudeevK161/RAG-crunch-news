import pickle
import time
import sys
from typing import Set

from .config import parser_config
from .logger import logger
from .lock import file_lock
from .parser import TechCrunchParser
from .client_qdrant import QdrantClient
from .backup_manager import BackupManager
from .embeddings import EmbeddingGenerator, ArticleEmbeddingProcessor


class Pipeline:
    def __init__(self):
        self.parser = TechCrunchParser()
        self.qdrant = QdrantClient()
        self.backup = BackupManager()
        self.embedder = EmbeddingGenerator()
        self.processor = ArticleEmbeddingProcessor()
        self.existing_ids = self._load_existing_ids()

    def _load_existing_ids(self) -> Set[str]:
        """Загружает ID существующих статей"""
        if self.qdrant.is_available():
            ids = self.qdrant.get_existing_article_ids()
            if ids:
                self._save_cache(ids)
                return ids

        if parser_config.CACHE_FILE.exists():
            with open(parser_config.CACHE_FILE, 'rb') as f:
                return pickle.load(f)

        if self.backup.has_backup():
            articles = self.backup.load_backup()
            return {a['id'] for a in articles}

        return set()

    def _save_cache(self, ids: Set[str]):
        with open(parser_config.CACHE_FILE, 'wb') as f:
            pickle.dump(ids, f)

    def _process_backup(self):
        """Загружает бэкап в Qdrant если возможно"""
        if not self.qdrant.is_available() or not self.backup.has_backup():
            return

        articles = self.backup.load_backup()
        new_articles = [a for a in articles if a['id'] not in self.existing_ids]

        if not new_articles:
            self.backup.delete_backup()
            return

        points, embeddings = self.processor.process_articles_batch(new_articles)
        if self.qdrant.save_chunks(points, embeddings):
            for a in new_articles:
                self.existing_ids.add(a['id'])
            self.backup.delete_backup()
            self._save_cache(self.existing_ids)
            logger.info(f"Бэкап загружен ({len(new_articles)} статей)")

    def _save_articles(self, articles: list) -> bool:
        """Сохраняет статьи (в Qdrant или бэкап)"""
        if not articles:
            return False

        if self.qdrant.is_available() and self.embedder.is_available():
            points, embeddings = self.processor.process_articles_batch(articles)
            if self.qdrant.save_chunks(points, embeddings):
                for a in articles:
                    self.existing_ids.add(a['id'])
                self._save_cache(self.existing_ids)
                return True

        self.backup.append_articles(articles)
        return False

    def run(self):
        start = time.time()

        self._process_backup()

        new_articles = self.parser.parse_articles(self.existing_ids)

        if new_articles:
            self._save_articles(new_articles)
            logger.info(f"Найдено {len(new_articles)} новых статей")
        else:
            logger.info("Новых статей не найдено")

        logger.info(f"Время: {(time.time() - start) / 60:.1f} мин")


def main():

    if len(sys.argv) > 1 and sys.argv[1] == "status":
        print(f"Qdrant: {'ok' if QdrantClient().is_available() else 'not'}")
        print(f"GPU: {'k' if EmbeddingGenerator().is_available() else 'not'}")
        print(f"Бэкап: {BackupManager().get_stats().get('articles_count', 0)} статей")
        return

    try:
        with file_lock():
            Pipeline().run()
    except RuntimeError:
        logger.info("Парсер уже запущен")


if __name__ == "__main__":
    main()