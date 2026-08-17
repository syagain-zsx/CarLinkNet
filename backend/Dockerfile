# 后端镜像：FastAPI + 预训练模型，CPU-only 轻量部署
FROM python:3.13-slim

# 可用 --build-arg / compose 环境变量覆盖为国内镜像（见 DEPLOY.md「国内镜像加速」）
ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PYTORCH_FIND_LINKS=https://download.pytorch.org/whl/cpu

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# OpenMP 运行库（scikit-learn / xgboost 等需要 libgomp）
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 先装 CPU 版 PyTorch：版本明确带 +cpu，避免误拉 PyPI 的 CUDA 版（体积差数倍）。
# 官方源与阿里云镜像均为「目录式」wheel 仓库，统一走 --find-links；依赖(sympy/jinja2 等)走主 pip 索引。
RUN pip install torch==2.13.0+cpu \
    --index-url ${PIP_INDEX_URL} \
    --find-links ${PYTORCH_FIND_LINKS}

COPY requirements.txt .
# requirements 里未锁定的 torch 已被上一步满足，此处自动跳过
RUN pip install -r requirements.txt --index-url ${PIP_INDEX_URL}

# 复制应用代码、预训练模型与示例数据
COPY app ./app
COPY models ./models
COPY data ./data

RUN mkdir -p uploads persist

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
