"""Script generation using fixed templates - fast, no LLM needed."""
import os
import json
from app.config import settings


def escape_xpath(xpath: str) -> str:
    """Escape XPath for Python string."""
    if not xpath:
        return '""'
    if '"' not in xpath:
        return f'"{xpath}"'
    if "'" not in xpath:
        return f"'{xpath}'"
    return f'"""{xpath}"""'


def generate_crawl_script(task_id: int, config: dict) -> str:
    """生成采集脚本 - 固定模板，只替换配置"""
    url = config.get("url", "")
    engine = config.get("engine", "requests")
    max_pages = config.get("max_pages", 5)
    interval = config.get("interval", 2)
    detail_link_xpath = config.get("detail_link_xpath", "")
    next_xpath = config.get("next_xpath", "")
    page_url_template = config.get("page_url_template", "")
    # 标准化page_url_template：双花括号转单花括号
    if page_url_template:
        page_url_template = page_url_template.replace("{{", "{").replace("}}", "}")
    db_host = config.get("db_host", "localhost")
    db_port = config.get("db_port", 3306)
    db_name = config.get("db_name", "")
    db_table = config.get("db_table", "crawler_feachdata")
    db_user = config.get("db_user", "root")
    db_password = config.get("db_password", "")
    spider_name = config.get("spider_name", f"spider_{task_id}")
    task_name = config.get("task_name", "")
    fields = config.get("fields", {})
    user_agent = config.get("user_agent", "")
    custom_headers = config.get("custom_headers", "")
    cookies = config.get("cookies", "")
    proxy = config.get("proxy", "")
    timeout = config.get("timeout", 30)

    return f'''# -*- coding: utf-8 -*-
"""采集脚本 - 任务{task_id}"""
import time
import pymysql
import hashlib
from lxml import html as lxml_html
from urllib.parse import urljoin

# 配置
URL = {escape_xpath(url)}
ENGINE = {escape_xpath(engine)}
MAX_PAGES = {max_pages}
INTERVAL = {interval}
DETAIL_LINK_XPATH = {escape_xpath(detail_link_xpath)}
NEXT_XPATH = {escape_xpath(next_xpath)}
PAGE_URL_TEMPLATE = {escape_xpath(page_url_template)}

DB_HOST = {escape_xpath(db_host)}
DB_PORT = {db_port}
DB_NAME = {escape_xpath(db_name)}
DB_TABLE = {escape_xpath(db_table)}
DB_USER = {escape_xpath(db_user)}
DB_PASSWORD = {escape_xpath(db_password)}
SPIDER_NAME = {escape_xpath(spider_name)}
TASK_NAME = {escape_xpath(task_name)}
LLM_CONFIG_ID = {config.get("llm_config_id") or "None"}

# 请求设置
USER_AGENT = {escape_xpath(user_agent)}
CUSTOM_HEADERS = {escape_xpath(custom_headers)}
COOKIES = {escape_xpath(cookies)}
PROXY = {escape_xpath(proxy)}
TIMEOUT = {timeout}

# 字段配置（JSON字符串，需要解析为字典）
_fields_json = {escape_xpath(json.dumps(fields, ensure_ascii=False))}
fields = json.loads(_fields_json) if isinstance(_fields_json, str) else _fields_json


def log(msg):
    try:
        print(f"[SPIDER] {{msg}}", flush=True)
    except UnicodeEncodeError:
        print(f"[SPIDER] {{msg.encode('utf-8', errors='replace').decode('utf-8', errors='replace')}}", flush=True)


def trans_date(value):
    """将各种日期格式统一为 YYYY-MM-DD HH:MM:SS，支持多个日期取第一个"""
    import re
    if not value or not str(value).strip():
        return ""
    s = str(value).strip()
    # 移除"发布时间："等前缀
    s = re.sub(r'^[^\\dA-Za-z]*', '', s)
    # 中文日期替换
    s = re.sub(r'(\\d{{4}})年(\\d{{1,2}})月(\\d{{1,2}})日', r'\\1-\\2-\\3', s)
    s = re.sub(r'(\\d{{4}})年(\\d{{1,2}})月', r'\\1-\\2-01', s)
    s = re.sub(r'(\\d{{4}})年', r'\\1-01-01', s)
    from dateutil import parser as date_parser
    # 尝试直接解析整个字符串
    try:
        dt = date_parser.parse(s, fuzzy=True)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        pass
    # 按空格分割，找包含时间AM/PM的日期
    tokens = s.split()
    for i, token in enumerate(tokens):
        # 检查token是否包含AM或PM（如 "3:57PM"）
        if re.search(r'\\d:\\d{2}\\s*(?:AM|PM)', token, re.IGNORECASE) and i >= 3:
            candidate = ' '.join(tokens[max(0, i - 4):i + 1])
            try:
                dt = date_parser.parse(candidate, fuzzy=True)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                continue
    # 退而求其次，尝试解析每个token组合
    for i in range(len(tokens)):
        for j in range(i + 3, min(i + 8, len(tokens) + 1)):
            candidate = ' '.join(tokens[i:j])
            try:
                dt = date_parser.parse(candidate, fuzzy=True)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                continue
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
            f"INSERT IGNORE INTO `{{DB_TABLE}}` (url, solrid, spider_name, parseflag, creationtime) "
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
        resp = requests.get(url, headers={{"User-Agent": "Mozilla/5.0"}}, timeout=30)
        # 智能编码检测
        encoding = None
        ct = resp.headers.get('content-type', '')
        if 'charset=' in ct:
            encoding = ct.split('charset=')[-1].strip()
        if not encoding or encoding.lower() in ('iso-8859-1', 'latin-1', 'ascii'):
            import re as _re
            m = _re.search(rb'charset[=\\"\\s]+([a-zA-Z0-9_-]+)', resp.content[:3000], _re.I)
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
        log(f"第{{page_num}}页: {{current_url}}")

        try:
            html = fetch_page(current_url)
            tree = lxml_html.fromstring(html)

            # 提取详情页链接
            links = tree.xpath(DETAIL_LINK_XPATH)
            log(f"找到 {{len(links)}} 个链接")

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
            log(f"错误: {{e}}")
            break

    log(f"采集完成: 新增 {{saved}} 条URL")


if __name__ == "__main__":
    crawl()
'''


