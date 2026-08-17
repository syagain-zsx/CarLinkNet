"""端到端训练：多视图特征 -> 分支模型 -> PSO-CFW 集成 -> 双教师知识蒸馏。

产出保存到 MODEL_DIR，供后端检测模块与 evaluate.py 加载。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from sklearn.model_selection import train_test_split

from app.config import DATA_DIR, MODEL_DIR
from app.core.data.synthetic import generate_sample
from app.core.data.loader import load_flow_csv
from app.core.features import MultiViewPipeline
from app.core.models import CNNModel, XGBModel, FTTModel, StudentModel
from app.core.ensemble import PSO_CFW
from app.core.distillation import distill
from app.core.detector import EnsembleDetector
from app.core.metrics import macro_metrics

VIEW_ORDER = ["statistical", "btsf", "frequency"]


def _logits(proba: np.ndarray) -> np.ndarray:
    return np.log(np.clip(proba, 1e-9, 1.0))


def main():
    data_path = DATA_DIR / "sample_flows.csv"
    if data_path.exists():
        df = load_flow_csv(data_path)
        print(f"加载数据 {data_path} ({len(df)} 条)")
    else:
        df = generate_sample(n_per_class=200, seed=42)
        print(f"未找到数据文件，使用合成数据 {len(df)} 条")

    train_val, test = train_test_split(df, test_size=0.3, stratify=df["Label"], random_state=42)
    train, val = train_test_split(train_val, test_size=0.2, stratify=train_val["Label"], random_state=42)
    print(f"训练 {len(train)} / 验证 {len(val)} / 测试 {len(test)}")

    pipe = MultiViewPipeline().fit(train)
    views_train, views_val, views_test = pipe.transform(train), pipe.transform(val), pipe.transform(test)
    print("特征视图维度:", {k: v.shape[1] for k, v in views_train.items()})
    y_train, y_val, y_test = pipe.encode_labels(train), pipe.encode_labels(val), pipe.encode_labels(test)
    n_classes = len(pipe.classes_)

    # 1) 分支模型
    print("\n[1/4] 训练分支模型 ...")
    cnn = CNNModel(n_classes, n_features=views_train["statistical"].shape[1], epochs=20).fit(
        views_train["statistical"].values, y_train)
    xgbm = XGBModel(n_classes).fit(views_train["btsf"].values, y_train)
    ftt = FTTModel(n_classes, n_features=views_train["frequency"].shape[1], epochs=20).fit(
        views_train["frequency"].values, y_train)
    branch = {"statistical": cnn, "btsf": xgbm, "frequency": ftt}

    print("\n=== 单分支测试集性能 ===")
    for k in VIEW_ORDER:
        pred = branch[k].predict(views_test[k].values)
        print(f"{k:12s} -> {macro_metrics(y_test, pred)}")

    # 2) PSO-CFW 集成
    print("\n[2/4] PSO-CFW 集成权重学习 ...")
    val_probs = [branch[k].predict_proba(views_val[k].values) for k in VIEW_ORDER]
    pso = PSO_CFW(n_models=3, n_classes=n_classes, n_iter=20).fit(val_probs, y_val)
    print(f"最佳适应度(0.5*Acc + 0.5*F1_macro) = {pso.best_fitness_:.4f}")

    test_probs = [branch[k].predict_proba(views_test[k].values) for k in VIEW_ORDER]
    print(f"集成(PSO-CFW) -> {macro_metrics(y_test, pso.predict(test_probs))}")

    # 3) 双教师知识蒸馏
    print("\n[3/4] 双教师知识蒸馏（轻量学生模型）...")
    X_train_cat, X_test_cat = pipe.concat_views(views_train), pipe.concat_views(views_test)
    train_probs = [branch[k].predict_proba(views_train[k].values) for k in VIEW_ORDER]
    teacherA = _logits(pso.predict_proba(train_probs))          # 教师A：集成软标签
    teacherB = _logits(branch["btsf"].predict_proba(views_train["btsf"].values))  # 教师B：最优单分支
    student = StudentModel(n_classes, n_features=X_train_cat.shape[1], hidden=32)
    distill(student, X_train_cat, y_train, [teacherA, teacherB], T=4.0, alpha=0.3, epochs=30, verbose=False)

    student_pred = student.predict(X_test_cat)
    print(f"学生模型 -> {macro_metrics(y_test, student_pred)}")

    teacher_params = cnn.num_parameters() + ftt.num_parameters()
    print(f"\n参数量对比: 教师集成(CNN+FTT) = {teacher_params:,} 参数, 蒸馏学生 = {student.num_parameters():,} 参数")

    # 4) 保存
    print("\n[4/4] 保存模型产物 ...")
    EnsembleDetector(pipe, branch, pso, student).save(MODEL_DIR)
    print(f"已保存到 {MODEL_DIR}")


if __name__ == "__main__":
    main()
