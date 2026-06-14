"""Unit tests for JWT issue/verify — no database required."""

import os

import pytest

os.environ.setdefault("JWT_SIGNING_KEY", "test-signing-key-not-for-prod")

from services import tokens  # noqa: E402

_ACCOUNT = {"id": 7, "email": "lifter@example.com", "username": "lifter"}


class TestRoundTrip:
    def test_access_token_decodes_with_claims(self):
        claims = tokens.decode(tokens.issue_access(_ACCOUNT), "access")
        assert claims["sub"] == "7"
        assert claims["email"] == "lifter@example.com"
        assert claims["username"] == "lifter"
        assert claims["type"] == "access"

    def test_refresh_token_has_refresh_type(self):
        claims = tokens.decode(tokens.issue_refresh(_ACCOUNT), "refresh")
        assert claims["type"] == "refresh"


class TestTypeConfusion:
    def test_access_token_rejected_as_refresh(self):
        with pytest.raises(tokens.TokenError):
            tokens.decode(tokens.issue_access(_ACCOUNT), "refresh")

    def test_refresh_token_rejected_as_access(self):
        with pytest.raises(tokens.TokenError):
            tokens.decode(tokens.issue_refresh(_ACCOUNT), "access")


class TestTampering:
    def test_garbage_token_rejected(self):
        with pytest.raises(tokens.TokenError):
            tokens.decode("not.a.jwt", "access")

    def test_wrong_signature_rejected(self):
        forged = tokens.issue_access(_ACCOUNT) + "x"
        with pytest.raises(tokens.TokenError):
            tokens.decode(forged, "access")
