"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.core.database import init_db, get_sync_session
from app.service.user_service import UserService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    print(f"[Spider Manager] Initializing database...")
    init_db()

    # Create default admin user
    db = get_sync_session()
    try:
        UserService.init_default_admin_sync(db)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Spider Manager] Admin user init warning: {e}")
    finally:
        db.close()

    # Reset all running tasks to idle on startup
    db = get_sync_session()
    try:
        from sqlalchemy import update
        from app.models import Task, TaskRun
        db.execute(update(Task).where(Task.status == "running").values(status="idle"))
        db.execute(update(TaskRun).where(TaskRun.status.in_(["running", "pending"])).values(status="failed", error_message="Server restarted"))
        db.commit()
        print("[Spider Manager] Reset all running tasks to idle")
    except Exception as e:
        print(f"[Spider Manager] Task reset warning: {e}")
    finally:
        db.close()

    print(f"[Spider Manager] {settings.APP_NAME} v{settings.APP_VERSION} started")
    print(f"[Spider Manager] API docs: http://localhost:8000/docs")
    yield
    # Shutdown
    print("[Spider Manager] Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS
cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")] if settings.CORS_ORIGINS else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
from app.api.v1.task import router as task_router
from app.api.v1.script import router as script_router, validate_router
from app.api.v1.log import router as log_router
from app.api.v1.data import router as data_router
from app.api.v1.auth import router as auth_router
from app.api.v1.schedule import router as schedule_router
from app.api.v1.engine import router as engine_router
from app.api.v1.group import router as group_router
from app.api.v1.datasource import router as datasource_router
from app.api.v1.llm_config import router as llm_config_router
from app.api.v1.ai_analysis import router as ai_analysis_router
from app.api.ws.log_stream import router as ws_router

app.include_router(task_router, prefix="/api/v1")
app.include_router(script_router, prefix="/api/v1")
app.include_router(validate_router, prefix="/api/v1")
app.include_router(log_router, prefix="/api/v1")
app.include_router(data_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(schedule_router, prefix="/api/v1")
app.include_router(engine_router, prefix="/api/v1")
app.include_router(group_router, prefix="/api/v1")
app.include_router(datasource_router, prefix="/api/v1")
app.include_router(llm_config_router, prefix="/api/v1")
app.include_router(ai_analysis_router, prefix="/api/v1")
app.include_router(ws_router)

# 挂载temp目录为静态文件，用于HTML源码查看
import os as _os
_temp_dir = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "data", "temp")
_os.makedirs(_temp_dir, exist_ok=True)
app.mount("/temp", StaticFiles(directory=_temp_dir), name="temp_files")


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "status": "running",
    }


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
