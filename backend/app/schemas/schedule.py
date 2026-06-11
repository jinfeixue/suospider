"""Schedule-related Pydantic schemas."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ScheduleCreate(BaseModel):
    trigger_type: str = "interval"
    cron_expr: Optional[str] = None
    interval_seconds: Optional[int] = None
    run_at: Optional[datetime] = None
    is_active: bool = True


class ScheduleUpdate(BaseModel):
    trigger_type: Optional[str] = None
    cron_expr: Optional[str] = None
    interval_seconds: Optional[int] = None
    run_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class ScheduleOut(BaseModel):
    id: int
    task_id: int
    trigger_type: str
    cron_expr: Optional[str] = None
    interval_seconds: Optional[int] = None
    run_at: Optional[datetime] = None
    is_active: bool
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
