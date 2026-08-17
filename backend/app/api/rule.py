"""规则管理接口：规则集上传 / 列表 / 启停 / 内置默认规则。"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from ..config import UPLOAD_DIR
from ..database import get_conn
from ..deps import get_current_user
from ..schemas import RuleOut
from ..services.rule_engine import DEFAULT_RULES

router = APIRouter(prefix="/rule", tags=["规则管理"])


@router.get("/list", response_model=list[RuleOut])
def list_rules(user: dict = Depends(get_current_user)):
    conn = get_conn()
    try:
        rows = conn.execute("SELECT * FROM rulesets ORDER BY id DESC").fetchall()
    finally:
        conn.close()
    return [RuleOut(id=r["id"], name=r["name"], filename=r["filename"],
                    enabled=bool(r["enabled"]), rule_count=r["rule_count"],
                    uploaded_at=r["uploaded_at"]) for r in rows]


@router.get("/default")
def default_rules(user: dict = Depends(get_current_user)):
    """返回内置默认规则，供前端展示与快速创建。"""
    return {"rules": DEFAULT_RULES, "count": len(DEFAULT_RULES)}


@router.post("/upload", response_model=RuleOut)
def upload(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if not (file.filename or "").lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="仅支持 JSON 规则文件")
    content = file.file.read()
    try:
        data = json.loads(content.decode("utf-8"))
        rules = data if isinstance(data, list) else data.get("rules", [])
        if not isinstance(rules, list) or not rules:
            raise ValueError("规则文件为空或格式错误")
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"规则解析失败: {e}") from e

    name = (file.filename or "rules.json").rsplit(".", 1)[0]
    path = Path(UPLOAD_DIR) / f"rules_{uuid.uuid4().hex[:8]}.json"
    path.write_bytes(content)

    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO rulesets (name, filename, path, rule_count) VALUES (?, ?, ?, ?)",
            (name, file.filename, str(path), len(rules)),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM rulesets WHERE id = ?", (cur.lastrowid,)).fetchone()
    finally:
        conn.close()
    return RuleOut(id=row["id"], name=row["name"], filename=row["filename"],
                   enabled=bool(row["enabled"]), rule_count=row["rule_count"],
                   uploaded_at=row["uploaded_at"])


@router.post("/{rule_id}/toggle", response_model=RuleOut)
def toggle(rule_id: int, user: dict = Depends(get_current_user)):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM rulesets WHERE id = ?", (rule_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="规则集不存在")
        new_enabled = 0 if row["enabled"] else 1
        conn.execute("UPDATE rulesets SET enabled = ? WHERE id = ?", (new_enabled, rule_id))
        conn.commit()
        row = conn.execute("SELECT * FROM rulesets WHERE id = ?", (rule_id,)).fetchone()
    finally:
        conn.close()
    return RuleOut(id=row["id"], name=row["name"], filename=row["filename"],
                   enabled=bool(row["enabled"]), rule_count=row["rule_count"],
                   uploaded_at=row["uploaded_at"])


@router.delete("/{rule_id}")
def delete(rule_id: int, user: dict = Depends(get_current_user)):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM rulesets WHERE id = ?", (rule_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="规则集不存在")
        if row["path"]:
            Path(row["path"]).unlink(missing_ok=True)
        conn.execute("DELETE FROM rulesets WHERE id = ?", (rule_id,))
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}
