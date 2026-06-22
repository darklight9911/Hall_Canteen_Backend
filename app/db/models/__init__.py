# Import all models here so Alembic can detect them
from app.db.models.food_item import FoodItem
from app.db.models.partner_application import ApplicationStatus, PartnerApplication
from app.db.models.restaurant import Restaurant
from app.db.models.user import Role, User

__all__ = [
    "ApplicationStatus",
    "FoodItem",
    "PartnerApplication",
    "Restaurant",
    "Role",
    "User",
]
