from dataclasses import dataclass
from typing import Optional, List, Dict


@dataclass
class Article:
    """Модель статьи"""
    id: str
    url: str
    title: str
    published_date: str
    text: str
    word_count: int
    parsed_at: str

    def to_dict(self) -> Dict:
        """Конвертация в словарь"""
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "published_date": self.published_date,
            "text": self.text,
            "word_count": self.word_count,
            "parsed_at": self.parsed_at
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Article':
        """Создание из словаря"""
        return cls(
            id=data['id'],
            url=data['url'],
            title=data['title'],
            published_date=data['published_date'],
            text=data['text'],
            word_count=data['word_count'],
            parsed_at=data['parsed_at']
        )

    def get_preview(self, length: int = 200) -> str:
        """Получить превью текста"""
        return self.text[:length] + "..." if len(self.text) > length else self.text


@dataclass
class ParseStats:
    """Статистика парсинга"""
    articles_found: int
    articles_saved_to_qdrant: int
    duration_seconds: float
    qdrant_available: bool
    backup_file: Optional[str] = None
    errors: List[str] = None

    def to_dict(self) -> Dict:
        return {
            "articles_found": self.articles_found,
            "articles_saved_to_qdrant": self.articles_saved_to_qdrant,
            "duration_minutes": self.duration_seconds / 60,
            "qdrant_available": self.qdrant_available,
            "backup_file": self.backup_file,
            "errors": self.errors or []
        }