"""DrissionPage-based engine (requires pip install DrissionPage)."""
import asyncio
from app.engine import BaseCrawlerEngine, EngineConfig, RawResponse


class DrissionEngine(BaseCrawlerEngine):
    name = "drission"

    async def fetch(self, config: EngineConfig) -> RawResponse:
        def _do():
            try:
                from DrissionPage import SessionPage
                page = SessionPage()
                page.get(config.url)
                return RawResponse(
                    url=page.url, status_code=200,
                    headers={}, text=page.html, content=page.html.encode("utf-8"),
                )
            except Exception as e:
                return RawResponse(url=config.url, status_code=0, headers={}, text="", content=b"", error=str(e))

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _do)

    async def close(self):
        pass
