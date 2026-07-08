from pydantic import BaseModel, Field, model_validator
from enum import Enum
from datetime import datetime


class Severity(str, Enum):
    P0 = "P0-紧急"
    P1 = "P1-严重"
    P2 = "P2-一般"
    P3 = "P3-提示"


class DiagnosisResult(BaseModel):
    """Structured diagnosis output from LLM."""
    summary: str = Field(description="问题摘要，一句话描述")
    severity: Severity = Field(description="严重程度")
    root_cause: str = Field(description="根因分析")
    fix_steps: list[str] = Field(description="修复步骤，每步含可执行命令")
    prevention: str = Field(description="预防建议")


class DiagnoseRequest(BaseModel):
    log_content: str = Field(description="日志内容文本")
    service_hint: str | None = Field(default=None, description="提示涉及的服务类型")
    provider_id: int | None = Field(default=None, description="供应商ID，不传则使用默认")


class DiagnosisRecord(BaseModel):
    id: int
    timestamp: datetime
    log_preview: str
    severity: str
    summary: str
    full_result: str  # JSON string of DiagnosisResult


class HistoryResponse(BaseModel):
    records: list[DiagnosisRecord]
    total: int


class ProviderCreate(BaseModel):
    name: str = Field(description="供应商名称")
    api_key: str = Field(description="API Key")
    base_url: str = Field(description="API Base URL")
    model: str = Field(description="模型名称")
    is_default: bool = Field(default=False, description="是否设为默认")


class ProviderUpdate(BaseModel):
    name: str | None = Field(default=None, description="供应商名称")
    api_key: str | None = Field(default=None, description="API Key")
    base_url: str | None = Field(default=None, description="API Base URL")
    model: str | None = Field(default=None, description="模型名称")
    is_default: bool | None = Field(default=None, description="是否设为默认")


class ProviderResponse(BaseModel):
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
        key = data.get("api_key", "")
        if key and len(key) > 8:
            data["api_key"] = key[:4] + "****" + key[-4:]
        return data
