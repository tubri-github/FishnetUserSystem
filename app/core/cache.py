# app/core/cache.py
import json
import pickle
from typing import Optional, Any, Union
from datetime import timedelta
import redis.asyncio as redis
from app.config import get_settings

settings = get_settings()


class CacheManager:
    """缓存管理器"""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._initialized = False

    async def initialize(self):
        """初始化Redis连接"""
        if self._initialized:
            return

        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD,
                encoding="utf-8",
                decode_responses=False
            )
            await self.redis_client.ping()
            self._initialized = True
            print("✅ Redis connection established")
        except Exception as e:
            print(f"❌ Failed to connect to Redis: {e}")
            self.redis_client = None

    async def close(self):
        """关闭Redis连接"""
        if self.redis_client:
            await self.redis_client.close()
            self._initialized = False

    async def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
        if not self.redis_client:
            return default

        try:
            value = await self.redis_client.get(key)
            if value is None:
                return default

            try:
                return pickle.loads(value)
            except:
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
            serialized_value = pickle.dumps(value)

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


# 创建全局实例
cache_manager = CacheManager()