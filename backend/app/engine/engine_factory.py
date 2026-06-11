"""Engine factory - creates engine instances by name."""
from typing import Dict, Type
from app.engine import BaseCrawlerEngine
from app.engine.httpx_engine import HttpxEngine
from app.engine.requests_engine import RequestsEngine

_ENGINE_MAP: Dict[str, Type[BaseCrawlerEngine]] = {
    "httpx": HttpxEngine,
    "requests": RequestsEngine,
}

# Register optional engines if available
try:
    from app.engine.urllib3_engine import Urllib3Engine
    _ENGINE_MAP["urllib3"] = Urllib3Engine
except ImportError:
    pass

try:
    from app.engine.playwright_engine import PlaywrightEngine
    _ENGINE_MAP["playwright"] = PlaywrightEngine
except ImportError:
    pass

try:
    from app.engine.drission_engine import DrissionEngine
    _ENGINE_MAP["drission"] = DrissionEngine
except ImportError:
    pass

try:
    from app.engine.curlcffi_engine import CurlCffiEngine
    _ENGINE_MAP["curlcffi"] = CurlCffiEngine
    _ENGINE_MAP["requests-curlcffi"] = CurlCffiEngine  # alias
except ImportError:
    pass

try:
    from app.engine.scrapling_engine import ScraplingEngine
    _ENGINE_MAP["scrapling"] = ScraplingEngine
except ImportError:
    pass


def get_engine(name: str) -> BaseCrawlerEngine:
    """Get a crawler engine instance by name."""
    engine_cls = _ENGINE_MAP.get(name)
    if engine_cls is None:
        available = ", ".join(_ENGINE_MAP.keys())
        raise ValueError(f"Unknown engine '{name}'. Available: {available}")
    return engine_cls()


def list_engines() -> list:
    """List all available engine names."""
    return list(_ENGINE_MAP.keys())


def get_engine_descriptions() -> Dict[str, str]:
    """Get engine descriptions for UI display."""
    return {
        "requests": "静态网页首选，简单高效",
        "httpx": "同步/异步，HTTP/2 支持",
        "curlcffi": "高防网站，JA3/TP 指纹模拟",
        "requests-curlcffi": "高防网站，JA3/TP 指纹模拟（别名）",
        "playwright": "动态 JS 渲染，浏览器模拟",
        "drission": "混合模式，一键切换动静",
        "scrapling": "轻量级爬虫引擎",
        "urllib3": "底层 HTTP 客户端",
    }
