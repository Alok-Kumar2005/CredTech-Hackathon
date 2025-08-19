import redis
import json
import pickle
from typing import Any, Optional
from app.config.settings import settings
from loguru import logger

class Cache:
    def __init__(self):
        self.redis_client = redis.from_url(settings.redis_url, decode_responses=False)
        
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        try:
            ser = pickle.dumps(value)
            return self.redis_client.setex(key, ttl, ser)
        except Exception as e:
            logger.error(f"cache set error : {e}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        try:
            data = self.redis_client.get(key)
            return pickle.loads(data) if data else None
        except Exception as e:
            logger.error(f"cache get error: {e}")
            return None
    
    async def set_json(self, key: str, value: dict, ttl: int = 3600) -> bool:
        try:
            return self.redis_client.setex(f"json:{key}", ttl, json.dumps(value))
        except Exception as e:
            logger.error(f"cache json set error: {e}")
            return False
    
    async def get_json(self, key: str) -> Optional[dict]:
        try:
            data = self.redis_client.get(f"json:{key}")
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"cache get json error: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        try:
            return self.redis_client.delete(key) > 0
        except Exception as e:
            logger.error(f"cache delete error: {e}")
            return False

cache = Cache()