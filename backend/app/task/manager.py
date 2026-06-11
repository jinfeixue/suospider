"""TaskManager - manages crawler task execution in subprocesses."""
import asyncio
import os
import sys
import json
import uuid
import datetime
from typing import Dict, Optional
from dataclasses import dataclass, field

from app.config import settings
from app.task.log_bus import log_bus


@dataclass
class RunningTask:
    run_id: int
    task_id: int
    process: object  # subprocess.Popen or asyncio.subprocess.Process
    started_at: datetime.datetime = field(default_factory=datetime.datetime.utcnow)


class TaskManager:
    """Manages concurrent crawler task execution."""

    def __init__(self, max_concurrent: int = None):
        self.max_concurrent = max_concurrent or settings.MAX_CONCURRENT_TASKS
        self._running: Dict[int, RunningTask] = {}  # run_id -> RunningTask
        self._lock = asyncio.Lock()

    @property
    def running_count(self) -> int:
        return len(self._running)

    def is_running(self, run_id: int) -> bool:
        return run_id in self._running

    def get_running_task_ids(self) -> list:
        """Get list of currently running task IDs."""
        return [rt.task_id for rt in self._running.values()]

    async def start_task(self, run_id: int, task_id: int, script_path: str, config_json: dict = None) -> bool:
        """Start a task in a subprocess."""
        print(f"[TaskManager] start_task called: run_id={run_id}, task_id={task_id}")
        print(f"[TaskManager] script_path={script_path}")
        print(f"[TaskManager] running_count={self.running_count}, max_concurrent={self.max_concurrent}")
        
        async with self._lock:
            if self.running_count >= self.max_concurrent:
                print(f"[TaskManager] REJECTED: max concurrent reached ({self.running_count}/{self.max_concurrent})")
                return False
            if run_id in self._running:
                print(f"[TaskManager] REJECTED: run_id {run_id} already running")
                return False

        env = os.environ.copy()
        env["SPIDER_RUN_ID"] = str(run_id)
        env["SPIDER_TASK_ID"] = str(task_id)
        env["SPIDER_CONFIG"] = json.dumps(config_json or {})
        env["PYTHONPATH"] = settings.BASE_DIR
        env["PYTHONUNBUFFERED"] = "1"  # Disable Python output buffering for real-time logs
        env["PYTHONIOENCODING"] = "utf-8"  # Force UTF-8 encoding for subprocess output
        
        # Pass database config from task config
        if config_json:
            env["SPIDER_DB_HOST"] = config_json.get("db_host", "localhost")
            env["SPIDER_DB_PORT"] = str(config_json.get("db_port", 3306))
            env["SPIDER_DB_NAME"] = config_json.get("db_name", "")
            env["SPIDER_DB_TABLE"] = config_json.get("db_table", "crawler_feachdata")
            env["SPIDER_DB_USER"] = config_json.get("db_user", settings.DB_USER)
            env["SPIDER_DB_PASSWORD"] = config_json.get("db_password", settings.DB_PASSWORD)

        # App database for LLM configs
        env["SPIDER_APP_DB_HOST"] = settings.DB_HOST
        env["SPIDER_APP_DB_PORT"] = str(settings.DB_PORT)
        env["SPIDER_APP_DB_NAME"] = settings.DB_NAME
        env["SPIDER_APP_DB_USER"] = settings.DB_USER
        env["SPIDER_APP_DB_PASSWORD"] = settings.DB_PASSWORD

        try:
            # Check if script exists
            if not os.path.exists(script_path):
                print(f"[TaskManager] ERROR: Script not found: {script_path}")
                await log_bus.push_log(run_id, "ERROR", f"Script not found: {script_path}")
                return False

            print(f"[TaskManager] Starting subprocess: {sys.executable} {script_path}")

            # Windows兼容：使用subprocess.Popen + PIPE
            import subprocess
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                cwd=settings.BASE_DIR,
                bufsize=1,
                text=True,
                encoding='utf-8',
                errors='replace',
            )

            print(f"[TaskManager] Process started: PID={process.pid}")

            running = RunningTask(run_id=run_id, task_id=task_id, process=process)
            async with self._lock:
                self._running[run_id] = running

            # Start log reader in background
            asyncio.create_task(self._read_output(run_id, task_id, process))

            await log_bus.push_log(run_id, "INFO", f"Task {task_id} started (PID: {process.pid})")
            return True
        except Exception as e:
            print(f"[TaskManager] EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            await log_bus.push_log(run_id, "ERROR", f"Failed to start task: {e}")
            # Clean up on failure
            async with self._lock:
                self._running.pop(run_id, None)
            return False

    async def _read_output(self, run_id: int, task_id: int, process):
        """Read subprocess stdout and push to LogBus."""
        try:
            # 使用线程池读取同步管道
            loop = asyncio.get_event_loop()
            while True:
                line = await loop.run_in_executor(None, process.stdout.readline)
                if not line:
                    break
                text = line.rstrip() if isinstance(line, str) else line.decode("utf-8", errors="replace").rstrip()
                if text:
                    print(f"[Task {run_id}] {text}")
                    # Determine log level from prefix
                    level = "INFO"
                    if "[ERROR]" in text or "Error" in text or "Traceback" in text:
                        level = "ERROR"
                    elif "[WARN]" in text or "Warning" in text:
                        level = "WARNING"
                    elif "[DEBUG]" in text:
                        level = "DEBUG"
                    await log_bus.push_log(run_id, level, text)
        except Exception as e:
            print(f"[Task {run_id}] Log reader error: {e}")
            await log_bus.push_log(run_id, "ERROR", f"Log reader error: {e}")
        finally:
            # Process finished
            try:
                returncode = await process.wait()
            except Exception:
                returncode = -1
            
            print(f"[Task {run_id}] Process finished with exit code {returncode}")
            
            # Clean up running task
            async with self._lock:
                self._running.pop(run_id, None)
            
            status = "success" if returncode == 0 else "failed"
            await log_bus.push_log(run_id, "INFO", f"Task finished with exit code {returncode}")
            await log_bus.push_status(run_id, status)
            
            # Update database status
            await self._update_task_status(run_id, task_id, status)

    async def _update_task_status(self, run_id: int, task_id: int, status: str):
        """Update task and run status in database."""
        from app.core.database import get_sync_session
        try:
            from app.models import Task, TaskRun
            from sqlalchemy import select
            db = get_sync_session()
            try:
                # Update task status
                result = db.execute(select(Task).where(Task.id == task_id))
                task = result.scalar_one_or_none()
                if task:
                    task.status = "idle"
                    task.last_run_at = datetime.datetime.utcnow()

                # Update run status
                result = db.execute(select(TaskRun).where(TaskRun.id == run_id))
                run = result.scalar_one_or_none()
                if run:
                    run.status = status
                    run.finished_at = datetime.datetime.utcnow()
                    if run.started_at:
                        run.duration_seconds = (run.finished_at - run.started_at).total_seconds()

                db.commit()
                print(f"[TaskManager] Updated task {task_id} status to idle, run {run_id} status to {status}")
            finally:
                db.close()
        except Exception as e:
            print(f"[TaskManager] Failed to update task status: {e}")

    async def stop_task(self, run_id: int) -> bool:
        """Stop a running task."""
        async with self._lock:
            running = self._running.get(run_id)
            if not running:
                return False
            try:
                running.process.terminate()
                try:
                    await asyncio.wait_for(running.process.wait(), timeout=10)
                except asyncio.TimeoutError:
                    running.process.kill()
                    await running.process.wait()
            except ProcessLookupError:
                pass  # Process already exited
            except Exception as e:
                await log_bus.push_log(run_id, "ERROR", f"Stop error: {e}")
            finally:
                self._running.pop(run_id, None)
        
        await log_bus.push_log(run_id, "WARNING", "Task stopped by user")
        await log_bus.push_status(run_id, "cancelled")
        return True

    async def force_cleanup(self):
        """Force cleanup all running tasks (for debugging)."""
        print(f"[TaskManager] force_cleanup called, clearing {len(self._running)} tasks")
        async with self._lock:
            for run_id, running in list(self._running.items()):
                try:
                    running.process.kill()
                except Exception:
                    pass
            self._running.clear()

    def get_running_info(self) -> list:
        """Get info about running tasks."""
        result = []
        for run_id, rt in self._running.items():
            result.append({
                "run_id": run_id,
                "task_id": rt.task_id,
                "pid": rt.process.pid,
                "started_at": rt.started_at.isoformat(),
            })
        return result


# Singleton
task_manager = TaskManager()
