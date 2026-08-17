"""生成合成示例流量数据。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DATA_DIR
from app.core.data.synthetic import save_sample


def main():
    path = DATA_DIR / "sample_flows.csv"
    df = save_sample(path, n_per_class=300, seed=42)
    print(f"已生成 {len(df)} 条合成流量样本 -> {path}")


if __name__ == "__main__":
    main()
