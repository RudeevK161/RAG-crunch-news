import portalocker
from contextlib import contextmanager
from pathlib import Path
from .logger import logger
from .config import config


@contextmanager
def file_lock(lock_file: str = None):
    """
    Контекстный менеджер для блокировки

    Использование:
        with file_lock():
            # ваш код
    """
    if lock_file is None:
        lock_file = config.LOCK_FILE

    # Создаем директорию если её нет
    Path(lock_file).parent.mkdir(parents=True, exist_ok=True)

    lock_fd = open(lock_file, 'w')
    try:
        # Пытаемся получить блокировку
        portalocker.lock(lock_fd, portalocker.LOCK_EX | portalocker.LOCK_NB)
        logger.info(f"Блокировка получена: {lock_file}")
        yield lock_fd
    except portalocker.exceptions.LockException:
        logger.warning(f"Парсер уже запущен (блокировка {lock_file} активна)")
        raise RuntimeError("Parser already running")
    except Exception as e:
        logger.error(f"Ошибка блокировки: {e}")
        raise
    finally:
        try:
            portalocker.unlock(lock_fd)
            lock_fd.close()
            Path(lock_file).unlink(missing_ok=True)
            logger.info("Блокировка снята")
        except Exception as e:
            logger.error(f"Ошибка снятия блокировки: {e}")


def is_running(lock_file: str = None) -> bool:
    """Проверяет, запущен ли парсер"""
    try:
        with file_lock(lock_file):
            return False
    except RuntimeError:
        return True