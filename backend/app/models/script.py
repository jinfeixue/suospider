"""Script model."""
import datetime
from sqlalchemy import Column, BigInteger, String, Text, Integer, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Script(Base):
    __tablename__ = "scripts"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(BigInteger, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    script_type = Column(Enum("crawl", "parse", "full"), default="full")
    code = Column(Text, default="")
    file_path = Column(String(500), default="")
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    task = relationship("Task", back_populates="scripts")
