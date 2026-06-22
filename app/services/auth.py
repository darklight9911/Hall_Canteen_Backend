from fastapi import status

from app.core.emails import email_domain_allowed
from app.core.errors import APIError
from app.core.firebase import InvalidFirebaseToken, verify_firebase_id_token
from app.core.security import hash_password, verify_password
from app.db.models.user import Role, User
from app.repositories.user import UserRepository
from app.services.session import SessionStore


class AuthService:
    """Authentication + session orchestration.

    Verifies credentials (password) or a Firebase ID token (Google), upserts the
    user via the repository, and mints a Redis session. Returns the user and the
    opaque session id for the caller to set as an httpOnly cookie.
    """

    def __init__(self, users: UserRepository, sessions: SessionStore) -> None:
        self.users = users
        self.sessions = sessions

    async def register(self, email: str, password: str, full_name: str) -> tuple[User, str]:
        email = email.strip().lower()
        self._assert_allowed_email(email)
        if await self.users.get_by_email(email) is not None:
            raise APIError(
                status.HTTP_409_CONFLICT, "EMAIL_TAKEN", "An account with this email already exists"
            )
        user = await self.users.create(
            email=email,
            full_name=full_name.strip(),
            hashed_password=hash_password(password),
            role=Role.student,
        )
        sid = await self.sessions.create(user)
        return user, sid

    async def login(self, email: str, password: str) -> tuple[User, str]:
        # No domain check on login — only existing (already-validated) accounts
        # have credentials, and partners may have non-DIU (Google) emails.
        email = email.strip().lower()
        user = await self.users.get_by_email(email)
        if (
            user is None
            or user.hashed_password is None
            or not verify_password(password, user.hashed_password)
        ):
            raise APIError(
                status.HTTP_401_UNAUTHORIZED, "INVALID_CREDENTIALS", "Incorrect email or password"
            )
        self._assert_active(user)
        sid = await self.sessions.create(user)
        return user, sid

    async def login_with_google(self, id_token: str) -> tuple[User, str]:
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
        full_name = claims.get("name") or email.split("@")[0]

        user = await self.users.get_by_firebase_uid(firebase_uid)
        if user is None:
            existing = await self.users.get_by_email(email)
            if existing is None:
                # Brand-new self-service account via the student path → enforce DIU.
                # (Partners come through PartnerService.apply, which has no DIU check.)
                self._assert_allowed_email(email)
                user = await self.users.create(
                    email=email,
                    full_name=full_name,
                    firebase_uid=firebase_uid,
                    role=Role.student,
                )
            else:
                # Link the Google identity to the existing email account.
                existing.firebase_uid = firebase_uid
                user = await self.users.save(existing)

        self._assert_active(user)
        sid = await self.sessions.create(user)
        return user, sid

    async def logout(self, sid: str) -> None:
        await self.sessions.delete(sid)

    @staticmethod
    def _assert_allowed_email(email: str) -> None:
        if not email_domain_allowed(email):
            raise APIError(
                status.HTTP_403_FORBIDDEN,
                "EMAIL_DOMAIN_NOT_ALLOWED",
                "Only @diu.edu.bd email addresses are allowed",
            )

    @staticmethod
    def _assert_active(user: User) -> None:
        if not user.is_active:
            raise APIError(
                status.HTTP_403_FORBIDDEN, "ACCOUNT_DISABLED", "This account is disabled"
            )
