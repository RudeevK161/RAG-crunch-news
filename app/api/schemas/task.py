from pydantic import BaseModel
from typing import Optional, Any, Dict


class TaskCreate(BaseModel):
    task_type: str
    collection_name: str
    data: Dict[str, Any]
    priority: int = 5


class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


class TaskStatus(BaseModel):
    task_id: str
    status: str
    task_type: Optional[str] = None
    collection_name: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: float = 0
    message: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None