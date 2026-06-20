from fastapi import APIRouter, Depends, Request, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.core.config import settings
from app.core.redis import get_redis
from app.db.models.user import User
from app.db.session import get_db
from app.repositories.user import UserRepository
from app.schemas.auth import GoogleLoginRequest, LoginRequest, RegisterRequest, UserRead
from app.services.auth import AuthService
from app.services.session import SessionStore

router = APIRouter()


def _service(db: AsyncSession, redis: Redis) -> AuthService:
    return AuthService(UserRepository(db), SessionStore(redis))


def _set_session_cookie(response: Response, sid: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=sid,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        domain=settings.session_cookie_domain,
        path="/",
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> User:
    user, sid = await _service(db, redis).register(body.email, body.password, body.full_name)
    _set_session_cookie(response, sid)
    return user


@router.post("/login", response_model=UserRead)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> User:
    user, sid = await _service(db, redis).login(body.email, body.password)
    _set_session_cookie(response, sid)
    return user


@router.post("/login/google", response_model=UserRead)
async def login_google(
    body: GoogleLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> User:
    user, sid = await _service(db, redis).login_with_google(body.id_token)
    _set_session_cookie(response, sid)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    redis: Redis = Depends(get_redis),
) -> None:
    sid = request.cookies.get(settings.session_cookie_name)
    if sid:
        await SessionStore(redis).delete(sid)
    response.delete_cookie(
        settings.session_cookie_name, path="/", domain=settings.session_cookie_domain
    )


@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(get_current_user)) -> User:
    return user
