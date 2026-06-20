# Import all models here so Alembic can detect them
from app.db.models.user import Role, User

__all__ = ["Role", "User"]
