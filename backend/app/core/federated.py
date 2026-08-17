"""多中心聚类联邦学习（商业计划书「隐私安全可控」核心技术）。

模拟多个工业客户端在数据不出域的前提下协同训练检测模型：
1. 非 IID 划分 —— 每个客户端仅持有部分类别的样本，形成数据异构；
2. 多中心聚类 —— 用 KMeans 对客户端数据分布聚类，聚合为若干“中心”；
3. 中心内 FedAvg —— 各中心内客户端本地训练后联邦平均，得到中心模型；
4. 跨中心聚合 —— 中心模型加权平均，得到全局模型。

客户端与中心均使用轻量 MLP，呼应「轻量化 + 隐私保护」的联合卖点。
"""
from __future__ import annotations

import numpy as np
import torch
from sklearn.cluster import KMeans
from sklearn.metrics import accuracy_score, f1_score

from .models.student import StudentMLP
from .models.base import to_numpy, train_classifier, torch_proba, set_seed


def simulate_clients(X, y, n_clients: int = 10, classes_per_client: int = 3, seed: int = 0):
    """非 IID 划分：每个客户端仅持有若干类别的样本。返回 (clients, hist)。"""
    X = to_numpy(X)
    y = np.asarray(y, dtype=int)
    n_classes = len(np.unique(y))
    rng = np.random.default_rng(seed)
    clients, hists = [], []
    for _ in range(n_clients):
        k = min(classes_per_client, n_classes)
        chosen = rng.choice(n_classes, size=k, replace=False)
        idxs = np.concatenate([np.where(y == c)[0] for c in chosen])
        rng.shuffle(idxs)
        clients.append((X[idxs], y[idxs]))
        h = np.bincount(y[idxs], minlength=n_classes).astype(float)
        hists.append(h / (h.sum() + 1e-9))
    return clients, np.array(hists)


def fedavg(states: list[dict], weights: list[float]) -> dict:
    total = sum(weights) + 1e-9
    avg = {k: sum(w * s[k] for w, s in zip(weights, states)) / total for k in states[0]}
    return avg


def _make_model(n_features: int, n_classes: int, hidden: int, seed: int) -> StudentMLP:
    set_seed(seed)
    return StudentMLP(n_features, n_classes, hidden)


def _proba(model: StudentMLP, X) -> np.ndarray:
    return torch_proba(model, X)


class MultiCenterFederated:
    def __init__(self, n_clients: int = 10, n_centers: int = 3, local_epochs: int = 8,
                 rounds: int = 10, hidden: int = 64, lr: float = 2e-3, seed: int = 0):
        self.n_clients = n_clients
        self.n_centers = n_centers
        self.local_epochs = local_epochs
        self.rounds = rounds
        self.hidden = hidden
        self.lr = lr
        self.seed = seed
        self.n_classes: int = 0
        self.n_features: int = 0
        self.center_models: list[StudentMLP] = []
        self.global_model: StudentMLP | None = None
        self.center_assign: np.ndarray | None = None
        self.center_classes: list[list[int]] = []   # 每个中心覆盖的类别（供「领域准确率」评估）

    def fit(self, X, y):
        X = to_numpy(X)
        y = np.asarray(y, dtype=int)
        self.n_features = X.shape[1]
        self.n_classes = len(np.unique(y))

        clients, hists = simulate_clients(X, y, self.n_clients, seed=self.seed)
        # 多中心聚类：按客户端数据分布特征聚类
        self.center_assign = KMeans(
            n_clusters=self.n_centers, n_init=10, random_state=self.seed
        ).fit_predict(hists)

        # 记录每个中心覆盖的类别集合（非 IID 下各中心天然拥有不同“领域”）
        self.center_classes = []
        for c in range(self.n_centers):
            cidx = np.where(self.center_assign == c)[0]
            classes: set[int] = set()
            for i in cidx:
                classes.update(np.unique(clients[i][1]).tolist())
            self.center_classes.append(sorted(classes))

        # 初始化每中心一个全局模型，客户端本地模型与之同步
        center_models = [_make_model(self.n_features, self.n_classes, self.hidden, self.seed + c)
                         for c in range(self.n_centers)]
        global_state = fedavg([m.state_dict() for m in center_models], [1.0] * self.n_centers)

        for r in range(self.rounds):
            new_center_models = []
            for c in range(self.n_centers):
                cidx = np.where(self.center_assign == c)[0]
                if len(cidx) == 0:
                    new_center_models.append(center_models[c])
                    continue
                local_states, weights = [], []
                for i in cidx:
                    xi, yi = clients[i]
                    m = _make_model(self.n_features, self.n_classes, self.hidden, self.seed)
                    m.load_state_dict(center_models[c].state_dict())
                    train_classifier(m, xi, yi, epochs=self.local_epochs, lr=self.lr)
                    local_states.append(m.state_dict())
                    weights.append(len(xi))
                new_center_models.append(_model_from_state(local_states, weights, self))
            center_models = new_center_models
            # 跨中心聚合 → 全局模型
            global_state = fedavg([m.state_dict() for m in center_models],
                                  [1.0] * self.n_centers)

        self.center_models = center_models
        self.global_model = _model_from_state([global_state], [1.0], self)
        return self

    def evaluate(self, X, y) -> dict:
        """在测试集上评估全局模型与各中心模型。

        返回：
            global: 全局模型在全量测试集上的指标（非 IID 下偏低，说明「单全局」局限）；
            centers: 各中心模型 —— full 为全量测试集指标，
                     domain 为该中心覆盖类别子集上的指标（体现「中心专注」优势）。
        """
        X = to_numpy(X)
        y = np.asarray(y, dtype=int)
        result: dict = {"global": None, "centers": []}
        if self.global_model is not None:
            pred = np.argmax(_proba(self.global_model, X), axis=1)
            result["global"] = {
                "accuracy": float(accuracy_score(y, pred)),
                "f1_macro": float(f1_score(y, pred, average="macro", zero_division=0)),
            }
        for c, m in enumerate(self.center_models):
            pred = np.argmax(_proba(m, X), axis=1)
            entry = {
                "id": c,
                "classes": list(self.center_classes[c]) if c < len(self.center_classes) else [],
                "n_classes": len(self.center_classes[c]) if c < len(self.center_classes) else 0,
                "accuracy_full": float(accuracy_score(y, pred)),
                "f1_full": float(f1_score(y, pred, average="macro", zero_division=0)),
            }
            if c < len(self.center_classes) and self.center_classes[c]:
                dom = np.array(self.center_classes[c])
                mask = np.isin(y, dom)
                if mask.any():
                    entry["accuracy_domain"] = float(accuracy_score(y[mask], pred[mask]))
                    entry["f1_domain"] = float(f1_score(y[mask], pred[mask], average="macro", zero_division=0))
            result["centers"].append(entry)
        return result


def _model_from_state(states: list[dict], weights: list[float], trainer: "MultiCenterFederated") -> StudentMLP:
    m = _make_model(trainer.n_features, trainer.n_classes, trainer.hidden, trainer.seed)
    m.load_state_dict(fedavg(states, weights))
    return m
