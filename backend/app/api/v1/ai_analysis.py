"""AI Analysis API - 两步分析：列表页识别链接+翻页，详情页识别字段."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict
from lxml import html as lxml_html
from urllib.parse import urljoin, urlparse
import json
import re
import httpx
import os
import datetime

from app.core.database import get_db
from app.models.llm_config import LLMConfig
from app.models.datasource import DataSource
from app.models.crawl_rule import CrawlRule
from app.service.llm_service import LLMService
from app.config import settings

router = APIRouter(prefix="/ai", tags=["AI分析"])


def get_domain_from_url(url: str) -> str:
    """从URL提取域名"""
    parsed = urlparse(url)
    return parsed.netloc or parsed.hostname or ""


def get_cached_rule(db: Session, domain: str) -> Optional[dict]:
    """获取缓存的采集规则"""
    rule = db.query(CrawlRule).filter(
        CrawlRule.domain == domain,
        CrawlRule.is_active == True
    ).first()

    if rule:
        # 更新使用统计
        rule.use_count += 1
        rule.last_used_at = datetime.datetime.utcnow()
        db.commit()

        return {
            "detail_link_xpath": rule.detail_link_xpath,
            "pagination_type": rule.pagination_type,
            "pagination_xpath": rule.pagination_xpath,
            "pagination_pattern": rule.pagination_pattern,
            "field_xpaths": rule.field_xpaths or {},
            "recommended_engine": rule.recommended_engine,
        }
    return None


def save_rule(db: Session, domain: str, url: str, xpath_data: dict, fields: dict = None):
    """保存采集规则到数据库"""
    existing = db.query(CrawlRule).filter(CrawlRule.domain == domain).first()

    if existing:
        # 更新现有规则
        for key, value in xpath_data.items():
            if value:
                setattr(existing, key, value)
        if fields:
            existing.field_xpaths = fields
        existing.updated_at = datetime.datetime.utcnow()
    else:
        # 创建新规则
        rule = CrawlRule(
            domain=domain,
            url_pattern=url,
            detail_link_xpath=xpath_data.get("detail_link_xpath"),
            pagination_type=xpath_data.get("pagination_type"),
            pagination_xpath=xpath_data.get("pagination_xpath"),
            pagination_pattern=xpath_data.get("pagination_pattern"),
            field_xpaths=fields or {},
            recommended_engine=xpath_data.get("recommended_engine", "requests"),
        )
        db.add(rule)

    db.commit()


def update_rule_success(db: Session, domain: str, success: bool):
    """更新规则成功/失败统计"""
    rule = db.query(CrawlRule).filter(CrawlRule.domain == domain).first()
    if rule:
        if success:
            rule.success_count += 1
            rule.last_success_at = datetime.datetime.utcnow()
        db.commit()


def merge_xpath(old_xpath: str, new_xpath: str) -> str:
    """合并两个XPath，用|连接"""
    if not old_xpath:
        return new_xpath
    if not new_xpath:
        return old_xpath
    if old_xpath == new_xpath:
        return old_xpath
    return f"{old_xpath} | {new_xpath}"


def clean_html_for_llm(raw_html: str, max_length: int = None) -> str:
    """清洗HTML - 不做截断，保留完整内容"""
    try:
        tree = lxml_html.fromstring(raw_html)
        for tag in tree.xpath("//script | //style | //noscript | //svg | //iframe"):
            parent = tag.getparent()
            if parent is not None:
                parent.remove(tag)
        for comment in tree.xpath("//comment()"):
            parent = comment.getparent()
            if parent is not None:
                parent.remove(comment)
        cleaned = lxml_html.tostring(tree, encoding="unicode", pretty_print=False)
        # 不做截断
        return cleaned
    except:
        return raw_html


# 列表页分析 Prompt
LIST_ANALYZE_PROMPT = """分析这个网页的HTML源码，找出文章详情页链接的XPath和翻页方式。

## 翻页方式判断（按优先级）：

1. **next_button**：页面有"下一页"链接，a标签的href指向下一页URL（非javascript:开头）
2. **url_pattern**：页面有数字页码链接（2,3,4,5...），href中包含页码规律。常见格式：
   - index_2.html, index_3.html（数字递增）
   - /page/2/, /page/3/（路径中带页码）
   - ?page=2, ?p=3（查询参数带页码）
   - list_2.html, list_3.html
   只要看到多个数字页码的a标签，就是url_pattern类型！
