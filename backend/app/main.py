"""FastAPI 应用入口：中间件、路由注册与启动初始化。"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .api import auth, data, feature, rule, detection, result, user

app = FastAPI(title="工业互联网智能入侵检测系统", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


init_db()

app.include_router(auth.router, prefix="/api")
app.include_router(data.router, prefix="/api")
app.include_router(feature.router, prefix="/api")
app.include_router(rule.router, prefix="/api")
app.include_router(detection.router, prefix="/api")
app.include_router(result.router, prefix="/api")
app.include_router(user.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "工业互联网智能入侵检测系统"}
