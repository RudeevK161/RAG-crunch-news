import os
from dotenv import load_dotenv

load_dotenv()


class GenerationConfig:
    """Конфигурация генерационного модуля"""

    # Параметры для семантического кэширования запросов
    SEM_COLLECTION_NAME: str = "semantic_cache"
    SEM_MODEL_NAME: str = "all-MiniLM-L6-v2"
    SEM_VECTOR_SIZE: int = 384

    # Тип использования модели генерации "local" - загружаем модель локально, "api" - используем API
    MODE: str = os.getenv("MODE", "api")

    # API настройки
    API_BASE_URL: str = "https://routerai.ru/api/v1"
    API_KEY: str = os.getenv("API_KEY", "your-api-key-here")
    API_MODEL: str = "qwen/qwen-2.5-7b-instruct"

    # Локальные настройки (используются только при MODE="local")
    LLM_MODEL: str = "Qwen/Qwen2.5-3B-Instruct"
    MAX_CONTEXT_TOKEN: int = 512

    # Общие параметры генерации
    DEFAULT_TEMPERATURE: float = 0.5
    DEFAULT_MAX_NEW_TOKENS: int = 256
    DEFAULT_TOP_P: float = 0.9
    DEFAULT_REPETITION_PENALTY: float = 1.05


generation_config = GenerationConfig()