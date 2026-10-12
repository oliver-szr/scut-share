import hashlib
import secrets

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError

password_hasher = PasswordHasher(
    time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16, type=Type.ID,
)
# Unknown accounts still perform password verification, without a fixed dummy password.
_dummy_hash = password_hasher.hash(secrets.token_urlsafe(32))


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, stored_hash: str | None) -> bool:
    try:
        valid = password_hasher.verify(stored_hash or _dummy_hash, password)
        return valid and stored_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def mask_student_no(student_no: str) -> str:
    visible = min(4, max(1, len(student_no) // 2))
    return "*" * (len(student_no) - visible) + student_no[-visible:]
