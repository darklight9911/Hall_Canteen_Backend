import json
import secrets
from typing import cast

from redis.asyncio import Redis

from app.core.config import settings
from app.db.models.user import User

_SESSION_PREFIX = "session:"


def _user_index_key(user_id: str) -> str:
    return f"user_sessions:{user_id}"


class SessionStore:
    """Opaque, server-side sessions stored in Redis with sliding expiration.

    Sessions are revocable (delete the key) and the session id is a random,
    high-entropy token delivered to the browser only as an httpOnly cookie.
    """

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def create(self, user: User) -> str:
        sid = secrets.token_urlsafe(32)
        payload = json.dumps(
            {"user_id": str(user.id), "role": user.role.value, "email": user.email}
        )
        await self.redis.set(_SESSION_PREFIX + sid, payload, ex=settings.session_ttl_seconds)
        # Track sessions per user so we can revoke all of them at once.
        await self.redis.sadd(_user_index_key(str(user.id)), sid)
        await self.redis.expire(_user_index_key(str(user.id)), settings.session_ttl_seconds)
        return sid

    async def get(self, sid: str) -> dict[str, str] | None:
        raw = await self.redis.get(_SESSION_PREFIX + sid)
        if raw is None:
            return None
        # Sliding expiration: refresh TTL on each authenticated request.
        await self.redis.expire(_SESSION_PREFIX + sid, settings.session_ttl_seconds)
        data: dict[str, str] = json.loads(raw)
        return data

    async def delete(self, sid: str) -> None:
        raw = await self.redis.get(_SESSION_PREFIX + sid)
        await self.redis.delete(_SESSION_PREFIX + sid)
        if raw is not None:
            data = json.loads(raw)
            await self.redis.srem(_user_index_key(data["user_id"]), sid)

    async def delete_all_for_user(self, user_id: str) -> None:
        sids = cast("set[str]", await self.redis.smembers(_user_index_key(user_id)))
        if sids:
            await self.redis.delete(*[_SESSION_PREFIX + sid for sid in sids])
        await self.redis.delete(_user_index_key(user_id))
