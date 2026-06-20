from fastapi import Request
from redis.asyncio import Redis

from app.core.config import settings


def create_redis_client() -> Redis:
    """Create the shared async Redis client. Connections are established lazily,
    so this never blocks app startup even when Redis is briefly unavailable."""
    return Redis.from_url(settings.redis_url, decode_responses=True)


def get_redis(request: Request) -> Redis:
    """FastAPI dependency returning the app-wide Redis client."""
    redis: Redis = request.app.state.redis
    return redis
