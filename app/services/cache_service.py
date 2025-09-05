# app/services/cache_service.py - 缓存服务
import json
import pickle
from typing import Optional, Any, Union
from datetime import timedelta
import redis.asyncio as redis
from app.config import get_settings

settings = get_settings()


class CacheService:
    """缓存服务"""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None

    async def initialize(self):
        """初始化Redis连接"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD,
                encoding="utf-8",
                decode_responses=False  # 使用二进制模式以支持pickle
            )
            # 测试连接
            await self.redis_client.ping()
        except Exception as e:
            print(f"Failed to connect to Redis: {e}")
            self.redis_client = None

    async def close(self):
        """关闭Redis连接"""
        if self.redis_client:
            await self.redis_client.close()

    async def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
        if not self.redis_client:
            return default

        try:
            value = await self.redis_client.get(key)
            if value is None:
                return default

            # 尝试反序列化
            try:
                return pickle.loads(value)
            except:
                # 如果pickle失败，尝试JSON
                try:
                    return json.loads(value.decode('utf-8'))
                except:
                    return value.decode('utf-8')
        except Exception as e:
            print(f"Cache get error for key {key}: {e}")
            return default

    async def set(
            self,
            key: str,
            value: Any,
            ttl: Optional[Union[int, timedelta]] = None
    ) -> bool:
        """设置缓存值"""
        if not self.redis_client:
            return False

        try:
            # 序列化值
            if isinstance(value, (dict, list, tuple)):
                serialized_value = pickle.dumps(value)
            elif isinstance(value, (str, int, float, bool)):
                serialized_value = pickle.dumps(value)
            else:
                serialized_value = pickle.dumps(value)

            # 设置TTL
            if ttl is None:
                ttl = settings.CACHE_DEFAULT_TTL

            if isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())

            await self.redis_client.set(key, serialized_value, ex=ttl)
            return True
        except Exception as e:
            print(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.redis_client:
            return False

        try:
            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            print(f"Cache delete error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """检查key是否存在"""
        if not self.redis_client:
            return False

        try:
            result = await self.redis_client.exists(key)
            return result > 0
        except Exception as e:
            print(f"Cache exists error for key {key}: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的所有key"""
        if not self.redis_client:
            return 0

        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                result = await self.redis_client.delete(*keys)
                return result
            return 0
        except Exception as e:
            print(f"Cache clear pattern error for pattern {pattern}: {e}")
            return 0