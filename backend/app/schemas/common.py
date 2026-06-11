"""Common response schemas."""
from pydantic import BaseModel
from typing import Any
from enum import Enum


class TaskStatus(str, Enum):
    idle = "idle"
    running = "running"
    paused = "paused"
    error = "error"


class EngineType(str, Enum):
    httpx = "httpx"
    requests = "requests"
    curlcffi = "curlcffi"
    urllib3 = "urllib3"
    playwright = "playwright"
    drission = "drission"


class ScriptType(str, Enum):
    crawl = "crawl"
    parse = "parse"
    full = "full"


class ResponseBase(BaseModel):
    code: int = 0
    message: str = "success"
    data: Any = None


class PagedResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: dict = {}


class ExportRequest(BaseModel):
    format: str = "json"  # json or excel
