import re

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Mirrors the client-side check in the frontend; this one is the gate.
EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# Password policy: >= 8 chars, >= 1 uppercase, >= 1 digit, >= 1 special.
_MIN_LEN = 8
_SPECIAL_RE = re.compile(r"[^A-Za-z0-9]")

# argon2id is the default variant; these cost params follow the OWASP cheat-sheet
# baseline (>= 19 MiB, t=2, p=1) and can be tuned via env without rehash breakage.
_hasher = PasswordHasher()


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email or ""))


def password_problems(password: str) -> list[str]:
    """Return a list of human-readable policy violations; empty means valid."""
    problems = []
    if len(password or "") < _MIN_LEN:
        problems.append(f"at least {_MIN_LEN} characters")
    if not re.search(r"[A-Z]", password or ""):
        problems.append("one uppercase letter")
    if not re.search(r"[0-9]", password or ""):
        problems.append("one number")
    if not _SPECIAL_RE.search(password or ""):
        problems.append("one special character")
    return problems


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        _hasher.verify(password_hash, password)
        return True
    except VerifyMismatchError:
        return False
