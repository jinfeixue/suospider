"""httpx-based crawler engine (async, HTTP/2 support)."""
import httpx
from app.engine import BaseCrawlerEngine, EngineConfig, RawResponse


class HttpxEngine(BaseCrawlerEngine):
    name = "httpx"

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self, config: EngineConfig):
        if self._client is None:
            proxies = config.proxy if config.proxy else None
            self._client = httpx.AsyncClient(
                verify=config.verify_ssl,
                follow_redirects=config.follow_redirects,
                timeout=httpx.Timeout(config.timeout),
                proxies=proxies,
                http2=True,
            )

    async def fetch(self, config: EngineConfig) -> RawResponse:
        await self._ensure_client(config)
        headers = {**config.headers}
        cookies = config.cookies or {}

        for attempt in range(config.max_retries):
            try:
                resp = await self._client.request(
                    method=config.method,
                    url=config.url,
                    headers=headers,
                    cookies=cookies,
                )
                
                # Fix encoding
                encoding = resp.encoding
                if encoding and encoding.lower() in ('iso-8859-1', 'latin-1', 'ascii'):
                    content_type = resp.headers.get('content-type', '').lower()
                    if 'charset=' in content_type:
                        charset = content_type.split('charset=')[-1].strip().split(';')[0].strip()
                        encoding = charset
                    elif b'charset=utf-8' in resp.content[:1000].lower():
                        encoding = 'utf-8'
                    elif b'charset=gbk' in resp.content[:1000].lower() or b'charset=gb2312' in resp.content[:1000].lower():
                        encoding = 'gbk'
                    elif b'charset=gb18030' in resp.content[:1000].lower():
                        encoding = 'gb18030'
                    else:
                        encoding = 'utf-8'
                
                return RawResponse(
                    url=str(resp.url),
                    status_code=resp.status_code,
                    headers=dict(resp.headers),
                    text=resp.content.decode(encoding or 'utf-8', errors='replace'),
                    content=resp.content,
                    encoding=encoding,
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

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
