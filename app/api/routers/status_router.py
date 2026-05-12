from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from app.tasks.redis_client import redis_client
from app.api.schemas.task import TaskStatus

router = APIRouter()


@router.get("/metrics")
async def get_metrics():
    try:
        metrics = redis_client.client.hgetall("rag_metrics")

        total_requests = int(metrics.get("total_requests", 0))
        total_latency = float(metrics.get("total_latency", 0))

        avg_latency = total_latency / total_requests if total_requests else 0

        return {
            "total_requests": total_requests,
            "avg_latency": round(avg_latency, 3),
            "cache_hits": int(metrics.get("cache_hits", 0)),
            "cache_misses": int(metrics.get("cache_misses", 0)),
            "cache_hit_rate": round(
                int(metrics.get("cache_hits", 0)) / total_requests, 3
            ) if total_requests else 0
        }

    except Exception as e:
        return {"error": str(e)}


@router.get("/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """Получить статус задачи по ID"""
    status = redis_client.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return TaskStatus(**status)


@router.get("/", response_model=List[TaskStatus])
async def list_tasks(limit: int = Query(100, le=1000), status_filter: Optional[str] = Query(None)):
    tasks = []
    keys = redis_client.client.keys("task:*")

    for key in keys[:limit]:
        task_data = redis_client.client.hgetall(key)
        task_id = key.replace("task:", "")

        task_data['task_id'] = task_id
        if 'status' not in task_data:
            task_data['status'] = 'pending'

        if status_filter and task_data.get('status') != status_filter:
            continue

        tasks.append(TaskStatus(**task_data))

    return tasks


@router.get("/queue/stats")
async def get_queue_stats():
    """Статистика очереди"""
    queue_length = redis_client.client.llen("tasks:queue")

    keys = redis_client.client.keys("task:*")
    status_counts = {}
    for key in keys:
        status = redis_client.client.hget(key, "status")
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "queue_length": queue_length,
        "status_counts": status_counts,
        "total_tasks": len(keys)
    }