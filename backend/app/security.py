"""认证与安全：密码加盐哈希、令牌签发与校验。"""
from __future__ import annotations

import hashlib
import os

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from .config import SECRET_KEY, TOKEN_EXPIRE_MINUTES

_serializer = URLSafeTimedSerializer(SECRET_KEY)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"pbkdf2${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_hex, dk_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(dk_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return dk == expected
    except (ValueError, AttributeError):
        return False


def create_token(user_id: int) -> str:
    return _serializer.dumps({"uid": user_id})


def decode_token(token: str) -> int | None:
    """返回 user_id；令牌无效或过期返回 None。"""
    try:
        data = _serializer.loads(token, max_age=TOKEN_EXPIRE_MINUTES * 60)
        return int(data["uid"])
    except (BadSignature, SignatureExpired, KeyError, TypeError):
        return None
