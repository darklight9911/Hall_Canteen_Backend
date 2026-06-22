import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.food_item import FoodItem
from app.db.models.partner_application import ApplicationStatus, PartnerApplication
from app.db.models.restaurant import Restaurant


class PartnerApplicationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, app_id: uuid.UUID) -> PartnerApplication | None:
        return await self.db.get(PartnerApplication, app_id)

    async def get_by_user(self, user_id: uuid.UUID) -> PartnerApplication | None:
        result = await self.db.execute(
            select(PartnerApplication)
            .where(PartnerApplication.user_id == user_id)
            .order_by(PartnerApplication.created_at.desc())
        )
        return result.scalars().first()

    async def list(self, status: ApplicationStatus | None = None) -> list[PartnerApplication]:
        stmt = select(PartnerApplication).order_by(PartnerApplication.created_at.desc())
        if status is not None:
            stmt = stmt.where(PartnerApplication.status == status)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        phone: str,
        full_name: str,
        shop_name: str,
        location: str,
        photo: str,
    ) -> PartnerApplication:
        app = PartnerApplication(
            user_id=user_id,
            phone=phone,
            full_name=full_name,
            shop_name=shop_name,
            location=location,
            photo=photo,
        )
        self.db.add(app)
        await self.db.commit()
        await self.db.refresh(app)
        return app

    async def save(self, app: PartnerApplication) -> PartnerApplication:
        await self.db.commit()
        await self.db.refresh(app)
        return app


class RestaurantRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_owner(self, owner_id: uuid.UUID) -> Restaurant | None:
        result = await self.db.execute(select(Restaurant).where(Restaurant.owner_id == owner_id))
        return result.scalar_one_or_none()

    async def create(
        self, *, owner_id: uuid.UUID, name: str, location: str, photo: str | None
    ) -> Restaurant:
        restaurant = Restaurant(owner_id=owner_id, name=name, location=location, photo=photo)
        self.db.add(restaurant)
        await self.db.commit()
        await self.db.refresh(restaurant)
        return restaurant


class FoodItemRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, item_id: uuid.UUID) -> FoodItem | None:
        return await self.db.get(FoodItem, item_id)

    async def list_by_restaurant(self, restaurant_id: uuid.UUID) -> list[FoodItem]:
        result = await self.db.execute(
            select(FoodItem)
            .where(FoodItem.restaurant_id == restaurant_id)
            .order_by(FoodItem.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, item: FoodItem) -> FoodItem:
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def save(self, item: FoodItem) -> FoodItem:
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete(self, item: FoodItem) -> None:
        await self.db.delete(item)
        await self.db.commit()
