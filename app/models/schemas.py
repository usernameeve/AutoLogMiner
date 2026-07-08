"""数据模型定义 — Pydantic 请求/响应结构、枚举、供应商模型（含 API Key 脱敏）。"""

from pydantic import BaseModel, Field, model_validator
from enum import Enum
from datetime import datetime


class Severity(str, Enum):
    """故障严重程度分级。"""
    P0 = "P0-紧急"
    P1 = "P1-严重"
    P2 = "P2-一般"
    P3 = "P3-提示"


class DiagnosisResult(BaseModel):
    """LLM 返回的结构化诊断结果。"""
    summary: str = Field(description="问题摘要，一句话描述")
    severity: Severity = Field(description="严重程度")
    root_cause: str = Field(description="根因分析")
    fix_steps: list[str] = Field(description="修复步骤，每步含可执行命令")
    prevention: str = Field(description="预防建议")


class DiagnoseRequest(BaseModel):
    """诊断请求体。"""
    log_content: str = Field(description="日志内容文本")
    service_hint: str | None = Field(default=None, description="提示涉及的服务类型")
    provider_id: int | None = Field(default=None, description="供应商 ID，不传则使用默认供应商")



class ProviderCreate(BaseModel):
    """新增供应商请求体。"""
    name: str = Field(description="供应商名称")
    api_key: str = Field(description="API Key")
    base_url: str = Field(description="API Base URL")
    model: str = Field(description="模型名称")
    is_default: bool = Field(default=False, description="是否设为默认供应商")


class ProviderUpdate(BaseModel):
    """编辑供应商请求体，所有字段可选。"""
    name: str | None = Field(default=None, description="供应商名称")
    api_key: str | None = Field(default=None, description="API Key")
    base_url: str | None = Field(default=None, description="API Base URL")
    model: str | None = Field(default=None, description="模型名称")
    is_default: bool | None = Field(default=None, description="是否设为默认供应商")


class ProviderResponse(BaseModel):
    """供应商响应体，api_key 字段自动脱敏为 前4位****后4位。"""
    id: int
    name: str
    api_key: str = Field(description="脱敏后的 API Key")
    base_url: str
    model: str
    is_default: bool
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def mask_api_key(cls, data: dict) -> dict:
        """将 api_key 脱敏：保留前 4 位和后 4 位，中间替换为 ****"""
        key = data.get("api_key", "")
        if key and len(key) > 8:
            data["api_key"] = key[:4] + "****" + key[-4:]
        return data

