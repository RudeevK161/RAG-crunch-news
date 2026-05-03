from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import time
from .main import Pipeline
from .lock import file_lock
from .logger import logger


def run_pipeline():
    try:
        with file_lock():
            logger.info("Запуск парсинга...")
            Pipeline().run()
            logger.info("Парсинг завершен")
    except RuntimeError:
        logger.info("Парсер уже запущен")


if __name__ == "__main__":
    scheduler = BackgroundScheduler()

    scheduler.add_job(
        run_pipeline,
        trigger=CronTrigger(day='*/5', hour=3, minute=0),
        id="techcrunch_parser"
    )

    scheduler.start()
    logger.info("Планировщик запущен. Расписание: каждые 5 дней в 03:00")

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.shutdown()
        logger.info("Остановлен")