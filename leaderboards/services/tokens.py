import os

import jwt

_ALG = "HS256"
_ISSUER = "myfitnessrank-auth"


class TokenError(Exception):
    """Raised when a token is missing, malformed, expired, or the wrong type."""


def _signing_key() -> str:
    key = os.environ.get("JWT_SIGNING_KEY")
    if not key:
        raise RuntimeError("JWT_SIGNING_KEY is not set")
    return key


def decode_access(token: str) -> dict:
    """Verify an access token minted by the auth service and return its claims.

    The signing key and issuer are shared with auth/services/tokens.py — this
    service only verifies, it never issues.
    """
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
    if claims.get("type") != "access":
        raise TokenError("expected an access token")
    return claims
