"""轻量规则引擎（签名匹配）。

对 CICFlowMeter 风格流量字段做阈值/端口/协议/标志位签名匹配，作为检测管道的
「规则快判」阶段。真实部署时可替换为 Suricata 等专业规则引擎（预留接口）。
"""
from __future__ import annotations

import json
import operator
from pathlib import Path

import numpy as np
import pandas as pd

# 内置默认规则（对应合成数据的攻击画像）
DEFAULT_RULES = [
    {
        "name": "SYN 洪泛 / DDoS 高并发",
        "label": "DDoS",
        "severity": "high",
        "conditions": [
            {"field": "Flow Packets/s", "op": ">", "value": 500},
            {"field": "SYN Flag Count", "op": ">", "value": 50},
        ],
    },
    {
        "name": "端口扫描（低载荷 SYN 探测）",
        "label": "PortScan",
        "severity": "high",
        "conditions": [
            {"field": "SYN Flag Count", "op": ">", "value": 10},
            {"field": "ACK Flag Count", "op": "<", "value": 5},
            {"field": "Fwd Packet Length Mean", "op": "<", "value": 60},
        ],
    },
    {
        "name": "Heartbleed 心跳漏洞利用",
        "label": "Heartbleed",
        "severity": "high",
        "conditions": [
            {"field": "Destination Port", "op": "==", "value": 443},
            {"field": "Total Fwd Packets", "op": "<", "value": 20},
        ],
    },
    {
        "name": "暴力破解（SSH/FTP/数据库端口）",
        "label": "Patator",
        "severity": "medium",
        "conditions": [
            {"field": "Destination Port", "op": "in", "value": [21, 22, 23, 25, 445, 3306, 1433]},
            {"field": "Flow Packets/s", "op": ">", "value": 10},
        ],
    },
    {
        "name": "Web 攻击（HTTP 异常流量）",
        "label": "Web Attack",
        "severity": "medium",
        "conditions": [
            {"field": "Destination Port", "op": "in", "value": [80, 8080, 8000, 8888]},
            {"field": "PSH Flag Count", "op": ">", "value": 3},
        ],
    },
    {
        "name": "慢速 DoS（长连接低速率）",
        "label": "DoS Slowloris",
        "severity": "medium",
        "conditions": [
            {"field": "Flow Duration", "op": ">", "value": 30},
            {"field": "Flow Packets/s", "op": "<", "value": 20},
            {"field": "SYN Flag Count", "op": ">", "value": 5},
        ],
    },
]

_OPS = {
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
}


def _eval_condition(series: pd.Series, cond: dict) -> pd.Series:
    op = cond["op"]
    value = cond["value"]
    if op == "in":
        return series.isin(value)
    if op == "not_in":
        return ~series.isin(value)
    fn = _OPS.get(op)
    if fn is None:
        raise ValueError(f"不支持的运算符: {op}")
    return fn(series, value)


class RuleEngine:
    """规则引擎：给定规则列表，输出每条流的匹配结果。"""

    def __init__(self, rules: list[dict] | None = None):
        self.rules = rules or DEFAULT_RULES

    @classmethod
    def from_file(cls, path: str | Path) -> "RuleEngine":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        rules = data if isinstance(data, list) else data.get("rules", [])
        return cls(rules)

    def match(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        """返回 (labels, matched_mask)。

        labels: 每条流命中的攻击标签，未命中为 None；
        matched_mask: 是否命中任意规则（bool 数组）。
        """
        n = len(df)
        labels = np.array([None] * n, dtype=object)
        matched = np.zeros(n, dtype=bool)
        for rule in self.rules:
            hit = pd.Series(True, index=df.index)
            ok = True
            for cond in rule.get("conditions", []):
                field = cond["field"]
                if field not in df.columns:
                    ok = False
                    break
                hit &= _eval_condition(df[field], cond).fillna(False)
            if not ok:
                continue
            hit = hit.astype(bool).values
            # 未命中过任何规则的样本才打上当前规则标签（规则按优先级顺序生效）
            assign = hit & (~matched)
            labels[assign] = rule.get("label", "ATTACK")
            matched |= hit
        return labels, matched
