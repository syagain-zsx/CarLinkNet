"""多视图集成检测器：封装特征流水线 + 分支模型 + PSO-CFW 集成 + 轻量学生模型。

提供训练产物的一键保存/加载，以及面向单条/批量流量数据的推理接口，供后端
检测模块与训练脚本复用。
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from .features import MultiViewPipeline
from .models import CNNModel, XGBModel, FTTModel, StudentModel
from .ensemble import PSO_CFW

VIEW_ORDER = ["statistical", "btsf", "frequency"]


class EnsembleDetector:
    def __init__(self, pipeline: MultiViewPipeline, branch_models: dict,
                 pso: PSO_CFW, student: StudentModel | None = None):
        self.pipeline = pipeline
        self.branch_models = branch_models
        self.pso = pso
        self.student = student

    # ---------- 推理 ----------
    def predict(self, df: pd.DataFrame, use_student: bool = False) -> dict:
        """对流量 DataFrame 进行检测。

        返回 dict：
            labels: 每行样本的判决类别名
            proba: (n, C) 类别概率
            confidence: 每行最大概率
            source: "ensemble" 或 "student"
            branch_probs: 各分支视图的概率 (n, C)
        """
        views = self.pipeline.transform(df)
        branch_probs = {k: self.branch_models[k].predict_proba(views[k].values) for k in VIEW_ORDER}

        if use_student and self.student is not None:
            X = self.pipeline.concat_views(views)
            proba = self.student.predict_proba(X)
            source = "student"
        else:
            proba = self.pso.predict_proba([branch_probs[k] for k in VIEW_ORDER])
            source = "ensemble"

        pred_idx = proba.argmax(axis=1)
        labels = [self.pipeline.decode_label(i) for i in pred_idx]
        confidence = proba.max(axis=1)
        return {
            "labels": labels,
            "proba": proba,
            "confidence": confidence,
            "source": source,
            "branch_probs": branch_probs,
        }

    # ---------- 序列化 ----------
    def save(self, directory: str | Path):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        meta = {
            "classes": self.pipeline.classes_,
            "n_classes": len(self.pipeline.classes_),
            "view_columns": {
                "statistical": self.pipeline.stat.columns or [],
                "btsf": self.pipeline.btsf.columns or [],
                "frequency": self.pipeline.freq.columns or [],
            },
            "has_student": self.student is not None,
        }
        (directory / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        with open(directory / "pipeline.pkl", "wb") as f:
            pickle.dump(self.pipeline, f)
        with open(directory / "pso.pkl", "wb") as f:
            pickle.dump(self.pso, f)
        self.branch_models["statistical"].save(directory / "cnn.pt")
        self.branch_models["btsf"].save(directory / "xgb.json")
        self.branch_models["frequency"].save(directory / "ftt.pt")
        if self.student is not None:
            self.student.save(directory / "student.pt")

    @classmethod
    def load(cls, directory: str | Path) -> "EnsembleDetector":
        directory = Path(directory)
        meta = json.loads((directory / "meta.json").read_text(encoding="utf-8"))
        with open(directory / "pipeline.pkl", "rb") as f:
            pipeline = pickle.load(f)
        with open(directory / "pso.pkl", "rb") as f:
            pso = pickle.load(f)

        n_classes = meta["n_classes"]
        vc = meta["view_columns"]
        stat = CNNModel(n_classes, n_features=len(vc["statistical"]))
        stat.load(directory / "cnn.pt")
        xgbm = XGBModel(n_classes, n_features=len(vc["btsf"]))
        xgbm.load(directory / "xgb.json")
        ftt = FTTModel(n_classes, n_features=len(vc["frequency"]))
        ftt.load(directory / "ftt.pt")
        branch_models = {"statistical": stat, "btsf": xgbm, "frequency": ftt}

        student = None
        if meta.get("has_student"):
            concat_dim = sum(len(v) for v in vc.values())
            student = StudentModel(n_classes, n_features=concat_dim)
            student.load(directory / "student.pt")

        return cls(pipeline, branch_models, pso, student)
