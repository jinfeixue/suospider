"""Playwright-based engine for JS-rendered pages (requires pip install playwright)."""
from app.engine import BaseCrawlerEngine, EngineConfig, RawResponse


class PlaywrightEngine(BaseCrawlerEngine):
    name = "playwright"

    def __init__(self):
        self._pw = None
        self._browser = None

    async def _ensure(self):
        if not self._pw:
            from playwright.async_api import async_playwright
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(headless=True)

    async def fetch(self, config: EngineConfig) -> RawResponse:
        await self._ensure()
        page = await self._browser.new_page()
        try:
            if config.headers:
                await page.set_extra_http_headers(config.headers)
            resp = await page.goto(config.url, timeout=config.timeout * 1000, wait_until="networkidle")
            content = await page.content()
            return RawResponse(
                url=page.url, status_code=resp.status if resp else 200,
                headers={}, text=content, content=content.encode("utf-8"),
            )
        except Exception as e:
            return RawResponse(url=config.url, status_code=0, headers={}, text="", content=b"", error=str(e))
        finally:
            await page.close()

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
