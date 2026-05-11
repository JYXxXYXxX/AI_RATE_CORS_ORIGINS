from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    document_id: str
    title: str | None = None
    filename: str
    subject: str | None = None
    degree_level: str | None = None
    char_count: int = Field(..., ge=0)
    status: str
    reused_existing: bool
    created_at: datetime


class UserSummary(BaseModel):
    id: str
    email: str
    display_name: str | None = None
    status: str
    credits_balance: int = Field(..., ge=0)
    created_at: datetime


class AuthRegisterRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=6)
    display_name: str | None = None


class AuthLoginRequest(BaseModel):
    email: str
    password: str


class AuthSessionResponse(BaseModel):
    token: str
    user: UserSummary


class BillingPackage(BaseModel):
    code: str
    title: str
    description: str
    amount_cents: int = Field(..., ge=0)
    credits: int = Field(..., ge=0)


class BillingOrderSummary(BaseModel):
    id: str
    order_no: str
    package_code: str
    credits: int = Field(..., ge=0)
    amount_cents: int = Field(..., ge=0)
    status: str
    provider: str
    created_at: datetime
    paid_at: datetime | None = None


class BillingPaymentChannel(BaseModel):
    code: str
    title: str
    description: str
    enabled: bool
    ready: bool
    mode: str


class CreditLedgerItem(BaseModel):
    id: str
    change_amount: int
    balance_after: int = Field(..., ge=0)
    source_type: str
    note: str | None = None
    created_at: datetime


class RecentAnalysisTaskSummary(BaseModel):
    task_id: str
    document_id: str
    run_id: str | None = None
    title: str | None = None
    filename: str | None = None
    status: Literal["queued", "processing", "completed", "failed"]
    progress: int = Field(..., ge=0, le=100)
    created_at: datetime
    finished_at: datetime | None = None


class BillingSummaryResponse(BaseModel):
    user: UserSummary
    recent_orders: list[BillingOrderSummary]
    recent_ledger: list[CreditLedgerItem]
    recent_tasks: list[RecentAnalysisTaskSummary] = Field(default_factory=list)
    packages: list[BillingPackage]
    payment_channels: list[BillingPaymentChannel] = Field(default_factory=list)


class MockCheckoutRequest(BaseModel):
    package_code: str


class MockCheckoutResponse(BaseModel):
    order: BillingOrderSummary
    balance_after: int = Field(..., ge=0)
    packages: list[BillingPackage]


class BillingOrderCreateRequest(BaseModel):
    package_code: str
    provider: Literal["mock_qr", "alipay", "wechat"] = "mock_qr"


class BillingOrderDetailResponse(BaseModel):
    order: BillingOrderSummary
    payment_url: str | None = None
    qr_content: str | None = None
    mock_pay_supported: bool = False
    pay_hint: str | None = None
    provider_label: str = ""
    provider_ready: bool = False


class BillingOrderPaymentResponse(BaseModel):
    order: BillingOrderSummary
    balance_after: int = Field(..., ge=0)
    credited: bool
    packages: list[BillingPackage]


class MockPaymentCallbackRequest(BaseModel):
    order_no: str
    paid_amount_cents: int = Field(..., ge=0)
    signature: str = Field(..., min_length=16)


class BillingCallbackResponse(BaseModel):
    accepted: bool
    order: BillingOrderSummary
    balance_after: int = Field(..., ge=0)
    credited: bool


class AnalyzeDocumentResponse(BaseModel):
    run_id: str
    document_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    created_at: datetime
    finished_at: datetime | None = None


class AnalysisRunStatusResponse(BaseModel):
    run_id: str
    document_id: str
    title: str | None = None
    filename: str
    subject: str | None = None
    degree_level: str | None = None
    status: Literal["queued", "processing", "completed", "failed"]
    stage: str
    progress: int = Field(..., ge=0, le=100)
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None


class AnalysisTaskCreateResponse(BaseModel):
    task_id: str
    document_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    progress: int = Field(..., ge=0, le=100)
    created_at: datetime


class AnalysisTaskStatusResponse(BaseModel):
    task_id: str
    document_id: str
    run_id: str | None = None
    title: str | None = None
    filename: str | None = None
    status: Literal["queued", "processing", "completed", "failed"]
    stage: str
    progress: int = Field(..., ge=0, le=100)
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None


