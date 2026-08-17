"""基于粒子群优化的类别级加权投票 PSO-CFW（论文 3.3.2）。

不再为各模型分配统一全局权重，而是针对每个攻击类别分别学习一组集成权重
（式 3.21~3.23），并引入 PSO 在类别级权重空间搜索最优权重矩阵，适应度函数
为 Accuracy 与 F1_macro 的加权组合（式 3.24）。
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics import accuracy_score, f1_score


def _softmax(x: np.ndarray, axis: int) -> np.ndarray:
    e = np.exp(x - x.max(axis=axis, keepdims=True))
    return e / e.sum(axis=axis, keepdims=True)


class PSO_CFW:
    def __init__(self, n_models: int, n_classes: int, n_particles: int = 24, n_iter: int = 30,
                 w: float = 0.7, c1: float = 1.5, c2: float = 1.5,
                 alpha: float = 0.5, beta: float = 0.5, seed: int = 0):
        self.n_models = n_models
        self.n_classes = n_classes
        self.n_particles = n_particles
        self.n_iter = n_iter
        self.w = w
        self.c1 = c1
        self.c2 = c2
        self.alpha = alpha
        self.beta = beta
        self.seed = seed
        self.weights_: np.ndarray | None = None  # (B, C)

    def _ensemble_proba(self, probs_list: list[np.ndarray], W: np.ndarray) -> np.ndarray:
        ens = np.zeros_like(probs_list[0])
        for b in range(self.n_models):
            ens += probs_list[b] * W[b][None, :]
        ens = np.clip(ens, 1e-12, None)
        return ens / ens.sum(axis=1, keepdims=True)

    def fit(self, probs_list: list[np.ndarray], y: np.ndarray) -> "PSO_CFW":
        """在验证集预测概率上搜索最优类别级权重矩阵。probs_list: [B 个 (n, C)]。"""
        B, C = self.n_models, self.n_classes
        y = np.asarray(y, dtype=int)
        rng = np.random.default_rng(self.seed)
        dim = B * C

        def fitness(flat: np.ndarray) -> float:
            W = _softmax(flat.reshape(B, C), axis=0)
            ens = self._ensemble_proba(probs_list, W)
            pred = np.argmax(ens, axis=1)
            acc = accuracy_score(y, pred)
            f1 = f1_score(y, pred, average="macro", zero_division=0)
            return self.alpha * acc + self.beta * f1

        pos = rng.uniform(0, 1, (self.n_particles, dim))
        vel = rng.uniform(-0.1, 0.1, (self.n_particles, dim))
        pbest_pos = pos.copy()
        pbest_fit = np.array([fitness(p) for p in pos])
        gbest_idx = int(np.argmax(pbest_fit))
        gbest_pos = pbest_pos[gbest_idx].copy()
        gbest_fit = pbest_fit[gbest_idx]

        for _ in range(self.n_iter):
            r1 = rng.random((self.n_particles, dim))
            r2 = rng.random((self.n_particles, dim))
            vel = self.w * vel + self.c1 * r1 * (pbest_pos - pos) + self.c2 * r2 * (gbest_pos - pos)
            pos = np.clip(pos + vel, 0.0, 1.0)
            fits = np.array([fitness(p) for p in pos])
            improved = fits > pbest_fit
            pbest_fit[improved] = fits[improved]
            pbest_pos[improved] = pos[improved]
            if fits.max() > gbest_fit:
                gbest_fit = fits.max()
                gbest_pos = pos[int(np.argmax(fits))].copy()

        self.weights_ = _softmax(gbest_pos.reshape(B, C), axis=0)
        self.best_fitness_ = float(gbest_fit)
        return self

    def predict_proba(self, probs_list: list[np.ndarray]) -> np.ndarray:
        if self.weights_ is None:
            # 未拟合时退化为平均集成
            ens = np.mean(np.stack(probs_list), axis=0)
            return ens / ens.sum(axis=1, keepdims=True)
        return self._ensemble_proba(probs_list, self.weights_)

    def predict(self, probs_list: list[np.ndarray]) -> np.ndarray:
        return np.argmax(self.predict_proba(probs_list), axis=1)
