from fastapi import APIRouter, HTTPException
from datetime import datetime
import logging

from app.tasks.tasks import generate_answer_task
from app.tasks.redis_client import redis_client
from app.api.schemas.task import TaskResponse
from app.api.schemas.rag import QuestionRequest, AnswerResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/ask", response_model=TaskResponse)
async def ask_question(request: QuestionRequest):
    """
    Задать вопрос и получить task_id для отслеживания
    """
    task = generate_answer_task.delay(
        question=request.question,
        style=request.style
    )

    return TaskResponse(
        task_id=task.id,
        status="processing",
        message="Задача поставлена в очередь"
    )


@router.get("/status/{task_id}", response_model=AnswerResponse)
async def get_answer_status(task_id: str):
    """
    Получить статус и результат выполнения задачи
    """
    task_status = redis_client.get_task_status(task_id)

    if not task_status:
        raise HTTPException(status_code=404, detail="Task not found")

    response = AnswerResponse(
        task_id=task_id,
        status=task_status.get("status", "unknown"),
        question=task_status.get("question", ""),
        answer=None,
        error=None,
        progress=task_status.get("progress"),
        completed_at=task_status.get("completed_at")
    )

    if task_status.get("status") == "completed":
        result = task_status.get("result", {})
        response.answer = result.get("answer") if isinstance(result, dict) else str(result)

    elif task_status.get("status") == "failed":
        response.error = task_status.get("error", "Unknown error")

    return response


@router.get("/result/{task_id}")
async def get_answer_result(task_id: str):
    """
    Синхронное ожидание результата (блокирующий вызов)
    """
    from celery.result import AsyncResult
    from app.tasks.tasks import celery_app

    task = AsyncResult(task_id, app=celery_app)

    try:
        result = task.get(timeout=60)
        return result
    except Exception as e:
        raise HTTPException(status_code=408, detail=f"Timeout or error: {str(e)}")


@router.delete("/task/{task_id}")
async def cancel_task(task_id: str):
    """
    Отмена задачи
    """
    from celery.result import AsyncResult
    from app.tasks.tasks import celery_app

    task = AsyncResult(task_id, app=celery_app)

    if task.state in ["PENDING", "STARTED"]:
        task.revoke(terminate=True)
        redis_client.set_task_status(
            task_id=task_id,
            status="cancelled",
            error="Task cancelled by user",
            failed_at=datetime.now().isoformat()
        )
        return {"message": "Task cancelled", "task_id": task_id}

    return {"message": f"Task cannot be cancelled in state: {task.state}", "task_id": task_id}