class ScoreBand(BaseModel):
    label: str
    center: float = Field(..., ge=0, le=1)
    low: float = Field(..., ge=0, le=1)
    high: float = Field(..., ge=0, le=1)
    center_percent: float = Field(..., ge=0, le=100)
    low_percent: float = Field(..., ge=0, le=100)
    high_percent: float = Field(..., ge=0, le=100)


class ReportSummary(BaseModel):
    comfort_score: int = Field(..., ge=0, le=100)
    overall_risk: Literal["low", "medium", "high"]
    one_line_judgement: str
    predicted_cnki_dup: ScoreBand
    predicted_cnki_aigc: ScoreBand
    confidence: float = Field(..., ge=0, le=1)
    first_fix_targets: list[str]


class LocalMetrics(BaseModel):
    ai_like_score: float = Field(..., ge=0, le=1)
    duplication_score: float = Field(..., ge=0, le=1)
    segment_count: int = Field(..., ge=0)
    high_risk_segment_count: int = Field(..., ge=0)


class ChapterHeatItem(BaseModel):
    chapter_title: str
    section_count: int = Field(..., ge=0)
    avg_aigc_score: float = Field(..., ge=0, le=1)
    avg_duplication_score: float = Field(..., ge=0, le=1)
    combined_score: float = Field(..., ge=0, le=1)
    risk_level: Literal["low", "medium", "high"]
    advice: str


class SectionRiskItem(BaseModel):
    section_index: int = Field(..., ge=0)
    title: str
    section_title: str | None = None
    paragraph_index: int | None = None
    text_preview: str
    char_count: int = Field(..., ge=0)
    aigc_score: float = Field(..., ge=0, le=1)
    duplication_score: float = Field(..., ge=0, le=1)
    combined_score: float = Field(..., ge=0, le=1)
    risk_level: Literal["low", "medium", "high"]
    reasons: list[str]


class SimilarityMatchItem(BaseModel):
    section_index: int = Field(..., ge=0)
    section_title: str
    matched_source: str
    matched_title: str
    matched_snippet: str
    similarity_score: float = Field(..., ge=0, le=1)
    similarity_percent: float = Field(..., ge=0, le=100)
    overlap_chars: int = Field(..., ge=0)
    match_type: Literal["exact", "semantic", "paraphrase"]
    source_url: str | None = None


class RevisionPlanItem(BaseModel):
    priority: int = Field(..., ge=1)
    title: str
    why: str
    how_to_fix: str
    expected_gain: str


class MentorBrief(BaseModel):
    headline: str
    summary: str
    suggested_message: str


class ChecklistItem(BaseModel):
    label: str
    done: bool = False


class WorkflowOverview(BaseModel):
    closure_score: int = Field(..., ge=0, le=100)
    closure_label: str
    provider_result_count: int = Field(..., ge=0)
    feedback_count: int = Field(..., ge=0)
    latest_feedback_at: datetime | None = None
    next_step: str


class ProviderResultTimelineItem(BaseModel):
    payload_id: str
    provider: str
    provider_label: str
    source_type: str
    duplication_percent: float | None = Field(default=None, ge=0, le=100)
    aigc_percent: float | None = Field(default=None, ge=0, le=100)
    confidence: float | None = Field(default=None, ge=0, le=1)
    version: str | None = None
    notes: str | None = None
    created_at: datetime


class FeedbackTimelineItem(BaseModel):
    feedback_id: str
    predicted_run_id: str | None = None
    cnki_dup_percent: float | None = Field(default=None, ge=0, le=100)
    cnki_aigc_percent: float | None = Field(default=None, ge=0, le=100)
    report_date: date | None = None
    notes: str | None = None
    verified: bool = False
    created_at: datetime


class CalibrationInsight(BaseModel):
    latest_cnki_dup_percent: float | None = Field(default=None, ge=0, le=100)
    latest_cnki_aigc_percent: float | None = Field(default=None, ge=0, le=100)
    predicted_dup_delta: float | None = None
    predicted_aigc_delta: float | None = None
    message: str