3. **js_click**：页码按钮通过JavaScript翻页，有以下特征：
   - href="javascript:void(0)" 或 href="javascript:;" 或 href="#"
   - 有 onclick="goPage(2)" 等JS函数调用
   - 有 paged="2" 等自定义属性存储页码
   - 有 data-page-number="2" 等data属性存储页码
   - 有 data-page="2" 等data属性存储页码
   只要看到href是javascript:或#开头的页码链接，就是js_click类型！
4. **null**：确实没有任何翻页元素

## 返回格式（严格只输出JSON，不要其他文字）：
{{
  "detail_link_xpath": "提取文章详情页链接href的XPath",
  "pagination_type": "next_button或url_pattern或js_click或null",
  "pagination_xpath": "页码容器或下一页按钮的XPath",
  "pagination_pattern": "URL翻页规律模板，如 index_{{page}}.html 或 /page/{{page}}/",
  "page_count": 0
}}

## 重要提示：
- 重点看HTML中是否有 class="page"、class="pagination"、class="pager" 等分页容器
- 分页容器内的 <a href="index_2.html">2</a> 就是url_pattern类型
- pagination_pattern中用 {{page}} 表示页码位置，如 index_{{page}}.html
- page_count填总页数（从页码数字中找最大的）

HTML源码（前30000字符）：
{html_content}"""

# 详情页分析 Prompt
DETAIL_ANALYZE_PROMPT = """你是XPath专家。分析详情页HTML，找出每个字段的XPath。

重要规则：
1. 先找到标题（h1标签），正文content一定在标题后面的div中
2. content必须用 //text() 结尾
3. content不要选标题上面的div（可能是CSS样式）
4. 如果有多个同名class的div，选择在标题之后的那个
5. 所有文本字段必须用 /text() 或 //text() 结尾

输出JSON格式：
{{
  "title": "标题XPath/text()",
  "content": "正文XPath//text()",
  "chubanriqi": "发布日期XPath/text()",
  "zuozhe": "作者XPath/text()",
  "keyword": "关键词XPath/text()",
  "kanming": "来源XPath/text()"
}}

HTML：
{html_content}"""


class AnalyzeRequest(BaseModel):
    url: str
    engine: Optional[str] = "requests"
    llm_config_id: Optional[int] = None


class SmartCreateRequest(BaseModel):
    url: str
    task_name: Optional[str] = None
    max_pages: int = 5
    request_interval: int = 2
    datasource_id: int
    fields: Optional[dict] = None  # 前端用户配置的字段 {name: xpath}
    llm_config_id: Optional[int] = None


def _get_llm_service(db: Session, llm_config_id: Optional[int] = None) -> LLMService:
    if llm_config_id:
        llm_config = db.query(LLMConfig).filter(LLMConfig.id == llm_config_id).first()
        if not llm_config:
            raise HTTPException(status_code=404, detail="指定的大模型配置不存在")
    else:
        llm_config = db.query(LLMConfig).filter(LLMConfig.is_default == True).first()
        if not llm_config:
            raise HTTPException(status_code=400, detail="未配置默认大模型，请先配置")
    return LLMService(
        provider=llm_config.provider, model=llm_config.model,
        api_key=llm_config.api_key, api_url=llm_config.api_url,
        timeout=llm_config.timeout
    )


async def _fetch_html(url: str, engine: str = "requests") -> str:
    """获取网页HTML - 六级降级，engine="playwright"跳过前三级"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    skip_to_playwright = (engine == "playwright")

    if not skip_to_playwright:
        # 第一级：requests
        try:
            import requests as req
            resp = req.get(url, headers=headers, timeout=30, allow_redirects=True)
            encoding = None
            ct = resp.headers.get('content-type', '')
            if 'charset=' in ct:
                encoding = ct.split('charset=')[-1].strip()
            if not encoding or encoding.lower() in ('iso-8859-1', 'latin-1', 'ascii'):
                try:
                    resp.content.decode('utf-8')
                    encoding = 'utf-8'
                except:
                    encoding = resp.apparent_encoding or 'utf-8'
            resp.encoding = encoding
            html = resp.text
            if len(html) > 1000 and '<html' in html.lower():
                print(f"[AI] requests获取成功，长度: {len(html)}")
                return html
        except Exception as e:
            print(f"[AI] requests失败: {e}")

        # 第二级：curlcffi
        try:
            from curl_cffi.requests import AsyncSession
            async with AsyncSession(impersonate="chrome") as s:
                resp = await s.get(url, headers=headers, timeout=30)
                html = resp.text
                if len(html) > 1000 and '<html' in html.lower():
                    print(f"[AI] curlcffi获取成功，长度: {len(html)}")
                    return html
        except Exception as e:
            print(f"[AI] curlcffi失败: {e}")

        # 第三级：httpx
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True, http2=True) as client:
                resp = await client.get(url, headers=headers)
                html = resp.text
                if len(html) > 1000 and '<html' in html.lower():
                    print(f"[AI] httpx获取成功，长度: {len(html)}")
                    return html
        except Exception as e:
            print(f"[AI] httpx失败: {e}")

    # 第四级：playwright
    try:
        print(f"[AI] 使用playwright获取")
        playwright_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", r"C:\hermes\cpython-3.12.13\python312\playwright")
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            launch_args = {"headless": True}
            if playwright_path:
                for root, dirs, files in os.walk(playwright_path):
                    for f in files:
                        if f in ["chrome.exe", "chromium.exe", "chrome-headless-shell.exe"]:
                            launch_args["executable_path"] = os.path.join(root, f)
                            break
                    if "executable_path" in launch_args:
                        break
            browser = await p.chromium.launch(**launch_args)
            page = await browser.new_page()
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(3000)
            content = await page.content()
            await browser.close()
            if len(content) > 1000:
                print(f"[AI] playwright获取成功，长度: {len(content)}")
                return content
    except Exception as e:
        print(f"[AI] playwright失败: {e}")

    # 第五级：drission
    try:
        from DrissionPage import SessionPage
        page = SessionPage()
        page.get(url)
        html = page.html
        if len(html) > 1000:
            print(f"[AI] drission获取成功，长度: {len(html)}")
            return html
    except Exception as e:
        print(f"[AI] drission失败: {e}")

    print("[AI] 所有引擎都获取失败")
    return ""


