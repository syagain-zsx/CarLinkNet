"""统计特征视图（论文 3.2.1）。

基于 CICFlowMeter 风格统计字段，选取数值特征并做标准化（StandardScaler）。
对应论文中“结构统计特征”分支，主要由一维 CNN 建模。
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

# CICFlowMeter 统计字段（数值型）
STAT_COLUMNS = [
    "Flow Duration",
    "Total Fwd Packets", "Total Backward Packets",
    "Total Length of Fwd Packets", "Total Length of Bwd Packets",
    "Fwd Packet Length Max", "Fwd Packet Length Min", "Fwd Packet Length Mean", "Fwd Packet Length Std",
    "Bwd Packet Length Max", "Bwd Packet Length Min", "Bwd Packet Length Mean", "Bwd Packet Length Std",
    "Flow Bytes/s", "Flow Packets/s",
    "Flow IAT Mean", "Flow IAT Std", "Flow IAT Max", "Flow IAT Min",
    "Fwd IAT Total", "Fwd IAT Mean", "Fwd IAT Std", "Fwd IAT Max", "Fwd IAT Min",
    "Bwd IAT Total", "Bwd IAT Mean", "Bwd IAT Std", "Bwd IAT Max", "Bwd IAT Min",
    "Fwd PSH Flags", "Bwd PSH Flags", "Fwd URG Flags", "Bwd URG Flags",
    "Active Mean", "Active Std", "Active Max", "Active Min",
    "Idle Mean", "Idle Std", "Idle Max", "Idle Min",
    "SYN Flag Count", "RST Flag Count", "PSH Flag Count", "ACK Flag Count",
    "URG Flag Count", "FIN Flag Count",
]


class StatisticalBuilder:
    """统计特征标准化器，fit 学习缩放参数，transform 输出标准化后的特征矩阵。"""

    def __init__(self):
        self.scaler = StandardScaler()
        self.columns: list[str] | None = None

    def _matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        x = pd.DataFrame(index=df.index)
        for c in STAT_COLUMNS:
            x[c] = df[c] if c in df.columns else 0.0
        return x.replace([np.inf, -np.inf], np.nan).fillna(0.0).astype(float)

    def fit(self, df: pd.DataFrame) -> "StatisticalBuilder":
        self.columns = STAT_COLUMNS
        self.scaler.fit(self._matrix(df))
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        z = self.scaler.transform(self._matrix(df))
        return pd.DataFrame(z, columns=[f"stat_{c}" for c in self.columns], index=df.index)

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        self.fit(df)
        return self.transform(df)
