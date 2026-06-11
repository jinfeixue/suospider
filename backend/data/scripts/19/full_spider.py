# -*- coding: utf-8 -*-
"""智能采集脚本 - 任务19
流程：采集列表页URL → 获取详情页 → LLM分析字段 → 解析数据 → 缓存规则
"""
import sys
import os
import re
import json
import time
import pymysql
import hashlib
import httpx
from lxml import html as lxml_html
from urllib.parse import urljoin, urlparse
import datetime

# 配置
URL = "https://www.dhs.gov/all-news-updates"
ENGINE = "playwright"
MAX_PAGES = 2
INTERVAL = 2
DETAIL_LINK_XPATH = "//div[contains(@class,'news-updates') and contains(@class,'views-row')]//h3/a/@href"
NEXT_XPATH = "//li[contains(@class,'usa-pagination__arrow')]/a"
PAGE_URL_TEMPLATE = "?page={page}"
LLM_CONFIG_ID = 1

DB_HOST = "192.168.1.191"
DB_PORT = 3308
DB_NAME = "ai_spider"
DB_TABLE = "crawler_feachdata"
DB_USER = "root"
DB_PASSWORD = "123456"
SPIDER_NAME = "spider_19_9b4d08d4"


def log(msg):
    print(f"[SPIDER] {msg}", flush=True)


def get_db():
    return pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER,
                          password=DB_PASSWORD, database=DB_NAME,
                          charset='utf8mb4', connect_timeout=10)


def get_domain(url):
    """从URL提取域名"""
    parsed = urlparse(url)
    return parsed.netloc or parsed.hostname or ""


def fetch_page(url):
    """获取页面HTML"""
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
        resp = httpx.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30, follow_redirects=True)
        return resp.text


def clean_html(html):
    """清洗HTML供LLM分析"""
    try:
        tree = lxml_html.fromstring(html)
        for tag in tree.xpath("//script | //style | //noscript | //svg | //iframe"):
            parent = tag.getparent()
            if parent is not None:
                parent.remove(tag)
        for comment in tree.xpath("//comment()"):
            parent = comment.getparent()
            if parent is not None:
                parent.remove(comment)
        return lxml_html.tostring(tree, encoding="unicode", pretty_print=False)
    except:
        return html


def call_llm(prompt):
    """调用LLM分析"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        if LLM_CONFIG_ID:
            cursor.execute("SELECT provider, model, api_key, api_url, timeout FROM llm_configs WHERE id = %s", (LLM_CONFIG_ID,))
        else:
            cursor.execute("SELECT provider, model, api_key, api_url, timeout FROM llm_configs WHERE is_default = 1 LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if not row:
            log("未找到LLM配置")
            return None

        provider, model, api_key, api_url, timeout = row

        if not api_url:
            if provider == "openai":
                api_url = "https://api.openai.com/v1/chat/completions"
            elif provider == "anthropic":
                api_url = "https://api.anthropic.com/v1/messages"
            else:
                api_url = "https://api.deepseek.com/v1/chat/completions"

        if not api_url.endswith("/chat/completions") and not api_url.endswith("/messages"):
            if api_url.endswith("/v1"):
                api_url += "/chat/completions"
            else:
                api_url += "/v1/chat/completions"

        resp = httpx.post(
            api_url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "max_tokens": 4000},
            timeout=timeout
        )

        if resp.status_code == 200:
            result = resp.json()
            return result["choices"][0]["message"]["content"]
        else:
            log(f"LLM调用失败: {resp.status_code}")
            return None
    except Exception as e:
        log(f"LLM调用异常: {e}")
        return None


def analyze_detail_page(html):
    """用LLM分析详情页，返回字段XPath"""
    cleaned = clean_html(html)
    prompt = f"""分析详情页HTML，识别内容字段的XPath。只输出JSON：

