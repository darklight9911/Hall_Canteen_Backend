import uuid
from collections.abc import Awaitable, Callable

from fastapi import Depends, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import APIError
from app.core.redis import get_redis
from app.db.models.user import Role, User
from app.db.session import get_db
from app.repositories.user import UserRepository
from app.services.session import SessionStore


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> User:
    sid = request.cookies.get(settings.session_cookie_name)
    if not sid:
        raise APIError(status.HTTP_401_UNAUTHORIZED, "NOT_AUTHENTICATED", "Not authenticated")

    data = await SessionStore(redis).get(sid)
    if data is None:
        raise APIError(
            status.HTTP_401_UNAUTHORIZED, "SESSION_EXPIRED", "Session expired or invalid"
        )

    try:
        user = await UserRepository(db).get_by_id(uuid.UUID(data["user_id"]))
    except (ValueError, KeyError):
        user = None
    if user is None or not user.is_active:
        raise APIError(status.HTTP_401_UNAUTHORIZED, "NOT_AUTHENTICATED", "Not authenticated")
    return user


def require_roles(*roles: Role) -> Callable[[User], Awaitable[User]]:
    """Dependency factory enforcing that the current user has one of `roles`."""

    async def _require(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise APIError(
                status.HTTP_403_FORBIDDEN, "FORBIDDEN", "You do not have access to this resource"
            )
        return user

    return _require
