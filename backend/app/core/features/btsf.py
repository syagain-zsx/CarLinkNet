"""行为时间结构特征 BTSF（论文 3.2.2）。

在统计特征基础上，从四个互补视角刻画网络会话的时间行为结构：
（1）通信上下文特征 —— 协议与服务场景的语义化抽象；
（2）时序波动特征 —— 包间到达时间(IAT)的变异系数、幅度比率与多尺度 Z-score；
（3）通信结构与方向行为特征 —— 前后向包/字节比例、载荷长度形态、方向一致性、
    标志位熵与 log 速率强度；
（4）行为基线偏离特征 —— 相对全局基线的均值偏移(Contrast-Mean)与能量偏移(Contrast-Energy)。

其中“基线偏离”与“多尺度 Z-score”依赖全局基线(μ, σ)，由 fit() 在训练集上计算。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..data.synthetic import (
    WEB_PORTS, MAIL_PORTS, DNS_PORTS, FILES_PORTS, REMOTE_PORTS, DB_PORTS,
)

_EPS = 1e-6


def _port_service(port) -> str:
    p = int(port)
    if p in WEB_PORTS:
        return "web"
    if p in MAIL_PORTS:
        return "mail"
    if p in DNS_PORTS:
        return "dns"
    if p in FILES_PORTS:
        return "files"
    if p in REMOTE_PORTS:
        return "remote"
    if p in DB_PORTS:
        return "db"
    return "other"


# 行为基线偏离所用的统计类别（论文表 3.4）
BASELINE_CATEGORIES = {
    "iat": ["Flow IAT Mean", "Flow IAT Std", "Fwd IAT Mean", "Bwd IAT Mean"],
    "rate": ["Flow Bytes/s", "Flow Packets/s"],
    "len": ["Fwd Packet Length Mean", "Fwd Packet Length Std", "Bwd Packet Length Mean", "Bwd Packet Length Std"],
    "flag": ["SYN Flag Count", "RST Flag Count", "PSH Flag Count", "ACK Flag Count", "URG Flag Count", "FIN Flag Count"],
}

# 多尺度节律 Z-score 所用的代表特征（fast / mid / slow）
MULTI_SCALE_FEATURES = {
    "fast": "Flow IAT Min",
    "mid": "Active Mean",
    "slow": "Flow Duration",
}

# 标志位类别（用于标志位熵）
FLAG_NAMES = ["SYN", "RST", "PSH", "ACK", "URG", "FIN"]


def _zscore(x: pd.Series, mu: float, sigma: float) -> pd.Series:
    return (x - mu) / (sigma + _EPS)


class BTSFBuilder:
    """行为时间结构特征构造器。"""

    def __init__(self):
        self.baseline: dict[str, dict[str, float]] = {}   # category -> {col: (mu, sigma)}
        self.scale_baseline: dict[str, tuple[float, float]] = {}  # fast/mid/slow -> (mu, sigma)
        self.columns: list[str] | None = None

    # ---------- fit：计算全局基线 ----------
    def fit(self, df: pd.DataFrame) -> "BTSFBuilder":
        for cat, cols in BASELINE_CATEGORIES.items():
            self.baseline[cat] = {}
            for c in cols:
                if c in df.columns:
                    s = df[c].replace([np.inf, -np.inf], np.nan).fillna(0.0)
                    self.baseline[cat][c] = (float(s.mean()), float(s.std()))
        for scale, c in MULTI_SCALE_FEATURES.items():
            if c in df.columns:
                s = df[c].replace([np.inf, -np.inf], np.nan).fillna(0.0)
                self.scale_baseline[scale] = (float(s.mean()), float(s.std()))
            else:
                self.scale_baseline[scale] = (0.0, 1.0)
        return self

    # ---------- 各子类特征 ----------
    def _context_features(self, df: pd.DataFrame, out: dict):
        proto = df["Protocol"].fillna(0).astype(int)
        out["ctx_proto_TCP"] = (proto == 6).astype(int)
        out["ctx_proto_UDP"] = (proto == 17).astype(int)
        out["ctx_proto_Other"] = (~proto.isin([6, 17])).astype(int)

        port = df["Destination Port"].fillna(0).astype(int)
        svc = port.map(_port_service)
        out["ctx_port_web"] = (svc == "web").astype(int)
        out["ctx_port_mail"] = (svc == "mail").astype(int)
        out["ctx_port_dns"] = (svc == "dns").astype(int)
        out["ctx_port_files"] = (svc == "files").astype(int)
        out["ctx_port_remote"] = (svc == "remote").astype(int)
        out["ctx_port_db"] = (svc == "db").astype(int)
        out["ctx_port_other"] = (svc == "other").astype(int)

    def _temporal_features(self, df: pd.DataFrame, out: dict):
        # 变异系数 CV = σ / μ（论文式 3.1）
        out["tmp_fwd_cv"] = df["Fwd IAT Std"] / (df["Fwd IAT Mean"] + _EPS)
        out["tmp_bwd_cv"] = df["Bwd IAT Std"] / (df["Bwd IAT Mean"] + _EPS)
        # 幅度比率 RR = (max - min) / μ（论文式 3.2）
        out["tmp_fwd_range_ratio"] = (df["Fwd IAT Max"] - df["Fwd IAT Min"]) / (df["Fwd IAT Mean"] + _EPS)
        out["tmp_bwd_range_ratio"] = (df["Bwd IAT Max"] - df["Bwd IAT Min"]) / (df["Bwd IAT Mean"] + _EPS)
        # 多尺度节律 Z-score（短/中/长期）
        for scale, c in MULTI_SCALE_FEATURES.items():
            mu, sigma = self.scale_baseline[scale]
            out[f"tmp_{scale}_z"] = _zscore(df[c], mu, sigma)

    def _structure_features(self, df: pd.DataFrame, out: dict):
        pf = df["Total Fwd Packets"].astype(float)
        pb = df["Total Backward Packets"].astype(float)
        bf = df["Total Length of Fwd Packets"].astype(float)
        bb = df["Total Length of Bwd Packets"].astype(float)
        # 流量规模结构（论文式 3.3 ~ 3.5）
        out["ratio_pkt"] = pf / (pb + 1)
        out["diff_pkt"] = pf - pb
        out["ratio_len"] = bf / (bb + 1)
        # 载荷长度形态（论文式 3.6 ~ 3.7）
        lmax = df["Fwd Packet Length Max"].astype(float)
        lmin = df["Fwd Packet Length Min"].astype(float)
        lmed = df["Fwd Packet Length Median"].astype(float) if "Fwd Packet Length Median" in df.columns else df["Fwd Packet Length Mean"]
        out["len_skew_like"] = (lmax - lmed) / (lmed + 1)
        out["len_tail_like"] = (lmax - lmin) / (lmax + 1)
        # 方向一致性（论文式 3.8）
        xf = df["Fwd Packet Length Mean"].astype(float)
        xb = df["Bwd Packet Length Mean"].astype(float)
        out["dir_consistency"] = 1.0 / (1.0 + (xf - xb).abs())
        # 标志位熵（论文式 3.9）
        flag_counts = np.stack([df[f"{f} Flag Count"].fillna(0).astype(float).values for f in FLAG_NAMES], axis=1)
        totals = flag_counts.sum(axis=1, keepdims=True) + _EPS
        prob = flag_counts / totals
        with np.errstate(divide="ignore", invalid="ignore"):
            ent = -np.nansum(prob * np.log(prob + _EPS), axis=1)
        out["flag_entropy"] = pd.Series(ent, index=df.index)
        out["flag_syn_ack"] = df["SYN Flag Count"].astype(float) / (df["ACK Flag Count"].astype(float) + 1)
        out["flag_rst_rate"] = df["RST Flag Count"].astype(float) / (pf + pb + 1)
        # log 流量强度（论文式 3.10）
        dur = df["Flow Duration"].astype(float) + _EPS
        out["log_Flow_Bytes/s"] = np.log1p(df["Flow Bytes/s"].astype(float))
        out["log_Flow_Packets/s"] = np.log1p(df["Flow Packets/s"].astype(float))
        out["log_Fwd_Packets/s"] = np.log1p(pf / dur)
        out["log_Bwd_Packets/s"] = np.log1p(pb / dur)

    def _baseline_deviation_features(self, df: pd.DataFrame, out: dict):
        for cat, cols in BASELINE_CATEGORIES.items():
            zs = []
            for c in cols:
                if c in self.baseline.get(cat, {}):
                    mu, sigma = self.baseline[cat][c]
                    zs.append(_zscore(df[c].fillna(0.0), mu, sigma).values)
            if zs:
                z = np.stack(zs, axis=1)
                out[f"contrast_{cat}_mean"] = pd.Series(z.mean(axis=1), index=df.index)
                out[f"contrast_{cat}_energy"] = pd.Series(np.square(z).sum(axis=1), index=df.index)
            else:
                out[f"contrast_{cat}_mean"] = 0.0
                out[f"contrast_{cat}_energy"] = 0.0

    # ---------- transform ----------
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        out: dict[str, pd.Series] = {}
        self._context_features(df, out)
        self._temporal_features(df, out)
        self._structure_features(df, out)
        self._baseline_deviation_features(df, out)
        result = pd.DataFrame(out, index=df.index).astype(float)
        self.columns = list(result.columns)
        return result

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        self.fit(df)
        return self.transform(df)
