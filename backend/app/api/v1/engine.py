"""Engine API routes."""
import os
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.security import get_current_user
from app.engine.engine_factory import list_engines, get_engine
from app.engine import EngineConfig
from app.config import settings

router = APIRouter(prefix="/engines", tags=["Engines"], dependencies=[Depends(get_current_user)])

# 自定义引擎存储目录
ENGINES_DIR = os.path.join(settings.DATA_DIR, "custom_engines")


class EngineCreate(BaseModel):
    name: str
    description: str = ""
    code: str = ""


class EngineUpdate(BaseModel):
    description: Optional[str] = None
    code: Optional[str] = None


def ensure_engines_dir():
    """确保引擎目录存在"""
    os.makedirs(ENGINES_DIR, exist_ok=True)


def get_engine_filepath(name: str) -> str:
    """获取引擎文件路径"""
    return os.path.join(ENGINES_DIR, f"{name}.py")


def load_custom_engines():
    """加载所有自定义引擎"""
    ensure_engines_dir()
    engines = []
    if not os.path.exists(ENGINES_DIR):
        return engines
    for filename in os.listdir(ENGINES_DIR):
        if filename.endswith('.py'):
            name = filename[:-3]
            filepath = os.path.join(ENGINES_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                description = ""
                for line in content.split('\n'):
                    if line.startswith('# description:'):
                        description = line.split(':', 1)[1].strip()
                        break
                
                engines.append({
                    "name": name,
                    "description": description,
                    "code": content,
                    "is_builtin": False,
                })
            except Exception as e:
                print(f"Error loading engine {name}: {e}")
    return engines


# 内置引擎代码
BUILTIN_ENGINES = {
    "requests": {
        "description": "requests库，静态页面首选，简单易用",
        "code": '''# description: requests库，静态页面首选，简单易用
import requests

def fetch(url, headers=None, timeout=30, **kwargs):
    """
    获取网页源代码
    
    参数:
        url: 目标URL
        headers: 请求头字典
        timeout: 超时时间(秒)
        **kwargs: 其他参数(如proxy, cookies等)
    
    返回:
        str: 网页HTML源代码
    """
    proxy = kwargs.get('proxy')
    cookies = kwargs.get('cookies', {})
    
    proxies = {'http': proxy, 'https': proxy} if proxy else None
    
    session = requests.Session()
    response = session.get(
        url,
        headers=headers or {},
        timeout=timeout,
        proxies=proxies,
        cookies=cookies,
        verify=True,
    )
    
    # 自动检测编码
    if response.encoding and response.encoding.lower() in ('iso-8859-1', 'latin-1'):
        content_type = response.headers.get('content-type', '').lower()
        if 'charset=' in content_type:
            charset = content_type.split('charset=')[-1].strip().split(';')[0].strip()
            response.encoding = charset
        elif b'charset=utf-8' in response.content[:1000].lower():
            response.encoding = 'utf-8'
        elif b'charset=gbk' in response.content[:1000].lower() or b'charset=gb2312' in response.content[:1000].lower():
            response.encoding = 'gbk'
        else:
            response.encoding = response.apparent_encoding or 'utf-8'
    
    session.close()
    return response.text
''',
    },
    "httpx": {
        "description": "httpx库，支持HTTP/2，异步请求",
        "code": '''# description: httpx库，支持HTTP/2，异步请求
import httpx

def fetch(url, headers=None, timeout=30, **kwargs):
    """
    获取网页源代码 (httpx)
    
    参数:
        url: 目标URL
        headers: 请求头字典
        timeout: 超时时间(秒)
        **kwargs: 其他参数(如proxy, cookies等)
    
    返回:
        str: 网页HTML源代码
    """
    proxy = kwargs.get('proxy')
    cookies = kwargs.get('cookies', {})
    
    client_kwargs = {
        'timeout': httpx.Timeout(timeout),
        'follow_redirects': True,
        'http2': True,
    }
    
    if proxy:
        client_kwargs['proxy'] = proxy
    
    with httpx.Client(**client_kwargs) as client:
        response = client.get(url, headers=headers or {}, cookies=cookies)
        
        # 自动检测编码
        encoding = response.encoding
        if encoding and encoding.lower() in ('iso-8859-1', 'latin-1'):
            content_type = response.headers.get('content-type', '').lower()
            if 'charset=' in content_type:
                encoding = content_type.split('charset=')[-1].strip().split(';')[0].strip()
            else:
                encoding = 'utf-8'
        
        return response.content.decode(encoding or 'utf-8', errors='replace')
''',
    },
    "urllib3": {
        "description": "urllib3库，底层HTTP请求",
        "code": '''# description: urllib3库，底层HTTP请求
import urllib3
from urllib.parse import urlparse

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def fetch(url, headers=None, timeout=30, **kwargs):
    """
    获取网页源代码 (urllib3)
    
    参数:
        url: 目标URL
        headers: 请求头字典
        timeout: 超时时间(秒)
        **kwargs: 其他参数(如proxy, cookies等)
    
    返回:
        str: 网页HTML源代码
    """
    proxy = kwargs.get('proxy')
    
    if proxy:
        http = urllib3.ProxyManager(proxy, cert_reqs='CERT_NONE')
    else:
        http = urllib3.PoolManager(cert_reqs='CERT_NONE')
    
    response = http.request(
        'GET',
        url,
        headers=headers or {},
        timeout=timeout,
    )
    
    # 检测编码
    content_type = response.headers.get('Content-Type', '')
    encoding = 'utf-8'
    if 'charset=' in content_type:
        encoding = content_type.split('charset=')[-1].strip().split(';')[0].strip()
    
    return response.data.decode(encoding, errors='replace')
''',
    },
    "playwright": {
        "description": "Playwright浏览器，支持JS渲染和登录",
        "code": '''# description: Playwright浏览器，支持JS渲染和登录
import asyncio

def fetch(url, headers=None, timeout=30, **kwargs):
    """
    获取网页源代码 (Playwright)
    支持JavaScript渲染的动态页面
    
    参数:
        url: 目标URL
        headers: 请求头字典
        timeout: 超时时间(秒)
        **kwargs: 其他参数
    
    返回:
        str: 网页HTML源代码
    """
    from playwright.sync_api import sync_playwright
    
    def _fetch():
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=headers.get('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36') if headers else 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            )
            page = context.new_page()
            
            # 设置额外headers
            if headers:
                page.set_extra_http_headers(headers)
            
            page.goto(url, timeout=timeout * 1000, wait_until='networkidle')
            
            # 等待页面加载
            page.wait_for_load_state('networkidle')
            
            content = page.content()
            
            browser.close()
            return content
    
    return _fetch()
''',
    },
    "drission": {
        "description": "DrissionPage，国产浏览器自动化",
        "code": '''# description: DrissionPage，国产浏览器自动化
def fetch(url, headers=None, timeout=30, **kwargs):
    """
    获取网页源代码 (DrissionPage)
    支持JavaScript渲染，国产库，无需额外安装浏览器

    参数:
        url: 目标URL
        headers: 请求头字典
        timeout: 超时时间(秒)
        **kwargs: 其他参数

    返回:
        str: 网页HTML源代码
    """
    from DrissionPage import ChromiumPage, ChromiumOptions

    # 配置浏览器选项
    co = ChromiumOptions()
    co.headless(True)
    co.set_timeouts(timeout)

    # 禁用图片等资源加载
    co.set_argument('--disable-images')

    page = ChromiumPage(co)

    try:
        page.get(url)
        # 等待页面加载
        page.wait.load_start()

        content = page.html
        return content
    finally:
        page.quit()
''',
    },
    "curlcffi": {
        "description": "curl-cffi，高防网站，JA3/TP 指纹模拟",
        "code": '''# description: curl-cffi，高防网站，JA3/TP 指纹模拟
def fetch(url, headers=None, timeout=30, **kwargs):
    """
    获取网页源代码 (curl-cffi)
    支持JA3/TLS指纹模拟，绕过Cloudflare等高防

    参数:
        url: 目标URL
        headers: 请求头字典
        timeout: 超时时间(秒)
        **kwargs: 其他参数

    返回:
        str: 网页HTML源代码
    """
    from curl_cffi.requests import Session

    proxy = kwargs.get('proxy')
    cookies = kwargs.get('cookies', {})

    proxies = {"https": proxy, "http": proxy} if proxy else None

    with Session(impersonate="chrome") as s:
        response = s.get(
            url,
            headers=headers or {},
            timeout=timeout,
            proxies=proxies,
            cookies=cookies,
        )
        return response.text
''',
    },
    "scrapling": {
        "description": "scrapling，轻量级爬虫引擎",
        "code": '''# description: scrapling，轻量级爬虫引擎
def fetch(url, headers=None, timeout=30, **kwargs):
    """
    获取网页源代码 (scrapling)

    参数:
        url: 目标URL
        headers: 请求头字典
        timeout: 超时时间(秒)
        **kwargs: 其他参数

    返回:
        str: 网页HTML源代码
    """
    from scrapling import Fetcher

    fetcher = Fetcher()
    response = fetcher.get(url, headers=headers or {}, timeout=timeout)
    return response.text
''',
    },
}


def get_builtin_engines():
    """获取内置引擎列表"""
    engines = []
    for name, info in BUILTIN_ENGINES.items():
        engines.append({
            "name": name,
            "description": info["description"],
            "code": info["code"],
            "is_builtin": True,
        })
    return engines


@router.get("/list")
async def list_all_engines():
    """列出所有引擎（内置+自定义）"""
    builtin = get_builtin_engines()
    custom = load_custom_engines()
    return {"code": 0, "data": builtin + custom}


@router.get("/{engine_name}")
async def get_engine_detail(engine_name: str):
    """获取引擎详情"""
    # 检查内置引擎
    if engine_name in BUILTIN_ENGINES:
        info = BUILTIN_ENGINES[engine_name]
        return {"code": 0, "data": {
            "name": engine_name,
            "description": info["description"],
            "code": info["code"],
            "is_builtin": True,
        }}
    
    # 检查自定义引擎
    filepath = get_engine_filepath(engine_name)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Engine not found")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    description = ""
    for line in content.split('\n'):
        if line.startswith('# description:'):
            description = line.split(':', 1)[1].strip()
            break
    
    return {"code": 0, "data": {
        "name": engine_name,
        "description": description,
        "code": content,
        "is_builtin": False,
    }}


@router.post("/create")
async def create_engine(data: EngineCreate):
    """创建自定义引擎"""
    import re
    
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', data.name):
        raise HTTPException(status_code=400, detail="引擎名称只能包含字母、数字和下划线")
    
    if data.name in BUILTIN_ENGINES:
        raise HTTPException(status_code=400, detail="不能使用内置引擎名称")
    
    filepath = get_engine_filepath(data.name)
    if os.path.exists(filepath):
        raise HTTPException(status_code=400, detail="引擎已存在")
    
    ensure_engines_dir()
    code = data.code or f"""# description: {data.description}
import requests

def fetch(url, headers=None, timeout=30, **kwargs):
    \"\"\"
    获取网页源代码
    \"\"\"
    response = requests.get(url, headers=headers or {{}}, timeout=timeout)
    response.encoding = response.apparent_encoding or 'utf-8'
    return response.text
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(code)
    
    return {"code": 0, "message": "引擎创建成功"}


@router.put("/{engine_name}")
async def update_engine(engine_name: str, data: EngineUpdate):
    """更新自定义引擎"""
    filepath = get_engine_filepath(engine_name)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="引擎不存在")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if data.description is not None:
        lines = content.split('\n')
        found = False
        for i, line in enumerate(lines):
            if line.startswith('# description:'):
                lines[i] = f'# description: {data.description}'
                found = True
                break
        if not found:
            lines.insert(0, f'# description: {data.description}')
        content = '\n'.join(lines)
    
    if data.code is not None:
        content = data.code
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return {"code": 0, "message": "引擎更新成功"}


@router.delete("/{engine_name}")
async def delete_engine(engine_name: str):
    """删除自定义引擎"""
    filepath = get_engine_filepath(engine_name)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="引擎不存在")
    
    os.remove(filepath)
    return {"code": 0, "message": "引擎删除成功"}


@router.post("")
async def get_engines():
    """列出所有可用引擎（兼容旧接口）"""
    builtin = get_builtin_engines()
    custom = load_custom_engines()
    return {"code": 0, "data": builtin + custom}


@router.post("/test")
async def test_engine(data: dict):
    """测试引擎"""
    engine_name = data.get("engine", "requests")
    url = data.get("url", "")
    if not url:
        return {"code": 1, "message": "URL is required"}

    try:
        cookies = {}
        cookie_str = data.get("cookie", "")
        if cookie_str:
            for item in cookie_str.split(";"):
                item = item.strip()
                if "=" in item:
                    key, value = item.split("=", 1)
                    cookies[key.strip()] = value.strip()
        
        # 检查是否是自定义引擎
        filepath = get_engine_filepath(engine_name)
        if os.path.exists(filepath):
            import importlib.util
            import asyncio
            spec = importlib.util.spec_from_file_location(f"custom_engine_{engine_name}", filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 调用fetch函数，支持同步和异步
            fetch_result = module.fetch(
                url=url,
                headers=data.get("headers", {}),
                timeout=data.get("timeout", 15),
                proxy=data.get("proxy"),
                cookies=cookies,
            )
            
            # 如果是协程，需要await
            if asyncio.iscoroutine(fetch_result):
                result = await fetch_result
            else:
                result = fetch_result
            
            # Save full html to temp file, return preview + temp_id
            import time as _time
            temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data", "temp")
            temp_dir = os.path.normpath(os.path.abspath(temp_dir))
            os.makedirs(temp_dir, exist_ok=True)
            temp_id = f"{engine_name}_{int(_time.time() * 1000)}"
            temp_file = os.path.join(temp_dir, f"test_{temp_id}.html")
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(result)
            
            return {"code": 0, "data": {
                "status_code": 200,
                "content_length": len(result),
                "elapsed": 0,
                "encoding": "utf-8",
                "preview": result[:20000],
                "html_temp_id": temp_id,
                "headers": {},
            }}
        else:
            # 使用内置引擎
            engine = get_engine(engine_name)
            config = EngineConfig(
                url=url,
                headers=data.get("headers", {}),
                timeout=data.get("timeout", 15),
                max_retries=data.get("max_retries", 3),
                proxy=data.get("proxy") or None,
                cookies=cookies,
            )
            
            async with engine:
                resp = await engine.fetch(config)

            if resp.ok:
                # Return preview for display, full html saved to temp
                html_content = resp.text
                content_length = len(html_content)
                preview = html_content[:20000]
                
                # Save full html to a temp file for source code viewing
                import time as _time
                temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data", "temp")
                temp_dir = os.path.normpath(os.path.abspath(temp_dir))
                os.makedirs(temp_dir, exist_ok=True)
                temp_id = f"{engine_name}_{int(_time.time() * 1000)}"
                temp_file = os.path.join(temp_dir, f"test_{temp_id}.html")
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write(html_content)
                
                return {"code": 0, "data": {
                    "status_code": resp.status_code,
                    "content_length": content_length,
                    "elapsed": resp.elapsed,
                    "encoding": resp.encoding,
                    "preview": preview,
                    "html_temp_id": temp_id,  # 用ID而非路径
                    "headers": dict(resp.headers) if resp.headers else {},
                }}
            else:
                return {"code": 1, "message": f"Request failed: {resp.error or resp.status_code}"}
    except Exception as e:
        import traceback
        return {"code": 1, "message": str(e), "traceback": traceback.format_exc()}


@router.get("/html-source")
async def get_html_source(temp_id: str):
    """获取保存的HTML源码文件内容，以纯文本流返回"""
    import os
    from fastapi.responses import FileResponse
    
    if not temp_id:
        return {"code": 1, "message": "缺少temp_id参数"}
    
    # 根据temp_id定位文件
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data", "temp")
    temp_dir = os.path.normpath(os.path.abspath(temp_dir))
    temp_file = os.path.join(temp_dir, f"test_{temp_id}.html")
    
    # 安全检查：防止路径穿越
    if not os.path.abspath(temp_file).startswith(temp_dir):
        return {"code": 1, "message": "无权访问此文件"}
    
    if not os.path.exists(temp_file):
        return {"code": 1, "message": "文件不存在"}
    
    return FileResponse(
        temp_file, 
        media_type="text/plain; charset=utf-8",
        filename=f"source_{temp_id}.html"
    )
