from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
from dataclasses import dataclass
from typing import List

from .config import settings


@dataclass
class UserRecord:
    username: str
    salt_b64: str
    hash_b64: str


def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)


def create_user(username: str, password: str) -> UserRecord:
    salt = secrets.token_bytes(16)
    pw_hash = _hash_password(password, salt)
    return UserRecord(
        username=username,
        salt_b64=base64.b64encode(salt).decode("utf-8"),
        hash_b64=base64.b64encode(pw_hash).decode("utf-8"),
    )


def verify_user(username: str, password: str, users: List[UserRecord]) -> bool:
    for u in users:
        if secrets.compare_digest(u.username, username):
            salt = base64.b64decode(u.salt_b64)
            expected = base64.b64decode(u.hash_b64)
            actual = _hash_password(password, salt)
            return secrets.compare_digest(actual, expected)
    return False


def load_users() -> List[UserRecord]:
    if not os.path.exists(settings.USERS_FILE):
        return []
    with open(settings.USERS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [UserRecord(**u) for u in data.get("users", [])]


def save_users(users: List[UserRecord]) -> None:
    os.makedirs(os.path.dirname(settings.USERS_FILE), exist_ok=True)
    with open(settings.USERS_FILE, "w", encoding="utf-8") as f:
        json.dump({"users": [u.__dict__ for u in users]}, f, indent=2)


def ensure_users_interactive() -> None:
    if os.path.exists(settings.USERS_FILE):
        return
    print("No users configured. Creating admin user for API access.")
    username = input("Admin username: ").strip()
    password = input("Admin password: ").strip()
    user = create_user(username, password)
    save_users([user])
    print("Saved users to", settings.USERS_FILE)
