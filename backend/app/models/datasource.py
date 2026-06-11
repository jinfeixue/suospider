"""DataSource model for managing database connections."""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from app.core.database import Base


class DataSource(Base):
    """数据源配置模型"""
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="数据源名称")
    host = Column(String(100), nullable=False, comment="数据库主机")
    port = Column(Integer, default=3306, comment="端口号")
    username = Column(String(50), nullable=False, comment="用户名")
    password = Column(Text, nullable=False, comment="密码（加密存储）")
    database_name = Column(String(100), comment="数据库名（可选）")
    charset = Column(String(20), default="utf8mb4", comment="字符集")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<DataSource(id={self.id}, name='{self.name}', host='{self.host}')>"
