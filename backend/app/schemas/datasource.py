"""Pydantic schemas for DataSource API."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DataSourceCreate(BaseModel):
    """创建数据源请求"""
    name: str = Field(..., description="数据源名称")
    host: str = Field(..., description="数据库主机")
    port: int = Field(3306, description="端口号")
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")
    database_name: Optional[str] = Field(None, description="数据库名（可选）")
    charset: str = Field("utf8mb4", description="字符集")


class DataSourceUpdate(BaseModel):
    """更新数据源请求"""
    name: Optional[str] = Field(None, description="数据源名称")
    host: Optional[str] = Field(None, description="数据库主机")
    port: Optional[int] = Field(None, description="端口号")
    username: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码")
    database_name: Optional[str] = Field(None, description="数据库名")
    charset: Optional[str] = Field(None, description="字符集")
    is_active: Optional[bool] = Field(None, description="是否启用")


class DataSourceResponse(BaseModel):
    """数据源响应"""
    id: int
    name: str
    host: str
    port: int
    username: str
    database_name: Optional[str]
    charset: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DataSourceTestResult(BaseModel):
    """数据源测试结果"""
    success: bool
    message: str
    response_time: Optional[float] = None
