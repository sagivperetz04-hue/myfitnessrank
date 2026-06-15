"""Unit tests for email/password policy and hashing — no database required."""

from services.security import (
    hash_password,
    is_valid_email,
    password_problems,
    username_problems,
    verify_password,
)


class TestEmail:
    def test_accepts_plain_address(self):
        assert is_valid_email("lifter@example.com")

    def test_accepts_plus_and_dots(self):
        assert is_valid_email("first.last+tag@sub.example.co")

    def test_rejects_missing_at(self):
        assert not is_valid_email("lifterexample.com")

    def test_rejects_missing_tld(self):
        assert not is_valid_email("lifter@example")

    def test_rejects_empty(self):
        assert not is_valid_email("")


class TestPasswordPolicy:
    def test_accepts_compliant_password(self):
        assert password_problems("Squat123!") == []

    def test_flags_too_short(self):
        assert "at least 8 characters" in password_problems("Sq1!")

    def test_flags_missing_uppercase(self):
        assert "one uppercase letter" in password_problems("squat123!")

    def test_flags_missing_number(self):
        assert "one number" in password_problems("SquatPass!")

    def test_flags_missing_special(self):
        assert "one special character" in password_problems("SquatPass1")

    def test_collects_multiple_problems(self):
        # "squat" violates every rule: too short, no upper, no digit, no special
        assert len(password_problems("squat")) == 4


class TestUsernamePolicy:
    def test_accepts_simple_username(self):
        assert username_problems("lifter") == []

    def test_accepts_letters_digits_underscore(self):
        assert username_problems("Squat_Master_99") == []

    def test_flags_too_short(self):
        assert "3 to 20 characters" in username_problems("ab")

    def test_flags_too_long(self):
        assert "3 to 20 characters" in username_problems("a" * 21)

    def test_flags_illegal_characters(self):
        assert "only letters, numbers, and underscores" in username_problems("bad name!")

    def test_rejects_empty(self):
        assert username_problems("") == ["3 to 20 characters"]


class TestHashing:
    def test_hash_is_not_plaintext(self):
        h = hash_password("Squat123!")
        assert h != "Squat123!"
        assert h.startswith("$argon2id$")

    def test_verify_accepts_correct_password(self):
        h = hash_password("Squat123!")
        assert verify_password(h, "Squat123!")

    def test_verify_rejects_wrong_password(self):
        h = hash_password("Squat123!")
        assert not verify_password(h, "Deadlift123!")

    def test_salts_differ_per_hash(self):
        assert hash_password("Squat123!") != hash_password("Squat123!")
