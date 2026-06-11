"""Script-related Pydantic schemas."""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ScriptUpdate(BaseModel):
    code: str


class ScriptOut(BaseModel):
    id: int
    task_id: int
    script_type: str
    code: str
    file_path: str
    version: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
