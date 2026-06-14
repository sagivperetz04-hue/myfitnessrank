import os
import time

import jwt

_ALG = "HS256"
# Short-lived access token; refresh token rides in an HttpOnly cookie and is the
# only credential allowed to mint new access tokens.
ACCESS_TTL_SECONDS = int(os.environ.get("ACCESS_TTL_SECONDS", 900))  # 15 min
REFRESH_TTL_SECONDS = int(os.environ.get("REFRESH_TTL_SECONDS", 604800))  # 7 days

_ISSUER = "myfitnessrank-auth"


class TokenError(Exception):
    """Raised when a token is missing, malformed, expired, or the wrong type."""


def _signing_key() -> str:
    key = os.environ.get("JWT_SIGNING_KEY")
    if not key:
        raise RuntimeError("JWT_SIGNING_KEY is not set")
    return key


def _issue(account: dict, token_type: str, ttl: int) -> str:
    now = int(time.time())
    payload = {
        "sub": str(account["id"]),
        "email": account["email"],
        "username": account["username"],
        "type": token_type,
        "iss": _ISSUER,
        "iat": now,
        "exp": now + ttl,
    }
    return jwt.encode(payload, _signing_key(), algorithm=_ALG)


def issue_access(account: dict) -> str:
    return _issue(account, "access", ACCESS_TTL_SECONDS)


def issue_refresh(account: dict) -> str:
    return _issue(account, "refresh", REFRESH_TTL_SECONDS)


def decode(token: str, expected_type: str) -> dict:
    try:
        claims = jwt.decode(
            token,
            _signing_key(),
            algorithms=[_ALG],
            issuer=_ISSUER,
            options={"require": ["exp", "iat", "sub", "type"]},
        )
    except jwt.InvalidTokenError as exc:
        raise TokenError(str(exc)) from exc
    if claims.get("type") != expected_type:
        raise TokenError(f"expected a {expected_type} token")
    return claims
