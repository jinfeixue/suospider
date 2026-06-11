"""Database connection and session management."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from sqlalchemy import create_engine
from app.config import settings
import asyncio

# 同步引擎（用于 alembic 和实际操作）
sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
)

# 异步引擎（保留用于需要的场景）
try:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
    )
    USE_ASYNC = True
except Exception:
    engine = None
    USE_ASYNC = False

async_session_factory = None
if engine:
    async_session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )


class Base(DeclarativeBase):
    pass


async def get_db():
    """获取数据库会话 - 使用同步 Session（Windows 上 aiomysql 不稳定）"""
    SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)
    db = SyncSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Create all tables."""
    # 导入所有模型以注册到Base.metadata
    from app.models import User, Task, Script, TaskRun, RunLog, Schedule, Group, DataSource, LLMConfig
    Base.metadata.create_all(sync_engine)


def get_sync_session():
    """获取同步数据库会话（用于同步操作）"""
    SessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)
    return SessionLocal()