class CnkiReportFragment(BaseModel):
    type: str = "unknown"
    source_text: str
    similar_text: str | None = None
    origin: str | None = None
    matched_section_index: int | None = None
    matched_section_title: str | None = None
    matched_text_preview: str | None = None
    match_ratio: float | None = None


class CnkiFeedbackDetails(BaseModel):
    remove_reference_dup_percent: float | None = Field(default=None, ge=0, le=100)
    single_max_dup_percent: float | None = Field(default=None, ge=0, le=100)
    suspected_plagiarism: dict[str, int] | None = None
    fragments: list[CnkiReportFragment] = Field(default_factory=list)


class UnifiedReportResponse(BaseModel):
    run_id: str
    document_id: str
    title: str
    subject: str | None = None
    degree_level: str | None = None
    generated_at: datetime
    summary: ReportSummary
    local_metrics: LocalMetrics
    chapter_heatmap: list[ChapterHeatItem]
    top_risk_sections: list[SectionRiskItem]
    top_similarity_matches: list[SimilarityMatchItem]
    revision_plan: list[RevisionPlanItem]
    mentor_brief: MentorBrief
    submission_checklist: list[ChecklistItem]
    workflow_overview: WorkflowOverview | None = None
    provider_results: list[ProviderResultTimelineItem] = Field(default_factory=list)
    feedback_timeline: list[FeedbackTimelineItem] = Field(default_factory=list)
    calibration_insight: CalibrationInsight | None = None
    cnki_report_details: CnkiFeedbackDetails | None = None
    disclaimer: str
    retained_content_policy: str


class CnkiFeedbackResponse(BaseModel):
    feedback_id: str
    document_id: str
    predicted_run_id: str | None = None
    calibration_updated: bool
    calibration_version: str
    auto_train_triggered: bool = False
    auto_train_versions: list[str] = Field(default_factory=list)
    created_at: datetime


class CnkiFeedbackOcrPreviewResponse(BaseModel):
    filename: str
    cnki_dup_percent: float | None = Field(default=None, ge=0, le=100)
    cnki_aigc_percent: float | None = Field(default=None, ge=0, le=100)
    report_date: str | None = None
    remove_reference_dup_percent: float | None = Field(default=None, ge=0, le=100)
    single_max_dup_percent: float | None = Field(default=None, ge=0, le=100)
    suspected_plagiarism: dict[str, int] | None = None
    fragments: list[CnkiReportFragment] = Field(default_factory=list)
    extracted_text_preview: str
    matched_fields: list[str]
    ocr_engine: str
    warnings: list[str]


class ProviderResultImportRequest(BaseModel):
    document_id: str
    run_id: str
    provider: Literal["wanfang", "vip", "turnitin", "manual"]
    duplication_percent: float | None = Field(default=None, ge=0, le=100)
    aigc_percent: float | None = Field(default=None, ge=0, le=100)
    confidence: float | None = Field(default=None, ge=0, le=1)
    version: str | None = None
    notes: str | None = None
    raw_payload: dict[str, object] = Field(default_factory=dict)


class ProviderResultImportResponse(BaseModel):
    payload_id: str
    document_id: str
    run_id: str
    provider: str
    accepted: bool
    created_at: datetime


class ProviderFetchRequest(BaseModel):
    document_id: str
    run_id: str
    provider: Literal["wanfang", "vip", "turnitin", "manual"]
    extra_payload: dict[str, object] = Field(default_factory=dict)


class ProviderFetchResponse(BaseModel):
    payload_id: str
    document_id: str
    run_id: str
    provider: str
    accepted: bool
    created_at: datetime


class ProviderConfigSummary(BaseModel):
    provider: str
    configured: bool
    mode: str | None = None
    version: str | None = None


class ProviderCatalogResponse(BaseModel):
    providers: list[ProviderConfigSummary]


class ProviderConfigDetail(BaseModel):
    provider: str
    supports_auto_fetch: bool
    configured: bool
    source: Literal["default", "override", "merged", "none"]
    mode: Literal["http", "file"] | None = None
    method: str | None = None
    url: str | None = None
    path: str | None = None
    auth_type: str | None = None
    token_env: str | None = None
    has_inline_token: bool = False
    version: str | None = None
    timeout_seconds: float | None = Field(default=None, ge=0)
    headers: dict[str, str] = Field(default_factory=dict)
    field_map: dict[str, str] = Field(default_factory=dict)
    validation_errors: list[str] = Field(default_factory=list)
    updated_in_registry: bool = False


