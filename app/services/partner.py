import uuid
from datetime import UTC, datetime

from fastapi import status

from app.core.errors import APIError
from app.core.firebase import InvalidFirebaseToken, verify_firebase_id_token
from app.db.models.food_item import FoodItem
from app.db.models.partner_application import ApplicationStatus, PartnerApplication
from app.db.models.restaurant import Restaurant
from app.db.models.user import Role, User
from app.repositories.partner import (
    FoodItemRepository,
    PartnerApplicationRepository,
    RestaurantRepository,
)
from app.repositories.user import UserRepository
from app.services.session import SessionStore


class PartnerService:
    """Partner onboarding (apply → developer review → approve) and shop/item management."""

    def __init__(
        self,
        users: UserRepository,
        applications: PartnerApplicationRepository,
        restaurants: RestaurantRepository,
        items: FoodItemRepository,
        sessions: SessionStore,
    ) -> None:
        self.users = users
        self.applications = applications
        self.restaurants = restaurants
        self.items = items
        self.sessions = sessions

    # ---------------- application (any Google account; DIU not required) ----------------

    async def apply(
        self,
        *,
        id_token: str,
        phone: str,
        full_name: str,
        shop_name: str,
        location: str,
        photo: str,
    ) -> tuple[User, PartnerApplication, str]:
        try:
            claims = await verify_firebase_id_token(id_token)
        except InvalidFirebaseToken as exc:
            raise APIError(
                status.HTTP_401_UNAUTHORIZED,
                "INVALID_GOOGLE_TOKEN",
                "Could not verify Google sign-in",
            ) from exc

        firebase_uid = claims.get("uid") or claims.get("sub")
        email = (claims.get("email") or "").strip().lower()
        if not firebase_uid or not email:
            raise APIError(
                status.HTTP_401_UNAUTHORIZED,
                "INVALID_GOOGLE_TOKEN",
                "Google token is missing required claims",
            )

        # Partner applicants may use any (Google) email — no DIU restriction.
        user = await self.users.get_by_firebase_uid(firebase_uid)
        if user is None:
            existing = await self.users.get_by_email(email)
            if existing is None:
                user = await self.users.create(
                    email=email,
                    full_name=claims.get("name") or full_name,
                    firebase_uid=firebase_uid,
                    role=Role.student,
                )
            else:
                existing.firebase_uid = firebase_uid
                user = await self.users.save(existing)

        current = await self.applications.get_by_user(user.id)
        if current is not None and current.status in (
            ApplicationStatus.pending,
            ApplicationStatus.approved,
        ):
            raise APIError(
                status.HTTP_409_CONFLICT,
                "APPLICATION_EXISTS",
                "You already have a partner application in progress",
            )

        app = await self.applications.create(
            user_id=user.id,
            phone=phone.strip(),
            full_name=full_name.strip(),
            shop_name=shop_name.strip(),
            location=location.strip(),
            photo=photo,
        )
        sid = await self.sessions.create(user)
        return user, app, sid

    async def get_user_application(self, user: User) -> PartnerApplication | None:
        return await self.applications.get_by_user(user.id)

    # ---------------- developer review ----------------

    async def list_applications(
        self, status_filter: ApplicationStatus | None = None
    ) -> list[PartnerApplication]:
        return await self.applications.list(status_filter)

    async def approve(self, app_id: uuid.UUID) -> Restaurant:
        app = await self._get_pending(app_id)
        user = await self.users.get_by_id(app.user_id)
        if user is None:
            raise APIError(
                status.HTTP_404_NOT_FOUND, "USER_NOT_FOUND", "Applicant no longer exists"
            )

        user.role = Role.partner
        await self.users.save(user)

        restaurant = await self.restaurants.get_by_owner(user.id)
        if restaurant is None:
            restaurant = await self.restaurants.create(
                owner_id=user.id, name=app.shop_name, location=app.location, photo=app.photo
            )

        app.status = ApplicationStatus.approved
        app.reviewed_at = datetime.now(UTC)
        await self.applications.save(app)
        return restaurant

    async def reject(self, app_id: uuid.UUID) -> PartnerApplication:
        app = await self._get_pending(app_id)
        app.status = ApplicationStatus.rejected
        app.reviewed_at = datetime.now(UTC)
        return await self.applications.save(app)

    async def _get_pending(self, app_id: uuid.UUID) -> PartnerApplication:
        app = await self.applications.get_by_id(app_id)
        if app is None:
            raise APIError(
                status.HTTP_404_NOT_FOUND, "APPLICATION_NOT_FOUND", "Application not found"
            )
        if app.status is not ApplicationStatus.pending:
            raise APIError(
                status.HTTP_409_CONFLICT,
                "ALREADY_REVIEWED",
                "This application has already been reviewed",
            )
        return app

    # ---------------- partner shop & food items ----------------

    async def get_restaurant(self, user: User) -> Restaurant:
        return await self._require_restaurant(user)

    async def list_items(self, user: User) -> list[FoodItem]:
        restaurant = await self._require_restaurant(user)
        return await self.items.list_by_restaurant(restaurant.id)

    async def create_item(
        self,
        user: User,
        *,
        name: str,
        description: str,
        price: int,
        category: str,
        image: str | None,
        is_available: bool,
    ) -> FoodItem:
        restaurant = await self._require_restaurant(user)
        item = FoodItem(
            restaurant_id=restaurant.id,
            name=name.strip(),
            description=description.strip(),
            price=price,
            category=category.strip(),
            image=image,
            is_available=is_available,
        )
        return await self.items.create(item)

    async def update_item(
        self,
        user: User,
        item_id: uuid.UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        price: int | None = None,
        category: str | None = None,
        image: str | None = None,
        is_available: bool | None = None,
    ) -> FoodItem:
        item = await self._owned_item(user, item_id)
        if name is not None:
            item.name = name.strip()
        if description is not None:
            item.description = description.strip()
        if price is not None:
            item.price = price
        if category is not None:
            item.category = category.strip()
        if image is not None:
            item.image = image
        if is_available is not None:
            item.is_available = is_available
        return await self.items.save(item)

    async def delete_item(self, user: User, item_id: uuid.UUID) -> None:
        item = await self._owned_item(user, item_id)
        await self.items.delete(item)

    async def _require_restaurant(self, user: User) -> Restaurant:
        restaurant = await self.restaurants.get_by_owner(user.id)
        if restaurant is None:
            raise APIError(
                status.HTTP_404_NOT_FOUND, "NO_RESTAURANT", "You do not have a restaurant yet"
            )
        return restaurant

    async def _owned_item(self, user: User, item_id: uuid.UUID) -> FoodItem:
        restaurant = await self._require_restaurant(user)
        item = await self.items.get_by_id(item_id)
        if item is None or item.restaurant_id != restaurant.id:
            raise APIError(status.HTTP_404_NOT_FOUND, "ITEM_NOT_FOUND", "Item not found")
        return item
