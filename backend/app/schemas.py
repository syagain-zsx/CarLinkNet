"""Pydantic 请求/响应模型。"""
from __future__ import annotations

from pydantic import BaseModel, Field


# ---------- 认证 ----------
class RegisterIn(BaseModel):
    username: str = Field(min_length=2, max_length=32)
    password: str = Field(min_length=6, max_length=64)
    display_name: str = Field(default="", max_length=32)


class LoginIn(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str | None = None
    role: str
    enabled: bool
    created_at: str | None = None


class TokenOut(BaseModel):
    token: str
    user: UserOut


# ---------- 数据 ----------
class DatasetOut(BaseModel):
    id: int
    name: str
    filename: str
    rows: int
    uploaded_at: str | None = None


# ---------- 特征 ----------
class FeatureGenIn(BaseModel):
    name: str = Field(default="", max_length=64)
    dataset_id: int
    feature_type: str = Field(default="all", description="statistical / btsf / frequency / all")


class FeatureSetOut(BaseModel):
    id: int
    name: str
    dataset_id: int | None
    feature_type: str
    dimensions: str
    created_at: str | None = None


# ---------- 规则 ----------
class RuleOut(BaseModel):
    id: int
    name: str
    filename: str | None
    enabled: bool
    rule_count: int
    uploaded_at: str | None = None


# ---------- 检测 ----------
class DetectionCreateIn(BaseModel):
    name: str = Field(default="", max_length=64)
    mode: str = Field(default="model", description="rule / model / collaborative")
    dataset_id: int
    ruleset_id: int | None = None
    use_student: bool = False


class TaskOut(BaseModel):
    id: int
    task_code: str
    name: str
    mode: str
    dataset_id: int | None
    ruleset_id: int | None
    use_student: bool
    status: str
    message: str | None = None
    created_at: str | None = None
    finished_at: str | None = None


# ---------- 结果 ----------
class ResultItem(BaseModel):
    label: str
    count: int
    confidence_avg: float


class ResultOut(BaseModel):
    task: TaskOut
    source: str
    total: int
    attack_count: int
    benign_count: int
    items: list[ResultItem]


# ---------- 用户管理 ----------
class UserUpdateIn(BaseModel):
    role: str | None = None
    enabled: bool | None = None
