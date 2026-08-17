"""用户管理接口（管理员）：用户列表 / 角色与启停管理。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_conn
from ..deps import require_admin
from ..schemas import UserOut, UserUpdateIn

router = APIRouter(prefix="/user", tags=["用户管理"])


@router.get("/list", response_model=list[UserOut])
def list_users(admin: dict = Depends(require_admin)):
    conn = get_conn()
    try:
        rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    finally:
        conn.close()
    return [UserOut(id=r["id"], username=r["username"], display_name=r["display_name"],
                    role=r["role"], enabled=bool(r["enabled"]), created_at=r["created_at"]) for r in rows]


@router.post("/{user_id}/update", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdateIn, admin: dict = Depends(require_admin)):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="用户不存在")
        if user_id == admin["id"] and payload.enabled is False:
            raise HTTPException(status_code=400, detail="不能禁用自己")
        if payload.role is not None and payload.role not in ("admin", "user"):
            raise HTTPException(status_code=400, detail="角色必须为 admin 或 user")
        if payload.role is not None:
            conn.execute("UPDATE users SET role = ? WHERE id = ?", (payload.role, user_id))
        if payload.enabled is not None:
            conn.execute("UPDATE users SET enabled = ? WHERE id = ?", (int(payload.enabled), user_id))
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    finally:
        conn.close()
    return UserOut(id=row["id"], username=row["username"], display_name=row["display_name"],
                   role=row["role"], enabled=bool(row["enabled"]), created_at=row["created_at"])
