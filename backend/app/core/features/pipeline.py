"""多视图特征流水线：统一组织三类特征视图与标签编码。

用法：
    pipe = MultiViewPipeline().fit(train_df)
    views = pipe.transform(df)      # {"statistical": df, "btsf": df, "frequency": df}
    y = pipe.encode_labels(df)      # np.ndarray[int]
    names = pipe.classes_           # 类别名列表
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .statistical import StatisticalBuilder
from .btsf import BTSFBuilder
from .frequency import FrequencyBuilder


class MultiViewPipeline:
    def __init__(self, wavelet: str = "db4", level: int = 3):
        self.stat = StatisticalBuilder()
        self.btsf = BTSFBuilder()
        self.freq = FrequencyBuilder(wavelet, level)
        self.classes_: list[str] = []
        self._label_map: dict[str, int] = {}

    def _fit_labels(self, df: pd.DataFrame):
        if "Label" not in df.columns:
            self.classes_ = []
            return
        self.classes_ = sorted(df["Label"].dropna().unique().tolist())
        self._label_map = {name: i for i, name in enumerate(self.classes_)}

    def fit(self, df: pd.DataFrame) -> "MultiViewPipeline":
        self.stat.fit(df)
        self.btsf.fit(df)
        self.freq.fit(df)
        self._fit_labels(df)
        return self

    def transform(self, df: pd.DataFrame) -> dict[str, pd.DataFrame]:
        return {
            "statistical": self.stat.transform(df),
            "btsf": self.btsf.transform(df),
            "frequency": self.freq.transform(df),
        }

    def fit_transform(self, df: pd.DataFrame) -> dict[str, pd.DataFrame]:
        self.fit(df)
        return self.transform(df)

    def encode_labels(self, df: pd.DataFrame) -> np.ndarray:
        if not self._label_map or "Label" not in df.columns:
            return np.zeros(len(df), dtype=int)
        return df["Label"].map(self._label_map).fillna(0).astype(int).values

    def decode_label(self, idx: int) -> str:
        if 0 <= idx < len(self.classes_):
            return self.classes_[idx]
        return "UNKNOWN"

    def concat_views(self, views: dict[str, pd.DataFrame]) -> np.ndarray:
        """将三类视图按列拼接，作为轻量学生模型 / 联邦学习模型的统一输入。"""
        return np.hstack([v.values for v in views.values()]).astype(np.float32)

    @property
    def view_shapes(self) -> dict[str, tuple]:
        return {
            "statistical": (len(self.stat.columns),) if self.stat.columns else (0,),
            "btsf": (len(self.btsf.columns),) if self.btsf.columns else (0,),
            "frequency": (len(self.freq.columns),) if self.freq.columns else (0,),
        }
