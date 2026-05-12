import os
from dotenv import load_dotenv

load_dotenv()


class GenerationConfig:
    """Конфигурация генерационного модуля"""

    # Параметры для семантического кэширования запросов
    SEM_COLLECTION_NAME: str = os.getenv("SEM_COLLECTION_NAME", "semantic_cache")
    SEM_MODEL_NAME: str = os.getenv("SEM_MODEL_NAME", "all-MiniLM-L6-v2")
    SEM_VECTOR_SIZE: int = int(os.getenv("SEM_VECTOR_SIZE", 384))

    # Режим работы
    MODE: str = os.getenv("MODE", "api")  # "local" или "api"

    # API настройки
    API_BASE_URL: str = os.getenv("API_BASE_URL", "https://routerai.ru/api/v1")
    API_KEY: str = os.getenv("API_KEY", "your-api-key-here")
    API_MODEL: str = os.getenv("API_MODEL", "qwen/qwen-2.5-7b-instruct")

    # Локальные настройки (только при MODE="local")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-3B-Instruct")
    MAX_CONTEXT_TOKEN: int = int(os.getenv("MAX_CONTEXT_TOKEN", 512))

    # Общие параметры генерации
    DEFAULT_TEMPERATURE: float = float(os.getenv("DEFAULT_TEMPERATURE", 0.5))
    DEFAULT_MAX_NEW_TOKENS: int = int(os.getenv("DEFAULT_MAX_NEW_TOKENS", 256))
    DEFAULT_TOP_P: float = float(os.getenv("DEFAULT_TOP_P", 0.9))
    DEFAULT_REPETITION_PENALTY: float = float(os.getenv("DEFAULT_REPETITION_PENALTY", 1.05))


generation_config = GenerationConfig()