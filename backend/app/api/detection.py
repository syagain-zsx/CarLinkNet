"""检测中心接口：创建检测任务 / 任务列表 / 任务详情。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_conn
from ..deps import get_current_user
from ..schemas import DetectionCreateIn, TaskOut
from ..services.scheduler import make_task_code, submit_task

router = APIRouter(prefix="/detection", tags=["检测中心"])

MODES = ["rule", "model", "collaborative"]


def _to_task(row) -> TaskOut:
    return TaskOut(
        id=row["id"], task_code=row["task_code"], name=row["name"], mode=row["mode"],
        dataset_id=row["dataset_id"], ruleset_id=row["ruleset_id"],
        use_student=bool(row["use_student"]), status=row["status"],
        message=row["message"], created_at=row["created_at"], finished_at=row["finished_at"],
    )


@router.post("/task", response_model=TaskOut)
def create_task(payload: DetectionCreateIn, user: dict = Depends(get_current_user)):
    if payload.mode not in MODES:
        raise HTTPException(status_code=400, detail=f"mode 必须为 {MODES}")
    conn = get_conn()
    try:
        dataset = conn.execute("SELECT id FROM datasets WHERE id = ?", (payload.dataset_id,)).fetchone()
        if dataset is None:
            raise HTTPException(status_code=404, detail="数据集不存在")
        if payload.ruleset_id and payload.mode in ("rule", "collaborative"):
            ruleset = conn.execute("SELECT id FROM rulesets WHERE id = ?", (payload.ruleset_id,)).fetchone()
            if ruleset is None:
                raise HTTPException(status_code=404, detail="规则集不存在")
        name = payload.name or f"检测任务-{payload.mode}"
        code = make_task_code()
        cur = conn.execute(
            "INSERT INTO tasks (task_code, name, mode, dataset_id, ruleset_id, use_student) VALUES (?, ?, ?, ?, ?, ?)",
            (code, name, payload.mode, payload.dataset_id, payload.ruleset_id, int(payload.use_student)),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    finally:
        conn.close()

    submit_task(row["id"])
    return _to_task(row)


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(user: dict = Depends(get_current_user)):
    conn = get_conn()
    try:
        rows = conn.execute("SELECT * FROM tasks ORDER BY id DESC LIMIT 200").fetchall()
    finally:
        conn.close()
    return [_to_task(r) for r in rows]


@router.get("/task/{task_code}", response_model=TaskOut)
def get_task(task_code: str, user: dict = Depends(get_current_user)):
    conn = get_conn()
    try:
        row = conn.execute("SELECT * FROM tasks WHERE task_code = ?", (task_code,)).fetchone()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return _to_task(row)
