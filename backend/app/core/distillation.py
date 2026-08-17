"""双教师知识蒸馏（商业计划书「轻量化部署」核心技术）。

让轻量学生模型同时学习两个教师的知识：
- 教师 A：PSO-CFW 集成模型的软标签（高精度、全局判别）；
- 教师 B：单一最优分支模型（如 XGBoost）的软标签（结构性判别）。

损失：L = α·CE(z_s, y) + Σ β_t·T²·KL(softmax(z_s/T) ‖ softmax(z_t/T))
蒸馏后得到体积远小于教师集成的轻量学生模型，可部署于低算力边缘设备。
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn.functional as F

from .models.base import to_numpy, train_classifier, device, set_seed


def _kl_div_loss(z_student: torch.Tensor, teacher_logits: torch.Tensor, T: float) -> torch.Tensor:
    """KL(q_teacher ‖ p_student)，q 为教师软分布，p 为学生软分布。"""
    q = F.softmax(teacher_logits / T, dim=1)
    p = F.log_softmax(z_student / T, dim=1)
    return F.kl_div(p, q, reduction="batchmean") * (T * T)


def distill(student_model, X, y, teacher_logits_list, T=4.0, alpha=0.3,
            teacher_weights=None, epochs=40, batch_size=128, lr=1e-3, seed=0, verbose=False):
    """训练学生模型。

    Args:
        student_model: 带 .model (nn.Module) 与 .n_classes 的轻量模型（如 StudentModel）。
        X: 学生输入特征 (n, d)。
        y: 硬标签 (n,)。
        teacher_logits_list: 教师 logits 列表，每个形状 (n, C)。
        alpha: 硬标签损失权重；1-alpha 由教师软标签损失分摊。
        teacher_weights: 各教师软标签损失的权重，默认均分。
    """
    set_seed(seed)
    dev = device()
    model = student_model.model
    if model is None:
        # 学生模型尚未构建（如 StudentModel 惰性建网），按输入特征维度构建
        if hasattr(student_model, "_build"):
            student_model._build(to_numpy(X).shape[1])
            model = student_model.model
        else:
            raise ValueError("student_model.model 为 None，请先构建学生模型")
    model = model.to(dev)

    n_teachers = len(teacher_logits_list)
    if teacher_weights is None:
        teacher_weights = [1.0 / n_teachers] * n_teachers

    Xt = torch.tensor(to_numpy(X))
    yt = torch.tensor(np.asarray(y, dtype=np.int64))
    tz_list = [torch.tensor(np.asarray(tz, dtype=np.float32)) for tz in teacher_logits_list]

    ds = torch.utils.data.TensorDataset(Xt, yt, *tz_list)
    loader = torch.utils.data.DataLoader(ds, batch_size=batch_size, shuffle=True)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    model.train()
    for epoch in range(epochs):
        total = 0.0
        for batch in loader:
            xb = batch[0].to(dev)
            yb = batch[1].to(dev)
            teachers_b = [t.to(dev) for t in batch[2:]]
            opt.zero_grad()
            z_s = model(xb)
            ce = F.cross_entropy(z_s, yb)
            kd = sum(w * _kl_div_loss(z_s, tz, T) for w, tz in zip(teacher_weights, teachers_b))
            loss = alpha * ce + (1.0 - alpha) * kd
            loss.backward()
            opt.step()
            total += loss.item() * len(xb)
        if verbose and (epoch + 1) % max(1, epochs // 5) == 0:
            print(f"    epoch {epoch + 1}/{epochs}  loss={total / max(len(Xt), 1):.4f}")
    model.eval()
    return student_model
