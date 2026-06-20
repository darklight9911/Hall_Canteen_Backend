from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    environment: str = "development"
    log_level: str = "INFO"

    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # Firebase (Google sign-in). Used to verify Firebase ID tokens from the client.
    firebase_project_id: str | None = None

    # Server-side sessions (Redis-backed, delivered as an httpOnly cookie)
    session_cookie_name: str = "hc_session"
    session_ttl_seconds: int = 60 * 60 * 24 * 7  # 7 days, refreshed on use
    session_cookie_secure: bool = False  # set True in production (HTTPS)
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    session_cookie_domain: str | None = None

    # Only accept sign-ups / logins from these email domains (apex + subdomains).
    # Empty list disables the restriction.
    allowed_email_domains: list[str] = ["diu.edu.bd"]

    # CORS
    backend_cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()  # type: ignore[call-arg]
