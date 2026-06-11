"""requests-based crawler engine (sync wrapped in async)."""
import asyncio
import requests
from app.engine import BaseCrawlerEngine, EngineConfig, RawResponse


class RequestsEngine(BaseCrawlerEngine):
    name = "requests"

    def __init__(self):
        self._session: requests.Session | None = None

    def _ensure_session(self, config: EngineConfig):
        if self._session is None:
            self._session = requests.Session()
            self._session.verify = config.verify_ssl

    async def fetch(self, config: EngineConfig) -> RawResponse:
        self._ensure_session(config)
        headers = {**config.headers}
        proxies = {"http": config.proxy, "https": config.proxy} if config.proxy else {}

        def _do_request():
            for attempt in range(config.max_retries):
                try:
                    resp = self._session.request(
                        method=config.method,
                        url=config.url,
                        headers=headers,
                        cookies=config.cookies,
                        timeout=config.timeout,
                        proxies=proxies,
                        allow_redirects=config.follow_redirects,
                    )
                    
                    # Fix encoding issue
                    # Try to detect encoding from content
                    if resp.encoding and resp.encoding.lower() in ('iso-8859-1', 'latin-1', 'ascii'):
                        # Try to detect from content-type header or meta tag
                        content_type = resp.headers.get('content-type', '').lower()
                        if 'charset=' in content_type:
                            charset = content_type.split('charset=')[-1].strip().split(';')[0].strip()
                            resp.encoding = charset
                        elif b'charset=utf-8' in resp.content[:1000].lower():
                            resp.encoding = 'utf-8'
                        elif b'charset=gbk' in resp.content[:1000].lower() or b'charset=gb2312' in resp.content[:1000].lower():
                            resp.encoding = 'gbk'
                        elif b'charset=gb18030' in resp.content[:1000].lower():
                            resp.encoding = 'gb18030'
                        else:
                            # Default to utf-8 for Chinese sites
                            resp.encoding = resp.apparent_encoding or 'utf-8'
                    
                    return RawResponse(
                        url=resp.url,
                        status_code=resp.status_code,
                        headers=dict(resp.headers),
                        text=resp.text,
                        content=resp.content,
                        encoding=resp.encoding,
                        elapsed=resp.elapsed.total_seconds(),
                    )
                except Exception as e:
                    if attempt == config.max_retries - 1:
                        return RawResponse(
                            url=config.url,
                            status_code=0,
                            headers={},
                            text="",
                            content=b"",
                            error=str(e),
                        )

        return await asyncio.to_thread(_do_request)

    async def close(self):
        if self._session:
            self._session.close()
            self._session = None
