"""Schedule model - task scheduling configuration."""
import datetime
from sqlalchemy import Column, BigInteger, String, Integer, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Schedule(Base):
    __tablename__ = "schedules"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    trigger_type = Column(Enum("cron", "interval", "once"), default="interval")
    cron_expr = Column(String(100), nullable=True)
    interval_seconds = Column(Integer, nullable=True)
    run_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    task = relationship("Task", back_populates="schedules")
