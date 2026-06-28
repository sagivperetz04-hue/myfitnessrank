"""Name encryption round-trip — no database required."""

import os

from cryptography.fernet import Fernet

# A throwaway key for the test process only; the real key comes from a Secret.
os.environ.setdefault("LEADERBOARD_ENC_KEY", Fernet.generate_key().decode())

import services.crypto as crypto  # noqa: E402


class TestNameEncryption:
    def test_round_trip(self):
        assert (
            crypto.decrypt_name(crypto.encrypt_name("Ray Williams")) == "Ray Williams"
        )

    def test_ciphertext_is_not_plaintext(self):
        token = crypto.encrypt_name("Jesus Olivares")
        assert "Jesus" not in token
        assert token != "Jesus Olivares"

    def test_randomized_ciphertext(self):
        # Fernet embeds a random IV, so the same name encrypts to different tokens.
        assert crypto.encrypt_name("Stefi Cohen") != crypto.encrypt_name("Stefi Cohen")

    def test_handles_unicode(self):
        name = "Žydrūnas Savickas"
        assert crypto.decrypt_name(crypto.encrypt_name(name)) == name
