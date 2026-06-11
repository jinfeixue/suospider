# -*- coding: utf-8 -*-
"""解析脚本 - 任务25"""
import time
import pymysql
import hashlib
from lxml import html as lxml_html

# 配置
ENGINE = "requests"
DB_HOST = "192.168.1.191"
DB_PORT = 3308
DB_NAME = "ai_spider"
DB_TABLE = "crawler_feachdata"
DB_USER = "root"
DB_PASSWORD = "123456"
SPIDER_NAME = "spider_25_9b4d08d4"


def log(msg):
    print(f"[PARSE] {msg}", flush=True)


def get_db():
    return pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER,
                          password=DB_PASSWORD, database=DB_NAME,
                          charset='utf8mb4', connect_timeout=10)


def get_unparsed_urls(limit=100):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT id, url FROM `{DB_TABLE}` WHERE spider_name = %s AND (parseflag = 0 OR parseflag IS NULL) LIMIT %s",
            (SPIDER_NAME, limit)
        )
        return cursor.fetchall()
    finally:
        conn.close()


def update_record(record_id, data):
    conn = get_db()
    try:
        cursor = conn.cursor()
        set_clauses = []
        values = []
        for k, v in data.items():
            if v is not None:
                set_clauses.append(f"`{k}` = %s")
                values.append(v)
        set_clauses.append("`parseflag` = 1")
        set_clauses.append("`lastmodifiedtime` = NOW()")
        values.append(record_id)
        sql = f"UPDATE `{DB_TABLE}` SET {', '.join(set_clauses)} WHERE id = %s"
        cursor.execute(sql, values)
        conn.commit()
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


def parse():
    """主解析逻辑"""
    urls = get_unparsed_urls()
    log(f"待解析: {len(urls)} 条")

    for record_id, url in urls:
        try:
            html = fetch_page(url)
            tree = lxml_html.fromstring(html)
            data = {"url": url, "spider_name": SPIDER_NAME}
            
        try:
            vals = tree.xpath("//h1[contains(@class,'uswds-page-title')]/text()")
            data["title"] = vals[0].strip() if vals else ""
        except:
            data["title"] = ""
        try:
            vals = tree.xpath("//h1[contains(@class,'uswds-page-title')]/following::div[contains(@class,'field--name-body')][1]//text()")
            data["content"] = vals[0].strip() if vals else ""
        except:
            data["content"] = ""
        try:
            vals = tree.xpath("//span[contains(@class,'news-release-date-value')]/text()")
            data["chubanriqi"] = vals[0].strip() if vals else ""
        except:
            data["chubanriqi"] = ""
        try:
            vals = tree.xpath("//ul[contains(@class,'usa-collection__meta')]/li/a/text()")
            data["keyword"] = vals[0].strip() if vals else ""
        except:
            data["keyword"] = ""
        try:
            vals = tree.xpath("//ol[contains(@class,'uswds-breadcrumbs')]/li[contains(a,'Press Releases')]/a/text()")
            data["kanming"] = vals[0].strip() if vals else ""
        except:
            data["kanming"] = ""

            # 生成solrid
            data["solrid"] = hashlib.md5(url.encode()).hexdigest()
            update_record(record_id, data)
            log(f"解析成功: {url[:60]}")
            time.sleep(1)
        except Exception as e:
            log(f"解析失败: {url[:60]} - {e}")

    log("解析完成")


if __name__ == "__main__":
    parse()