def _parse_llm_result(result: str) -> dict:
    """解析LLM返回的JSON"""
    try:
        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"[AI] JSON解析失败: {e}")
    return {}


def _detect_pagination_from_html(html: str, base_url: str) -> dict:
    """从HTML中自动检测翻页方式 - 当LLM未识别时的后处理"""
    import re
    from urllib.parse import urljoin
    tree = lxml_html.fromstring(html)

    # 1. 检测"下一页"按钮（非JS的）
    next_xpaths = [
        '//a[contains(text(),"下一页")]/@href',
        '//a[contains(text(),"Next")]/@href',
        '//a[contains(@class,"next")]/@href',
        '//li[contains(@class,"next")]/a/@href',
        '//a[contains(@class,"arrow") and contains(@class,"right")]/@href',
    ]
    for xpath in next_xpaths:
        try:
            vals = tree.xpath(xpath)
            if vals:
                # 检查是否是JS链接（javascript:void(0)）
                href_val = vals[0] if isinstance(vals[0], str) else vals[0]
                if 'javascript:' in str(href_val) or 'void' in str(href_val):
                    continue  # 跳过JS链接，进入下面的JS检测
                return {
                    "type": "next_button",
                    "xpath": xpath.replace('/@href', ''),
                    "pattern": "",
                    "page_count": 0
                }
        except:
            pass

    # 1.5 检测JS翻页（href="javascript:void(0)" 但有 paged 属性）
    js_page_links = tree.xpath('//a[@href="javascript:void(0)"][@paged]')
    if js_page_links:
        page_nums = []
        for a in js_page_links:
            paged = a.get('paged', '')
            if paged.isdigit():
                page_nums.append(int(paged))
        if page_nums:
            max_page = max(page_nums)
            # 找到页码容器
            container = js_page_links[0].getparent()
            container_xpath = ""
            if container is not None:
                cls = container.get('class', '')
                tag = container.tag
                if cls:
                    container_xpath = f'//{tag}[@class="{cls}"]'
            return {
                "type": "js_click",
                "xpath": container_xpath or '//a[@paged]',
                "pattern": "",
                "page_count": max_page
            }

    # 1.6 检测 data-page-number 属性（如NASA网站）
    dpn_links = tree.xpath('//a[@data-page-number]')
    if dpn_links:
        page_nums = []
        for a in dpn_links:
            dpn = a.get('data-page-number', '')
            if dpn.isdigit():
                page_nums.append(int(dpn))
        if page_nums:
            max_page = max(page_nums)
            container = dpn_links[0].getparent()
            container_xpath = ""
            if container is not None:
                cls = container.get('class', '')
                tag = container.tag
                if cls:
                    container_xpath = f'//{tag}[@class="{cls}"]'
            return {
                "type": "js_click",
                "xpath": container_xpath or '//a[@data-page-number]',
                "pattern": "",
                "page_count": max_page
            }

    # 2. 直接从所有a标签中检测数字页码链接（最通用的方式）
    all_links = tree.xpath('//a')
    page_links = []  # (href, page_num) pairs
    for a in all_links:
        href = a.get('href', '')
        text = a.text_content().strip()
        # 方式1：href中包含页码（index_2.html, page/2, ?page=2）
        m = re.search(r'(?:index[_-]?|page[/=_-]?|p[=-]?)(\d+)(?:\.html?|$|\?)', href, re.I)
        if m:
            page_links.append((href, int(m.group(1))))
            continue
        # 方式2：链接文本是纯数字且较小（页码按钮）
        if text.isdigit() and 1 <= int(text) <= 999:
            page_links.append((href, int(text)))

    if page_links:
        # 按页码排序
        page_links.sort(key=lambda x: x[1])
        max_page = max(p[1] for p in page_links)
        # 用页码>1的href生成pattern（确保href中包含页码数字）
        pattern = ""
        for href, num in page_links:
            if num > 1 and str(num) in href:
                pattern = href.replace(str(num), '{{page}}')
                break
        if not pattern and page_links:
            # fallback: 用第一个链接
            href, num = page_links[0]
            if str(num) in href:
                pattern = href.replace(str(num), '{{page}}')
            else:
                pattern = href

        # 确定容器XPath
        container_xpath = ""
        if page_links:
            first_a = [a for a in all_links if a.get('href', '') == page_links[0][0]]
            if first_a:
                parent = first_a[0].getparent()
                if parent is not None:
                    # 向上找到合适的容器
                    for _ in range(5):
                        if parent is None:
                            break
                        cls = parent.get('class', '')
                        tag = parent.tag
                        if tag in ('div', 'ul', 'nav') and cls:
                            container_xpath = f'//{tag}[@class="{cls}"]'
                            break
                        parent = parent.getparent()

        return {
            "type": "url_pattern",
            "xpath": container_xpath,
            "pattern": pattern,
            "page_count": max_page
        }

    # 3. 没有检测到翻页
    return {
        "type": None,
        "xpath": "",
        "pattern": "",
        "page_count": 0
    }


