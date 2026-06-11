# -*- coding: utf-8 -*-
"""采集脚本 - 任务22"""
import time
import pymysql
import hashlib
from lxml import html as lxml_html
from urllib.parse import urljoin

# 配置
URL = "https://www.dhs.gov/all-news-updates"
ENGINE = "playwright"
MAX_PAGES = 2
INTERVAL = 2
DETAIL_LINK_XPATH = "//div[contains(@class,'news-updates') and contains(@class,'views-row')]//h3/a/@href"
NEXT_XPATH = "//li[contains(@class,'usa-pagination__arrow')]/a"
PAGE_URL_TEMPLATE = "?page={page}"

DB_HOST = "192.168.1.191"
DB_PORT = 3308
DB_NAME = "ai_spider"
DB_TABLE = "crawler_feachdata"
DB_USER = "root"
DB_PASSWORD = "123456"
SPIDER_NAME = "spider_22_9b4d08d4"


def log(msg):
    print(f"[SPIDER] {msg}", flush=True)


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
        resp.encoding = resp.apparent_encoding or 'utf-8'
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
                current_url = PAGE_URL_TEMPLATE.replace("{page}", str(page_num + 1))
            else:
                break

            time.sleep(INTERVAL)

        except Exception as e:
            log(f"错误: {e}")
            break

    log(f"采集完成: 新增 {saved} 条URL")


if __name__ == "__main__":
    crawl()
