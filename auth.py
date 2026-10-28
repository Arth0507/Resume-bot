import os
import time

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from db import conn

ALGO = "HS256"
TOKEN_LIFE = 7 * 24 * 3600  # 7 days
bearer = HTTPBearer(auto_error=False)


def secret():
    return os.getenv("SECRET_KEY", "dev-secret-change-me")


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode()[:72], bcrypt.gensalt()).decode()


def check_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode()[:72], hashed.encode())


def make_token(user_id: int) -> str:
    payload = {"sub": str(user_id), "exp": int(time.time()) + TOKEN_LIFE}
    return jwt.encode(payload, secret(), algorithm=ALGO)


def current_user(cred: HTTPAuthorizationCredentials = Depends(bearer)):
    if not cred:
        raise HTTPException(401, "Please log in")
    try:
        data = jwt.decode(cred.credentials, secret(), algorithms=[ALGO])
    except jwt.PyJWTError:
        raise HTTPException(401, "Session expired, please log in again")
    with conn() as c:
        row = c.execute("SELECT id, name, email FROM users WHERE id=?", (data["sub"],)).fetchone()
    if not row:
        raise HTTPException(401, "User not found")
    return dict(row)