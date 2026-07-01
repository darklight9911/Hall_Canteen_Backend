import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.delivery_slot import DeliverySlot
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
        result = await self.db.execute(
            select(FoodItem)
            .where(FoodItem.id == item_id)
            .options(selectinload(FoodItem.slots))
        )
        return result.scalar_one_or_none()

    async def list_by_restaurant(self, restaurant_id: uuid.UUID) -> list[FoodItem]:
        result = await self.db.execute(
            select(FoodItem)
            .where(FoodItem.restaurant_id == restaurant_id)
            .options(selectinload(FoodItem.slots))
            .order_by(FoodItem.created_at.desc())
        )
        return list(result.scalars().all())

    async def slots_by_ids(
        self, slot_ids: list[uuid.UUID], restaurant_id: uuid.UUID
    ) -> list[DeliverySlot]:
        if not slot_ids:
            return []
        result = await self.db.execute(
            select(DeliverySlot).where(
                DeliverySlot.id.in_(slot_ids),
                DeliverySlot.restaurant_id == restaurant_id,
            )
        )
        return list(result.scalars().all())

    async def create(
        self, item: FoodItem, slot_ids: list[uuid.UUID], restaurant_id: uuid.UUID
    ) -> FoodItem:
        item.slots = await self.slots_by_ids(slot_ids, restaurant_id)
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def save(
        self,
        item: FoodItem,
        slot_ids: list[uuid.UUID] | None = None,
        restaurant_id: uuid.UUID | None = None,
    ) -> FoodItem:
        if slot_ids is not None and restaurant_id is not None:
            item.slots = await self.slots_by_ids(slot_ids, restaurant_id)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete(self, item: FoodItem) -> None:
        await self.db.delete(item)
        await self.db.commit()


class DeliverySlotRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, slot_id: uuid.UUID) -> DeliverySlot | None:
        return await self.db.get(DeliverySlot, slot_id)

    async def list_by_restaurant(self, restaurant_id: uuid.UUID) -> list[DeliverySlot]:
        result = await self.db.execute(
            select(DeliverySlot)
            .where(DeliverySlot.restaurant_id == restaurant_id)
            .order_by(DeliverySlot.start_time)
        )
        return list(result.scalars().all())

    async def create(self, slot: DeliverySlot) -> DeliverySlot:
        self.db.add(slot)
        await self.db.commit()
        await self.db.refresh(slot)
        return slot

    async def save(self, slot: DeliverySlot) -> DeliverySlot:
        await self.db.commit()
        await self.db.refresh(slot)
        return slot

    async def delete(self, slot: DeliverySlot) -> None:
        await self.db.delete(slot)
        await self.db.commit()