{"title": "标题XPath/text()", "content": "正文XPath", "chubanriqi": "发布日期XPath/text()", "zuozhe": "作者XPath/text()", "keyword": "关键词XPath/text()", "abstract": "摘要XPath/text()"}

规则：提取文本的字段加 /text()，content是HTML不加。只填能识别到的字段。

HTML：
{cleaned[:30000]}"""

    result = call_llm(prompt)
    if result:
        try:
            match = re.search(r'\{[\s\S]*\}', result)
            if match:
                return json.loads(match.group())
        except:
            pass
    return {}


def get_cached_fields():
    """从数据库获取缓存的字段XPath"""
    domain = get_domain(URL)
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT field_xpaths FROM crawl_rules WHERE domain = %s AND is_active = 1", (domain,))
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            return json.loads(row[0]) if isinstance(row[0], str) else row[0]
    except:
        pass
    return None


def save_fields_to_cache(fields):
    """保存字段XPath到数据库"""
    domain = get_domain(URL)
    try:
        conn = get_db()
        cursor = conn.cursor()
        # 检查是否已存在
        cursor.execute("SELECT id, field_xpaths FROM crawl_rules WHERE domain = %s", (domain,))
        row = cursor.fetchone()

        if row:
            # 合并新旧字段
            rule_id, old_fields = row
            old_fields = json.loads(old_fields) if isinstance(old_fields, str) and old_fields else (old_fields or {})

            # 对每个字段，如果新的XPath不同，用|合并
            merged = {}
            all_keys = set(list(old_fields.keys()) + list(fields.keys()))
            for key in all_keys:
                old_xpath = old_fields.get(key, "")
                new_xpath = fields.get(key, "")
                if old_xpath and new_xpath and old_xpath != new_xpath:
                    merged[key] = f"{old_xpath} | {new_xpath}"
                elif new_xpath:
                    merged[key] = new_xpath
                else:
                    merged[key] = old_xpath

            cursor.execute(
                "UPDATE crawl_rules SET field_xpaths = %s, updated_at = %s WHERE id = %s",
                (json.dumps(merged), datetime.datetime.now(), rule_id)
            )
            log(f"规则已更新合并: {domain}")
        else:
            cursor.execute(
                "INSERT INTO crawl_rules (domain, url_pattern, field_xpaths, is_active, created_at, updated_at) VALUES (%s, %s, %s, 1, %s, %s)",
                (domain, URL, json.dumps(fields), datetime.datetime.now(), datetime.datetime.now())
            )
            log(f"规则已缓存: {domain}")

        conn.commit()
    except Exception as e:
        log(f"缓存规则失败: {e}")


def merge_xpath(old_xpath, new_xpath):
    """合并两个XPath"""
    if not old_xpath:
        return new_xpath
    if not new_xpath:
        return old_xpath
    if old_xpath == new_xpath:
        return old_xpath
    return f"{old_xpath} | {new_xpath}"


def save_url(url):
    """保存URL到数据库"""
    solrid = hashlib.md5(url.encode()).hexdigest()
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"INSERT IGNORE INTO `{DB_TABLE}` (url, solrid, spider_name, parseflag, creationtime) VALUES (%s, %s, %s, 0, NOW())",
            (url, solrid, SPIDER_NAME)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def crawl():
    """阶段1：采集列表页，提取详情页URL"""
    current_url = URL
    saved = 0

    for page_num in range(1, MAX_PAGES + 1):
        log(f"采集第{page_num}页: {current_url}")
        try:
            html = fetch_page(current_url)
            tree = lxml_html.fromstring(html)

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
            log(f"采集错误: {e}")
            break

    log(f"采集完成: 新增 {saved} 条URL")
    return saved


def parse_with_retry(fields):
    """解析所有未解析的URL，失败时自动重新分析并合并XPath"""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT id, url FROM `{DB_TABLE}` WHERE spider_name = %s AND (parseflag = 0 OR parseflag IS NULL) LIMIT 1000",
            (SPIDER_NAME,)
        )
        urls = cursor.fetchall()
    finally:
        conn.close()

    log(f"待解析: {len(urls)} 条")
    parsed = 0
    failed_count = 0
    reanalyze_threshold = 3  # 连续失败N次后重新分析

    for record_id, url in urls:
        success = False
        for attempt in range(2):  # 最多重试1次
            try:
                html = fetch_page(url)
                tree = lxml_html.fromstring(html)
                data = {"url": url, "spider_name": SPIDER_NAME}

                for name, xpath in fields.items():
                    try:
                        # 尝试多个XPath（用|分隔的）
                        for single_xpath in xpath.split("|"):
                            single_xpath = single_xpath.strip()
                            if single_xpath:
                                vals = tree.xpath(single_xpath)
                                if vals:
                                    data[name] = vals[0].strip() if isinstance(vals[0], str) else vals[0]
                                    break
                    except:
                        data[name] = ""

                # 检查是否提取到关键数据
                has_data = any(v for k, v in data.items() if k not in ["url", "spider_name", "solrid"] and v)

                if has_data:
                    data["solrid"] = hashlib.md5(url.encode()).hexdigest()

                    # 更新数据库
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

                    parsed += 1
                    success = True
                    log(f"解析成功: {url[:60]}")
                    break
                else:
                    log(f"提取不到数据，尝试重新分析: {url[:60]}")

            except Exception as e:
                log(f"解析异常: {e}")

            # 如果第一次失败，重新分析并合并XPath
            if attempt == 0 and not success:
                log("重新分析详情页...")
                new_fields = analyze_detail_page(html)
                if new_fields:
                    # 合并新旧XPath
                    for name, new_xpath in new_fields.items():
                        if name in fields and new_xpath:
                            fields[name] = merge_xpath(fields[name], new_xpath)
                        elif new_xpath:
                            fields[name] = new_xpath
                    log(f"合并后字段: {list(fields.keys())}")
                    # 保存更新后的规则
                    save_fields_to_cache(fields)

        if not success:
            failed_count += 1

        time.sleep(1)

    log(f"解析完成: {parsed} 条成功, {failed_count} 条失败")
    return parsed, fields  # 返回更新后的字段


def main():
    """主流程"""
    log("===== 开始智能采集 =====")

    # 阶段1：采集列表页URL
    crawl()

    # 阶段2：获取详情页，分析或使用缓存字段
    log("准备解析字段...")
    fields = get_cached_fields()

    if fields:
        log(f"使用缓存字段: {list(fields.keys())}")
    else:
        log("无缓存字段，进行LLM分析...")
        first_url = None
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT id, url FROM `{DB_TABLE}` WHERE spider_name = %s AND (parseflag = 0 OR parseflag IS NULL) LIMIT 1",
                (SPIDER_NAME,)
            )
            first_url = cursor.fetchone()
        finally:
            conn.close()

        if first_url:
            record_id, url = first_url
            log(f"分析详情页: {url}")
            try:
                html = fetch_page(url)
                fields = analyze_detail_page(html)
                log(f"识别到字段: {list(fields.keys())}")
                # 缓存成功的字段
                if fields:
                    save_fields_to_cache(fields)
            except Exception as e:
                log(f"详情页分析失败: {e}")

    # 备用字段
    if not fields:
        log("使用备用字段配置")
        fields = {
            "title": "//h1/text()",
            "content": "//article//text()",
            "chubanriqi": "//time/@datetime",
        }

    log(f"最终字段配置: {fields}")

    # 阶段3：解析所有详情页（带重试和XPath合并）
    parsed, final_fields = parse_with_retry(fields)

    # 保存最终的字段配置
    if final_fields != fields:
        save_fields_to_cache(final_fields)

    log(f"===== 采集完成: {parsed} 条数据已解析 =====")


if __name__ == "__main__":
    main()
