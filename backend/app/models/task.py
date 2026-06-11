"""Task model."""
import datetime
from sqlalchemy import Column, BigInteger, String, Text, Integer, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class Task(Base):
    __tablename__ = "tasks"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    task_type = Column(Enum("smart", "professional"), default="professional", comment="任务类型：smart=智能采集，professional=专业采集")
    group_name = Column(String(100), default="默认分组")
    engine = Column(String(30), default="requests")
    config_json = Column(JSON, default=dict)
    datasource_id = Column(Integer, ForeignKey("data_sources.id"), nullable=True, comment="关联数据源ID")
    status = Column(Enum("idle", "running", "paused", "error"), default="idle")
    total_crawled = Column(Integer, default=0)
    total_parsed = Column(Integer, default=0)
    last_run_at = Column(DateTime, nullable=True)
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    creator = relationship("User", back_populates="tasks")
    scripts = relationship("Script", back_populates="task", cascade="all, delete-orphan")
    runs = relationship("TaskRun", back_populates="task", cascade="all, delete-orphan")
    schedules = relationship("Schedule", back_populates="task", cascade="all, delete-orphan")
