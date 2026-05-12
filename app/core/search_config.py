import os
from dotenv import load_dotenv

load_dotenv()


class SearchConfig:
    """Конфигурация поискового модуля"""

    # Qdrant
    QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
    QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION_NAME", "techcrunch_articles")

    # Embedding
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "Octen/Octen-Embedding-0.6B")
    EMBEDDING_SIZE = os.getenv("EMBEDDING_SIZE", 1024)

    # Search
    DEFAULT_TOP_K = int(os.getenv("SEARCH_TOP_K", 5))
    DEFAULT_FRESHNESS_WEIGHT = float(os.getenv("SEARCH_FRESHNESS_WEIGHT", 0.3))
    DEFAULT_RELEVANCE_WEIGHT = float(os.getenv("SEARCH_RELEVANCE_WEIGHT", 0.7))
    DEFAULT_MAX_DAYS = int(os.getenv("SEARCH_MAX_DAYS", 150))
    DEFAULT_SCORE_THRESHOLD = float(os.getenv("SEARCH_SCORE_THRESHOLD", 0.0))

    # Logs
    SEARCH_LOG_FILE = os.getenv("SEARCH_LOG_FILE", "search.log")
    SEARCH_LOG_LEVEL = os.getenv("SEARCH_LOG_LEVEL", "INFO")

    # Chunking
    CHUNK_SIZE = int(os.getenv("MAX_CHUNK_SIZE", 1500))
    CHUNK_SIZE_OVERLAP = int(os.getenv("MIN_CHUNK_SIZE", 300))


search_config = SearchConfig()