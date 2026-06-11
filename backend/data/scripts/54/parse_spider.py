# -*- coding: utf-8 -*-
"""解析脚本 - 任务54"""
import time
import os
import json
import re
import pymysql
import hashlib
import httpx
from lxml import html as lxml_html
from urllib.parse import urlparse

# 配置
ENGINE = "requests"
DB_HOST = "192.168.1.191"
DB_PORT = 3308
DB_NAME = "ai_spider"
DB_TABLE = "crawler_feachdata"
DB_USER = "root"
DB_PASSWORD = "123456"
SPIDER_NAME = "spider_54_a32f16a3"
TASK_NAME = "上海要闻"
LLM_CONFIG_ID = 1

# 字段配置（JSON字符串，需要解析为字典）
_fields_json = """{"title": "//h2[@id='ivs_title']/text()[1]", "content": "//div[@id='ivs_content']//text()", "chubanriqi": "//meta[@name='PubDate']/@content", "zuozhe": "//meta[@name='Author']/@content", "keyword": "//meta[@name='keywords']/@content", "kanming": "//meta[@name='ContentSource']/@content"}"""
fields = json.loads(_fields_json) if isinstance(_fields_json, str) else _fields_json


def log(msg):
    try:
        print(f"[PARSE] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[PARSE] {msg.encode('utf-8', errors='replace').decode('utf-8', errors='replace')}", flush=True)


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
        # content为空时设parseflag=0，下次重新解析
        _parseflag = 1 if data.get("content") else 0
        set_clauses.append(f"`parseflag` = {_parseflag}")
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


def extract_fields(tree, fields):
    """从HTML中提取字段值 - 运行时从fields字典读取XPath"""
    data = {}
    _multi_value_fields = {"zuozhe", "author", "zuozhedanwei", "author_addrs", "keyword", "keyword_eng"}
    for name, field_conf in fields.items():
        try:
            if isinstance(field_conf, str):
                field_type = "xpath"
                xpath_val = field_conf
                constant_val = ""
            else:
                field_type = field_conf.get("type", "xpath")
                xpath_val = field_conf.get("xpath", "")
                constant_val = field_conf.get("value", "")

            if field_type == "constant":
                data[name] = constant_val
            else:
                for single_xpath in xpath_val.split("|"):
                    single_xpath = single_xpath.strip()
                    if single_xpath:
                        vals = tree.xpath(single_xpath)
                        if vals:
                            texts = []
                            for v in vals:
                                if isinstance(v, str):
                                    t = v.strip()
                                    if t and len(t) > 3:
                                        texts.append(t)
                                elif hasattr(v, 'text_content'):
                                    t = v.text_content().strip()
                                    if t and len(t) > 3:
                                        texts.append(t)
                            _sep = chr(123) + "|" + chr(125) if name in _multi_value_fields else " "
                            data[name] = _sep.join(texts) if texts else ""
                            break
        except:
            data[name] = ""
    # 日期字段标准化
    for _df in ("chubanriqi", "releasetime", "creationtime", "lastmodifiedtime", "upload_time"):
        if _df in data and data[_df]:
            data[_df] = trans_date(data[_df])
    return data


def trans_date(value):
    """将各种日期格式统一为 YYYY-MM-DD HH:MM:SS"""
    if not value or not str(value).strip():
        return ""
    s = str(value).strip()
    s = re.sub(r'^[^\dA-Za-z]*', '', s)
    s = re.sub(r'(\d{4})年(\d{1,2})月(\d{1,2})日', r'\1-\2-\3', s)
    s = re.sub(r'(\d{4})年(\d{1,2})月', r'\1-\2-01', s)
    s = re.sub(r'(\d{4})年', r'\1-01-01', s)
    try:
        from dateutil import parser as date_parser
        dt = date_parser.parse(s, fuzzy=True)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        tokens = s.split()
        for i, token in enumerate(tokens):
            if re.search(r'\d:\d{2}\s*(?:AM|PM)', token, re.IGNORECASE) and i >= 3:
                candidate = ' '.join(tokens[max(0, i - 4):i + 1])
                try:
                    from dateutil import parser as _dp
                    dt = _dp.parse(candidate, fuzzy=True)
                    return dt.strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    continue
    return value


def save_fields_to_cache(fields):
    """保存字段XPath到缓存"""
    domain = get_domain(URL)
    try:
        conn = pymysql.connect(
            host=os.environ.get("SPIDER_APP_DB_HOST", "localhost"),
            port=int(os.environ.get("SPIDER_APP_DB_PORT", "3306")),
            user=os.environ.get("SPIDER_APP_DB_USER", "root"),
            password=os.environ.get("SPIDER_APP_DB_PASSWORD", ""),
            database=os.environ.get("SPIDER_APP_DB_NAME", "spider"),
            charset='utf8mb4', connect_timeout=10
        )
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM crawl_rules WHERE domain = %s", (domain,))
        row = cursor.fetchone()
        if row:
            cursor.execute("UPDATE crawl_rules SET field_xpaths = %s, updated_at = %s WHERE id = %s",
                           (json.dumps(fields), datetime.datetime.now(), row[0]))
        else:
            cursor.execute("INSERT INTO crawl_rules (domain, field_xpaths, is_active, created_at, updated_at) VALUES (%s, %s, 1, %s, %s)",
                           (domain, json.dumps(fields), datetime.datetime.now(), datetime.datetime.now()))
        conn.commit()
        conn.close()
    except Exception as e:
        log(f"缓存规则失败: {e}")


