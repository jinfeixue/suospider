"""LLM Service for interacting with various LLM APIs."""
import httpx
import json
from typing import Optional, Dict, Any


class LLMService:
    """大模型服务类"""
    
    def __init__(self, provider: str, model: str, api_key: str, 
                 api_url: Optional[str] = None, timeout: int = 30):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        
        # 根据提供商设置默认API地址
        if api_url:
            self.api_url = api_url
        elif provider == "openai":
            self.api_url = "https://api.openai.com/v1"
        elif provider == "anthropic":
            self.api_url = "https://api.anthropic.com/v1"
        elif provider == "aliyun":
            self.api_url = "https://dashscope.aliyuncs.com/api/v1"
        else:
            self.api_url = api_url or ""

    async def test_connection(self) -> Dict[str, Any]:
        """测试API连通性"""
        try:
            if self.provider == "openai":
                return await self._test_openai()
            elif self.provider == "anthropic":
                return await self._test_anthropic()
            elif self.provider == "aliyun":
                return await self._test_aliyun()
            else:
                return await self._test_custom()
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def _test_openai(self) -> Dict[str, Any]:
        """测试OpenAI API"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 10
                }
            )
            if response.status_code == 200:
                return {"success": True, "message": "连接成功"}
            else:
                return {"success": False, "message": f"API错误: {response.text}"}

    async def _test_anthropic(self) -> Dict[str, Any]:
        """测试Anthropic API"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_url}/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hello"}]
                }
            )
            if response.status_code == 200:
                return {"success": True, "message": "连接成功"}
            else:
                return {"success": False, "message": f"API错误: {response.text}"}

    async def _test_aliyun(self) -> Dict[str, Any]:
        """测试阿里云API"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_url}/services/aigc/text-generation/generation",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "input": {
                        "messages": [{"role": "user", "content": "Hello"}]
                    },
                    "parameters": {
                        "max_tokens": 10
                    }
                }
            )
            if response.status_code == 200:
                return {"success": True, "message": "连接成功"}
            else:
                return {"success": False, "message": f"API错误: {response.text}"}

    async def _test_custom(self) -> Dict[str, Any]:
        """测试自定义API"""
        # 自动补全URL路径
        url = self.api_url.rstrip('/')
        if not url.endswith('/chat/completions'):
            if url.endswith('/v1'):
                url = url + '/chat/completions'
            elif '/v1/' in url:
                url = url.split('/v1/')[0] + '/v1/chat/completions'
            else:
                url = url + '/v1/chat/completions'

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 10
                }
            )
            if response.status_code == 200:
                return {"success": True, "message": "连接成功"}
            else:
                return {"success": False, "message": f"API错误: {response.status_code} - {response.text[:200]}"}

    async def analyze(self, prompt: str) -> str:
        """调用大模型分析"""
        if self.provider == "openai":
            return await self._analyze_openai(prompt)
        elif self.provider == "anthropic":
            return await self._analyze_anthropic(prompt)
        elif self.provider == "aliyun":
            return await self._analyze_aliyun(prompt)
        else:
            return await self._analyze_custom(prompt)

    async def _analyze_openai(self, prompt: str) -> str:
        """使用OpenAI API分析"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 4000
                }
            )
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                raise Exception(f"API错误: {response.text}")

    async def _analyze_anthropic(self, prompt: str) -> str:
        """使用Anthropic API分析"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_url}/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "max_tokens": 4000,
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            if response.status_code == 200:
                result = response.json()
                return result["content"][0]["text"]
            else:
                raise Exception(f"API错误: {response.text}")

    async def _analyze_aliyun(self, prompt: str) -> str:
        """使用阿里云API分析"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.api_url}/services/aigc/text-generation/generation",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "input": {
                        "messages": [{"role": "user", "content": prompt}]
                    },
                    "parameters": {
                        "max_tokens": 4000,
                        "temperature": 0.1
                    }
                }
            )
            if response.status_code == 200:
                result = response.json()
                return result["output"]["choices"][0]["message"]["content"]
            else:
                raise Exception(f"API错误: {response.text}")

    async def _analyze_custom(self, prompt: str) -> str:
        """使用自定义API分析"""
        # 自动补全URL路径
        url = self.api_url.rstrip('/')
        if not url.endswith('/chat/completions'):
            if url.endswith('/v1'):
                url = url + '/chat/completions'
            elif '/v1/' in url:
                url = url.split('/v1/')[0] + '/v1/chat/completions'
            else:
                url = url + '/v1/chat/completions'

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 4000
                }
            )
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                raise Exception(f"API错误: {response.text}")
