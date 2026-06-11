"""Task API routes."""
import json
import os
import traceback
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas import TaskCreate, TaskUpdate, TaskOut, ResponseBase, PagedResponse
from app.service.task_service import TaskService
from app.task.manager import task_manager
from app.task.log_bus import log_bus
from app.models import Script
from app.config import settings

router = APIRouter(prefix="/tasks", tags=["Tasks"], dependencies=[Depends(get_current_user)])


@router.get("")
async def list_tasks(
    group: str = None, status: str = None, task_type: str = None,
    page: int = 1, page_size: int = 20,
    db: Session = Depends(get_db),
):
    data = TaskService.list_tasks(db, group=group, status=status, task_type=task_type, page=page, page_size=page_size)
    items = []
    for t_dict in data["items"]:
        t = t_dict
        if "_sa_instance_state" in t:
            del t["_sa_instance_state"]
        for k in ["last_run_at", "created_at", "updated_at"]:
            if t.get(k):
                t[k] = str(t[k])
        # Ensure new fields are present
        if "task_type" not in t:
            t["task_type"] = "professional"
        if "datasource_id" not in t:
            t["datasource_id"] = None
        items.append(t)
    data["items"] = items
    return {"code": 0, "message": "success", "data": data}


@router.post("")
async def create_task(data: TaskCreate, db: Session = Depends(get_db)):
    task = TaskService.create_task(db, data)
    return {"code": 0, "message": "success", "data": {"id": task.id, "name": task.name}}


@router.get("/groups")
async def get_groups(db: Session = Depends(get_db)):
    groups = TaskService.get_groups(db)
    return {"code": 0, "data": groups}


@router.get("/{task_id}")
async def get_task(task_id: int, db: Session = Depends(get_db)):
    task = TaskService.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    t = {k: v for k, v in task.__dict__.items() if not k.startswith("_")}
    for k in ["last_run_at", "created_at", "updated_at"]:
        if t.get(k):
            t[k] = str(t[k])
    # Ensure new fields are present
    if "task_type" not in t:
        t["task_type"] = "professional"
    if "datasource_id" not in t:
        t["datasource_id"] = None
    return {"code": 0, "data": t}


@router.put("/{task_id}")
async def update_task(task_id: int, data: TaskUpdate, db: Session = Depends(get_db)):
    task = TaskService.update_task(db, task_id, data)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"code": 0, "message": "updated"}


@router.delete("/{task_id}")
async def delete_task(task_id: int, db: Session = Depends(get_db)):
    ok = TaskService.delete_task(db, task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"code": 0, "message": "deleted"}


@router.post("/{task_id}/run")
async def run_task(task_id: int, script_type: str = "full", db: Session = Depends(get_db)):
    """Run a task with specified script type (crawl/parse/full)."""
    task = TaskService.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status == "running":
        raise HTTPException(status_code=400, detail="Task already running")

    # Clean up any stale running state
    runs = TaskService.get_runs(db, task_id)
    for run in runs:
        if run.status in ("running", "pending"):
            if not task_manager.is_running(run.id):
                TaskService.finish_run(db, run.id, "failed", "Process not found")
    db.commit()

    # Create a run record
    run = TaskService.create_run(db, task_id, "manual")
    db.commit()

    # Find all scripts for this task
    from sqlalchemy import select
    result = db.execute(
        select(Script).where(Script.task_id == task_id)
    )
    scripts = {s.script_type: s for s in result.scalars().all()}

    if not scripts:
        task.status = "idle"
        db.commit()
        raise HTTPException(status_code=400, detail="No scripts found. Please sync scripts first.")

    # Save all scripts to files
    from app.utils.script_generator import save_script
    task_dir = os.path.join(settings.SCRIPTS_DIR, str(task_id))
    os.makedirs(task_dir, exist_ok=True)
    
    for stype, script in scripts.items():
        save_script(task_id, stype, script.code)

    # Determine which script to run
    if script_type not in scripts:
        script_type = "full"  # Default to full
    
    script_path = os.path.join(task_dir, f"{script_type}_spider.py")

    # Verify script exists
    if not os.path.exists(script_path):
        task.status = "idle"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Script file not found: {script_path}")

    config = task.config_json or {}
    config["engine"] = task.engine

    # Log start attempt
    await log_bus.push_log(run.id, "INFO", f"Starting task {task_id} with {script_type} script...")
    await log_bus.push_log(run.id, "INFO", f"Script: {script_path}")
    await log_bus.push_log(run.id, "INFO", f"Engine: {task.engine}")

    try:
        started = await task_manager.start_task(run.id, task_id, script_path, config)
    except Exception as e:
        error_msg = f"Exception starting task: {str(e)}"
        await log_bus.push_log(run.id, "ERROR", error_msg)
        TaskService.finish_run(db, run.id, "failed", error_msg)
        db.commit()
        task.status = "idle"
        db.commit()
        raise HTTPException(status_code=500, detail=error_msg)

    if not started:
        running_info = task_manager.get_running_info()
        error_msg = f"Cannot start task. Running: {len(running_info)}/{task_manager.max_concurrent}"
        await log_bus.push_log(run.id, "ERROR", error_msg)
        TaskService.finish_run(db, run.id, "failed", error_msg)
        db.commit()
        task.status = "idle"
        db.commit()
        raise HTTPException(status_code=503, detail=error_msg)

    return {"code": 0, "message": "Task started", "data": {"run_id": run.id, "script_type": script_type}}


