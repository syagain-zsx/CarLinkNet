"""任务调度：任务编码生成 + 后台线程执行 + 状态机更新。"""
from __future__ import annotations

import json
import threading
import uuid
from collections import Counter
from datetime import datetime

import numpy as np
import pandas as pd

from ..config import LABELS
from ..database import get_conn
from .detector import run_detection
from .rule_engine import DEFAULT_RULES


def make_task_code() -> str:
    return "TASK-" + datetime.now().strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6].upper()


def _load_rules(ruleset_row) -> list[dict] | None:
    if not ruleset_row or not ruleset_row["path"]:
        return None
    try:
        data = json.loads(open(ruleset_row["path"], encoding="utf-8").read())
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, list) else data.get("rules", DEFAULT_RULES)


def execute_task(task_id: int):
    """后台执行：加载数据集 -> 检测 -> 聚合落库 -> 更新状态（pending/running/finished/failed）。"""
    conn = get_conn()
    try:
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if task is None:
            return
        conn.execute("UPDATE tasks SET status = 'running' WHERE id = ?", (task_id,))
        conn.commit()
        dataset = conn.execute("SELECT * FROM datasets WHERE id = ?", (task["dataset_id"],)).fetchone()
        ruleset = conn.execute("SELECT * FROM rulesets WHERE id = ?", (task["ruleset_id"],)).fetchone() \
            if task["ruleset_id"] else None
    finally:
        conn.close()

    try:
        df = pd.read_csv(dataset["path"])
        rules = _load_rules(ruleset)
        result = run_detection(df, task["mode"], rules, bool(task["use_student"]))

        labels = np.asarray(result["labels"], dtype=object)
        confidence = np.asarray(result["confidence"], dtype=float)
        counts = Counter(labels.tolist())
        conf_sum: Counter = Counter()
        conf_cnt: Counter = Counter()
        for lb, cf in zip(labels, confidence):
            conf_sum[lb] += float(cf)
            conf_cnt[lb] += 1

        conn = get_conn()
        try:
            conn.execute("DELETE FROM results WHERE task_id = ?", (task_id,))
            ordered = LABELS + [x for x in counts if x not in LABELS]
            for lb in ordered:
                if counts.get(lb, 0) == 0:
                    continue
                avg = conf_sum.get(lb, 0.0) / max(conf_cnt.get(lb, 1), 1)
                conn.execute(
                    "INSERT INTO results (task_id, label, count, confidence_avg) VALUES (?, ?, ?, ?)",
                    (task_id, lb, counts[lb], round(avg, 4)),
                )
            conn.execute(
                "UPDATE tasks SET status = 'finished', finished_at = datetime('now','localtime') WHERE id = ?",
                (task_id,),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:  # noqa: BLE001
        conn = get_conn()
        try:
            conn.execute(
                "UPDATE tasks SET status = 'failed', message = ?, finished_at = datetime('now','localtime') WHERE id = ?",
                (str(e)[:500], task_id),
            )
            conn.commit()
        finally:
            conn.close()


def submit_task(task_id: int) -> threading.Thread:
    """提交后台线程执行任务。"""
    t = threading.Thread(target=execute_task, args=(task_id,), daemon=True)
    t.start()
    return t