def _extract_detail_url(html: str, xpath: str, base_url: str) -> Optional[str]:
    """从列表页提取详情页URL - 带验证和备用方案"""
    tree = lxml_html.fromstring(html)

    # 备用XPath列表（按优先级排序）
    fallback_xpaths = [
        xpath,  # LLM返回的XPath优先
        # 常见标题链接模式
        "//h3/a/@href",
        "//h2/a/@href",
        "//h4/a/@href",
        # article/news容器内的链接
        "//article//a/@href",
        "//div[contains(@class,'article')]//a/@href",
        "//div[contains(@class,'news')]//a/@href",
        "//div[contains(@class,'views-row')]//a/@href",
        "//div[contains(@class,'list-item')]//a/@href",
        "//div[contains(@class,'card')]//a/@href",
        # 常见路径模式
        "//a[contains(@href,'/news/')]/@href",
        "//a[contains(@href,'/press/')]/@href",
        "//a[contains(@href,'/article/')]/@href",
        "//a[contains(@href,'/post/')]/@href",
        "//a[contains(@href,'/detail/')]/@href",
        # 包含年份的链接（通常是文章）
        "//a[matches(@href, '/20\\d{2}/')]/@href",
    ]

    # 去重
    seen = set()
    unique_xpaths = []
    for x in fallback_xpaths:
        if x and x not in seen:
            seen.add(x)
            unique_xpaths.append(x)

    base_path = urlparse(base_url).path.rstrip('/')

    for try_xpath in unique_xpaths:
        try:
            links = tree.xpath(try_xpath)
            if not links:
                continue

            print(f"[AI] XPath '{try_xpath}' 匹配到 {len(links)} 个链接")

            # 收集有效链接
            candidates = []
            for link in links:
                href = link if isinstance(link, str) else link.get("href", "")
                if not href or href.startswith("#") or href.startswith("javascript:"):
                    continue

                full_url = urljoin(base_url, href)
                url_path = urlparse(full_url).path

                # 跳过与基础URL相同的链接
                if url_path.rstrip('/') == base_path:
                    continue

                # 跳过太短的路径（导航链接）
                depth = len([p for p in url_path.split('/') if p])
                if depth < 3:
                    continue

                candidates.append((depth, full_url))

            if candidates:
                # 按路径深度排序，选最深的
                candidates.sort(key=lambda x: x[0], reverse=True)
                best_url = candidates[0][1]
                print(f"[AI] 选取详情页URL: {best_url}")
                return best_url

        except Exception as e:
            print(f"[AI] XPath '{try_xpath}' 执行失败: {e}")
            continue

    print("[AI] 所有XPath都未匹配到详情页链接")
    return None


