"""数据管理接口：流量数据上传 / 列表 / 删除。"""
from __future__ import annotations

import uuid
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from ..config import UPLOAD_DIR
from ..database import get_conn
from ..deps import get_current_user
from ..schemas import DatasetOut

router = APIRouter(prefix="/data", tags=["数据管理"])


@router.post("/upload", response_model=DatasetOut)
def upload(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="仅支持 CSV 文件")
    name = (file.filename or "flows.csv").rsplit(".", 1)[0]
    unique = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    path = Path(UPLOAD_DIR) / unique
    content = file.file.read()
    path.write_bytes(content)
    try:
        df = pd.read_csv(path)
        rows = int(len(df))
    except Exception as e:  # noqa: BLE001
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"CSV 解析失败: {e}") from e

    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO datasets (name, filename, path, rows) VALUES (?, ?, ?, ?)",
            (name, file.filename, str(path), rows),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM datasets WHERE id = ?", (cur.lastrowid,)).fetchone()
    finally:
        conn.close()
    return DatasetOut(id=row["id"], name=row["name"], filename=row["filename"],
                      rows=row["rows"], uploaded_at=row["uploaded_at"])


@router.get("/list", response_model=list[DatasetOut])
def list_datasets(user: dict = Depends(get_current_user)):
    conn = get_conn()
    try:
        rows = conn.execute("SELECT * FROM datasets ORDER BY id DESC").fetchall()
    finally:
        conn.close()
    return [DatasetOut(id=r["id"], name=r["name"], filename=r["filename"],
                       rows=r["rows"], uploaded_at=r["uploaded_at"]) for r in rows]


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: int, user: dict = Depends(get_current_user)):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="数据集不存在")
        Path(row["path"]).unlink(missing_ok=True)
        conn.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))
        conn.commit()
    finally:
        conn.close()
    return {"ok": True}
