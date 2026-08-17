#!/usr/bin/env bash
# 打包部署产物：排除 node_modules / __pycache__ / 运行时数据等，生成可上传的 tar 包
# 用法（Windows 上用 Git Bash 或 WSL 运行，或直接在 Linux 上运行）：
#   bash pack.sh
set -euo pipefail
cd "$(dirname "$0")"

OUT="ids-deploy.tar.gz"

tar czf "$OUT" \
  --exclude='frontend/node_modules' \
  --exclude='frontend/dist' \
  --exclude='frontend/.vite' \
  --exclude='backend/__pycache__' \
  --exclude='*/__pycache__' \
  --exclude='*.pyc' \
  --exclude='backend/ids.db' \
  --exclude='backend/uploads' \
  --exclude='backend/.venv' \
  --exclude='.git' \
  --exclude="$OUT" \
  backend frontend docker-compose.yml .env.example

echo "✅ 打包完成: $OUT ($(du -h "$OUT" | cut -f1))"
echo "上传命令: scp $OUT root@<服务器IP>:/opt/"
