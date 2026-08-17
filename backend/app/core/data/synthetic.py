"""合成示例流量数据生成器。

生成 CICIDS2017 风格的流级 CSV，供特征工程 / 模型训练 / 联邦学习 / 系统演示使用。
真实数据接入时通过 loader.load_cicids2017() 读取官方 CSV，字段与本模块保持一致。

设计要点：每个攻击类别用一套“驱动参数”刻画其宏观行为（时长、包数、包长、
包间到达时间 IAT、活跃/空闲阶段、标志位、协议与端口），再由驱动参数推导出
CICFlowMeter 风格的统计列，保证不同类别在特征空间上具有可区分的模式。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# 检测类别（与论文表 3.6 对齐）
LABELS = [
    "BENIGN", "DDoS", "DoS Hulk", "DoS GoldenEye", "DoS Slowloris",
    "DoS Slowhttptest", "PortScan", "Bot", "Web Attack", "Heartbleed", "Patator",
]

# 服务端口 → 场景映射（论文 3.2.2 通信上下文特征）
WEB_PORTS = {80, 443, 8080, 8000, 8888, 8443}
MAIL_PORTS = {25, 110, 143, 465, 587, 993, 995}
DNS_PORTS = {53}
FILES_PORTS = {20, 21, 69}
REMOTE_PORTS = {22, 23, 3389, 5900}
DB_PORTS = {3306, 5432, 1521, 1433, 6379}

_EPS = 1e-6


def _uniform(rng, lo, hi, n):
    return rng.uniform(lo, hi, n)


def _log_uniform(rng, lo, hi, n):
    return np.exp(rng.uniform(np.log(lo), np.log(hi), n))


# 每个类别的驱动参数：时长(秒)、前/后向包数、前/后向包长均值与标准差、
# IAT 均值与标准差(秒)、活跃/空闲均值与标准差(秒)、标志位概率、协议与目标端口策略。
_PROFILES = {
    "BENIGN": dict(
        duration=(2.0, 60.0), fwd_pkts=(8, 60), bwd_pkts=(6, 55),
        fwd_len=(300, 1200), fwd_len_std=(60, 300), bwd_len=(400, 1500), bwd_len_std=(80, 400),
        iat_mean=(0.01, 0.5), iat_std=(0.005, 0.3),
        active_mean=(0.5, 6.0), active_std=(0.2, 2.0), idle_mean=(0.1, 4.0), idle_std=(0.05, 2.0),
        flags=dict(syn=0.10, rst=0.01, psh=0.45, ack=0.65, urg=0.005, fin=0.08),
        protocol=[(6, 0.80), (17, 0.20)], port="benign",
    ),
    "DDoS": dict(
        duration=(0.05, 0.4), fwd_pkts=(500, 3000), bwd_pkts=(0, 20),
        fwd_len=(40, 200), fwd_len_std=(20, 100), bwd_len=(40, 120), bwd_len_std=(10, 60),
        iat_mean=(0.0001, 0.002), iat_std=(0.00005, 0.001),
        active_mean=(0.01, 0.2), active_std=(0.005, 0.1), idle_mean=(0.0, 0.05), idle_std=(0.0, 0.02),
        flags=dict(syn=0.55, rst=0.05, psh=0.05, ack=0.10, urg=0.0, fin=0.0),
        protocol=[(6, 0.95), (17, 0.05)], port="web",
    ),
    "DoS Hulk": dict(
        duration=(1.0, 20.0), fwd_pkts=(200, 1500), bwd_pkts=(0, 30),
        fwd_len=(300, 900), fwd_len_std=(150, 400), bwd_len=(100, 300), bwd_len_std=(50, 150),
        iat_mean=(0.0002, 0.005), iat_std=(0.0001, 0.003),
        active_mean=(0.05, 1.0), active_std=(0.02, 0.5), idle_mean=(0.0, 0.1), idle_std=(0.0, 0.05),
        flags=dict(syn=0.30, rst=0.02, psh=0.20, ack=0.40, urg=0.0, fin=0.02),
        protocol=[(6, 1.0)], port="web",
    ),
    "DoS GoldenEye": dict(
        duration=(0.5, 5.0), fwd_pkts=(100, 800), bwd_pkts=(0, 40),
        fwd_len=(500, 1200), fwd_len_std=(200, 500), bwd_len=(100, 400), bwd_len_std=(50, 200),
        iat_mean=(0.0005, 0.01), iat_std=(0.0002, 0.005),
        active_mean=(0.02, 0.5), active_std=(0.01, 0.2), idle_mean=(0.0, 0.1), idle_std=(0.0, 0.05),
        flags=dict(syn=0.35, rst=0.02, psh=0.25, ack=0.30, urg=0.0, fin=0.02),
        protocol=[(6, 1.0)], port="web",
    ),
    "DoS Slowloris": dict(
        duration=(60.0, 600.0), fwd_pkts=(50, 400), bwd_pkts=(10, 80),
        fwd_len=(60, 200), fwd_len_std=(20, 80), bwd_len=(60, 200), bwd_len_std=(20, 80),
        iat_mean=(2.0, 30.0), iat_std=(1.0, 20.0),
        active_mean=(5.0, 60.0), active_std=(2.0, 30.0), idle_mean=(0.0, 2.0), idle_std=(0.0, 1.0),
        flags=dict(syn=0.60, rst=0.01, psh=0.10, ack=0.20, urg=0.0, fin=0.01),
        protocol=[(6, 1.0)], port="web",
    ),
    "DoS Slowhttptest": dict(
        duration=(30.0, 300.0), fwd_pkts=(80, 600), bwd_pkts=(20, 120),
        fwd_len=(60, 250), fwd_len_std=(20, 100), bwd_len=(60, 250), bwd_len_std=(20, 100),
        iat_mean=(1.0, 15.0), iat_std=(0.5, 10.0),
        active_mean=(3.0, 40.0), active_std=(1.0, 20.0), idle_mean=(0.0, 2.0), idle_std=(0.0, 1.0),
        flags=dict(syn=0.55, rst=0.01, psh=0.15, ack=0.25, urg=0.0, fin=0.01),
        protocol=[(6, 1.0)], port="web",
    ),
    "PortScan": dict(
        duration=(0.5, 10.0), fwd_pkts=(20, 300), bwd_pkts=(0, 20),
        fwd_len=(20, 60), fwd_len_std=(5, 20), bwd_len=(20, 60), bwd_len_std=(5, 20),
        iat_mean=(0.001, 0.05), iat_std=(0.0005, 0.03),
        active_mean=(0.01, 0.3), active_std=(0.005, 0.15), idle_mean=(0.0, 0.2), idle_std=(0.0, 0.1),
        flags=dict(syn=0.90, rst=0.05, psh=0.0, ack=0.05, urg=0.0, fin=0.0),
        protocol=[(6, 0.90), (17, 0.10)], port="scan",
    ),
    "Bot": dict(
        duration=(5.0, 120.0), fwd_pkts=(30, 300), bwd_pkts=(30, 300),
        fwd_len=(60, 400), fwd_len_std=(30, 150), bwd_len=(60, 400), bwd_len_std=(30, 150),
        iat_mean=(0.5, 10.0), iat_std=(0.2, 5.0),
        active_mean=(0.5, 10.0), active_std=(0.2, 5.0), idle_mean=(0.5, 10.0), idle_std=(0.2, 5.0),
        flags=dict(syn=0.10, rst=0.02, psh=0.40, ack=0.55, urg=0.0, fin=0.05),
        protocol=[(6, 0.85), (17, 0.15)], port="bot",
    ),
    "Web Attack": dict(
        duration=(0.1, 5.0), fwd_pkts=(5, 80), bwd_pkts=(2, 60),
        fwd_len=(200, 800), fwd_len_std=(80, 300), bwd_len=(200, 800), bwd_len_std=(80, 300),
        iat_mean=(0.05, 1.0), iat_std=(0.02, 0.5),
        active_mean=(0.1, 2.0), active_std=(0.05, 1.0), idle_mean=(0.05, 2.0), idle_std=(0.02, 1.0),
        flags=dict(syn=0.20, rst=0.03, psh=0.50, ack=0.50, urg=0.0, fin=0.05),
        protocol=[(6, 1.0)], port="web",
    ),
    "Heartbleed": dict(
        duration=(0.05, 0.5), fwd_pkts=(2, 20), bwd_pkts=(2, 20),
        fwd_len=(100, 400), fwd_len_std=(40, 150), bwd_len=(100, 400), bwd_len_std=(40, 150),
        iat_mean=(0.001, 0.05), iat_std=(0.0005, 0.02),
        active_mean=(0.005, 0.1), active_std=(0.002, 0.05), idle_mean=(0.0, 0.05), idle_std=(0.0, 0.02),
        flags=dict(syn=0.20, rst=0.02, psh=0.30, ack=0.40, urg=0.0, fin=0.03),
        protocol=[(6, 1.0)], port="heartbleed",
    ),
    "Patator": dict(
        duration=(0.5, 20.0), fwd_pkts=(20, 400), bwd_pkts=(20, 400),
        fwd_len=(60, 300), fwd_len_std=(30, 120), bwd_len=(60, 300), bwd_len_std=(30, 120),
        iat_mean=(0.01, 0.5), iat_std=(0.005, 0.3),
        active_mean=(0.1, 2.0), active_std=(0.05, 1.0), idle_mean=(0.05, 1.0), idle_std=(0.02, 0.5),
        flags=dict(syn=0.30, rst=0.04, psh=0.30, ack=0.40, urg=0.0, fin=0.03),
        protocol=[(6, 1.0)], port="patator",
    ),
}


def _sample_ports(rng, strategy, n):
    """按策略采样目标端口。"""
    pool = np.array(sorted(WEB_PORTS | MAIL_PORTS | DNS_PORTS | FILES_PORTS | REMOTE_PORTS | DB_PORTS))
    high = rng.integers(1024, 65535, n)
    if strategy == "web":
        return rng.choice(sorted(WEB_PORTS), n)
    if strategy == "scan":
        return rng.integers(1, 65535, n)
    if strategy == "bot":
        return np.where(rng.random(n) < 0.5, rng.choice([80, 443, 8080], n), rng.integers(1024, 65535, n))
    if strategy == "heartbleed":
        return np.full(n, 443)
    if strategy == "patator":
        return rng.choice([21, 22, 23, 25, 445, 3306, 1433], n)
    # benign：偏向常见服务端口
    common = rng.choice(sorted(WEB_PORTS | MAIL_PORTS | DNS_PORTS), n)
    return np.where(rng.random(n) < 0.8, common, rng.integers(1024, 65535, n))


def _sample_protocol(rng, protocol_spec, n):
    protos = [p for p, _ in protocol_spec]
    probs = [w for _, w in protocol_spec]
    return rng.choice(protos, n, p=np.array(probs) / np.sum(probs))


def _random_ip(rng, n, prefix="192.168"):
    return [f"{prefix}.{rng.integers(1, 255)}.{rng.integers(1, 255)}" for _ in range(n)]


def _make_class(label: str, n: int, rng: np.random.Generator) -> pd.DataFrame:
    p = _PROFILES[label]
    d = pd.DataFrame()
    d["_label"] = [label] * n

    d["_duration"] = _log_uniform(rng, *p["duration"], n)
    d["_fwd_pkts"] = _uniform(rng, *p["fwd_pkts"], n)
    d["_bwd_pkts"] = _uniform(rng, *p["bwd_pkts"], n)
    d["_fwd_len_mean"] = _uniform(rng, *p["fwd_len"], n)
    d["_fwd_len_std"] = _uniform(rng, *p["fwd_len_std"], n)
    d["_bwd_len_mean"] = _uniform(rng, *p["bwd_len"], n)
    d["_bwd_len_std"] = _uniform(rng, *p["bwd_len_std"], n)
    d["_iat_mean"] = _uniform(rng, *p["iat_mean"], n)
    d["_iat_std"] = _uniform(rng, *p["iat_std"], n)
    d["_fwd_iat_mean"] = d["_iat_mean"] * rng.uniform(0.5, 1.2, n)
    d["_fwd_iat_std"] = d["_iat_std"] * rng.uniform(0.5, 1.2, n)
    d["_bwd_iat_mean"] = d["_iat_mean"] * rng.uniform(0.5, 1.5, n)
    d["_bwd_iat_std"] = d["_iat_std"] * rng.uniform(0.5, 1.5, n)
    d["_active_mean"] = _uniform(rng, *p["active_mean"], n)
    d["_active_std"] = _uniform(rng, *p["active_std"], n)
    d["_idle_mean"] = _uniform(rng, *p["idle_mean"], n)
    d["_idle_std"] = _uniform(rng, *p["idle_std"], n)

    flags = p["flags"]
    for flag in ("syn", "rst", "psh", "ack", "urg", "fin"):
        d[f"_fwd_{flag}_prob"] = rng.uniform(0, max(flags[flag] * 2, 0.01), n).clip(0, 1)
        d[f"_bwd_{flag}_prob"] = rng.uniform(0, max(flags[flag], 0.01), n).clip(0, 1)

    d["_protocol"] = _sample_protocol(rng, p["protocol"], n)
    d["_dst_port"] = _sample_ports(rng, p["port"], n)
    d["_src_port"] = rng.integers(1024, 65535, n)
    d["_src_ip"] = _random_ip(rng, n, "192.168")
    d["_dst_ip"] = _random_ip(rng, n, "10.0")

    return d


def _derive_flow(d: pd.DataFrame) -> pd.DataFrame:
    """由驱动参数推导 CICFlowMeter 风格的统计列。"""
    d = d.copy()
    d["Flow Duration"] = d["_duration"]
    d["Total Fwd Packets"] = d["_fwd_pkts"].round().astype(int)
    d["Total Backward Packets"] = d["_bwd_pkts"].round().astype(int)

    for f, col in (("fwd", "Fwd"), ("bwd", "Bwd")):
        mean = d[f"_{f}_len_mean"].values
        std = d[f"_{f}_len_std"].values
        d[f"{col} Packet Length Mean"] = mean
        d[f"{col} Packet Length Std"] = std
        d[f"{col} Packet Length Max"] = mean + 2 * std
        d[f"{col} Packet Length Min"] = np.maximum(mean - 2 * std, 1)
        d[f"{col} Packet Length Median"] = mean * 1.02

    d["Total Length of Fwd Packets"] = d["Total Fwd Packets"] * d["Fwd Packet Length Mean"]
    d["Total Length of Bwd Packets"] = d["Total Backward Packets"] * d["Bwd Packet Length Mean"]

    total_bytes = d["Total Length of Fwd Packets"] + d["Total Length of Bwd Packets"]
    total_pkts = d["Total Fwd Packets"] + d["Total Backward Packets"]
    d["Flow Bytes/s"] = total_bytes / np.maximum(d["Flow Duration"], _EPS)
    d["Flow Packets/s"] = total_pkts / np.maximum(d["Flow Duration"], _EPS)

    for f, col, pkt_col in (
        ("fwd", "Fwd", "Total Fwd Packets"),
        ("bwd", "Bwd", "Total Backward Packets"),
    ):
        iat_mean = d[f"_{f}_iat_mean"].values
        iat_std = d[f"_{f}_iat_std"].values
        d[f"{col} IAT Mean"] = iat_mean
        d[f"{col} IAT Std"] = iat_std
        d[f"{col} IAT Max"] = iat_mean + 3 * iat_std
        d[f"{col} IAT Min"] = np.maximum(iat_mean - 2 * iat_std, _EPS)
        d[f"{col} IAT Total"] = iat_mean * d[pkt_col]

    flow_iat_mean = d["_iat_mean"].values
    flow_iat_std = d["_iat_std"].values
    d["Flow IAT Mean"] = flow_iat_mean
    d["Flow IAT Std"] = flow_iat_std
    d["Flow IAT Max"] = flow_iat_mean + 3 * flow_iat_std
    d["Flow IAT Min"] = np.maximum(flow_iat_mean - 2 * flow_iat_std, _EPS)

    for col in ("Active", "Idle"):
        mean = d[f"_{col.lower()}_mean"].values
        std = d[f"_{col.lower()}_std"].values
        d[f"{col} Mean"] = mean
        d[f"{col} Std"] = std
        d[f"{col} Max"] = mean + 3 * std
        d[f"{col} Min"] = np.maximum(mean - 2 * std, _EPS)

    fwd = d["Total Fwd Packets"].values.astype(float)
    bwd = d["Total Backward Packets"].values.astype(float)
    for flag in ("SYN", "RST", "PSH", "ACK", "URG", "FIN"):
        fwd_prob = d[f"_fwd_{flag.lower()}_prob"].values
        bwd_prob = d[f"_bwd_{flag.lower()}_prob"].values
        d[f"{flag} Flag Count"] = (fwd * fwd_prob + bwd * bwd_prob).round().astype(int)
        d[f"Fwd {flag} Flags"] = (fwd * fwd_prob).round().astype(int)
        d[f"Bwd {flag} Flags"] = (bwd * bwd_prob).round().astype(int)

    d["Protocol"] = d["_protocol"]
    d["Source Port"] = d["_src_port"].astype(int)
    d["Destination Port"] = d["_dst_port"].astype(int)
    d["Source IP"] = d["_src_ip"]
    d["Destination IP"] = d["_dst_ip"]
    d["Label"] = d["_label"]

    drop_cols = [c for c in d.columns if c.startswith("_")]
    return d.drop(columns=drop_cols).reset_index(drop=True)


def generate_sample(n_per_class: int = 300, seed: int = 42, labels: list[str] | None = None) -> pd.DataFrame:
    """生成合成流量样本。默认每类 n_per_class 条。"""
    labels = labels or LABELS
    rng = np.random.default_rng(seed)
    frames = [_derive_flow(_make_class(lb, n_per_class, rng)) for lb in labels]
    return pd.concat(frames, ignore_index=True)


def save_sample(path, n_per_class: int = 300, seed: int = 42) -> pd.DataFrame:
    df = generate_sample(n_per_class, seed)
    df.to_csv(path, index=False)
    return df
