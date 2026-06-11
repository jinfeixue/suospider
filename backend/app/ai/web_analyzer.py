"""Web analyzer for analyzing page structure and extracting information."""
from lxml import html as lxml_html
from urllib.parse import urljoin, urlparse
import re
from typing import Dict, List, Optional


class WebAnalyzer:
    """网页分析器"""
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    async def analyze(self, url: str, html_content: str = None, engine: str = "requests") -> Dict:
        """
        分析网页结构
        
        Args:
            url: 目标URL
            html_content: HTML内容（如果提供则直接分析，否则使用引擎获取）
            engine: 使用的引擎
            
        Returns:
            分析结果字典
        """
        # 如果未提供HTML内容，使用引擎获取
        if not html_content:
            html_content = await self._fetch_html(url, engine)
        
        if not html_content:
            return {"error": "无法获取网页内容"}
        
        # 分析HTML
        try:
            tree = lxml_html.fromstring(html_content)
        except Exception as e:
            return {"error": f"HTML解析失败: {str(e)}"}
        
        # 检测页面类型
        page_type = self._detect_page_type(tree, url)
        
        # 提取链接
        links = self._extract_links(tree, url)
        
        # 检测翻页
        pagination = self._detect_pagination(tree, url)
        
        # 提取标题
        title = self._extract_title(tree)
        
        return {
            "url": url,
            "html": html_content[:10000],  # 限制返回的HTML长度
            "page_type": page_type,
            "links": links[:100],  # 限制数量
            "pagination": pagination,
            "title": title,
            "engine": engine
        }

    async def _fetch_html(self, url: str, engine: str) -> Optional[str]:
        """使用指定引擎获取HTML"""
        try:
            if engine == "requests":
                import requests
                response = requests.get(url, headers=self.headers, timeout=30)
                response.encoding = 'utf-8'
                return response.text
            elif engine == "httpx":
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, headers=self.headers, timeout=30)
                    return response.text
            elif engine == "Playwright":
                from playwright.async_api import async_playwright
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    await page.goto(url, wait_until='networkidle', timeout=30000)
                    content = await page.content()
                    await browser.close()
                    return content
            else:
                # 默认使用requests
                import requests
                response = requests.get(url, headers=self.headers, timeout=30)
                response.encoding = 'utf-8'
                return response.text
        except Exception as e:
            print(f"获取HTML失败: {e}")
            return None

    def _detect_page_type(self, tree, url: str) -> str:
        """检测页面类型：list/detail"""
        # 检测是否为列表页（包含多个链接）
        links = tree.xpath("//a[@href]")
        if len(links) > 10:
            return "list"
        return "detail"

    def _extract_links(self, tree, base_url: str) -> List[str]:
        """提取所有链接"""
        links = []
        for elem in tree.xpath("//a[@href]"):
            href = elem.get("href")
            if href and not href.startswith("#") and not href.startswith("javascript:"):
                full_url = urljoin(base_url, href)
                links.append(full_url)
        return list(set(links))

    def _detect_pagination(self, tree, url: str) -> Optional[Dict]:
        """检测翻页方式"""
        # 检测"下一页"按钮
        next_selectors = [
            "//a[contains(text(), '下一页')]",
            "//a[contains(text(), 'Next')]",
            "//a[contains(@class, 'next')]",
            "//li[contains(@class, 'next')]/a",
            "//a[contains(@rel, 'next')]"
        ]
        
        for selector in next_selectors:
            elements = tree.xpath(selector)
            if elements:
                return {
                    "type": "button",
                    "xpath": selector,
                    "url": elements[0].get("href")
                }
        
        # 检测页码规律
        page_pattern = self._detect_page_pattern(url)
        if page_pattern:
            return {
                "type": "page_number",
                "pattern": page_pattern
            }
        
        return None

    def _detect_page_pattern(self, url: str) -> Optional[str]:
        """检测URL中的页码规律"""
        patterns = [
            (r'/page/(\d+)', '/page/{page_num}'),
            (r'[?&]page=(\d+)', '?page={page_num}'),
            (r'_p(\d+)\.html', '_p{page_num}.html'),
            (r'index_(\d+)\.html', 'index_{page_num}.html'),
            (r'/p(\d+)/', '/p{page_num}/')
        ]
        
        for pattern, template in patterns:
            if re.search(pattern, url):
                return template
        return None

    def _extract_title(self, tree) -> str:
        """提取页面标题"""
        title = tree.xpath("//title/text()")
        return title[0].strip() if title else ""
