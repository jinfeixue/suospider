"""TaskRun and Log Pydantic schemas."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TaskRunOut(BaseModel):
    id: int
    task_id: int
    trigger: str
    status: str
    pid: Optional[int] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    result_summary: Optional[dict] = None

    model_config = {"from_attributes": True}


class LogOut(BaseModel):
    id: int
    run_id: int
    level: str
    message: str
    timestamp: Optional[datetime] = None

    model_config = {"from_attributes": True}
