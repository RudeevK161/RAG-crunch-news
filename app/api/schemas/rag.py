from pydantic import BaseModel, Field
from typing import Optional


class QuestionRequest(BaseModel):
    question: str = Field(..., description="Вопрос пользователя", min_length=1, max_length=1000)
    style: str = Field(default="concise", description="Стиль ответа: detailed, concise, comprehensive")


class AnswerResponse(BaseModel):
    task_id: str
    status: str
    question: str
    answer: Optional[str] = None
    error: Optional[str] = None
    progress: Optional[float] = None
    completed_at: Optional[str] = None