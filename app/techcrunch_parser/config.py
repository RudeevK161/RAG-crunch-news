import os
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).parent.parent
PARSER_DATA_DIR = Path(os.getenv("PARSER_DATA_DIR", BASE_DIR / "parser_data"))

DATA_DIR = PARSER_DATA_DIR / "data"  # кэш, временные файлы
LOGS_DIR = PARSER_DATA_DIR / "logs"  # логи
BACKUPS_DIR = PARSER_DATA_DIR / "backups"  # бэкапы статей
MODELS_DIR = PARSER_DATA_DIR / "models"  # кэш моделей эмбеддингов

# Создаем все директории
for dir_path in [PARSER_DATA_DIR, DATA_DIR, LOGS_DIR, BACKUPS_DIR, MODELS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)



class Config:
    """Основная конфигурация"""

    # Qdrant
    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
    QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION_NAME", "techcrunch_articles")
    VECTOR_SIZE = int(os.getenv("VECTOR_SIZE", 1024))

    # Парсер
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    TARGET_ARTICLES = int(os.getenv("TARGET_ARTICLES_PER_RUN", 100))
    MAX_PAGES = int(os.getenv("MAX_PAGES", 20))

    # Chunking
    MAX_CHUNK_SIZE = int(os.getenv("MAX_CHUNK_SIZE", 1500))
    MIN_CHUNK_SIZE = int(os.getenv("MIN_CHUNK_SIZE", 300))

    # Файлы (все внутри PARSER_DATA_DIR)
    LOCK_FILE = os.getenv("LOCK_FILE", "/tmp/techcrunch_parser.lock")
    CACHE_FILE = DATA_DIR / os.getenv("CACHE_FILE", "article_ids_cache.pkl")

    # Директории
    DATA_DIR = DATA_DIR
    LOGS_DIR = LOGS_DIR
    BACKUPS_DIR = BACKUPS_DIR
    MODELS_DIR = MODELS_DIR

    # Фичи
    SAVE_BACKUP = os.getenv("SAVE_BACKUP_ALWAYS", "true").lower() == "true"
    GENERATE_EMBEDDINGS = os.getenv("GENERATE_EMBEDDINGS", "true").lower() == "true"

    # Заголовки для HTTP запросов
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }


config = Config()