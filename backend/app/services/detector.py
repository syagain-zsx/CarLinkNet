"""检测编排服务：规则检测 / 模型检测 / 协同检测。"""
from __future__ import annotations

import threading

import numpy as np
import pandas as pd

from ..config import MODEL_DIR
from ..core.detector import EnsembleDetector
from .rule_engine import RuleEngine, DEFAULT_RULES

# 模型检测器懒加载单例（避免每个任务重复加载 torch/xgboost 权重）
_lock = threading.Lock()
_detector: EnsembleDetector | None = None


def get_detector() -> EnsembleDetector:
    global _detector
    with _lock:
        if _detector is None:
            _detector = EnsembleDetector.load(MODEL_DIR)
        return _detector


def _model_predict(df: pd.DataFrame, use_student: bool):
    """模型检测：返回 (labels, confidence)。"""
    det = get_detector()
    r = det.predict(df, use_student=use_student)
    return np.asarray(r["labels"]), np.asarray(r["confidence"], dtype=float)


def run_detection(df: pd.DataFrame, mode: str, rules: list[dict] | None = None,
                  use_student: bool = False):
    """对流量 DataFrame 执行检测。

    mode: rule / model / collaborative
    返回 dict: {labels, confidence, source}
    """
    if mode == "rule":
        engine = RuleEngine(rules if rules is not None else DEFAULT_RULES)
        labels, matched = engine.match(df)
        confidence = np.where(matched, 1.0, 0.0)
        labels = np.where(matched, labels, "BENIGN")
        source = "rule"
    elif mode == "model":
        labels, confidence = _model_predict(df, use_student)
        source = "student" if use_student else "ensemble"
    elif mode == "collaborative":
        # 协同：规则快判优先，未命中交模型（论文图 4.4 分阶段逻辑）
        engine = RuleEngine(rules if rules is not None else DEFAULT_RULES)
        rule_labels, matched = engine.match(df)
        model_labels, model_conf = _model_predict(df, use_student)
        labels = np.where(matched, rule_labels, model_labels)
        confidence = np.where(matched, 1.0, model_conf)
        source = "collaborative"
    else:
        raise ValueError(f"未知检测模式: {mode}")

    return {"labels": labels, "confidence": confidence, "source": source}

