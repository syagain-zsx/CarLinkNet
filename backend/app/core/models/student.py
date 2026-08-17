"""轻量学生模型（商业计划书「轻量化部署」）。

一个 3 层小 MLP，接受拼接后的多视图特征，作为双教师知识蒸馏的蒸馏目标，
可直接部署在低算力工业边缘设备。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from .base import BaseClassifier, to_numpy, train_classifier, torch_proba, torch_logits, set_seed


class StudentMLP(nn.Module):
    def __init__(self, n_features: int, n_classes: int, hidden: int = 32):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_features, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, n_classes),
        )

    def forward(self, x):
        return self.net(x)


class StudentModel(BaseClassifier):
    def __init__(self, n_classes: int, n_features: int | None = None, hidden: int = 32,
                 epochs: int = 30, lr: float = 1e-3, seed: int = 0):
        self.n_classes = n_classes
        self.n_features = n_features
        self.hidden = hidden
        self.epochs = epochs
        self.lr = lr
        self.seed = seed
        self.model: StudentMLP | None = None

    def _build(self, n_features: int):
        set_seed(self.seed)
        self.n_features = n_features
        self.model = StudentMLP(n_features, self.n_classes, self.hidden)

    def fit(self, X, y):
        X = to_numpy(X)
        if self.model is None or self.n_features != X.shape[1]:
            self._build(X.shape[1])
        train_classifier(self.model, X, y, epochs=self.epochs, lr=self.lr)
        return self

    def predict_proba(self, X) -> np.ndarray:
        return torch_proba(self.model, X)

    def predict_logits(self, X) -> np.ndarray:
        return torch_logits(self.model, X)

    def num_parameters(self) -> int:
        return sum(p.numel() for p in self.model.parameters())

    def save(self, path: str | Path):
        torch.save(self.model.state_dict(), path)

    def load(self, path: str | Path):
        state = torch.load(path, map_location="cpu", weights_only=True)
        if self.model is None:
            self._build(self.n_features)
        self.model.load_state_dict(state)
        self.model.eval()
        return self
