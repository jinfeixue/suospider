from curl_cffi import requests as curl_requests
import time
def fetch(url, headers=None, timeout=30, **kwargs):
    """
    获取网页源代码 (curl_cffi)
    模拟chrome110指纹，支持代理，自动重试8次，自动编码识别
    
    参数:
        url: 目标URL
        headers: 请求头字典
        timeout: 超时时间(秒)
        **kwargs: 其他参数(如proxy)
    
    返回:
        str: 网页HTML源代码
    """
    proxy = kwargs.get('proxy')
    html = None
    retry_times = 0
    max_retry = 5

    # 重试循环
    while retry_times < max_retry:
        try:
            # 构造请求参数
            request_kwargs = {
                "impersonate": "chrome110",
                "timeout": timeout,
                "headers": headers or {},
            }

            # 代理配置
            if proxy:
                request_kwargs["proxies"] = {"http": proxy, "https": proxy}

            # 发送请求
            html = curl_requests.get(url, **request_kwargs)
            
            # 打印重试次数
            print(f"=================== times={retry_times} ===================")
            break

        except Exception as e:
            retry_times += 1
            print(f'errmsg={str(e)}')
            print(f'retry times={retry_times}')
            time.sleep(1)
            continue

    # 无响应时返回空
    if html is None:
        return ""

    # 状态码日志
    print(f"返回状态码:【{html.status_code}】")

    # 自动识别编码
    content_type = html.headers.get("Content-Type", "")
    encoding = "utf-8"
    if "charset=" in content_type:
        encoding = content_type.split("charset=")[-1].strip().split(";")[0].strip()

    # 解码返回
    try:
        return html.content.decode(encoding, errors="replace")
    except:
        return html.text