def generate_parse_script(task_id: int, config: dict) -> str:
    """生成解析脚本 - 固定模板，只替换字段XPath"""
    fields = config.get("fields", {})
    engine = config.get("engine", "requests")
    db_host = config.get("db_host", "localhost")
    db_port = config.get("db_port", 3306)
    db_name = config.get("db_name", "")
    db_table = config.get("db_table", "crawler_feachdata")
    db_user = config.get("db_user", "root")
    db_password = config.get("db_password", "")
    spider_name = config.get("spider_name", f"spider_{task_id}")
    task_name = config.get("task_name", "")

    # 生成字段提取代码（支持 xpath 和 constant 类型）
    field_extractions = ""
    for name, field_conf in fields.items():
        # 兼容旧格式（直接是 xpath 字符串）
        if isinstance(field_conf, str):
            field_type = "xpath"
            xpath_val = field_conf
            constant_val = ""
        else:
            field_type = field_conf.get("type", "xpath")
            xpath_val = field_conf.get("xpath", "")
            constant_val = field_conf.get("value", "")

        if field_type == "constant":
            # 常量值：直接赋值
            field_extractions += f'''
            try:
                data["{name}"] = {escape_xpath(constant_val)}
            except:
                data["{name}"] = {escape_xpath(constant_val)}'''
        else:
            # XPath 提取
            _sep = chr(123) + "|" + chr(125) if name in ("zuozhe", "author", "zuozhedanwei", "author_addrs", "keyword", "keyword_eng") else " "
            field_extractions += f'''
            try:
                vals = tree.xpath({escape_xpath(xpath_val)})
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
                _sep = {_sep!r}
                _val = _sep.join(texts) if texts else ""
                if "{name}" in ("chubanriqi", "releasetime", "creationtime", "lastmodifiedtime", "upload_time"):
                    _val = trans_date(_val)
                data["{name}"] = _val
            except:
                data["{name}"] = ""'''

    return f'''# -*- coding: utf-8 -*-
"""解析脚本 - 任务{task_id}"""
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
ENGINE = {escape_xpath(engine)}
DB_HOST = {escape_xpath(db_host)}
DB_PORT = {db_port}
DB_NAME = {escape_xpath(db_name)}
DB_TABLE = {escape_xpath(db_table)}
DB_USER = {escape_xpath(db_user)}
DB_PASSWORD = {escape_xpath(db_password)}
SPIDER_NAME = {escape_xpath(spider_name)}
TASK_NAME = {escape_xpath(task_name)}
LLM_CONFIG_ID = {config.get("llm_config_id") or "None"}

# 请求设置
USER_AGENT = {escape_xpath(config.get("user_agent", ""))}
CUSTOM_HEADERS = {escape_xpath(config.get("custom_headers", ""))}
COOKIES = {escape_xpath(config.get("cookies", ""))}
PROXY = {escape_xpath(config.get("proxy", ""))}
TIMEOUT = {config.get("timeout", 30)}

# 字段配置（JSON字符串，需要解析为字典）
_fields_json = {escape_xpath(json.dumps(fields, ensure_ascii=False))}
fields = json.loads(_fields_json) if isinstance(_fields_json, str) else _fields_json


def log(msg):
    try:
        print(f"[PARSE] {{msg}}", flush=True)
    except UnicodeEncodeError:
        print(f"[PARSE] {{msg.encode('utf-8', errors='replace').decode('utf-8', errors='replace')}}", flush=True)


def get_db():
    return pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER,
                          password=DB_PASSWORD, database=DB_NAME,
                          charset='utf8mb4', connect_timeout=10)


def get_unparsed_urls(limit=100):
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT id, url FROM `{{DB_TABLE}}` WHERE spider_name = %s AND (parseflag = 0 OR parseflag IS NULL) LIMIT %s",
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
                set_clauses.append(f"`{{k}}` = %s")
                values.append(v)
        # content为空时设parseflag=0，下次重新解析
        _parseflag = 1 if data.get("content") else 0
        set_clauses.append(f"`parseflag` = {{_parseflag}}")
        set_clauses.append("`lastmodifiedtime` = NOW()")
        values.append(record_id)
        sql = f"UPDATE `{{DB_TABLE}}` SET {{', '.join(set_clauses)}} WHERE id = %s"
        cursor.execute(sql, values)
        conn.commit()
    finally:
        conn.close()


def fetch_page(url):
    """根据引擎获取页面"""
    # 构建请求头
    headers = {{"User-Agent": USER_AGENT or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}}
    if CUSTOM_HEADERS:
        try:
            import json as _json
            custom = _json.loads(CUSTOM_HEADERS) if isinstance(CUSTOM_HEADERS, str) else CUSTOM_HEADERS
            headers.update(custom)
        except Exception:
            pass
    # 构建cookies
    cookies_dict = None
    if COOKIES:
        try:
            import json as _json
            cookies_dict = _json.loads(COOKIES) if isinstance(COOKIES, str) else COOKIES
        except Exception:
            pass
    # 构建代理
    proxies = None
    if PROXY:
        proxies = {{"http": PROXY, "https": PROXY}}

    if ENGINE == "playwright":
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until='networkidle', timeout=60000)
            content = page.content()
            browser.close()
            return content
    else:
        import requests
        resp = requests.get(url, headers=headers, cookies=cookies_dict, proxies=proxies, timeout=TIMEOUT)
        # 智能编码检测
        encoding = None
        ct = resp.headers.get('content-type', '')
        if 'charset=' in ct:
            encoding = ct.split('charset=')[-1].strip()
        if not encoding or encoding.lower() in ('iso-8859-1', 'latin-1', 'ascii'):
            import re as _re
            m = _re.search(rb'charset[=\\"\\s]+([a-zA-Z0-9_-]+)', resp.content[:3000], _re.I)
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
    data = {{}}
    _multi_value_fields = {{"zuozhe", "author", "zuozhedanwei", "author_addrs", "keyword", "keyword_eng"}}
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
    s = re.sub(r'^[^\\dA-Za-z]*', '', s)
    s = re.sub(r'(\\d{{4}})年(\\d{{1,2}})月(\\d{{1,2}})日', r'\\1-\\2-\\3', s)
    s = re.sub(r'(\\d{{4}})年(\\d{{1,2}})月', r'\\1-\\2-01', s)
    s = re.sub(r'(\\d{{4}})年', r'\\1-01-01', s)
    try:
        from dateutil import parser as date_parser
        dt = date_parser.parse(s, fuzzy=True)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        tokens = s.split()
        for i, token in enumerate(tokens):
            if re.search(r'\\d:\\d{{2}}\\s*(?:AM|PM)', token, re.IGNORECASE) and i >= 3:
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
        log(f"缓存规则失败: {{e}}")


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
    log(f"待解析: {{len(urls)}} 条")
    parsed = 0
    failed = 0

    for record_id, url in urls:
        success = False
        html = ""
        for attempt in range(3):
            try:
                html = fetch_page(url)
                tree = lxml_html.fromstring(html)
                data = {{"url": url, "spider_name": SPIDER_NAME}}
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
                    log(f"解析成功: {{url}}")
                    break
                else:
                    log(f"content和abstract为空，第{{attempt+1}}次重试: {{url}}")
            except Exception as e:
                log(f"解析异常: {{url}} - {{e}}")

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
                                          headers={{"Authorization": f"Bearer {{api_key}}", "Content-Type": "application/json"}},
                                          json={{"model": model, "messages": [{{"role": "user", "content": prompt}}], "temperature": 0.1, "max_tokens": 4000}},
                                          timeout=llm_timeout)
                        if resp.status_code == 200:
                            result = resp.json()["choices"][0]["message"]["content"]
                            _lb2 = chr(123)
                            _rb2 = chr(125)
                            match = re.search(_lb2 + r'[\\s\\S]*' + _rb2, result)
                            if match:
                                new_fields = json.loads(match.group())
                                log(f"LLM返回新字段: {{list(new_fields.keys())}}")
                                # 合并新旧XPath
                                for name, new_xpath in new_fields.items():
                                    if name in fields and new_xpath:
                                        _old = fields[name] if isinstance(fields[name], str) else fields[name].get("xpath", "")
                                        fields[name] = merge_xpath(_old, new_xpath)
                                    elif new_xpath:
                                        fields[name] = new_xpath
                                log(f"合并后content: {{fields.get('content', '')}}")
                                save_fields_to_cache(fields)
                except Exception as e:
                    log(f"LLM重试失败: {{e}}")

        if not success:
            failed += 1
        time.sleep(1)

    log(f"解析完成: {{parsed}} 条成功, {{failed}} 条失败")


if __name__ == "__main__":
    parse()
'''


