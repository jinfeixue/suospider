"""CrawlRule model for caching XPath rules by domain."""
import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from app.core.database import Base


class CrawlRule(Base):
    """采集规则缓存模型"""
    __tablename__ = "crawl_rules"

    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(200), nullable=False, index=True, comment="域名")
    url_pattern = Column(String(500), comment="URL匹配规则")

    # 列表页规则
    detail_link_xpath = Column(Text, comment="详情页链接XPath")
    pagination_type = Column(String(50), comment="翻页类型")
    pagination_xpath = Column(Text, comment="翻页XPath")
    pagination_pattern = Column(String(200), comment="URL翻页规律")

    # 详情页字段规则
    field_xpaths = Column(JSON, default=dict, comment="字段XPath映射")

    # 引擎推荐
    recommended_engine = Column(String(50), default="requests", comment="推荐引擎")

    # 使用统计
    use_count = Column(Integer, default=0, comment="使用次数")
    success_count = Column(Integer, default=0, comment="成功次数")
    last_used_at = Column(DateTime, comment="最后使用时间")
    last_success_at = Column(DateTime, comment="最后成功时间")

    # 状态
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CrawlRule(id={self.id}, domain='{self.domain}')>"
