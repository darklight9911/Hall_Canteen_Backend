import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user, require_roles
from app.core.cookies import set_session_cookie
from app.core.redis import get_redis
from app.db.models.partner_application import ApplicationStatus
from app.db.models.user import Role, User
from app.db.session import get_db
from app.repositories.partner import (
    FoodItemRepository,
    PartnerApplicationRepository,
    RestaurantRepository,
)
from app.repositories.user import UserRepository
from app.schemas.partner import (
    FoodItemCreate,
    FoodItemRead,
    FoodItemUpdate,
    PartnerApplicationRead,
    PartnerApplyRequest,
    RestaurantRead,
)
from app.services.partner import PartnerService
from app.services.session import SessionStore

router = APIRouter()

# Pre-built role guards (developer is a superuser, so it passes both).
require_developer = require_roles()
require_partner = require_roles(Role.partner)


def _service(db: AsyncSession, redis: Redis) -> PartnerService:
    return PartnerService(
        UserRepository(db),
        PartnerApplicationRepository(db),
        RestaurantRepository(db),
        FoodItemRepository(db),
        SessionStore(redis),
    )


# ---------------- Partner application (any Google account) ----------------


@router.post("/apply", response_model=PartnerApplicationRead, status_code=status.HTTP_201_CREATED)
async def apply(
    body: PartnerApplyRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> object:
    _user, application, sid = await _service(db, redis).apply(
        id_token=body.id_token,
        phone=body.phone,
        full_name=body.full_name,
        shop_name=body.shop_name,
        location=body.location,
        photo=body.photo,
    )
    set_session_cookie(response, sid)
    return application


@router.get("/application", response_model=PartnerApplicationRead | None)
async def my_application(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> object:
    return await _service(db, redis).get_user_application(user)


# ---------------- Developer review (developer only) ----------------


@router.get("/applications", response_model=list[PartnerApplicationRead])
async def list_applications(
    status_filter: ApplicationStatus | None = Query(default=None, alias="status"),
    _dev: User = Depends(require_developer),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> object:
    return await _service(db, redis).list_applications(status_filter)


@router.post("/applications/{app_id}/approve", response_model=RestaurantRead)
async def approve_application(
    app_id: uuid.UUID,
    _dev: User = Depends(require_developer),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> object:
    return await _service(db, redis).approve(app_id)


@router.post("/applications/{app_id}/reject", response_model=PartnerApplicationRead)
async def reject_application(
    app_id: uuid.UUID,
    _dev: User = Depends(require_developer),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> object:
    return await _service(db, redis).reject(app_id)


# ---------------- Partner shop & food items (partner; developer is superuser) ----------------


@router.get("/restaurant", response_model=RestaurantRead)
async def my_restaurant(
    user: User = Depends(require_partner),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> object:
    return await _service(db, redis).get_restaurant(user)


@router.get("/items", response_model=list[FoodItemRead])
async def list_items(
    user: User = Depends(require_partner),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> object:
    return await _service(db, redis).list_items(user)


@router.post("/items", response_model=FoodItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(
    body: FoodItemCreate,
    user: User = Depends(require_partner),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> object:
    return await _service(db, redis).create_item(
        user,
        name=body.name,
        description=body.description,
        price=body.price,
        category=body.category,
        image=body.image,
        is_available=body.is_available,
    )


@router.patch("/items/{item_id}", response_model=FoodItemRead)
async def update_item(
    item_id: uuid.UUID,
    body: FoodItemUpdate,
    user: User = Depends(require_partner),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> object:
    return await _service(db, redis).update_item(
        user,
        item_id,
        name=body.name,
        description=body.description,
        price=body.price,
        category=body.category,
        image=body.image,
        is_available=body.is_available,
    )


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: uuid.UUID,
    user: User = Depends(require_partner),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> None:
    await _service(db, redis).delete_item(user, item_id)
