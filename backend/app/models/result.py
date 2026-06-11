"""TaskRun model - represents a single execution of a task."""
import datetime
from sqlalchemy import Column, BigInteger, String, Text, Integer, DateTime, Enum, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from app.core.database import Base


class TaskRun(Base):
    __tablename__ = "task_runs"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    trigger = Column(Enum("manual", "schedule", "api"), default="manual")
    status = Column(Enum("pending", "running", "success", "failed", "timeout", "cancelled"), default="pending")
    pid = Column(Integer, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    result_summary = Column(JSON, nullable=True)

    task = relationship("Task", back_populates="runs")
    logs = relationship("RunLog", back_populates="run", cascade="all, delete-orphan")
