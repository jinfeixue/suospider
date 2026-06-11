"""scrapling-based crawler engine (requires pip install scrapling)."""
from app.engine import BaseCrawlerEngine, EngineConfig, RawResponse


class ScraplingEngine(BaseCrawlerEngine):
    name = "scrapling"

    async def fetch(self, config: EngineConfig) -> RawResponse:
        try:
            from scrapling import Fetcher
            fetcher = Fetcher()
            response = fetcher.get(
                config.url,
                headers=config.headers,
                timeout=config.timeout,
            )
            return RawResponse(
                url=config.url,
                status_code=response.status,
                headers=dict(response.headers) if hasattr(response, 'headers') else {},
                text=response.text,
                content=response.content if hasattr(response, 'content') else response.text.encode('utf-8'),
                encoding='utf-8',
            )
        except ImportError:
            return RawResponse(
                url=config.url, status_code=0, headers={}, text="", content=b"",
                error="scrapling not installed. Run: pip install scrapling"
            )
        except Exception as e:
            return RawResponse(
                url=config.url, status_code=0, headers={}, text="", content=b"",
                error=str(e)
            )

    async def close(self):
        pass
