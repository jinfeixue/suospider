"""Schedule API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Schedule
from app.schemas import ScheduleCreate

router = APIRouter(tags=["Schedules"], dependencies=[Depends(get_current_user)])


@router.get("/tasks/{task_id}/schedules")
def get_schedules(task_id: int, db: Session = Depends(get_db)):
    result = db.execute(select(Schedule).where(Schedule.task_id == task_id))
    schedules = result.scalars().all()
    items = [
        {"id": s.id, "task_id": s.task_id, "trigger_type": s.trigger_type,
         "cron_expr": s.cron_expr, "interval_seconds": s.interval_seconds,
         "is_active": s.is_active, "last_run_at": str(s.last_run_at) if s.last_run_at else None,
         "created_at": str(s.created_at) if s.created_at else None}
        for s in schedules
    ]
    return {"code": 0, "data": items}


@router.post("/tasks/{task_id}/schedules")
def create_schedule(task_id: int, data: ScheduleCreate, db: Session = Depends(get_db)):
    schedule = Schedule(
        task_id=task_id,
        trigger_type=data.trigger_type,
        cron_expr=data.cron_expr,
        interval_seconds=data.interval_seconds,
        run_at=data.run_at,
        is_active=data.is_active,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return {"code": 0, "data": {"id": schedule.id}}


@router.delete("/schedules/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    result = db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    db.delete(schedule)
    return {"code": 0, "message": "deleted"}


@router.post("/schedules/{schedule_id}/toggle")
def toggle_schedule(schedule_id: int, db: Session = Depends(get_db)):
    result = db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    schedule.is_active = not schedule.is_active
    return {"code": 0, "data": {"is_active": schedule.is_active}}
