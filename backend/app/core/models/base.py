"""模型公共基础设施：统一接口、PyTorch 训练/推理辅助。"""
from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import torch


def set_seed(seed: int = 0):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def to_numpy(X) -> np.ndarray:
    if hasattr(X, "values"):  # pandas DataFrame / Series
        return np.asarray(X.values, dtype=np.float32)
    return np.asarray(X, dtype=np.float32)


def train_classifier(model: torch.nn.Module, X, y, epochs=30, batch_size=128,
                     lr=1e-3, weight_decay=0.0, verbose=False) -> torch.nn.Module:
    """通用 PyTorch 分类训练循环。"""
    dev = device()
    model = model.to(dev)
    Xt = torch.tensor(to_numpy(X))
    yt = torch.tensor(np.asarray(y, dtype=np.int64))
    ds = torch.utils.data.TensorDataset(Xt, yt)
    loader = torch.utils.data.DataLoader(ds, batch_size=batch_size, shuffle=True)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    loss_fn = torch.nn.CrossEntropyLoss()
    model.train()
    for epoch in range(epochs):
        total = 0.0
        for xb, yb in loader:
            xb, yb = xb.to(dev), yb.to(dev)
            opt.zero_grad()
            loss = loss_fn(model(xb), yb)
            loss.backward()
            opt.step()
            total += loss.item() * len(xb)
        if verbose and (epoch + 1) % max(1, epochs // 5) == 0:
            print(f"    epoch {epoch + 1}/{epochs}  loss={total / max(len(Xt), 1):.4f}")
    model.eval()
    return model


@torch.no_grad()
def torch_logits(model: torch.nn.Module, X, batch_size=1024) -> np.ndarray:
    dev = device()
    model = model.to(dev).eval()
    Xt = torch.tensor(to_numpy(X))
    outs = []
    for i in range(0, len(Xt), batch_size):
        outs.append(model(Xt[i:i + batch_size].to(dev)).cpu().numpy())
    return np.vstack(outs)


@torch.no_grad()
def torch_proba(model: torch.nn.Module, X, batch_size=1024) -> np.ndarray:
    logits = torch_logits(model, X, batch_size)
    e = np.exp(logits - logits.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


class BaseClassifier:
    """分类器统一接口：fit / predict_proba / predict_logits / predict / save / load。"""

    n_features: int
    n_classes: int

    def fit(self, X, y) -> "BaseClassifier":
        raise NotImplementedError

    def predict_proba(self, X) -> np.ndarray:
        raise NotImplementedError

    def predict_logits(self, X) -> np.ndarray:
        p = np.clip(self.predict_proba(X), 1e-9, 1.0)
        return np.log(p)

    def predict(self, X) -> np.ndarray:
        return np.argmax(self.predict_proba(X), axis=1)

    def save(self, path: str | Path):
        raise NotImplementedError

    def load(self, path: str | Path):
        raise NotImplementedError

    def num_parameters(self) -> int:
        return 0
