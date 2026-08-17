"""FastAPI 依赖：鉴权与权限。"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Header

from .database import get_conn
from .security import decode_token


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    """解析 Authorization: Bearer <token>，返回当前用户行。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization[len("Bearer "):].strip()
    uid = decode_token(token)
    if uid is None:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    user = dict(row)
    if not user["enabled"]:
        raise HTTPException(status_code=403, detail="账号已被禁用")
    return user


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user