@router.post("/analyze")
async def analyze_webpage(request: AnalyzeRequest, db: Session = Depends(get_db)):
    """
    两步分析：
    1. 列表页 → 翻页 + 详情页链接
    2. 详情页 → 字段XPath（title, content, chubanriqi等）
    """
    llm_service = _get_llm_service(db, request.llm_config_id)

    # 第一步：获取并分析列表页（带重试机制）
    list_html = await _fetch_html(request.url, request.engine)
    if not list_html:
        raise HTTPException(status_code=400, detail="无法获取网页内容")

    print(f"[AI] 原始HTML长度: {len(list_html)}")
    cleaned_list = clean_html_for_llm(list_html)

    # 带重试的分析
    max_retries = 3
    parsed = {}
    detail_link_xpath = ""

    for attempt in range(max_retries):
        if attempt == 0:
            prompt = LIST_ANALYZE_PROMPT.format(html_content=cleaned_list)
        else:
            prompt = f"""上次你返回的XPath "{detail_link_xpath}" 在HTML中没有匹配到任何链接。
请重新分析HTML，返回正确的详情页链接XPath。

返回JSON格式：
{{
  "detail_link_xpath": "正确的XPath表达式",
  "pagination_type": "next_button或url_pattern或null",
  "pagination_xpath": "下一页按钮XPath",
  "pagination_pattern": "URL分页规律"
}}

HTML源码：
{cleaned_list}"""

        result = await llm_service.analyze(prompt)
        parsed = _parse_llm_result(result)
        detail_link_xpath = parsed.get("detail_link_xpath", "")
        print(f"[AI] 第{attempt+1}次分析: {parsed}")

        # 验证XPath是否有效
        if detail_link_xpath:
            try:
                tree = lxml_html.fromstring(list_html)
                links = tree.xpath(detail_link_xpath)
                if links:
                    print(f"[AI] XPath验证通过，匹配到 {len(links)} 个链接")
                    break  # 匹配成功，不再重试
                else:
                    print(f"[AI] XPath验证失败，重试...")
            except Exception as e:
                print(f"[AI] XPath执行出错: {e}，重试...")
    pagination = None
    pag_type = parsed.get("pagination_type")
    if pag_type and pag_type != "null":
        pagination = {
            "type": pag_type,
            "xpath": parsed.get("pagination_xpath", ""),
            "pattern": parsed.get("pagination_pattern", ""),
        }

    # 后处理：如果LLM未识别翻页，从HTML自动检测
    if not pagination:
        print("[AI] LLM未识别翻页，尝试HTML自动检测...")
        detected = _detect_pagination_from_html(list_html, request.url)
        if detected.get("type"):
            pagination = detected
            print(f"[AI] HTML检测到翻页: {detected}")
        else:
            # 如果静态HTML没检测到，尝试用playwright获取渲染后的HTML
            print("[AI] 静态HTML未检测到翻页，尝试playwright渲染...")
            try:
                rendered_html = await _fetch_html(request.url, "playwright")
                if rendered_html and rendered_html != list_html:
                    detected = _detect_pagination_from_html(rendered_html, request.url)
                    if detected.get("type"):
                        pagination = detected
                        print(f"[AI] Playwright渲染后检测到翻页: {detected}")
            except Exception as e:
                print(f"[AI] Playwright渲染失败: {e}")

    # 第二步：提取详情页URL并分析
    field_xpaths = []
    detail_url = _extract_detail_url(list_html, detail_link_xpath, request.url)
    print(f"[AI] 详情页URL: {detail_url}")

    if detail_url:
        detail_html = await _fetch_html(detail_url, request.engine)
        if detail_html:
            cleaned_detail = clean_html_for_llm(detail_html)

            # 详情页分析带重试（最多3次）
            detail_parsed = {}
            for attempt in range(3):
                print(f"[AI] 详情页LLM分析第{attempt+1}次...")
                detail_prompt = DETAIL_ANALYZE_PROMPT.format(html_content=cleaned_detail)
                detail_result = await llm_service.analyze(detail_prompt)
                detail_parsed = _parse_llm_result(detail_result)
                print(f"[AI] 详情页分析结果: {detail_parsed}")
                if detail_parsed:
                    break
                print(f"[AI] LLM返回空结果，重试...")

            for name, xpath in detail_parsed.items():
                if xpath:
                    field_xpaths.append({"name": name, "xpath": xpath, "confidence": 85})

    # 网页预览 - 优先显示详情页
    preview_html = detail_html if detail_url and 'detail_html' in dir() else list_html
    preview_url = detail_url if detail_url else request.url

    # 给HTML添加base标签，让相对路径的CSS/图片能正常加载
    if preview_html and '<base' not in preview_html.lower():
        preview_html = preview_html.replace('<head>', f'<head><base href="{preview_url}" target="_blank">', 1)
        if '<head>' not in preview_html:
            preview_html = f'<base href="{preview_url}" target="_blank">' + preview_html

    # 保存分析结果到缓存
    if detail_link_xpath:
        domain = get_domain_from_url(request.url)
        save_rule(db, domain, request.url, {
            "detail_link_xpath": detail_link_xpath,
            "pagination_type": pagination.get("type") if pagination else None,
            "pagination_xpath": pagination.get("xpath") if pagination else None,
            "pagination_pattern": pagination.get("pattern") if pagination else None,
            "recommended_engine": "requests",
        }, {f["name"]: f["xpath"] for f in field_xpaths if f.get("name") and f.get("xpath")})
        print(f"[AI] 分析结果已缓存: {domain}")

    return {
        "code": 0,
        "data": {
            "url": request.url,
            "html": preview_html,
            "page_type": "列表页",
            "detail_link_xpath": detail_link_xpath,
            "pagination": pagination,
            "field_xpaths": field_xpaths,
            "detail_url": detail_url,
            "engine": request.engine,
        }
    }


