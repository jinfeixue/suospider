"""Base crawler engine abstract class."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import time


@dataclass
class EngineConfig:
    """Unified engine configuration."""
    url: str = ""
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    proxy: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    verify_ssl: bool = True
    follow_redirects: bool = True
    encoding: Optional[str] = None


@dataclass
class RawResponse:
    """Unified raw response from any engine."""
    url: str
    status_code: int
    headers: Dict[str, str]
    text: str
    content: bytes
    encoding: str = "utf-8"
    elapsed: float = 0.0
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status_code < 400


class BaseCrawlerEngine(ABC):
    """Abstract base class for all crawler engines."""

    name: str = "base"

    @abstractmethod
    async def fetch(self, config: EngineConfig) -> RawResponse:
        """Fetch a URL and return raw response."""
        pass

    @abstractmethod
    async def close(self):
        """Clean up resources."""
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
