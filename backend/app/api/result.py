"""结果分析接口：任务结果汇总 / 仪表盘统计。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_conn
from ..deps import get_current_user
from ..schemas import ResultItem, ResultOut, TaskOut

router = APIRouter(prefix="/result", tags=["结果分析"])


@router.get("/summary")
def summary(user: dict = Depends(get_current_user)):
    """仪表盘统计卡片数据（需定义在 /{task_code} 之前，避免路径参数吞掉 summary）。"""
    conn = get_conn()
    try:
        n_tasks = conn.execute("SELECT COUNT(*) c FROM tasks").fetchone()["c"]
        n_finished = conn.execute("SELECT COUNT(*) c FROM tasks WHERE status='finished'").fetchone()["c"]
        n_running = conn.execute("SELECT COUNT(*) c FROM tasks WHERE status IN ('pending','running')").fetchone()["c"]
        n_failed = conn.execute("SELECT COUNT(*) c FROM tasks WHERE status='failed'").fetchone()["c"]
        n_datasets = conn.execute("SELECT COUNT(*) c FROM datasets").fetchone()["c"]
        n_rulesets = conn.execute("SELECT COUNT(*) c FROM rulesets").fetchone()["c"]
        attack_rows = conn.execute("SELECT COALESCE(SUM(count),0) s FROM results WHERE label != 'BENIGN'").fetchone()["s"]
        benign_rows = conn.execute("SELECT COALESCE(SUM(count),0) s FROM results WHERE label = 'BENIGN'").fetchone()["s"]
    finally:
        conn.close()
    return {
        "total_tasks": n_tasks,
        "finished_tasks": n_finished,
        "running_tasks": n_running,
        "failed_tasks": n_failed,
        "total_datasets": n_datasets,
        "total_rulesets": n_rulesets,
        "total_attacks": attack_rows,
        "total_benign": benign_rows,
    }


@router.get("/{task_code}", response_model=ResultOut)
def get_result(task_code: str, user: dict = Depends(get_current_user)):
    conn = get_conn()
    try:
        task = conn.execute("SELECT * FROM tasks WHERE task_code = ?", (task_code,)).fetchone()
        if task is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        rows = conn.execute("SELECT * FROM results WHERE task_id = ? ORDER BY count DESC", (task["id"],)).fetchall()
    finally:
        conn.close()

    items = [ResultItem(label=r["label"], count=r["count"], confidence_avg=r["confidence_avg"]) for r in rows]
    total = sum(i.count for i in items)
    attack_count = sum(i.count for i in items if i.label != "BENIGN")
    benign_count = sum(i.count for i in items if i.label == "BENIGN")
    task_out = TaskOut(
        id=task["id"], task_code=task["task_code"], name=task["name"], mode=task["mode"],
        dataset_id=task["dataset_id"], ruleset_id=task["ruleset_id"],
        use_student=bool(task["use_student"]), status=task["status"],
        message=task["message"], created_at=task["created_at"], finished_at=task["finished_at"],
    )
    source = "student" if task_out.use_student else ("rule" if task_out.mode == "rule" else task_out.mode)
    return ResultOut(task=task_out, source=source, total=total,
                     attack_count=attack_count, benign_count=benign_count, items=items)
