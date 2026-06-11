"""Pydantic schemas for LLMConfig API."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class LLMConfigCreate(BaseModel):
    """创建大模型配置请求"""
    name: str = Field(..., description="配置名称")
    provider: str = Field(..., description="提供商：openai/anthropic/aliyun/custom")
    model: str = Field(..., description="模型名称")
    api_key: str = Field(..., description="API密钥")
    api_url: Optional[str] = Field(None, description="API地址")
    temperature: str = Field("0.1", description="温度参数")
    max_tokens: int = Field(4000, description="最大token数")
    timeout: int = Field(30, description="超时时间（秒）")


class LLMConfigUpdate(BaseModel):
    """更新大模型配置请求"""
    name: Optional[str] = Field(None, description="配置名称")
    provider: Optional[str] = Field(None, description="提供商")
    model: Optional[str] = Field(None, description="模型名称")
    api_key: Optional[str] = Field(None, description="API密钥")
    api_url: Optional[str] = Field(None, description="API地址")
    temperature: Optional[str] = Field(None, description="温度参数")
    max_tokens: Optional[int] = Field(None, description="最大token数")
    timeout: Optional[int] = Field(None, description="超时时间（秒）")
    is_default: Optional[bool] = Field(None, description="是否默认配置")
    is_active: Optional[bool] = Field(None, description="是否启用")


class LLMConfigResponse(BaseModel):
    """大模型配置响应"""
    id: int
    name: str
    provider: str
    model: str
    api_url: Optional[str]
    temperature: str
    max_tokens: int
    timeout: int
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LLMTestResult(BaseModel):
    """大模型测试结果"""
    success: bool
    message: str
    response_time: Optional[float] = None
