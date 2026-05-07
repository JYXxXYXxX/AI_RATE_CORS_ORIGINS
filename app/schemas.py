from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class AnalyzeTextRequest(BaseModel):
    text: str = Field(..., min_length=1)
    title: str | None = None
    subject: str | None = None
    degree_level: str | None = None
    options: dict[str, object] = Field(default_factory=dict)


class DetectorSignal(BaseModel):
    name: str
    score: float = Field(..., ge=0, le=1)
    weight: float = Field(..., ge=0)
    reasons: list[str] = Field(default_factory=list)


class SegmentReport(BaseModel):
    index: int
    section_title: str | None = None
    paragraph_index: int | None = None
    text_preview: str
    char_count: int
    raw_ai_score: float = Field(..., ge=0, le=1)
    ai_probability: float = Field(..., ge=0, le=1)
    ai_like_score: float = Field(..., ge=0, le=1)
    risk_level: str
    reasons: list[str] = Field(default_factory=list)
    signals: list[DetectorSignal] = Field(default_factory=list)


class CnkiRiskRange(BaseModel):
    lower: float = Field(..., ge=0, le=1)
    upper: float = Field(..., ge=0, le=1)
    lower_percent: float = Field(..., ge=0, le=100)
    upper_percent: float = Field(..., ge=0, le=100)
    label: str


class AnalyzeResponse(BaseModel):
    report_id: str
    title: str | None
    subject: str | None = None
    degree_level: str | None = None
    ai_like_score: float = Field(..., ge=0, le=1)
    ai_like_percent: float = Field(..., ge=0, le=100)
    predicted_cnki_range: CnkiRiskRange
    confidence: float = Field(..., ge=0, le=1)
    risk_level: str
    segment_count: int
    total_chars: int
    high_risk_segments: list[int]
    segment_reports: list[SegmentReport]
    model_version: str
    calibration_version: str
    disclaimer: str
    generated_at: datetime
    retained_content_policy: str

    @property
    def ai_rate(self) -> float:
        return self.ai_like_score

    @property
    def ai_rate_percent(self) -> float:
        return self.ai_like_percent

    @property
    def confidence_interval(self) -> tuple[float, float]:
        return (self.predicted_cnki_range.lower, self.predicted_cnki_range.upper)

    @property
    def segments(self) -> list[SegmentReport]:
        return self.segment_reports


class JobCreateResponse(BaseModel):
    job_id: str
    status: Literal["queued"]
    progress: int = Field(..., ge=0, le=100)
    stage: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    progress: int = Field(..., ge=0, le=100)
    stage: str
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    title: str | None = None
    subject: str | None = None
    degree_level: str | None = None


class CalibrationSampleRequest(BaseModel):
    job_id: str | None = None
    ai_like_score: float | None = Field(default=None, ge=0, le=1)
    cnki_ai_rate: float | None = Field(default=None, ge=0, le=1)
    cnki_ai_rate_percent: float | None = Field(default=None, ge=0, le=100)
    subject: str | None = None
    degree_level: str | None = None
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_scores(self) -> "CalibrationSampleRequest":
        if self.job_id is None and self.ai_like_score is None:
            raise ValueError("job_id 或 ai_like_score 至少提供一个")
        if self.cnki_ai_rate is None and self.cnki_ai_rate_percent is None:
            raise ValueError("cnki_ai_rate 或 cnki_ai_rate_percent 至少提供一个")
        return self


class CalibrationSampleResponse(BaseModel):
    calibration_version: str
    sample_count: int
    accepted: bool
