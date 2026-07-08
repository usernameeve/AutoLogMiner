from pydantic import BaseModel, Field
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