class ProviderConfigListResponse(BaseModel):
    providers: list[ProviderConfigDetail]


class ProviderConfigUpdateRequest(BaseModel):
    mode: Literal["http", "file"]
    method: str | None = None
    url: str | None = None
    path: str | None = None
    auth_type: str | None = None
    token_env: str | None = None
    version: str | None = None
    timeout_seconds: float | None = Field(default=None, ge=1)
    headers: dict[str, str] = Field(default_factory=dict)
    field_map: dict[str, str] = Field(default_factory=dict)


class ProxyModelTrainRequest(BaseModel):
    model_type: Literal["cnki_dup_proxy", "cnki_aigc_proxy", "both"] = "both"
    scene_key: str | None = None
    activate: bool = True
    min_samples: int | None = Field(default=None, ge=1)


class TrainedModelSummary(BaseModel):
    model_type: str
    version: str
    train_count: int
    mae: float
    rmse: float
    artifact_path: str
    scene_key: str | None = None
    activated: bool


class ProxyModelTrainResponse(BaseModel):
    trained_models: list[TrainedModelSummary]
    dataset_rows: int


class ModelStatusItem(BaseModel):
    model_type: str
    version: str
    scene_key: str | None = None
    is_active: bool
    metrics: dict[str, object]
    artifact_path: str | None = None
    created_at: datetime


class ModelStatusResponse(BaseModel):
    feedback_count: int
    calibration_version: str
    auto_train_enabled: bool
    auto_train_every_feedbacks: int
    active_models: list[ModelStatusItem]
    recent_models: list[ModelStatusItem]


class RewriteSentenceItem(BaseModel):
    original: str
    risk: Literal["high", "medium", "low"]
    rewritten: str
    explanation: str


class RewriteAdviceResponse(BaseModel):
    run_id: str
    section_index: int
    diagnosis: str
    sentences: list[RewriteSentenceItem]
    rewritten_paragraph: str
    overall_advice: str
    error: str | None = None


class ReanalyzeSectionItem(BaseModel):
    section_index: int
    content: str


class ReanalyzeRequest(BaseModel):
    sections: list[ReanalyzeSectionItem]


class ReanalyzeSectionResult(BaseModel):
    section_index: int
    section_title: str | None = None
    aigc_score: float
    duplication_score: float
    risk_level: Literal["high", "medium", "low"]


class ReanalyzeResponse(BaseModel):
    ai_like_score: float
    ai_like_percent: float
    duplication_score: float
    duplication_percent: float
    risk_level: Literal["high", "medium", "low"]
    predicted_cnki_range: str
    confidence: str
    segment_count: int
    total_chars: int
    sections: list[ReanalyzeSectionResult]
    disclaimer: str


class ExportSectionItem(BaseModel):
    section_index: int
    content: str
    risk_level: Literal["low", "medium", "high", "normal"] = "normal"


class ExportRequest(BaseModel):
    sections: list[ExportSectionItem]
    format: Literal["docx", "txt"] = "docx"


# ------------------------------------------------------------------
# Document Blocks & Patches
# ------------------------------------------------------------------

class DocumentBlockResponse(BaseModel):
    block_id: str
    block_type: str
    text: str
    html: str | None = None
    effective_text: str | None = None
    risk_score: float | None = None
    rewrite_status: str = "none"
    source_type: str
    source_map: dict[str, Any] | None = None
    section_title: str | None = None
    section_type: str | None = None
    char_count: int = 0
    display_order: int


class DocumentPatchRequest(BaseModel):
    block_id: str
    old_text: str
    new_text: str
    source_map: dict[str, Any] | None = None


class DocumentPatchResponse(BaseModel):
    id: str
    document_id: str
    run_id: str | None = None
    block_id: str
    old_text: str
    new_text: str
    created_at: str
    format: Literal["docx", "txt"] = "docx"
