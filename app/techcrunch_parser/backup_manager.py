import json
from datetime import datetime
from typing import List, Dict
from .logger import logger
from .config import BACKUPS_DIR


class BackupManager:
    """Простой менеджер бэкапов - одна активная копия + очистка после загрузки"""

    def __init__(self):
        self.backup_dir = BACKUPS_DIR
        self.backup_file = None
        self._find_active_backup()

    def _find_active_backup(self):
        """Находит активный бэкап-файл"""
        if not self.backup_dir.exists():
            return

        backups = list(self.backup_dir.glob("techcrunch_backup_*.json"))
        if backups:
            # Берем самый свежий бэкап
            self.backup_file = max(backups, key=lambda x: x.stat().st_mtime)
            logger.info(f" Найден активный бэкап: {self.backup_file.name}")

    def has_backup(self) -> bool:
        """Проверяет, есть ли необработанный бэкап"""
        return self.backup_file is not None and self.backup_file.exists()

    def load_backup(self) -> List[Dict]:
        """Загружает статьи из бэкап-файла"""
        if not self.has_backup():
            return []

        try:
            with open(self.backup_file, 'r', encoding='utf-8') as f:
                articles = json.load(f)
            logger.info(f" Загружено {len(articles)} статей из бэкапа: {self.backup_file.name}")
            return articles
        except Exception as e:
            logger.error(f"Ошибка загрузки бэкапа: {e}")
            return []

    def delete_backup(self):
        """Удаляет бэкап-файл после успешной загрузки в Qdrant"""
        if self.backup_file and self.backup_file.exists():
            try:
                self.backup_file.unlink()
                logger.info(f"Удален бэкап: {self.backup_file.name}")
                self.backup_file = None
            except Exception as e:
                logger.error(f"Ошибка удаления бэкапа: {e}")

    def append_articles(self, new_articles: List[Dict]):
        """
        Добавляет новые статьи в существующий бэкап
        Проверяет дубликаты по ID
        """
        if not new_articles:
            return

        # Загружаем существующие статьи
        existing_articles = self.load_backup() if self.has_backup() else []

        # Получаем ID существующих статей
        existing_ids = {a['id'] for a in existing_articles}

        # Добавляем только новые
        unique_new = [a for a in new_articles if a['id'] not in existing_ids]

        if not unique_new:
            logger.info("Все новые статьи уже есть в бэкапе")
            return

        # Объединяем
        all_articles = existing_articles + unique_new

        # Сохраняем
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = self.backup_dir / f"techcrunch_backup_{timestamp}_{len(all_articles)}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=2)

        # Удаляем старый бэкап
        if self.backup_file and self.backup_file.exists():
            self.backup_file.unlink()

        self.backup_file = filename
        logger.info(f" Добавлено {len(unique_new)} статей в бэкап (всего: {len(all_articles)})")

    def get_stats(self) -> Dict:
        """Получает статистику бэкапа"""
        if not self.has_backup():
            return {"has_backup": False}

        try:
            articles = self.load_backup()
            return {
                "has_backup": True,
                "filename": self.backup_file.name,
                "articles_count": len(articles),
                "size_mb": round(self.backup_file.stat().st_size / (1024 * 1024), 2),
                "created": datetime.fromtimestamp(self.backup_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            }
        except:
            return {"has_backup": True, "error": "can't read"}