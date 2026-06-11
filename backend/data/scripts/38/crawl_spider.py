# -*- coding: utf-8 -*-
"""采集脚本 - 任务38"""
import time
import pymysql
import hashlib
from lxml import html as lxml_html
from urllib.parse import urljoin

# 配置
URL = "https://whfgw.wuhu.gov.cn/fgyw/fgyw/index.html"
ENGINE = "requests"
MAX_PAGES = 2
INTERVAL = 2
DETAIL_LINK_XPATH = "//ul[contains(@class,'doc_list')]/li/a/@href"
NEXT_XPATH = '//div[@class="pagination"]'
PAGE_URL_TEMPLATE = ""

DB_HOST = "192.168.1.191"
DB_PORT = 3308
DB_NAME = "ai_spider"
DB_TABLE = "crawler_feachdata"
DB_USER = "root"
DB_PASSWORD = "123456"
SPIDER_NAME = "spider_38_f9baee61"


def log(msg):
    try:
        print(f"[SPIDER] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[SPIDER] {msg.encode('utf-8', errors='replace').decode('utf-8', errors='replace')}", flush=True)


def trans_date(value):
    """将各种日期格式统一为 YYYY-MM-DD HH:MM:SS"""
    import re
    if not value or not str(value).strip():
        return ""
    s = str(value).strip()
    s = re.sub(r'(\d{4})年(\d{1,2})月(\d{1,2})日', r'\1-\2-\3', s)
    s = re.sub(r'(\d{4})年(\d{1,2})月', r'\1-\2-01', s)
    s = re.sub(r'(\d{4})年', r'\1-01-01', s)
    s = re.sub(r'^[^\d]*', '', s)
    try:
        from dateutil import parser as date_parser
        dt = date_parser.parse(s, fuzzy=True)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return value


def get_db():
    return pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER,
                          password=DB_PASSWORD, database=DB_NAME,
                          charset='utf8mb4', connect_timeout=10)


def save_url(url):
    solrid = hashlib.md5(url.encode()).hexdigest()
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"INSERT IGNORE INTO `{DB_TABLE}` (url, solrid, spider_name, parseflag, creationtime) "
            f"VALUES (%s, %s, %s, 0, NOW())",
            (url, solrid, SPIDER_NAME)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def fetch_page(url):
    """根据引擎获取页面"""
    if ENGINE == "playwright":
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until='networkidle', timeout=30000)
            content = page.content()
            browser.close()
            return content
    else:
        import requests
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        # 智能编码检测
        encoding = None
        ct = resp.headers.get('content-type', '')
        if 'charset=' in ct:
            encoding = ct.split('charset=')[-1].strip()
        if not encoding or encoding.lower() in ('iso-8859-1', 'latin-1', 'ascii'):
            import re as _re
            m = _re.search(rb'charset[=\"\s]+([a-zA-Z0-9_-]+)', resp.content[:3000], _re.I)
            if m:
                encoding = m.group(1).decode('ascii', errors='ignore')
        if not encoding or encoding.lower() in ('iso-8859-1', 'latin-1', 'ascii'):
            try:
                resp.content.decode('utf-8')
                encoding = 'utf-8'
            except:
                encoding = resp.apparent_encoding or 'utf-8'
        resp.encoding = encoding
        return resp.text


def crawl():
    """主采集逻辑"""
    current_url = URL
    saved = 0

    for page_num in range(1, MAX_PAGES + 1):
        log(f"第{page_num}页: {current_url}")

        try:
            html = fetch_page(current_url)
            tree = lxml_html.fromstring(html)

            # 提取详情页链接
            links = tree.xpath(DETAIL_LINK_XPATH)
            log(f"找到 {len(links)} 个链接")

            for link in links:
                href = link if isinstance(link, str) else link.get("href", "")
                if href:
                    full_url = urljoin(current_url, href)
                    if save_url(full_url):
                        saved += 1

            # 翻页
            if NEXT_XPATH:
                next_links = tree.xpath(NEXT_XPATH)
                if next_links:
                    next_href = next_links[0] if isinstance(next_links[0], str) else next_links[0].get("href", "")
                    if next_href:
                        current_url = urljoin(current_url, next_href)
                    else:
                        break
                else:
                    break
            elif PAGE_URL_TEMPLATE:
                _pn = str(page_num + 1)
                _rb = chr(125)
                _pb = chr(123)
                next_page_url = PAGE_URL_TEMPLATE
                next_page_url = next_page_url.replace(_pb + "page_num" + _rb, _pn)
                next_page_url = next_page_url.replace(_pb + "page" + _rb, _pn)
                # 如果是相对路径，转换为绝对路径
                if not next_page_url.startswith("http"):
                    current_url = urljoin(URL, next_page_url)
                else:
                    current_url = next_page_url
            else:
                break

            time.sleep(INTERVAL)

        except Exception as e:
            log(f"错误: {e}")
            break

    log(f"采集完成: 新增 {saved} 条URL")


if __name__ == "__main__":
    crawl()
