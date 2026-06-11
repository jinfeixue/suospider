"""LLMConfig model for managing LLM API configurations."""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from app.core.database import Base


class LLMConfig(Base):
    """大模型配置模型"""
    __tablename__ = "llm_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="配置名称")
    provider = Column(String(50), nullable=False, comment="提供商：openai/anthropic/aliyun/custom")
    model = Column(String(100), nullable=False, comment="模型名称")
    api_key = Column(Text, nullable=False, comment="API密钥（加密存储）")
    api_url = Column(String(500), comment="API地址")
    temperature = Column(String(10), default="0.1", comment="温度参数")
    max_tokens = Column(Integer, default=4000, comment="最大token数")
    timeout = Column(Integer, default=30, comment="超时时间（秒）")
    is_default = Column(Boolean, default=False, comment="是否默认配置")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<LLMConfig(id={self.id}, name='{self.name}', provider='{self.provider}')>"
