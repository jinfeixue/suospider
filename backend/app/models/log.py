"""RunLog model - log entries for task runs."""
import datetime
from sqlalchemy import Column, BigInteger, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class RunLog(Base):
    __tablename__ = "run_logs"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(BigInteger, ForeignKey("task_runs.id", ondelete="CASCADE"), nullable=False)
    level = Column(String(20), default="INFO")
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    run = relationship("TaskRun", back_populates="logs")
