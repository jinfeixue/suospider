"""Log service - log querying and management."""
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models import RunLog, TaskRun


class LogService:

    @staticmethod
    def get_logs(db: Session, run_id: int = None, level: str = None,
                       keyword: str = None, page: int = 1, page_size: int = 100) -> dict:
        query = select(RunLog)
        count_query = select(func.count(RunLog.id))

        if run_id:
            query = query.where(RunLog.run_id == run_id)
            count_query = count_query.where(RunLog.run_id == run_id)
        if level:
            query = query.where(RunLog.level == level)
            count_query = count_query.where(RunLog.level == level)
        if keyword:
            query = query.where(RunLog.message.contains(keyword))
            count_query = count_query.where(RunLog.message.contains(keyword))

        total = (db.execute(count_query)).scalar() or 0
        query = query.order_by(RunLog.timestamp.desc()).offset((page - 1) * page_size).limit(page_size)
        result = db.execute(query)
        logs = result.scalars().all()

        return {
            "items": [
                {"id": l.id, "run_id": l.run_id, "level": l.level,
                 "message": l.message, "timestamp": str(l.timestamp) if l.timestamp else None}
                for l in logs
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    def add_log(db: Session, run_id: int, level: str, message: str):
        log_entry = RunLog(run_id=run_id, level=level, message=message)
        db.add(log_entry)

    @staticmethod
    def get_all_logs(db: Session, task_id: int = None, page: int = 1, page_size: int = 50) -> dict:
        """Get logs across all runs, optionally filtered by task."""
        query = select(RunLog)
        count_query = select(func.count(RunLog.id))

        if task_id:
            query = query.join(TaskRun, RunLog.run_id == TaskRun.id).where(TaskRun.task_id == task_id)
            count_query = count_query.join(TaskRun, RunLog.run_id == TaskRun.id).where(TaskRun.task_id == task_id)

        total = (db.execute(count_query)).scalar() or 0
        query = query.order_by(RunLog.timestamp.desc()).offset((page - 1) * page_size).limit(page_size)
        result = db.execute(query)
        logs = result.scalars().all()

        return {
            "items": [
                {"id": l.id, "run_id": l.run_id, "level": l.level,
                 "message": l.message, "timestamp": str(l.timestamp) if l.timestamp else None}
                for l in logs
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
