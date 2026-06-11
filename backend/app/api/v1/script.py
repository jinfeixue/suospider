"""Script API routes."""
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas import ScriptUpdate, ScriptOut
from app.models import Script, Task
from app.task.sandbox import validate_script
from app.utils.script_generator import save_script, generate_crawl_script, generate_parse_script, generate_full_script

router = APIRouter(prefix="/tasks/{task_id}/scripts", tags=["Scripts"], dependencies=[Depends(get_current_user)])


@router.get("")
def get_scripts(task_id: int, db: Session = Depends(get_db)):
    result = db.execute(select(Script).where(Script.task_id == task_id))
    scripts = result.scalars().all()
    items = [
        {"id": s.id, "task_id": s.task_id, "script_type": s.script_type,
         "code": s.code, "file_path": s.file_path, "version": s.version,
         "created_at": str(s.created_at) if s.created_at else None}
        for s in scripts
    ]
    return {"code": 0, "data": items}


@router.get("/{script_type}")
def get_script(task_id: int, script_type: str, db: Session = Depends(get_db)):
    result = db.execute(
        select(Script).where(Script.task_id == task_id, Script.script_type == script_type)
    )
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return {"code": 0, "data": {
        "id": script.id, "task_id": script.task_id, "script_type": script.script_type,
        "code": script.code, "file_path": script.file_path, "version": script.version,
    }}


@router.put("/{script_type}")
def update_script(task_id: int, script_type: str, data: ScriptUpdate, db: Session = Depends(get_db)):
    # Validate syntax
    valid, msg = validate_script(data.code)
    if not valid:
        raise HTTPException(status_code=400, detail=f"Script validation failed: {msg}")

    result = db.execute(
        select(Script).where(Script.task_id == task_id, Script.script_type == script_type)
    )
    script = result.scalar_one_or_none()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    script.code = data.code
    script.version += 1
    script.file_path = save_script(task_id, script_type, data.code)

    return {"code": 0, "message": "Script updated", "data": {"version": script.version}}


@router.post("/{script_type}/regenerate")
def regenerate_script(task_id: int, script_type: str, db: Session = Depends(get_db)):
    """Regenerate a script from the task's visual config."""
    result = db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    config = task.config_json or {}
    config["engine"] = task.engine

    generators = {
        "crawl": generate_crawl_script,
        "parse": generate_parse_script,
        "full": generate_full_script,
    }
    gen_func = generators.get(script_type)
    if not gen_func:
        raise HTTPException(status_code=400, detail="Invalid script type")

    code = gen_func(task_id, config)
    filepath = save_script(task_id, script_type, code)

    # Update or create
    sr = db.execute(select(Script).where(Script.task_id == task_id, Script.script_type == script_type))
    script = sr.scalar_one_or_none()
    if script:
        script.code = code
        script.file_path = filepath
        script.version += 1
    else:
        db.add(Script(task_id=task_id, script_type=script_type, code=code, file_path=filepath))

    return {"code": 0, "message": "Script regenerated"}


# Standalone script validation endpoint
validate_router = APIRouter(prefix="/scripts", tags=["Scripts"], dependencies=[Depends(get_current_user)])


@validate_router.post("/validate")
def validate_code(data: ScriptUpdate):
    valid, msg = validate_script(data.code)
    return {"code": 0, "data": {"valid": valid, "message": msg}}
