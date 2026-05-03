import logging
from logging.handlers import RotatingFileHandler
from .config import LOGS_DIR


def setup_logger(name: str = "techcrunch_parser") -> logging.Logger:
    """Настройка логгера с ротацией файлов"""

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Хендлер для файла (с ротацией)
    log_file = LOGS_DIR / "parser.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Хендлер для консоли
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


logger = setup_logger()