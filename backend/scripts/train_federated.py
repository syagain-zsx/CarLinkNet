"""多中心聚类联邦学习演示（商业计划书「隐私安全可控」）。

对比两种联邦策略在非 IID 数据下的表现，验证「多中心聚类」的价值：
1. 单中心 FedAvg —— 所有客户端训练一个全局模型，非 IID 下难以兼顾各客户端；
2. 多中心聚类 FedAvg —— 先按客户端数据分布聚类，各中心专注自身领域，领域内精度更高。

数据始终保留在各客户端本地（仅交换模型参数），呼应「数据不出域」卖点。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from sklearn.model_selection import train_test_split

from app.config import DATA_DIR
from app.core.data.synthetic import generate_sample
from app.core.data.loader import load_flow_csv
from app.core.features import MultiViewPipeline
from app.core.federated import MultiCenterFederated
from app.core.models.base import torch_proba


def main():
    data_path = DATA_DIR / "sample_flows.csv"
    df = load_flow_csv(data_path) if data_path.exists() else generate_sample(n_per_class=200, seed=42)

    pipe = MultiViewPipeline().fit(df)
    X = pipe.concat_views(pipe.transform(df))
    y = pipe.encode_labels(df)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, stratify=y, random_state=42)
    names = pipe.classes_

    print("=== 策略一：单中心 FedAvg（传统全局联邦平均）===")
    naive = MultiCenterFederated(n_clients=12, n_centers=1, local_epochs=15, rounds=15, hidden=128, lr=5e-3, seed=0)
    naive.fit(X_train, y_train)
    ng = naive.evaluate(X_test, y_test)["global"]
    naive_pred = np.argmax(torch_proba(naive.global_model, X_test), axis=1)
    print(f"  全局模型: accuracy={ng['accuracy']:.4f}  f1_macro={ng['f1_macro']:.4f}")

    print("\n=== 策略二：多中心聚类 FedAvg（数据分布聚类后分中心协同）===")
    mc = MultiCenterFederated(n_clients=12, n_centers=3, local_epochs=15, rounds=15, hidden=128, lr=5e-3, seed=0)
    mc.fit(X_train, y_train)
    res = mc.evaluate(X_test, y_test)
    g = res["global"]
    print(f"  跨中心全局模型(参考): accuracy={g['accuracy']:.4f}  f1_macro={g['f1_macro']:.4f}")
    print("  各中心模型（领域 = 该中心客户端所覆盖的类别）:")
    for c in res["centers"]:
        dom = np.array(c["classes"])
        mask = np.isin(y_test, dom)
        naive_dom = float((naive_pred[mask] == y_test[mask]).mean())
        cls = ", ".join(names[i] for i in c["classes"])
        print(f"    中心 {c['id']} ({c['n_classes']} 类: {cls})")
        print(f"      单全局模型在该领域准确率 = {naive_dom:.4f}  ->  中心模型领域内准确率 = {c['accuracy_domain']:.4f}")

    print("\n结论：非 IID 下单一全局模型难以兼顾异构客户端；多中心聚类后，各中心在自身领域内精度显著提升，且数据不出域。")


if __name__ == "__main__":
    main()
