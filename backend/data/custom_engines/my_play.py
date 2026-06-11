"""
Playwright 异步引擎 - 用于 Spider Manager 系统
"""
import asyncio
import os

# Playwright浏览器路径
PLAYWRIGHT_CHROME_PATH = os.environ.get(
    "PLAYWRIGHT_CHROME_PATH",
    r"C:\hermes\cpython-3.12.13\python312\playwright\chromium-1208\chrome-win64\chrome.exe"
)


async def fetch(url, headers=None, timeout=30, **kwargs):
    """
    使用 Playwright 异步API 获取网页源代码
    
    参数:
        url: 目标网页URL
        headers: 请求头字典
        timeout: 超时时间(秒)
        **kwargs: 其他参数
    
    返回:
        str: 网页HTML源代码
    """
    from playwright.async_api import async_playwright
    
    timeout = 30
    is_headless = True
    max_retry = 3
    js_wait_time = 5
    html = ""
    proxies = kwargs.get('proxy', {})
    
    print(f"准备爬取URL：{url}，超时时间：{timeout}秒")
    print(f"准备爬取URL：{url}（最多重试{max_retry}次）")
    
    for retry_count in range(max_retry):
        print(f"第{retry_count}次尝试获取网页源码")
        try:
            async with async_playwright() as p:
                # 启动浏览器
                launch_options = {
                    "executable_path": PLAYWRIGHT_CHROME_PATH,
                    "headless": is_headless,
                    "slow_mo": 0,
                    "args": [
                        "--disable-gpu",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-web-security",
                        "--disable-features=NetworkService",
                        "--disable-blink-features=AutomationControlled"
                    ],
                }
                
                if proxies:
                    proxy_server = proxies.get("http") or proxies.get("https") or proxies.get("socks5")
                    if proxy_server:
                        launch_options["proxy"] = {"server": proxy_server, "bypass": "localhost"}

                browser = await p.chromium.launch(**launch_options)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                               "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    ignore_https_errors=True,
                    java_script_enabled=True
                )
                page = await context.new_page()

                # 设置默认超时
                page.set_default_timeout(timeout * 1000)

                # 指纹隐藏脚本
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en-US', 'en']});
                    window.chrome = {runtime: {}, loadTimes: function(){}};
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                """)
                
                # 访问页面
                try:
                    print(f"正在访问: {url}")
                    await page.goto(
                        url,
                        wait_until="commit",
                        timeout=timeout * 1000
                    )
                except Exception as e:
                    print(f"导航超时或异常: {type(e).__name__}: {e}，但继续等待 JS 执行")
                
                # 等待 body 出现
                try:
                    await page.wait_for_selector("body", state="visible", timeout=10000)
                    print("页面 body 已可见")
                except Exception:
                    print("body 未出现，但仍继续")
            
                # 等待 JS 执行
                await page.wait_for_timeout(js_wait_time * 1000)
                
                # 获取当前 HTML
                html = await page.content()

                if html.strip():
                    print(f"成功获取页面源码（长度: {len(html)} 字符）")
                    await context.close()
                    await browser.close()
                    break
                else:
                    print(f"获取的页面内容为空: {url}, 再次重试")
                    await context.close()
                    await browser.close()
                    continue

        except Exception as e:
            print(f"第{retry_count}次超时{timeout}秒，未获取到可见的body元素，准备重试（剩余{max_retry - retry_count}次）")
            if retry_count < max_retry - 1:
                await asyncio.sleep(1)
            continue
    
    return html.strip() if html else ""
