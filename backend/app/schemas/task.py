"""Task-related Pydantic schemas."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class TaskCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    task_type: str = Field("professional", description="任务类型：smart/professional")
    group_name: str = "默认分组"
    engine: str = "requests"
    config_json: dict = {}
    datasource_id: Optional[int] = Field(None, description="关联数据源ID")


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    group_name: Optional[str] = None
    engine: Optional[str] = None
    config_json: Optional[dict] = None
    datasource_id: Optional[int] = None


class TaskOut(BaseModel):
    id: int
    name: str
    description: str
    task_type: str
    group_name: str
    engine: str
    config_json: dict
    datasource_id: Optional[int] = None
    status: str
    total_crawled: int
    total_parsed: int
    last_run_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
