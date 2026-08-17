"""特征生成接口：选择数据集生成多视图特征集，返回维度统计。"""
from __future__ import annotations

import json

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from ..config import DATA_DIR
from ..core.features import MultiViewPipeline
from ..database import get_conn
from ..deps import get_current_user
from ..schemas import FeatureGenIn, FeatureSetOut

router = APIRouter(prefix="/feature", tags=["特征生成"])

VIEW_LABELS = {"statistical": "统计特征", "btsf": "行为时间结构特征", "frequency": "多尺度频域特征"}


@router.post("/generate")
def generate(payload: FeatureGenIn, user: dict = Depends(get_current_user)):
    conn = get_conn()
    try:
        dataset = conn.execute("SELECT * FROM datasets WHERE id = ?", (payload.dataset_id,)).fetchone()
    finally:
        conn.close()
    if dataset is None:
        raise HTTPException(status_code=404, detail="数据集不存在")

    df = pd.read_csv(dataset["path"])
    pipe = MultiViewPipeline().fit(df)
    views = pipe.transform(df)
    dims = {k: int(v.shape[1]) for k, v in views.items()}

    feature_type = payload.feature_type
    if feature_type != "all" and feature_type in dims:
        dims = {feature_type: dims[feature_type]}

    name = payload.name or f"{dataset['name']}-{feature_type}"
    dims_str = json.dumps(dims, ensure_ascii=False)
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO feature_sets (name, dataset_id, feature_type, dimensions) VALUES (?, ?, ?, ?)",
            (name, dataset["id"], feature_type, dims_str),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM feature_sets WHERE id = ?", (cur.lastrowid,)).fetchone()
    finally:
        conn.close()

    return {
        "id": row["id"],
        "name": row["name"],
        "dataset_id": row["dataset_id"],
        "feature_type": row["feature_type"],
        "dimensions": dims,
        "total": sum(dims.values()),
        "view_labels": {k: VIEW_LABELS.get(k, k) for k in dims},
    }


@router.get("/list", response_model=list[FeatureSetOut])
def list_features(user: dict = Depends(get_current_user)):
    conn = get_conn()
    try:
        rows = conn.execute("SELECT * FROM feature_sets ORDER BY id DESC").fetchall()
    finally:
        conn.close()
    return [FeatureSetOut(id=r["id"], name=r["name"], dataset_id=r["dataset_id"],
                          feature_type=r["feature_type"], dimensions=r["dimensions"],
                          created_at=r["created_at"]) for r in rows]


@router.get("/types")
def feature_types(user: dict = Depends(get_current_user)):
    """返回三类特征视图的说明（供前端下拉选择）。"""
    return [
        {"value": "all", "label": "全部视图（拼接）", "dim": 103},
        {"value": "statistical", "label": "统计特征", "dim": 47},
        {"value": "btsf", "label": "行为时间结构特征", "dim": 38},
        {"value": "frequency", "label": "多尺度频域特征", "dim": 18},
    ]
