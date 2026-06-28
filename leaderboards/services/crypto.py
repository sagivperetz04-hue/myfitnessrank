import os
import threading

from cryptography.fernet import Fernet

# Lifter names are PII. They are stored only as Fernet (AES-128-CBC + HMAC)
# ciphertext at rest and decrypted just before serialization. The key is a
# urlsafe-base64 32-byte Fernet key, injected from a K8s Secret — never in git.
_fernet: Fernet | None = None
_lock = threading.Lock()


def _cipher() -> Fernet:
    global _fernet
    if _fernet is None:
        with _lock:
            if _fernet is None:
                key = os.environ.get("LEADERBOARD_ENC_KEY")
                if not key:
                    raise RuntimeError("LEADERBOARD_ENC_KEY is not set")
                _fernet = Fernet(key.encode())
    return _fernet


def encrypt_name(name: str) -> str:
    return _cipher().encrypt(name.encode()).decode()


def decrypt_name(token: str) -> str:
    return _cipher().decrypt(token.encode()).decode()
