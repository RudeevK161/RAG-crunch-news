import redis
import json
import os
from typing import Optional, Dict, Any, Union
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))


class RedisClient:
    def __init__(self):
        self.client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True
        )

    def close(self):
        self.client.close()

    def _serialize_value(self, value: Any) -> str:
        """Сериализует значение для сохранения в Redis"""
        if value is None:
            return ""
        if isinstance(value, (str, int, float, bool)):
            return str(value)
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, ensure_ascii=False, default=str)
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    def push_task(self, task_data: Dict[str, Any]) -> str:
        task_id = task_data.get('task_id')
        serialized_data = {}
        for k, v in task_data.items():
            serialized_data[k] = self._serialize_value(v)

        self.client.rpush("tasks:queue", json.dumps(serialized_data))
        logger.info(f"Task {task_id} pushed to queue")
        return task_id

    def pop_task(self) -> Optional[Dict[str, Any]]:
        result = self.client.blpop("tasks:queue", timeout=1)
        if result:
            data = json.loads(result[1])
            for k, v in data.items():
                try:
                    data[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    pass
            return data
        return None

    def set_task_status(self, task_id: str, status: str, **kwargs):
        """
        Сохранить статус задачи
        """
        key = f"task:{task_id}"

        data = {
            "task_id": task_id,
            "status": status,
            "updated_at": datetime.now().isoformat()
        }

        for k, v in kwargs.items():
            data[k] = self._serialize_value(v)

        self.client.hset(key, mapping=data)
        self.client.expire(key, 86400)  # 24 часа

        logger.debug(f"Task {task_id} status set to {status}")

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Получить статус задачи
        """
        data = self.client.hgetall(f"task:{task_id}")
        if not data:
            return None

        result = {}
        for k, v in data.items():
            try:
                result[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                result[k] = v

        return result

    def update_task_progress(self, task_id: str, progress: float, message: str = None, **kwargs):
        """
        Обновить прогресс задачи
        """
        key = f"task:{task_id}"

        updates = {
            "progress": progress,
            "updated_at": datetime.now().isoformat()
        }

        if message:
            updates["message"] = message

        for k, v in kwargs.items():
            updates[k] = self._serialize_value(v)

        self.client.hset(key, mapping=updates)
        logger.debug(f"Task {task_id} progress updated to {progress}")

    def task_exists(self, task_id: str) -> bool:
        """Проверить существует ли задача"""
        return self.client.exists(f"task:{task_id}") > 0

    def delete_task(self, task_id: str):
        """Удалить задачу"""
        self.client.delete(f"task:{task_id}")
        logger.info(f"Task {task_id} deleted")

    def get_all_tasks(self, pattern: str = "task:*") -> Dict[str, Dict[str, Any]]:
        """
        Получить все задачи (для мониторинга)
        """
        tasks = {}
        for key in self.client.scan_iter(match=pattern):
            task_id = key.replace("task:", "")
            tasks[task_id] = self.get_task_status(task_id)
        return tasks


redis_client = RedisClient()