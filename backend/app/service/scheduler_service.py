"""Scheduler service - manages APScheduler for task scheduling."""
import datetime
import logging
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

from app.config import settings

logger = logging.getLogger(__name__)


class SchedulerService:
    """Manages scheduled task execution using APScheduler."""

    def __init__(self):
        self._scheduler: Optional[AsyncIOScheduler] = None

    async def start(self):
        """Start the scheduler."""
        if not settings.SCHEDULER_ENABLED:
            logger.info("Scheduler is disabled")
            return

        self._scheduler = AsyncIOScheduler()
        self._scheduler.start()
        logger.info("Scheduler started")

    async def stop(self):
        """Stop the scheduler."""
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    async def add_schedule(self, schedule_id: int, task_id: int, trigger_type: str,
                           cron_expr: str = None, interval_seconds: int = None,
                           run_at: datetime.datetime = None):
        """Add a scheduled job."""
        if not self._scheduler:
            return

        job_id = f"task_{task_id}_schedule_{schedule_id}"

        # Remove existing job if any
        existing = self._scheduler.get_job(job_id)
        if existing:
            existing.remove()

        if trigger_type == "cron" and cron_expr:
            trigger = CronTrigger.from_crontab(cron_expr)
        elif trigger_type == "interval" and interval_seconds:
            trigger = IntervalTrigger(seconds=interval_seconds)
        elif trigger_type == "once" and run_at:
            trigger = DateTrigger(run_date=run_at)
        else:
            logger.warning(f"Invalid schedule config for {job_id}")
            return

        self._scheduler.add_job(
            self._execute_scheduled_task,
            trigger=trigger,
            id=job_id,
            args=[task_id, schedule_id],
            replace_existing=True,
        )
        logger.info(f"Added schedule {job_id}: {trigger_type}")

    async def remove_schedule(self, schedule_id: int, task_id: int):
        """Remove a scheduled job."""
        if not self._scheduler:
            return
        job_id = f"task_{task_id}_schedule_{schedule_id}"
        job = self._scheduler.get_job(job_id)
        if job:
            job.remove()
            logger.info(f"Removed schedule {job_id}")

    async def _execute_scheduled_task(self, task_id: int, schedule_id: int):
        """Execute a task triggered by the scheduler."""
        logger.info(f"Executing scheduled task {task_id} (schedule {schedule_id})")
        import os
        from app.core.database import get_sync_session
        from app.service.task_service import TaskService
        from sqlalchemy import select
        from app.models import Schedule, Script
        from app.task.manager import task_manager

        db = get_sync_session()
        try:
            # Create a run record
            run = TaskService.create_run(db, task_id, "schedule")
            db.commit()

            # Update schedule last_run_at
            result = db.execute(select(Schedule).where(Schedule.id == schedule_id))
            schedule = result.scalar_one_or_none()
            if schedule:
                schedule.last_run_at = datetime.datetime.utcnow()
                db.commit()

            # Find the script to execute
            script_result = db.execute(
                select(Script).where(Script.task_id == task_id, Script.script_type == "full")
            )
            script = script_result.scalar_one_or_none()

            if script:
                # Save script to file and get config
                from app.utils.script_generator import save_script
                save_script(task_id, "full", script.code)

                # Get task config
                task = TaskService.get_task(db, task_id)
                config = task.config_json or {}
                config["engine"] = task.engine

                script_path = os.path.join(settings.SCRIPTS_DIR, str(task_id), "full_spider.py")
                started = await task_manager.start_task(run.id, task_id, script_path, config)
                if started:
                    logger.info(f"Scheduled task {task_id} started as run {run.id}")
                else:
                    logger.warning(f"Scheduled task {task_id} could not start (max concurrent reached)")
            else:
                logger.warning(f"No full script found for task {task_id}")
        except Exception as e:
            logger.error(f"Failed to execute scheduled task {task_id}: {e}")
            db.rollback()
        finally:
            db.close()

    def get_jobs(self) -> list:
        """Get all scheduled jobs."""
        if not self._scheduler:
            return []
        return [
            {
                "id": job.id,
                "next_run_time": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger),
            }
            for job in self._scheduler.get_jobs()
        ]


# Singleton
scheduler_service = SchedulerService()
