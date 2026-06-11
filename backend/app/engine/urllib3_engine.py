"""urllib3-based engine (sync wrapped in async)."""
import asyncio
import urllib3
from app.engine import BaseCrawlerEngine, EngineConfig, RawResponse


class Urllib3Engine(BaseCrawlerEngine):
    name = "urllib3"

    async def fetch(self, config: EngineConfig) -> RawResponse:
        def _do():
            pm = urllib3.ProxyManager(config.proxy) if config.proxy else urllib3.PoolManager()
            try:
                resp = pm.request(
                    config.method, config.url,
                    headers=config.headers,
                    timeout=config.timeout,
                    retries=config.max_retries,
                )
                return RawResponse(
                    url=config.url, status_code=resp.status,
                    headers=dict(resp.headers), text=resp.data.decode("utf-8", errors="replace"),
                    content=resp.data,
                )
            except Exception as e:
                return RawResponse(url=config.url, status_code=0, headers={}, text="", content=b"", error=str(e))

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _do)

    async def close(self):
        pass
