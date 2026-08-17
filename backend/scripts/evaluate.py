"""加载已训练模型产物，在测试数据上评估集成/学生模型性能。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sklearn.metrics import classification_report

from app.config import DATA_DIR, MODEL_DIR
from app.core.data.synthetic import generate_sample
from app.core.data.loader import load_flow_csv
from app.core.detector import EnsembleDetector
from app.core.metrics import macro_metrics


def main():
    det = EnsembleDetector.load(MODEL_DIR)

    data_path = DATA_DIR / "sample_flows.csv"
    df = load_flow_csv(data_path) if data_path.exists() else generate_sample(n_per_class=100, seed=7)

    for use_student, name in [(False, "集成(PSO-CFW)"), (True, "学生模型(蒸馏)")]:
        r = det.predict(df, use_student=use_student)
        y_true = det.pipeline.encode_labels(df)
        y_pred = [det.pipeline.classes_.index(lb) for lb in r["labels"]]
        print(f"\n=== {name} ===")
        print(macro_metrics(y_true, y_pred))
        print(classification_report(y_true, y_pred, target_names=det.pipeline.classes_, zero_division=0))


if __name__ == "__main__":
    main()
