"""多尺度频域特征（论文 3.2.3）。

流程：构造时间统计结构向量 s（10 维，按短/中/长期尺度语义排序）→ 3 层离散
小波变换(DWT) → {A3, D3, D2, D1} 四组频带 → 逐频带提取能量/相对能量/均值/标准差，
再计算多尺度谱熵与主导频带，共 18 维（论文表 3.5）。
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import pywt

# 时间统计结构向量（论文式 3.15）——按短/中/长期尺度语义排序
S_VECTOR_COLS = [
    "Flow IAT Min", "Flow IAT Max", "Flow IAT Std",     # 短时尺度
    "Active Mean", "Active Std", "Idle Mean", "Idle Std",  # 中时尺度
    "Flow IAT Mean", "Flow Duration", "Flow Packets/s",  # 长时尺度
]


class FrequencyBuilder:
    """多尺度频域特征构造器（无需 fit，逐样本计算）。"""

    def __init__(self, wavelet: str = "db4", level: int = 3):
        self.wavelet = wavelet
        self.level = level
        self.columns: list[str] | None = None

    def _build_vector(self, df: pd.DataFrame) -> pd.DataFrame:
        x = pd.DataFrame(index=df.index)
        for c in S_VECTOR_COLS:
            x[c] = df[c] if c in df.columns else 0.0
        return x.replace([np.inf, -np.inf], np.nan).fillna(0.0).astype(float)

    def _band_names(self) -> list[str]:
        # 从低频到高频：A3, D3, D2, D1
        return ["A" + str(self.level)] + ["D" + str(self.level - i + 1) for i in range(1, self.level + 1)]

    def _dwt_features(self, s: np.ndarray) -> dict[str, float]:
        # 样本内标准化，消除特征间量纲差异，突出相对结构
        std = float(np.std(s))
        z = (s - np.mean(s)) / (std + 1e-9) if std > 1e-12 else np.zeros_like(s)
        with warnings.catch_warnings():
            # 短序列做高层 DWT 会触发边界效应提示，属预期行为，此处静默
            warnings.simplefilter("ignore", UserWarning)
            coeffs = pywt.wavedec(z, self.wavelet, level=self.level)
        # coeffs = [cA_level, cD_level, ..., cD1]
        names = self._band_names()
        energies = [float(np.sum(np.square(c))) for c in coeffs]
        total = float(np.sum(energies)) + 1e-12

        feats: dict[str, float] = {}
        for name, c, e in zip(names, coeffs, energies):
            feats[f"E_{name}"] = e
            feats[f"R_{name}"] = e / total
            feats[f"M_{name}"] = float(np.mean(c))
            feats[f"S_{name}"] = float(np.std(c))

        p = np.array(energies) / total
        p = p[p > 0]
        feats["SpecEntropy"] = float(-np.sum(p * np.log(p)))
        feats["DominantBand"] = float(np.argmax(energies))
        return feats

    def fit(self, df: pd.DataFrame) -> "FrequencyBuilder":
        # 频域特征逐样本计算，无需拟合基线
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        vec = self._build_vector(df)
        rows = [self._dwt_features(vec.iloc[i].values) for i in range(len(vec))]
        result = pd.DataFrame(rows, index=df.index)
        self.columns = list(result.columns)
        return result

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.transform(df)
