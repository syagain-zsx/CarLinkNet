"""认证接口：注册 / 登录 / 当前用户。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_conn
from ..deps import get_current_user
from ..schemas import RegisterIn, LoginIn, UserOut, TokenOut
from ..security import hash_password, verify_password, create_token

router = APIRouter(prefix="/auth", tags=["认证"])


def _to_user(row) -> UserOut:
    return UserOut(
        id=row["id"], username=row["username"], display_name=row["display_name"],
        role=row["role"], enabled=bool(row["enabled"]), created_at=row["created_at"],
    )


@router.post("/register", response_model=TokenOut)
def register(payload: RegisterIn):
    conn = get_conn()
    try:
        exists = conn.execute("SELECT id FROM users WHERE username = ?", (payload.username,)).fetchone()
        if exists:
            raise HTTPException(status_code=400, detail="用户名已存在")
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, display_name, role) VALUES (?, ?, ?, 'user')",
            (payload.username, hash_password(payload.password), payload.display_name or payload.username),
        )
        conn.commit()
        uid = cur.lastrowid
        row = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    finally:
        conn.close()
    return TokenOut(token=create_token(uid), user=_to_user(row))


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (payload.username,)).fetchone()
        if row is None or not verify_password(payload.password, row["password_hash"]):
            raise HTTPException(status_code=400, detail="用户名或密码错误")
        if not row["enabled"]:
            raise HTTPException(status_code=403, detail="账号已被禁用")
    finally:
        conn.close()
    return TokenOut(token=create_token(row["id"]), user=_to_user(row))


@router.get("/me", response_model=UserOut)
def me(user: dict = Depends(get_current_user)):
    return _to_user(user)
