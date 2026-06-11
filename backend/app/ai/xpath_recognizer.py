"""XPath recognizer for identifying XPath expressions using LLM."""
import json
import re
from typing import Dict, List, Optional


class XPathRecognizer:
    """XPath识别器"""
    
    def __init__(self, llm_service):
        self.llm_service = llm_service

    async def recognize(self, html_content: str, page_type: str) -> Dict:
        """
        识别XPath
        
        Args:
            html_content: HTML内容
            page_type: 页面类型（list/detail）
            
        Returns:
            识别结果字典
        """
        if page_type == "list":
            return await self._recognize_list_page(html_content)
        else:
            return await self._recognize_detail_page(html_content)

    async def _recognize_list_page(self, html_content: str) -> Dict:
        """识别列表页XPath"""
        prompt = f"""
你是一个网页结构分析专家，精通XPath表达式。

请分析以下HTML片段，识别：

1. **翻页XPath**：
   - "下一页"按钮的XPath（优先）
   - 或页码递增URL规律（如 index_{{page_num}}.html）

2. **详情页链接XPath**：
   - 文章列表中每条记录的详情页链接
   - 要求XPath能匹配所有文章链接

HTML内容：
{html_content[:3000]}

要求：
- XPath必须精准，避免匹配到无关元素
- 优先使用class/id等稳定属性
- 返回JSON格式，包含XPath和置信度（0-100）

返回示例：
{{
  "pagination_xpath": {{"xpath": "//a[contains(text(), '下一页')]", "confidence": 95}},
  "detail_link_xpath": {{"xpath": "//div[@class='news-item']/h2/a/@href", "confidence": 90}}
}}
"""
        result = await self.llm_service.analyze(prompt)
        return self._parse_result(result)

    async def _recognize_detail_page(self, html_content: str) -> Dict:
        """识别详情页XPath"""
        prompt = f"""你是一个网页结构分析专家。请分析以下HTML，识别详情页中各字段的XPath。

**必须识别的字段**（核心字段）：
1. title - 文章标题（通常是h1标签）
2. content - 正文内容（通常是article或div内容区）
3. chubanriqi - 出版日期（字符串格式，如"2024-01-01"）
4. zuozhe - 作者（中文）
5. author - 作者（英文，如果没有留空）
6. keyword - 关键词
7. abstract - 摘要
8. wwwimages - 文章图片（多个用|分割）

**可选字段**（如果页面有就识别）：
- kanming - 来源/刊名
- viewnum - 浏览次数
- releasetime - 发布时间（datetime格式）

HTML内容（截取前8000字符）：
{html_content[:8000]}

要求：
- 只返回JSON，不要其他文字
- xpath用双引号包裹
- confidence是0-100的置信度
- 如果某个字段不存在，不要包含在结果中

返回格式：
{{"field_xpaths":[{{"name":"字段名","xpath":"XPath表达式","confidence":90}}]}}"""
        result = await self.llm_service.analyze(prompt)
        return self._parse_result(result)

    def _parse_result(self, result: str) -> Dict:
        """解析大模型返回的结果"""
        try:
            # 提取JSON部分
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            print(f"解析结果失败: {e}")
        return {"error": "解析失败", "raw_result": result}