@router.post("/{task_id}/stop")
async def stop_task(task_id: int, db: Session = Depends(get_db)):
    task = TaskService.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    runs = TaskService.get_runs(db, task_id)
    stopped = False
    for run in runs:
        if run.status in ("running", "pending"):
            await task_manager.stop_task(run.id)
            TaskService.finish_run(db, run.id, "cancelled")
            stopped = True

    task.status = "idle"
    db.commit()

    if stopped:
        return {"code": 0, "message": "Task stopped"}
    return {"code": 0, "message": "Task status reset to idle"}


@router.post("/{task_id}/reset-parse")
async def reset_parseflag(task_id: int, db: Session = Depends(get_db)):
    """重置任务的解析标志，允许重新解析所有记录"""
    task = TaskService.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    import pymysql
    from app.config import settings

    config = task.config_json or {}
    spider_name = config.get("spider_name", "")

    if not spider_name:
        raise HTTPException(status_code=400, detail="No spider_name found in task config")

    try:
        conn = pymysql.connect(
            host=config.get("db_host", settings.DB_HOST),
            port=config.get("db_port", settings.DB_PORT),
            user=config.get("db_user", settings.DB_USER),
            password=config.get("db_password", settings.DB_PASSWORD),
            database=config.get("db_name", settings.DB_NAME),
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        db_table = config.get("db_table", "crawler_feachdata")
        cursor.execute(
            f"UPDATE `{db_table}` SET parseflag = 0 WHERE spider_name = %s",
            (spider_name,)
        )
        updated = cursor.rowcount
        conn.commit()
        conn.close()
        return {"code": 0, "message": f"已重置 {updated} 条记录的解析标志"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置失败: {str(e)}")


@router.get("/{task_id}/runs")
async def get_runs(task_id: int, db: Session = Depends(get_db)):
    runs = TaskService.get_runs(db, task_id)
    items = []
    for r in runs:
        items.append({
            "id": r.id, "task_id": r.task_id, "trigger": r.trigger,
            "status": r.status, "pid": r.pid,
            "started_at": str(r.started_at) if r.started_at else None,
            "finished_at": str(r.finished_at) if r.finished_at else None,
            "duration_seconds": r.duration_seconds,
            "error_message": r.error_message,
            "result_summary": r.result_summary,
        })
    return {"code": 0, "data": items}


@router.post("/cleanup")
async def cleanup_tasks(db: Session = Depends(get_db)):
    """Force cleanup all running tasks."""
    await task_manager.force_cleanup()
    from sqlalchemy import update
    from app.models import Task
    db.execute(update(Task).where(Task.status == "running").values(status="idle"))
    db.commit()
    return {"code": 0, "message": "All tasks cleaned up"}
