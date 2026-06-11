"""Rule cache for storing and retrieving AI analysis results."""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from urllib.parse import urlparse


class RuleCache:
    """规则缓存管理器"""
    
    def __init__(self, cache_dir: str = "data/ai_cache"):
        self.cache_dir = cache_dir
        self.rules_dir = os.path.join(cache_dir, "rules")
        self.stats_file = os.path.join(cache_dir, "cache_stats.json")
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """确保目录存在"""
        os.makedirs(self.rules_dir, exist_ok=True)
    
    def _get_domain(self, url: str) -> str:
        """从URL提取域名"""
        parsed = urlparse(url)
        return parsed.netloc or parsed.hostname or "unknown"
    
    def _get_cache_file(self, domain: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.rules_dir, f"{domain}.json")
    
    def get(self, url: str) -> Optional[Dict]:
        """
        获取缓存的规则
        
        Args:
            url: 目标URL
            
        Returns:
            缓存的规则，如果不存在或过期则返回None
        """
        domain = self._get_domain(url)
        cache_file = self._get_cache_file(domain)
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # 检查是否过期（7天）
            cached_time = datetime.fromisoformat(cache_data.get("cached_at", "2000-01-01"))
            if datetime.now() - cached_time > timedelta(days=7):
                return None
            
            return cache_data.get("rules")
        except Exception as e:
            print(f"读取缓存失败: {e}")
            return None
    
    def set(self, url: str, rules: Dict):
        """
        缓存规则
        
        Args:
            url: 目标URL
            rules: 规则数据
        """
        domain = self._get_domain(url)
        cache_file = self._get_cache_file(domain)
        
        cache_data = {
            "domain": domain,
            "url": url,
            "rules": rules,
            "cached_at": datetime.now().isoformat()
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            # 更新统计
            self._update_stats(domain)
        except Exception as e:
            print(f"写入缓存失败: {e}")
    
    def delete(self, url: str):
        """删除缓存"""
        domain = self._get_domain(url)
        cache_file = self._get_cache_file(domain)
        
        if os.path.exists(cache_file):
            os.remove(cache_file)
    
    def clear_expired(self):
        """清理过期缓存"""
        expired_count = 0
        for filename in os.listdir(self.rules_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.rules_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    
                    cached_time = datetime.fromisoformat(cache_data.get("cached_at", "2000-01-01"))
                    if datetime.now() - cached_time > timedelta(days=7):
                        os.remove(filepath)
                        expired_count += 1
                except Exception:
                    pass
        
        return expired_count
    
    def _update_stats(self, domain: str):
        """更新缓存统计"""
        stats = self._load_stats()
        stats["total_cached"] = stats.get("total_cached", 0) + 1
        stats["last_cached"] = datetime.now().isoformat()
        stats["domains"] = stats.get("domains", [])
        if domain not in stats["domains"]:
            stats["domains"].append(domain)
        
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def _load_stats(self) -> Dict:
        """加载统计数据"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        stats = self._load_stats()
        stats["cached_domains"] = len([f for f in os.listdir(self.rules_dir) if f.endswith('.json')])
        return stats