def merge_xpath(old_xpath, new_xpath):
    """合并两个XPath，确保XPath以//text()或/text()结尾"""
    def _ensure_text(xp):
        if not xp:
            return xp
        xp = xp.strip()
        if not xp.endswith("/text()"):
            xp = xp.rstrip("/") + "//text()"
        return xp

    old_xpath = _ensure_text(old_xpath)
    new_xpath = _ensure_text(new_xpath)

    if not old_xpath:
        return new_xpath
    if not new_xpath:
        return old_xpath
    if old_xpath == new_xpath:
        return old_xpath
    return old_xpath + " | " + new_xpath


def parse():
    """主解析逻辑 - content/abstract为空时立即调用LLM重新分析并重试"""
    urls = get_unparsed_urls()
    log(f"待解析: {len(urls)} 条")
    parsed = 0
    failed = 0

    for record_id, url in urls:
        success = False
        html = ""
        for attempt in range(3):
            try:
                html = fetch_page(url)
                tree = lxml_html.fromstring(html)
                data = {"url": url, "spider_name": SPIDER_NAME}
                # 运行时从fields字典提取字段（支持重试时的动态更新）
                extracted = extract_fields(tree, fields)
                data.update(extracted)

                # 生成solrid
                data["solrid"] = hashlib.md5(url.encode()).hexdigest()
                # 自动填充tag和crawlerserverurl
                if not data.get("tag"):
                    data["tag"] = TASK_NAME
                if not data.get("crawlerserverurl"):
                    try:
                        data["crawlerserverurl"] = urlparse(url).netloc
                    except:
                        pass

                # 检查关键字段
                has_content = bool(data.get("content"))
                has_abstract = bool(data.get("abstract"))
                has_data = has_content or has_abstract

                update_record(record_id, data)

                if has_data:
                    success = True
                    log(f"解析成功: {url}")
                    break
                else:
                    log(f"content和abstract为空，第{attempt+1}次重试: {url}")
            except Exception as e:
                log(f"解析异常: {url} - {e}")

            # 重新分析并合并XPath
            if not success:
                log("调用LLM重新分析详情页...")
                try:
                    _app_db_host = os.environ.get("SPIDER_APP_DB_HOST", "localhost")
                    _app_db_port = int(os.environ.get("SPIDER_APP_DB_PORT", "3306"))
                    _app_db_name = os.environ.get("SPIDER_APP_DB_NAME", "spider")
                    _app_db_user = os.environ.get("SPIDER_APP_DB_USER", "root")
                    _app_db_password = os.environ.get("SPIDER_APP_DB_PASSWORD", "")
                    conn = pymysql.connect(host=_app_db_host, port=_app_db_port, user=_app_db_user,
                                           password=_app_db_password, database=_app_db_name,
                                           charset='utf8mb4', connect_timeout=10)
                    cursor = conn.cursor()
                    if LLM_CONFIG_ID:
                        cursor.execute("SELECT provider, model, api_key, api_url, timeout FROM llm_configs WHERE id = %s", (LLM_CONFIG_ID,))
                    else:
                        cursor.execute("SELECT provider, model, api_key, api_url, timeout FROM llm_configs WHERE is_default = 1 LIMIT 1")
                    row = cursor.fetchone()
                    conn.close()

                    if row:
                        provider, model, api_key, api_url, llm_timeout = row
                        if not api_url:
                            api_url = "https://api.deepseek.com/v1/chat/completions"
                        if not api_url.endswith("/chat/completions"):
                            api_url += "/v1/chat/completions" if not api_url.endswith("/v1") else "/chat/completions"

                        # 清洗HTML并构建prompt
                        cleaned = html[:30000]
                        _lb = chr(123)
                        _rb = chr(125)
                        _example = _lb + '"title": "...", "content": "...", "chubanriqi": "...", "zuozhe": "...", "keyword": "...", "abstract": "..."' + _rb
                        prompt = "分析详情页HTML，识别内容字段的XPath。只输出JSON：" + chr(10) + chr(10) + _example + chr(10) + chr(10) + "规则：content和abstract必须返回。" + chr(10) + chr(10) + "HTML：" + chr(10) + cleaned

                        resp = httpx.post(api_url,
                                          headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                                          json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "max_tokens": 4000},
                                          timeout=llm_timeout)
                        if resp.status_code == 200:
                            result = resp.json()["choices"][0]["message"]["content"]
                            _lb2 = chr(123)
                            _rb2 = chr(125)
                            match = re.search(_lb2 + r'[\s\S]*' + _rb2, result)
                            if match:
                                new_fields = json.loads(match.group())
                                log(f"LLM返回新字段: {list(new_fields.keys())}")
                                # 合并新旧XPath
                                for name, new_xpath in new_fields.items():
                                    if name in fields and new_xpath:
                                        _old = fields[name] if isinstance(fields[name], str) else fields[name].get("xpath", "")
                                        fields[name] = merge_xpath(_old, new_xpath)
                                    elif new_xpath:
                                        fields[name] = new_xpath
                                log(f"合并后content: {fields.get('content', '')}")
                                save_fields_to_cache(fields)
                except Exception as e:
                    log(f"LLM重试失败: {e}")

        if not success:
            failed += 1
        time.sleep(1)

    log(f"解析完成: {parsed} 条成功, {failed} 条失败")


if __name__ == "__main__":
    parse()
