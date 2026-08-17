"""统一数据接入接口。

真实 CICIDS2017 数据接入：将官方 MachineLearningCSV 目录下合并后的 CSV 放入
data/ 目录，列名与 synthetic.py 生成的字段保持一致，直接调用 load_flow_csv()。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def load_flow_csv(path: str | Path) -> pd.DataFrame:
    """加载流级 CSV（合成示例或 CICIDS2017 预处理文件）。"""
    df = pd.read_csv(path)
    df = df.replace([np.inf, -np.inf], np.nan)
    return df


def _merge_label(raw: str) -> str:
    """合并 CICIDS2017 中 Web Attack 的多个子类，统一为 Web Attack。"""
    if not isinstance(raw, str):
        return raw
    if raw.lower().startswith("web attack"):
        return "Web Attack"
    return raw


def load_cicids2017(csv_path: str | Path) -> pd.DataFrame:
    """预留接口：加载官方 CICIDS2017 预处理 CSV，清洗并合并类别。

    官方 CSV 含 'Label' 列（如 'BENIGN'、'DDoS'、'PortScan'、'Web Attack - Brute Force' 等），
    本接口返回与合成数据同构、可直接进入特征工程的 DataFrame。
    """
    df = pd.read_csv(csv_path)
    df = df.replace([np.inf, -np.inf], np.nan)
    df["Label"] = df["Label"].apply(_merge_label)
    # 清洗标签为空的行
    df = df[df["Label"].notna()]
    return df.reset_index(drop=True)