def generate_full_script(task_id: int, config: dict) -> str:
    """生成完整脚本：采集列表页 + 智能分析详情页 + 解析数据 + 规则缓存"""
    # 生成配置的字段JSON
    configured_fields = config.get("fields", {})
    fields_json = json.dumps(configured_fields, ensure_ascii=False)

    # 标准化page_url_template：双花括号转单花括号
    page_url_template = config.get("page_url_template", "")
    if page_url_template:
        page_url_template = page_url_template.replace("{{", "{").replace("}}", "}")

    # 提取task_name
    task_name = config.get("task_name", "")
    spider_name = config.get("spider_name", f"spider_{task_id}")

    return f'''# -*- coding: utf-8 -*-
"""智能采集脚本 - 任务{task_id}
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
URL = {escape_xpath(config.get("url", ""))}
ENGINE = {escape_xpath(config.get("engine", "requests"))}
MAX_PAGES = {config.get("max_pages", 5)}
INTERVAL = {config.get("interval", 2)}
DETAIL_LINK_XPATH = {escape_xpath(config.get("detail_link_xpath", ""))}
PAGINATION_TYPE = {escape_xpath(config.get("pagination_type", "next_button"))}
NEXT_XPATH = {escape_xpath(config.get("next_xpath", ""))}
PAGE_URL_TEMPLATE = {escape_xpath(page_url_template)}
PAGE_COUNT = {config.get("page_count", 0)}
LLM_CONFIG_ID = {config.get("llm_config_id") or "None"}

# 任务配置的字段（专业采集配置的 fields 优先使用）
CONFIGURED_FIELDS = {fields_json}

DB_HOST = {escape_xpath(config.get("db_host", "localhost"))}
DB_PORT = {config.get("db_port", 3306)}
DB_NAME = {escape_xpath(config.get("db_name", ""))}
DB_TABLE = {escape_xpath(config.get("db_table", "crawler_feachdata"))}
DB_USER = {escape_xpath(config.get("db_user", "root"))}
DB_PASSWORD = {escape_xpath(config.get("db_password", ""))}
SPIDER_NAME = {escape_xpath(spider_name)}
TASK_NAME = {escape_xpath(task_name)}
LLM_CONFIG_ID = {config.get("llm_config_id") or "None"}

# 请求设置
USER_AGENT = {escape_xpath(config.get("user_agent", ""))}
CUSTOM_HEADERS = {escape_xpath(config.get("custom_headers", ""))}
COOKIES = {escape_xpath(config.get("cookies", ""))}
PROXY = {escape_xpath(config.get("proxy", ""))}
TIMEOUT = {config.get("timeout", 30)}

# 字段配置（JSON字符串，需要解析为字典）
_fields_json = {escape_xpath(json.dumps(configured_fields, ensure_ascii=False))}
fields = json.loads(_fields_json) if isinstance(_fields_json, str) else _fields_json


def log(msg):
    try:
        print(f"[SPIDER] {{msg}}", flush=True)
    except UnicodeEncodeError:
        print(f"[SPIDER] {{msg.encode('utf-8', errors='replace').decode('utf-8', errors='replace')}}", flush=True)


def trans_date(value):
    """将各种日期格式统一为 YYYY-MM-DD HH:MM:SS，支持多个日期取第一个"""
    import re
    if not value or not str(value).strip():
        return ""
    s = str(value).strip()
    # 移除"发布时间："等前缀
    s = re.sub(r'^[^\\dA-Za-z]*', '', s)
    # 中文日期替换
    s = re.sub(r'(\\d{{4}})年(\\d{{1,2}})月(\\d{{1,2}})日', r'\\1-\\2-\\3', s)
    s = re.sub(r'(\\d{{4}})年(\\d{{1,2}})月', r'\\1-\\2-01', s)
    s = re.sub(r'(\\d{{4}})年', r'\\1-01-01', s)
    from dateutil import parser as date_parser
    # 尝试直接解析整个字符串
    try:
        dt = date_parser.parse(s, fuzzy=True)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        pass
    # 按空格分割，找包含时间AM/PM的日期
    tokens = s.split()
    for i, token in enumerate(tokens):
        # 检查token是否包含AM或PM（如 "3:57PM"）
        if re.search(r'\\d:\\d{2}\\s*(?:AM|PM)', token, re.IGNORECASE) and i >= 3:
            candidate = ' '.join(tokens[max(0, i - 4):i + 1])
            try:
                dt = date_parser.parse(candidate, fuzzy=True)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                continue
    # 退而求其次，尝试解析每个token组合
    for i in range(len(tokens)):
        for j in range(i + 3, min(i + 8, len(tokens) + 1)):
            candidate = ' '.join(tokens[i:j])
            try:
                dt = date_parser.parse(candidate, fuzzy=True)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                continue
    return value


def get_db():
    return pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER,
                          password=DB_PASSWORD, database=DB_NAME,
                          charset='utf8mb4', connect_timeout=10)


def get_domain(url):
    """从URL提取域名"""
    parsed = urlparse(url)
    return parsed.netloc or parsed.hostname or ""


def fetch_page(url):
    """获取页面HTML - 六级降级：requests → curlcffi → httpx → playwright → drission → scrapling"""
    # 构建请求头
    headers = {{"User-Agent": USER_AGENT or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}}
    if CUSTOM_HEADERS:
        try:
            import json as _json
            custom = _json.loads(CUSTOM_HEADERS) if isinstance(CUSTOM_HEADERS, str) else CUSTOM_HEADERS
            headers.update(custom)
        except Exception:
            pass
    # 构建cookies
    cookies_dict = None
    if COOKIES:
        try:
            import json as _json
            cookies_dict = _json.loads(COOKIES) if isinstance(COOKIES, str) else COOKIES
        except Exception:
            pass
    # 构建代理
    proxies = None
    if PROXY:
        proxies = {{"http": PROXY, "https": PROXY}}
    import os

    # 第一级：requests（静态网页首选）
    try:
        import requests as req
        resp = req.get(url, headers=headers, cookies=cookies_dict, proxies=proxies, timeout=TIMEOUT, allow_redirects=True)
        # 智能编码检测
        _enc = None
        _ct = resp.headers.get('content-type', '')
        if 'charset=' in _ct:
            _enc = _ct.split('charset=')[-1].strip()
        if not _enc or _enc.lower() in ('iso-8859-1', 'latin-1', 'ascii'):
            import re as _re
            _m = _re.search(rb'charset[=\\\\\"\\\\\\s]+([a-zA-Z0-9_-]+)', resp.content[:3000], _re.I)
            if _m:
                _enc = _m.group(1).decode('ascii', errors='ignore')
        if not _enc or _enc.lower() in ('iso-8859-1', 'latin-1', 'ascii'):
            try:
                resp.content.decode('utf-8')
                _enc = 'utf-8'
            except:
                _enc = resp.apparent_encoding or 'utf-8'
        resp.encoding = _enc
        html = resp.text
        if len(html) > 1000 and '<html' in html.lower():
            return html
    except Exception as e:
        log(f"requests失败: {{e}}")

    # 第二级：curlcffi（高防、JA3/TP指纹模拟）
    try:
        from curl_cffi.requests import Session
        with Session(impersonate="chrome") as s:
            resp = s.get(url, headers=headers, timeout=30)
            html = resp.text
            if len(html) > 1000 and '<html' in html.lower():
                return html
    except Exception as e:
        log(f"curlcffi失败: {{e}}")

    # 第三级：httpx（HTTP/2支持）
    try:
        resp = httpx.get(url, headers=headers, timeout=30, follow_redirects=True, http2=True)
        html = resp.text
        if len(html) > 1000 and '<html' in html.lower():
            return html
    except Exception as e:
        log(f"httpx失败: {{e}}")

    # 第四级：playwright（动态JS渲染）
    try:
        playwright_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", r"C:\hermes\cpython-3.12.13\python312\playwright")
        exec_path = None
        if playwright_path:
            for root, dirs, files in os.walk(playwright_path):
                for f in files:
                    if f in ["chrome.exe", "chromium.exe", "chrome-headless-shell.exe"]:
                        exec_path = os.path.join(root, f)
                        break
                if exec_path:
                    break

        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            launch_args = {{"headless": True}}
            if exec_path:
                launch_args["executable_path"] = exec_path
            browser = p.chromium.launch(**launch_args)
            page = browser.new_page()
            page.goto(url, wait_until='networkidle', timeout=30000)
            content = page.content()
            browser.close()
            if len(content) > 1000:
                return content
    except Exception as e:
        log(f"playwright失败: {{e}}")

    # 第五级：drission（混合模式）
    try:
        from DrissionPage import SessionPage
        page = SessionPage()
        page.get(url)
        html = page.html
        if len(html) > 1000:
            return html
    except Exception as e:
        log(f"drission失败: {{e}}")

    # 第六级：scrapling（专门突破Cloudflare）
    try:
        from scrapling.fetchers import StealthySession
        with StealthySession(headless=True, solve_cloudflare=True) as session:
            page = session.fetch(url=url, google_search=False, timeout=60000)
            html = page.html_content
            if html and len(html) > 1000:
                return html
    except Exception as e:
        log(f"scrapling失败: {{e}}")

    return ""


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
        # LLM配置在app数据库（spider）中，不在数据源数据库中
        import os
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
            headers={{"Authorization": f"Bearer {{api_key}}", "Content-Type": "application/json"}},
            json={{"model": model, "messages": [{{"role": "user", "content": prompt}}], "temperature": 0.1, "max_tokens": 4000}},
            timeout=timeout
        )

        if resp.status_code == 200:
            result = resp.json()
            return result["choices"][0]["message"]["content"]
        else:
            log(f"LLM调用失败: {{resp.status_code}}")
            return None
    except Exception as e:
        log(f"LLM调用异常: {{e}}")
        return None


def analyze_detail_page(html):
    """用LLM分析详情页，返回字段XPath"""
    cleaned = clean_html(html)
    _lb = chr(123)
    _rb = chr(125)
    _example = _lb + '"title": "标题XPath/text()", "content": "正文XPath", "chubanriqi": "发布日期XPath/text()", "zuozhe": "作者XPath/text()", "keyword": "关键词XPath/text()", "abstract": "摘要XPath/text()"' + _rb
    _nl = chr(10)
    prompt = ("分析详情页HTML，识别内容字段的XPath。只输出JSON：" + _nl + _nl
              + _example + _nl + _nl
              + "规则：" + _nl
              + "1. content字段必须返回，找文章正文所在的div，用//text()提取所有文本" + _nl
              + "2. 如果找不到single-blog-content，找最大的文本块div" + _nl
              + "3. title和content是必填字段，其他字段可选" + _nl
              + "4. 提取文本的字段加 /text()" + _nl + _nl
              + "HTML：" + _nl + cleaned[:30000])

    result = call_llm(prompt)
    if result:
        log(f"LLM原始返回: {{result[:200]}}")
        try:
            _lb = chr(123)
            _rb = chr(125)
            match = re.search(_lb + r'[\s\S]*' + _rb, result)
            if match:
                parsed = json.loads(match.group())
                log(f"LLM解析结果: {{parsed}}")
                return parsed
        except Exception as e:
            log(f"LLM JSON解析失败: {{e}}")
    _empty = {{}}
    return _empty


def get_cached_fields():
    """从数据库获取缓存的字段XPath"""
    domain = get_domain(URL)
    try:
        import os
        conn = pymysql.connect(
            host=os.environ.get("SPIDER_APP_DB_HOST", "localhost"),
            port=int(os.environ.get("SPIDER_APP_DB_PORT", "3306")),
            user=os.environ.get("SPIDER_APP_DB_USER", "root"),
            password=os.environ.get("SPIDER_APP_DB_PASSWORD", ""),
            database=os.environ.get("SPIDER_APP_DB_NAME", "spider"),
            charset='utf8mb4', connect_timeout=10
        )
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
        import os
        conn = pymysql.connect(
            host=os.environ.get("SPIDER_APP_DB_HOST", "localhost"),
            port=int(os.environ.get("SPIDER_APP_DB_PORT", "3306")),
            user=os.environ.get("SPIDER_APP_DB_USER", "root"),
            password=os.environ.get("SPIDER_APP_DB_PASSWORD", ""),
            database=os.environ.get("SPIDER_APP_DB_NAME", "spider"),
            charset='utf8mb4', connect_timeout=10
        )
        cursor = conn.cursor()
        # 检查是否已存在
        cursor.execute("SELECT id, field_xpaths FROM crawl_rules WHERE domain = %s", (domain,))
        row = cursor.fetchone()

        if row:
            # 合并新旧字段
            rule_id, old_fields = row
            old_fields = json.loads(old_fields) if isinstance(old_fields, str) and old_fields else (old_fields or {{}})

            # 对每个字段，如果新的XPath不同，用|合并
            merged = {{}}
            all_keys = set(list(old_fields.keys()) + list(fields.keys()))
            for key in all_keys:
                old_xpath = old_fields.get(key, "")
                new_xpath = fields.get(key, "")
                if old_xpath and new_xpath and old_xpath != new_xpath:
                    merged[key] = f"{{old_xpath}} | {{new_xpath}}"
                elif new_xpath:
                    merged[key] = new_xpath
                else:
                    merged[key] = old_xpath

            cursor.execute(
                "UPDATE crawl_rules SET field_xpaths = %s, updated_at = %s WHERE id = %s",
                (json.dumps(merged), datetime.datetime.now(), rule_id)
            )
            log(f"规则已更新合并: {{domain}}")
        else:
            cursor.execute(
                "INSERT INTO crawl_rules (domain, url_pattern, field_xpaths, is_active, created_at, updated_at) VALUES (%s, %s, %s, 1, %s, %s)",
                (domain, URL, json.dumps(fields), datetime.datetime.now(), datetime.datetime.now())
            )
            log(f"规则已缓存: {{domain}}")

        conn.commit()
    except Exception as e:
        log(f"缓存规则失败: {{e}}")


def merge_xpath(old_xpath, new_xpath):
    """合并两个XPath，确保XPath以//text()或/text()结尾"""
    def _ensure_text(xp):
        if not xp:
            return xp
        xp = xp.strip()
        # 如果XPath不以text()结尾，添加//text()
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


def save_url(url):
    """保存URL到数据库"""
    solrid = hashlib.md5(url.encode()).hexdigest()
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"INSERT IGNORE INTO `{{DB_TABLE}}` (url, solrid, spider_name, parseflag, creationtime) VALUES (%s, %s, %s, 0, NOW())",
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

    # 如果是JS翻页，使用playwright采集
    if PAGINATION_TYPE == "js_click":
        return _crawl_js_click(saved)

    for page_num in range(1, MAX_PAGES + 1):
        log(f"采集第{{page_num}}页: {{current_url}}")
        try:
            html = fetch_page(current_url)
            tree = lxml_html.fromstring(html)

            links = tree.xpath(DETAIL_LINK_XPATH)
            log(f"找到 {{len(links)}} 个链接")

            for link in links:
                href = link if isinstance(link, str) else link.get("href", "")
                if href:
                    full_url = urljoin(current_url, href)
                    if save_url(full_url):
                        saved += 1

            # 翻页
            if PAGINATION_TYPE == "next_button" and NEXT_XPATH:
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
            log(f"采集错误: {{e}}")
            break

    log(f"采集完成: 新增 {{saved}} 条URL")
    return saved


def _crawl_drission(saved):
    """使用DrissionPage进行JS翻页采集"""
    try:
        from DrissionPage import ChromiumPage
    except ImportError:
        log("DrissionPage未安装")
        return saved

    try:
        page = ChromiumPage()
        page.get(URL)
        log(f"Drission页面加载完成: {{URL}}")

        max_page = PAGE_COUNT if PAGE_COUNT > 0 else MAX_PAGES
        log(f"Drission计划采集 {{max_page}} 页")

        for page_num in range(1, max_page + 1):
            log(f"Drission翻页-第{{page_num}}页")
            try:
                page.wait.load_start()
                html = page.html
                log(f"页面内容长度: {{len(html)}}")
                tree = lxml_html.fromstring(html)

                # 提取详情页链接
                links = tree.xpath(DETAIL_LINK_XPATH)
                log(f"找到 {{len(links)}} 个链接")
                for link in links:
                    href = link if isinstance(link, str) else link.get("href", "")
                    if href:
                        full_url = urljoin(URL, href)
                        if save_url(full_url):
                            saved += 1

                # 点击下一页
                if page_num < max_page:
                    clicked = False
                    _np = str(page_num + 1)

                    # 尝试paged属性
                    try:
                        btn = page.ele('a:paged@{{_np}}')
                        if btn:
                            btn.click()
                            clicked = True
                            log("Drission通过paged属性点击第" + _np + "页")
                    except:
                        pass

                    # 尝试data-page-number属性
                    if not clicked:
                        try:
                            btn = page.ele('a:data-page-number@{{_np}}')
                            if btn:
                                btn.click()
                                clicked = True
                                log("Drission通过data-page-number属性点击第" + _np + "页")
                        except:
                            pass

                    # 尝试下一页链接
                    if not clicked:
                        try:
                            btn = page.ele('text:下一页')
                            if btn:
                                btn.click()
                                clicked = True
                                log("Drission点击下一页链接")
                        except:
                            pass

                    if not clicked:
                        log("Drission无法点击第" + _np + "页，停止翻页")
                        break

                    page.wait(2)
            except Exception as e:
                log(f"Drission翻页第{{page_num}}页出错: {{e}}")
                break

        page.quit()
    except Exception as e:
        log(f"Drission运行异常: {{e}}")

    log(f"Drission采集完成: 新增 {{saved}} 条URL")
    return saved


def _crawl_fallback(saved):
    """最终降级 - 用requests采集首页"""
    log("使用requests降级采集首页")
    try:
        html = fetch_page(URL)
        if not html:
            log("无法获取页面")
            return saved
        tree = lxml_html.fromstring(html)
        links = tree.xpath(DETAIL_LINK_XPATH)
        log(f"找到 {{len(links)}} 个链接")
        for link in links:
            href = link if isinstance(link, str) else link.get("href", "")
            if href:
                full_url = urljoin(URL, href)
                if save_url(full_url):
                    saved += 1
    except Exception as e:
        log(f"降级采集失败: {{e}}")
    log(f"降级采集完成: 新增 {{saved}} 条URL")
    return saved


def _crawl_js_click(saved):
    """JS翻页采集 - 使用playwright点击页码按钮"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log("playwright未安装，尝试Drission降级")
        return _crawl_drission(saved)

    try:
        pw = sync_playwright().start()
    except Exception as e:
        log(f"playwright启动失败({{e}})，尝试Drission降级")
        return _crawl_drission(saved)

    browser = None
    try:
        # 自动查找playwright浏览器路径
        import os as _os
        _pw_path = _os.environ.get("PLAYWRIGHT_BROWSERS_PATH", r"C:\hermes\cpython-3.12.13\python312\playwright")
        _exec_path = None
        if _pw_path:
            for _root, _dirs, _files in _os.walk(_pw_path):
                for _f in _files:
                    if _f in ("chrome.exe", "chromium.exe", "chrome-headless-shell.exe"):
                        _exec_path = _os.path.join(_root, _f)
                        break
                if _exec_path:
                    break
        _launch_args = {{"headless": True}}
        if _exec_path:
            _launch_args["executable_path"] = _exec_path
            log(f"使用浏览器: {{_exec_path}}")
        browser = pw.chromium.launch(**_launch_args)
        page = browser.new_page()
        # 使用domcontentloaded更快加载，大页面用更长超时
        try:
            page.goto(URL, wait_until='domcontentloaded', timeout=60000)
        except Exception as e:
            log(f"页面加载超时，尝试继续: {{e}}")
        page.wait_for_timeout(3000)  # 额外等待3秒让JS执行
        log(f"页面加载完成: {{URL}}")

        max_page = PAGE_COUNT if PAGE_COUNT > 0 else MAX_PAGES
        log(f"计划采集 {{max_page}} 页")
        for page_num in range(1, max_page + 1):
            log(f"JS翻页-第{{page_num}}页")
            try:
                # 等待页面加载（使用domcontentloaded避免超时）
                try:
                    page.wait_for_load_state('domcontentloaded', timeout=30000)
                except:
                    pass
                page.wait_for_timeout(3000)  # 额外等待JS执行
                html = page.content()
                log(f"页面内容长度: {{len(html)}}")
                tree = lxml_html.fromstring(html)

                # 提取详情页链接
                links = tree.xpath(DETAIL_LINK_XPATH)
                log(f"找到 {{len(links)}} 个链接")
                for link in links:
                    href = link if isinstance(link, str) else link.get("href", "")
                    if href:
                        from urllib.parse import urljoin as _urljoin
                        full_url = _urljoin(URL, href)
                        if save_url(full_url):
                            saved += 1

                # 点击下一页
                if page_num < max_page:
                    # 尝试多种方式找到页码按钮并点击
                    clicked = False
                    next_page = page_num + 1
                    _np = str(next_page)

                    # 方式0：用paged或data-page-number属性点击
                    if not clicked:
                        try:
                            paged_btn = page.locator('a[paged="' + _np + '"]')
                            if paged_btn.count() > 0:
                                paged_btn.first.click()
                                clicked = True
                                log("通过paged属性点击第" + _np + "页")
                        except:
                            pass
                    if not clicked:
                        try:
                            dpn_btn = page.locator('a[data-page-number="' + _np + '"]')
                            if dpn_btn.count() > 0:
                                dpn_btn.first.click()
                                clicked = True
                                log("通过data-page-number属性点击第" + _np + "页")
                        except:
                            pass

                    # 方式1：点击"下一页"链接
                    if not clicked:
                        try:
                            next_link = page.locator('a:has-text("下一页")')
                            if next_link.count() > 0:
                                next_link.first.click()
                                clicked = True
                                log("点击下一页链接")
                        except Exception as e:
                            log("下一页链接点击失败: " + str(e))

                    # 方式2：用NEXT_XPATH（页码容器的XPath）
                    if not clicked and NEXT_XPATH:
                        try:
                            next_btn = page.locator(NEXT_XPATH).nth(page_num)
                            if next_btn.count() > 0:
                                next_btn.click()
                                clicked = True
                        except:
                            pass

                    # 方式3：点击包含页码数字的链接
                    if not clicked:
                        try:
                            page.locator("a:text-is('" + _np + "')").first.click()
                            clicked = True
                        except:
                            pass

                    # 方式4：JavaScript直接调用
                    if not clicked:
                        try:
                            page.evaluate("if(typeof goPage==='function') goPage(" + _np + "); else if(typeof page==='function') page(" + _np + ");")
                            clicked = True
                        except:
                            pass

                    if not clicked:
                        log("无法点击第" + _np + "页，停止翻页")
                        break

                    # 等待页面内容变化
                    page.wait_for_timeout(2000)
            except Exception as e:
                log(f"JS翻页采集第{{page_num}}页出错: {{e}}")
                break

    except Exception as e:
        log(f"playwright运行异常: {{e}}，尝试Drission降级")
        saved = _crawl_drission(saved)
        if saved == 0:
            log("Drission也未采集到数据，使用requests降级")
            saved = _crawl_fallback(saved)
    finally:
        if browser:
            try:
                browser.close()
            except:
                pass
        try:
            pw.stop()
        except:
            pass

    log(f"JS翻页采集完成: 新增 {{saved}} 条URL")
    return saved


def parse_with_retry(fields):
    """解析所有未解析的URL，失败时自动重新分析并合并XPath"""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT id, url FROM `{{DB_TABLE}}` WHERE spider_name = %s AND (parseflag = 0 OR parseflag IS NULL) LIMIT 1000",
            (SPIDER_NAME,)
        )
        urls = cursor.fetchall()
    finally:
        conn.close()

    log(f"待解析: {{len(urls)}} 条")
    parsed = 0
    failed_count = 0

    for record_id, url in urls:
        success = False
        for attempt in range(3):  # 最多重试2次
            try:
                html = fetch_page(url)
                tree = lxml_html.fromstring(html)
                data = {{"url": url, "spider_name": SPIDER_NAME}}

                # 多值字段列表：用特殊分隔符
                _sep_char = chr(123) + "|" + chr(125)
                _multi_value_fields = {"zuozhe", "author", "zuozhedanwei", "author_addrs", "keyword", "keyword_eng"}

                for name, field_conf in fields.items():
                    try:
                        # 兼容旧格式（直接是 xpath 字符串）
                        if isinstance(field_conf, str):
                            field_type = "xpath"
                            xpath_val = field_conf
                            constant_val = ""
                        else:
                            field_type = field_conf.get("type", "xpath")
                            xpath_val = field_conf.get("xpath", "")
                            constant_val = field_conf.get("value", "")

                        if field_type == "constant":
                            # 常量值：直接赋值
                            data[name] = constant_val
                        else:
                            # XPath 提取
                            # 尝试多个XPath（用|分隔的）
                            for single_xpath in xpath_val.split("|"):
                                single_xpath = single_xpath.strip()
                                if single_xpath:
                                    vals = tree.xpath(single_xpath)
                                    if vals:
                                        # 连接所有文本节点，过滤CSS和空文本
                                        texts = []
                                        for v in vals:
                                            if isinstance(v, str):
                                                text = v.strip()
                                                # 过滤CSS样式和空文本
                                                if text and not text.startswith('.') and len(text) > 5 and 'color' not in text and 'display' not in text:
                                                    texts.append(text)
                                            elif hasattr(v, 'text_content'):
                                                text = v.text_content().strip()
                                                if text and not text.startswith('.') and len(text) > 5:
                                                    texts.append(text)
                                        if texts:
                                            _sep = _sep_char if name in _multi_value_fields else " "
                                            data[name] = _sep.join(texts)
                                        break
                    except:
                        data[name] = ""

                # 日期字段标准化
                for _df in ("chubanriqi", "releasetime", "creationtime", "lastmodifiedtime", "upload_time"):
                    if _df in data and data[_df]:
                        data[_df] = trans_date(data[_df])

                # 检查是否提取到关键数据（title必须有值）
                has_title = bool(data.get("title"))
                has_data = has_title  # 只要有title就认为有数据

                if has_data:
                    data["solrid"] = hashlib.md5(url.encode()).hexdigest()
                    # 自动填充tag和crawlerserverurl
                    if not data.get("tag"):
                        data["tag"] = TASK_NAME
                    if not data.get("crawlerserverurl"):
                        try:
                            data["crawlerserverurl"] = urlparse(url).netloc
                        except:
                            pass

                    # 更新数据库
                    conn = get_db()
                    try:
                        cursor = conn.cursor()
                        set_clauses = []
                        values = []
                        for k, v in data.items():
                            if v is not None:
                                set_clauses.append(f"`{{k}}` = %s")
                                values.append(v)
                        # content为空时设parseflag=0，下次重新解析
                        _parseflag = 1 if data.get("content") else 0
                        set_clauses.append(f"`parseflag` = {{_parseflag}}")
                        set_clauses.append("`lastmodifiedtime` = NOW()")
                        values.append(record_id)
                        sql = f"UPDATE `{{DB_TABLE}}` SET {{', '.join(set_clauses)}} WHERE id = %s"
                        cursor.execute(sql, values)
                        conn.commit()
                    finally:
                        conn.close()

                    parsed += 1
                    if data.get("content"):
                        success = True
                        log(f"解析成功: {{url}}")
                        break
                    else:
                        log(f"title有值但content为空，重新分析: {{url}}")
                else:
                    log(f"提取不到数据，尝试重新分析: {{url}}")

            except Exception as e:
                log(f"解析异常: {{e}}")

            # 如果失败，重新分析并合并XPath
            if not success:
                log("重新分析详情页...")
                new_fields = analyze_detail_page(html)
                log(f"LLM返回: {{new_fields}}")
                if new_fields:
                    # 合并新旧XPath
                    for name, new_xpath in new_fields.items():
                        if name in fields and new_xpath:
                            fields[name] = merge_xpath(fields[name], new_xpath)
                        elif new_xpath:
                            fields[name] = new_xpath
                    # 显示合并后的字段和XPath
                    for _fn, _fv in fields.items():
                        if isinstance(_fv, str):
                            log(f"  {{_fn}}: {{_fv}}")
                        elif isinstance(_fv, dict):
                            log(f"  {{_fn}}: type={{_fv.get('type','xpath')}}, xpath={{_fv.get('xpath','')}}")
                    # 保存更新后的规则
                    save_fields_to_cache(fields)

        if not success:
            failed_count += 1

        time.sleep(1)

    log(f"解析完成: {{parsed}} 条成功, {{failed_count}} 条失败")
    return parsed, fields  # 返回更新后的字段


def main():
    """主流程"""
    log("===== 开始智能采集 =====")

    # 阶段1：采集列表页URL
    crawl()

    # 阶段2：获取详情页字段 - 优先使用任务配置的字段
    log("准备解析字段...")
    
    if CONFIGURED_FIELDS:
        log(f"使用任务配置字段: {{list(CONFIGURED_FIELDS.keys())}}")
        fields = CONFIGURED_FIELDS
    else:
        fields = get_cached_fields()

    if fields:
        log(f"使用字段: {{list(fields.keys())}}")
    else:
        log("无字段配置，进行LLM分析...")
        first_url = None
        conn = get_db()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT id, url FROM `{{DB_TABLE}}` WHERE spider_name = %s AND (parseflag = 0 OR parseflag IS NULL) LIMIT 1",
                (SPIDER_NAME,)
            )
            first_url = cursor.fetchone()
        finally:
            conn.close()

        if first_url:
            record_id, url = first_url
            log(f"分析详情页: {{url}}")
            try:
                html = fetch_page(url)
                fields = analyze_detail_page(html)
                log(f"识别到字段: {{list(fields.keys())}}")
                # 缓存成功的字段
                if fields:
                    save_fields_to_cache(fields)
            except Exception as e:
                log(f"详情页分析失败: {{e}}")

    # 备用字段
    if not fields:
        log("使用备用字段配置")
        fields = {{
            "title": "//h1/text()",
            "content": "//article//text()",
            "chubanriqi": "//time/@datetime",
        }}

    log(f"最终字段配置: {{fields}}")

    # 阶段3：解析所有详情页（带重试和XPath合并）
    parsed, final_fields = parse_with_retry(fields)

    # 保存最终的字段配置
    if final_fields != fields:
        save_fields_to_cache(final_fields)

    log(f"===== 采集完成: {{parsed}} 条数据已解析 =====")


if __name__ == "__main__":
    main()
'''


def save_script(task_id: int, script_type: str, code: str) -> str:
    """保存脚本到文件"""
    task_dir = os.path.join(settings.SCRIPTS_DIR, str(task_id))
    os.makedirs(task_dir, exist_ok=True)
    filepath = os.path.join(task_dir, f"{script_type}_spider.py")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)
    return filepath
