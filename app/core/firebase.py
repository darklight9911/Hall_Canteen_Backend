from typing import Any

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from starlette.concurrency import run_in_threadpool

from app.core.config import settings


class InvalidFirebaseToken(Exception):
    """Raised when a Firebase ID token cannot be verified."""


# Reusable transport for fetching/caching Google's public signing certs.
_transport = google_requests.Request()


def _verify(token: str) -> dict[str, Any]:
    # Verifies signature against Google's public keys and checks iss/aud/exp
    # for the configured Firebase project. Synchronous (does HTTP), so callers
    # run it off the event loop.
    claims: dict[str, Any] = google_id_token.verify_firebase_token(  # type: ignore[no-untyped-call]
        token, _transport, audience=settings.firebase_project_id
    )
    return claims


async def verify_firebase_id_token(token: str) -> dict[str, Any]:
    if not settings.firebase_project_id:
        raise InvalidFirebaseToken("Firebase project id is not configured on the server")
    try:
        claims = await run_in_threadpool(_verify, token)
    except Exception as exc:  # google-auth raises ValueError on any failure
        raise InvalidFirebaseToken(str(exc)) from exc
    if not claims:
        raise InvalidFirebaseToken("Token verification returned no claims")
    return claims
