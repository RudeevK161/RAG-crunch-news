from pathlib import Path


BASE_DIR = Path(__file__).parent.parent.parent
PARSER_DATA_DIR = BASE_DIR / "parser_data"

DATA_DIR = PARSER_DATA_DIR / "new_data"
LOGS_DIR = PARSER_DATA_DIR / "parsing_logs"
BACKUPS_DIR = PARSER_DATA_DIR / "backups"

for dir_path in [PARSER_DATA_DIR, DATA_DIR, LOGS_DIR, BACKUPS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)


class ParserConfig:
    """Конфигурация парсера TechCrunch"""

    # Параметры парсинга
    TARGET_ARTICLES = 100
    MAX_PAGES = 20

    # Файлы
    LOCK_FILE = "/tmp/techcrunch_parser.lock"
    CACHE_FILE = DATA_DIR / "article_ids_cache.pkl"

    # Фичи
    SAVE_BACKUP = True
    GENERATE_EMBEDDINGS = True

    # Заголовки
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }


parser_config = ParserConfig()