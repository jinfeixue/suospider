"""curlcffi-based engine (placeholder - requires pip install curl_cffi)."""
from app.engine import BaseCrawlerEngine, EngineConfig, RawResponse


class CurlCffiEngine(BaseCrawlerEngine):
    name = "curlcffi"

    async def fetch(self, config: EngineConfig) -> RawResponse:
        from curl_cffi.requests import AsyncSession
        async with AsyncSession(impersonate="chrome") as s:
            resp = await s.request(
                method=config.method,
                url=config.url,
                headers=config.headers,
                cookies=config.cookies,
                proxies={"https": config.proxy, "http": config.proxy} if config.proxy else None,
                timeout=config.timeout,
                verify=config.verify_ssl,
            )
            return RawResponse(
                url=str(resp.url), status_code=resp.status_code,
                headers=dict(resp.headers), text=resp.text,
                content=resp.content, encoding=resp.encoding or "utf-8",
            )

    async def close(self):
        pass
