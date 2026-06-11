"""Engine detector for automatically selecting the best crawler engine."""
import asyncio
from typing import Dict, Optional


class EngineDetector:
    """引擎检测器：自动检测最佳爬虫引擎"""

    # 引擎优先级列表（从简单到复杂）
    ENGINE_PRIORITY = [
        "requests",           # 静态网页首选
        "httpx",              # HTTP/2支持
        "curlcffi",           # 高防网站，JA3/TP 指纹模拟
        "playwright",         # 动态JS渲染、浏览器模拟
        "drission",           # 混合模式，一键切换动静
        "scrapling"           # 轻量级爬虫引擎
    ]

    def __init__(self):
        self.engines = {}
        self._load_engines()

    def _load_engines(self):
        """加载所有引擎"""
        try:
            from app.engine.requests_engine import RequestsEngine
            self.engines["requests"] = RequestsEngine
        except:
            pass

        try:
            from app.engine.httpx_engine import HttpxEngine
            self.engines["httpx"] = HttpxEngine
        except:
            pass

        try:
            from app.engine.playwright_engine import PlaywrightEngine
            self.engines["playwright"] = PlaywrightEngine
        except:
            pass

        try:
            from app.engine.drission_engine import DrissionEngine
            self.engines["drission"] = DrissionEngine
        except:
            pass

        try:
            from app.engine.curlcffi_engine import CurlCffiEngine
            self.engines["curlcffi"] = CurlCffiEngine
        except:
            pass

        try:
            from app.engine.scrapling_engine import ScraplingEngine
            self.engines["scrapling"] = ScraplingEngine
        except:
            pass

    async def detect_best_engine(self, url: str) -> Dict:
        """
        检测最佳引擎
        从简单到复杂依次尝试，返回第一个能获取源代码的引擎
        """
        for engine_name in self.ENGINE_PRIORITY:
            try:
                result = await self._test_engine(engine_name, url)
                if result["success"]:
                    return {
                        "engine": engine_name,
                        "confidence": result["confidence"],
                        "html_length": result["html_length"]
                    }
            except Exception as e:
                continue

        # 默认返回requests
        return {"engine": "requests", "confidence": 50, "html_length": 0}

    async def _test_engine(self, engine_name: str, url: str) -> Dict:
        """测试单个引擎"""
        try:
            if engine_name == "requests":
                import requests
                response = requests.get(url, timeout=10, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                })
                if response.status_code == 200:
                    return {
                        "success": True,
                        "confidence": 90,
                        "html_length": len(response.text)
                    }
            elif engine_name == "httpx":
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, timeout=10)
                    if response.status_code == 200:
                        return {
                            "success": True,
                            "confidence": 85,
                            "html_length": len(response.text)
                        }
            elif engine_name == "playwright":
                from playwright.async_api import async_playwright
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    await page.goto(url, wait_until='networkidle', timeout=15000)
                    content = await page.content()
                    await browser.close()
                    return {
                        "success": True,
                        "confidence": 95,
                        "html_length": len(content)
                    }
        except Exception as e:
            pass

        return {"success": False, "confidence": 0, "html_length": 0}

    def get_engine_recommendation(self, html_content: str) -> str:
        """
        根据HTML内容推荐引擎
        - 检测是否有JavaScript渲染
        - 检测是否有反爬措施
        - 返回推荐的引擎名称
        """
        # 检测JS渲染
        if self._detect_js_rendering(html_content):
            return "playwright"

        # 检测高防网站
        if self._detect_high_protection(html_content):
            return "curlcffi"

        # 默认使用requests
        return "requests"

    def _detect_js_rendering(self, html: str) -> bool:
        """检测是否需要JS渲染"""
        js_indicators = [
            "<noscript>",
            "window.__INITIAL_STATE__",
            "document.createElement",
            "React.createElement",
            "Vue.prototype",
            "__NEXT_DATA__",
            "__NUXT__"
        ]
        return any(indicator in html for indicator in js_indicators)

    def _detect_high_protection(self, html: str) -> bool:
        """检测是否有高防措施"""
        protection_indicators = [
            "Cloudflare",
            "Akamai",
            "WAF",
            "captcha",
            "verify",
            "challenge",
            "security"
        ]
        return any(indicator.lower() in html.lower() for indicator in protection_indicators)