@router.post("/smart-create")
async def smart_create_task(request: SmartCreateRequest, db: Session = Depends(get_db)):
    """智能采集：快速创建任务 + 自动运行"""
    # 确保URL有协议前缀
    if request.url and not request.url.startswith(("http://", "https://")):
        request.url = "https://" + request.url

    datasource = db.query(DataSource).filter(DataSource.id == request.datasource_id).first()
    if not datasource:
        raise HTTPException(status_code=404, detail="数据源不存在")

    # 检查是否有缓存的规则
    domain = get_domain_from_url(request.url)

    # 验证缓存规则是否有效
    cached_rule = get_cached_rule(db, domain)
    if cached_rule and cached_rule.get("detail_link_xpath"):
        # 验证缓存的XPath是否有效
        list_html = await _fetch_html(request.url, "requests")
        if list_html:
            tree = lxml_html.fromstring(list_html)
            try:
                links = tree.xpath(cached_rule["detail_link_xpath"])
                if not links:
                    print(f"[AI] 缓存的XPath无效，清除缓存重新分析")
                    # 删除无效的缓存规则
                    db.query(CrawlRule).filter(CrawlRule.domain == domain).delete()
                    db.commit()
                    cached_rule = None
            except:
                cached_rule = None

    # 初始化字段变量
    fields = {}
    detail_link_xpath = ""
    pagination = None
    detected_engine = "requests"

    if cached_rule:
        print(f"[AI] 使用缓存规则: {domain}")
        print(f"[AI] 缓存规则详情: {cached_rule}")
        detail_link_xpath = cached_rule.get("detail_link_xpath", "")
        fields = cached_rule.get("field_xpaths", {})
        pag_type = cached_rule.get("pagination_type")
        if pag_type:
            pagination = {"type": pag_type, "xpath": cached_rule.get("pagination_xpath", ""), "pattern": cached_rule.get("pagination_pattern", "")}
        detected_engine = cached_rule.get("recommended_engine", "requests")

        # 如果缓存的字段为空，重新分析详情页
        if not fields:
            print(f"[AI] 缓存字段为空，重新分析详情页")
            llm_service = _get_llm_service(db, request.llm_config_id)
            list_html = await _fetch_html(request.url)
            if list_html:
                detail_url = _extract_detail_url(list_html, detail_link_xpath, request.url)
                if detail_url:
                    try:
                        detail_html = await _fetch_html(detail_url, "requests")
                        if detail_html:
                            cleaned_detail = clean_html_for_llm(detail_html)

                            # 详情页分析带重试（最多3次）
                            for attempt in range(3):
                                print(f"[AI] 详情页LLM分析第{attempt+1}次...")
                                detail_prompt = DETAIL_ANALYZE_PROMPT.format(html_content=cleaned_detail)
                                detail_result = await llm_service.analyze(detail_prompt)
                                detail_parsed = _parse_llm_result(detail_result)
                                print(f"[AI] 详情页字段分析: {detail_parsed}")
                                if detail_parsed:
                                    break
                                print(f"[AI] LLM返回空结果，重试...")

                            # 验证XPath并填充字段
                            tree = lxml_html.fromstring(detail_html)
                            for name, xpath in detail_parsed.items():
                                if xpath:
                                    if name == "content" and not xpath.rstrip().endswith("/text()"):
                                        xpath = xpath.rstrip() + "//text()"
                                    try:
                                        vals = tree.xpath(xpath)
                                        if vals:
                                            fields[name] = xpath
                                            print(f"[AI] 验证通过: {name}")
                                    except:
                                        pass

                            # 更新缓存规则
                            save_rule(db, domain, request.url, {
                                "detail_link_xpath": detail_link_xpath,
                                "pagination_type": pag_type,
                                "pagination_xpath": cached_rule.get("pagination_xpath", ""),
                                "pagination_pattern": cached_rule.get("pagination_pattern", ""),
                                "recommended_engine": detected_engine,
                            }, fields)
                    except Exception as e:
                        print(f"[AI] 详情页分析失败: {e}")
    else:
        # 没有缓存，进行LLM分析
        print(f"[AI] 无缓存规则，进行LLM分析: {domain}")
        llm_service = _get_llm_service(db, request.llm_config_id)

        list_html = await _fetch_html(request.url)
        if not list_html:
            raise HTTPException(status_code=400, detail="无法获取网页内容")

        cleaned_list = clean_html_for_llm(list_html)
        prompt = LIST_ANALYZE_PROMPT.format(html_content=cleaned_list)
        result = await llm_service.analyze(prompt)
        parsed = _parse_llm_result(result)

        detail_link_xpath = parsed.get("detail_link_xpath", "")
        pag_type = parsed.get("pagination_type")
        pagination = {"type": pag_type, "xpath": parsed.get("pagination_xpath", ""), "pattern": parsed.get("pagination_pattern", "")} if pag_type and pag_type != "null" else {}

        # 后处理：如果LLM未识别翻页，从HTML自动检测
        if not pagination:
            print("[AI] LLM未识别翻页，尝试HTML自动检测...")
            detected = _detect_pagination_from_html(list_html, request.url)
            if detected.get("type"):
                pagination = detected
                print(f"[AI] HTML检测到翻页: {detected}")
            else:
                # 如果静态HTML没检测到，尝试用playwright获取渲染后的HTML
                print("[AI] 静态HTML未检测到翻页，尝试playwright渲染...")
                try:
                    rendered_html = await _fetch_html(request.url, "playwright")
                    if rendered_html and rendered_html != list_html:
                        detected = _detect_pagination_from_html(rendered_html, request.url)
                        if detected.get("type"):
                            pagination = detected
                            print(f"[AI] Playwright渲染后检测到翻页: {detected}")
                except Exception as e:
                    print(f"[AI] Playwright渲染失败: {e}")

        # 引擎策略：使用cascade模式，自动降级
        # 默认用requests，采集脚本会自动尝试curl_cffi和playwright
        detected_engine = "requests"

        # 分析详情页获取字段
        fields = {}
        detail_url = _extract_detail_url(list_html, detail_link_xpath, request.url)
        if detail_url:
            try:
                detail_html = await _fetch_html(detail_url, "requests")
                if detail_html:
                    cleaned_detail = clean_html_for_llm(detail_html)

                    # 详情页分析带重试（最多3次）
                    for attempt in range(3):
                        print(f"[AI] 详情页LLM分析第{attempt+1}次...")
                        detail_prompt = DETAIL_ANALYZE_PROMPT.format(html_content=cleaned_detail)
                        detail_result = await llm_service.analyze(detail_prompt)
                        detail_parsed = _parse_llm_result(detail_result)
                        print(f"[AI] 详情页字段分析: {detail_parsed}")
                        if detail_parsed:
                            break
                        print(f"[AI] LLM返回空结果，重试...")

                    # 验证XPath是否有效
                    tree = lxml_html.fromstring(detail_html)
                    for name, xpath in detail_parsed.items():
                        if xpath:
                            try:
                                # 确保content字段有text()
                                if name == "content" and not xpath.rstrip().endswith("/text()"):
                                    xpath = xpath.rstrip() + "//text()"
                                vals = tree.xpath(xpath)
                                if vals:
                                    fields[name] = xpath
                                    print(f"[AI] 验证通过: {name} -> {xpath[:50]}...")
                                else:
                                    print(f"[AI] 验证失败: {name} -> {xpath} 匹配不到内容")
                            except Exception as e:
                                print(f"[AI] XPath执行错误: {name} -> {e}")
            except Exception as e:
                print(f"[AI] 详情页分析失败: {e}")

        # 保存规则到数据库（包含字段）
        save_rule(db, domain, request.url, {
            "detail_link_xpath": detail_link_xpath,
            "pagination_type": pag_type,
            "pagination_xpath": parsed.get("pagination_xpath", ""),
            "pagination_pattern": parsed.get("pagination_pattern", ""),
            "recommended_engine": detected_engine,
        }, fields)
        print(f"[AI] 规则已缓存: {domain}, 字段: {list(fields.keys())}")

    task_name = request.task_name or f"智能采集_{request.url[:50]}"

    from app.service.task_service import generate_spider_name
    # 优先使用前端用户配置的字段，fallback到LLM分析的字段
    final_fields = request.fields if request.fields else fields

    config_json = {
        "url": request.url,
        "engine": detected_engine,
        "task_name": task_name,  # 任务名称，用于tag字段
        "max_pages": request.max_pages,
        "interval": request.request_interval,
        "fields": final_fields,  # 优先前端配置，fallback LLM分析
        "pagination_type": (pagination or {}).get("type", "next_button"),
        "next_xpath": (pagination or {}).get("xpath", ""),
        "page_url_template": (pagination or {}).get("pattern", ""),
        "page_count": (pagination or {}).get("page_count", 0),  # js_click翻页的总页数
        "detail_link_xpath": detail_link_xpath,
        "llm_config_id": request.llm_config_id,  # 传递LLM配置ID供运行时使用
        "db_host": datasource.host,
        "db_port": datasource.port,
        "db_name": datasource.database_name,
        "db_table": "crawler_feachdata",
        "db_user": datasource.username,
        "db_password": datasource.password,
    }

    from app.models import Task, Script
    from app.utils.script_generator import generate_crawl_script, generate_parse_script, generate_full_script, save_script

    task = Task(
        name=task_name,
        description=f"智能采集 - {request.url}",
        task_type="smart",
        group_name="智能采集",
        engine=detected_engine,
        config_json=config_json,
        datasource_id=request.datasource_id,
    )
    db.add(task)
    db.flush()

    # 生成spider_name并更新config（创建新dict确保SQLAlchemy检测到变化）
    spider_name = generate_spider_name(request.url, task.id)
    config_json = {**config_json, "spider_name": spider_name}

    # 使用ORM方式更新config_json（确保JSON列正确序列化）
    task.config_json = config_json
    db.flush()

    # 生成脚本
    crawl_code = generate_crawl_script(task.id, config_json)
    db.add(Script(task_id=task.id, script_type="crawl", code=crawl_code, file_path=save_script(task.id, "crawl", crawl_code)))

    parse_code = generate_parse_script(task.id, config_json)
    db.add(Script(task_id=task.id, script_type="parse", code=parse_code, file_path=save_script(task.id, "parse", parse_code)))

    full_code = generate_full_script(task.id, config_json)
    db.add(Script(task_id=task.id, script_type="full", code=full_code, file_path=save_script(task.id, "full", full_code)))

    db.commit()

    # 自动运行任务
    try:
        from app.task.manager import task_manager
        from app.service.task_service import TaskService
        from app.task.log_bus import log_bus

        # 创建运行记录
        run = TaskService.create_run(db, task.id, "manual")
        db.commit()

        # 保存脚本到文件
        task_dir = os.path.join(settings.SCRIPTS_DIR, str(task.id))
        os.makedirs(task_dir, exist_ok=True)
        for s in db.query(Script).filter(Script.task_id == task.id).all():
            save_script(task.id, s.script_type, s.code)

        # 启动任务
        script_path = os.path.join(task_dir, "full_spider.py")
        started = await task_manager.start_task(run.id, task.id, script_path, config_json)
        if started:
            print(f"[AI] 任务 {task.id} 已自动启动")
    except Exception as e:
        print(f"[AI] 自动启动任务失败: {e}")

    return {
        "code": 0,
        "message": "任务创建成功并已启动",
        "data": {
            "task_id": task.id,
            "task_name": task_name,
            "engine": detected_engine,
        }
    }
