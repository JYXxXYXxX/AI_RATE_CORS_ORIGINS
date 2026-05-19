export interface DocumentUploadResponse {
  document_id: string
  title?: string | null
  filename: string
  subject?: string | null
  degree_level?: string | null
  char_count: number
  status: string
  reused_existing: boolean
  created_at: string
}

export interface UserSummary {
  id: string
  email: string
  display_name?: string | null
  status: string
  credits_balance: number
  created_at: string
}

export interface AuthSessionResponse {
  token: string
  user: UserSummary
}

export interface BillingPackage {
  code: string
  title: string
  description: string
  amount_cents: number
  credits: number
}

export interface UnlockPackage {
  code: string
  title: string
  description: string
  amount_cents: number
  amount_yuan: string
}

export interface UnlockOrder {
  id: string
  user_id: string
  run_id: string
  order_no: string
  package_code: string
  amount_cents: number
  status: 'pending_payment' | 'pending_review' | 'unlocked' | 'rejected'
  payment_method: string | null
  screenshot_url: string | null
  reviewed_by: string | null
  reviewed_at: string | null
  created_at: string
  unlocked_at: string | null
}

export interface UnlockStatus {
  unlocked: boolean
  order: UnlockOrder | null
  package_code: string | null
}

export interface BillingOrderSummary {
  id: string
  order_no: string
  package_code: string
  credits: number
  amount_cents: number
  status: string
  provider: string
  created_at: string
  paid_at?: string | null
}

export interface BillingPaymentChannel {
  code: 'mock_qr' | 'alipay' | 'wechat'
  title: string
  description: string
  enabled: boolean
  ready: boolean
  mode: string
}

export interface BillingOrderDetailResponse {
  order: BillingOrderSummary
  payment_url?: string | null
  qr_content?: string | null
  mock_pay_supported: boolean
  pay_hint?: string | null
  provider_label: string
  provider_ready: boolean
}

export interface BillingOrderPaymentResponse {
  order: BillingOrderSummary
  balance_after: number
  credited: boolean
  packages: BillingPackage[]
}

export interface CreditLedgerItem {
  id: string
  change_amount: number
  balance_after: number
  source_type: string
  note?: string | null
  created_at: string
}

export interface RecentAnalysisTaskSummary {
  task_id: string
  document_id: string
  run_id?: string | null
  title?: string | null
  filename?: string | null
  status: 'queued' | 'processing' | 'completed' | 'failed'
  progress: number
  created_at: string
  finished_at?: string | null
}

export interface BillingSummaryResponse {
  user: UserSummary
  recent_orders: BillingOrderSummary[]
  recent_ledger: CreditLedgerItem[]
  recent_tasks: RecentAnalysisTaskSummary[]
  packages: BillingPackage[]
  payment_channels: BillingPaymentChannel[]
}

export interface AnalyzeDocumentResponse {
  run_id: string
  document_id: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  created_at: string
  finished_at?: string | null
}

export interface AnalysisTaskCreateResponse {
  task_id: string
  document_id: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  progress: number
  created_at: string
}

export interface AnalysisTaskStatusResponse {
  task_id: string
  document_id: string
  run_id?: string | null
  title?: string | null
  filename?: string | null
  status: 'queued' | 'processing' | 'completed' | 'failed'
  stage: string
  progress: number
  created_at: string
  started_at?: string | null
  finished_at?: string | null
  error_message?: string | null
}

export interface AnalysisRunStatusResponse {
  run_id: string
  document_id: string
  title?: string | null
  filename: string
  subject?: string | null
  degree_level?: string | null
  status: 'queued' | 'processing' | 'completed' | 'failed'
  stage: string
  progress: number
  mode: 'estimate' | 'report'
  created_at: string
  started_at?: string | null
  finished_at?: string | null
  error_message?: string | null
}

export interface ScoreBand {
  label: string
  center: number
  low: number
  high: number
  center_percent: number
  low_percent: number
  high_percent: number
}

export interface ReportSummary {
  risk_score: number
  overall_risk: 'low' | 'medium' | 'high'
  one_line_judgement: string
  predicted_cnki_dup: ScoreBand
  predicted_cnki_aigc: ScoreBand
  confidence: number
  first_fix_targets: string[]
  priority_summary?: string
}

export interface LocalMetrics {
  ai_like_score: number
  duplication_score: number
  segment_count: number
  high_risk_segment_count: number
}

export interface ChapterHeatItem {
  chapter_title: string
  section_count: number
  avg_aigc_score: number
  avg_duplication_score: number
  combined_score: number
  risk_level: 'low' | 'medium' | 'high'
  advice: string
}

export interface SubScores {
  ai_likelihood: number
  template_score: number
  semantic_empty_score: number
  repetition_score: number
  citation_risk: number
  overall_risk: number
}

export interface SectionRiskItem {
  section_index: number
  title: string
  section_title?: string | null
  paragraph_index?: number | null
  text_preview: string
  char_count: number
  aigc_score: number
  duplication_score: number
  combined_score: number
  risk_level: 'low' | 'medium' | 'high'
  reasons: string[]
  sub_scores?: SubScores
  priority_rank?: number
}

export interface SimilarityMatchItem {
  section_index: number
  section_title: string
  matched_source: string
  matched_title: string
  matched_snippet: string
  similarity_score: number
  similarity_percent: number
  overlap_chars: number
  match_type: 'exact' | 'semantic' | 'paraphrase'
  source_url?: string | null
}

export interface RevisionPlanItem {
  priority: number
  title: string
  why: string
  how_to_fix: string
  expected_gain: string
}

export interface MentorBrief {
  headline: string
  summary: string
  suggested_message: string
}

export interface ChecklistItem {
  label: string
  done: boolean
}

export interface WorkflowOverview {
  closure_score: number
  closure_label: string
  provider_result_count: number
  feedback_count: number
  latest_feedback_at?: string | null
  next_step: string
}

export interface ProviderResultTimelineItem {
  payload_id: string
  provider: string
  provider_label: string
  source_type: string
  duplication_percent?: number | null
  aigc_percent?: number | null
  confidence?: number | null
  version?: string | null
  notes?: string | null
  created_at: string
}

export interface CnkiReportFragment {
  type: string
  source_text: string
  similar_text?: string | null
  origin?: string | null
  matched_section_index?: number | null
  matched_section_title?: string | null
  matched_text_preview?: string | null
  match_ratio?: number | null
}

export interface CnkiFeedbackDetails {
  remove_reference_dup_percent?: number | null
  single_max_dup_percent?: number | null
  suspected_plagiarism?: Record<string, number> | null
  fragments: CnkiReportFragment[]
}

export interface FeedbackTimelineItem {
  feedback_id: string
  predicted_run_id?: string | null
  cnki_dup_percent?: number | null
  cnki_aigc_percent?: number | null
  report_date?: string | null
  notes?: string | null
  verified: boolean
  details?: CnkiFeedbackDetails | null
  created_at: string
}

export interface CalibrationInsight {
  latest_cnki_dup_percent?: number | null
  latest_cnki_aigc_percent?: number | null
  predicted_dup_delta?: number | null
  predicted_aigc_delta?: number | null
  message: string
}

export interface UnifiedReportResponse {
  run_id: string
  document_id: string
  title: string
  subject?: string | null
  degree_level?: string | null
  generated_at: string
  summary: ReportSummary
  local_metrics: LocalMetrics
  chapter_heatmap: ChapterHeatItem[]
  top_risk_sections: SectionRiskItem[]
  priority_sections?: SectionRiskItem[]
  top_similarity_matches: SimilarityMatchItem[]
  revision_plan: RevisionPlanItem[]
  mentor_brief: MentorBrief
  submission_checklist: ChecklistItem[]
  workflow_overview?: WorkflowOverview | null
  provider_results: ProviderResultTimelineItem[]
  feedback_timeline: FeedbackTimelineItem[]
  calibration_insight?: CalibrationInsight | null
  cnki_report_details?: CnkiFeedbackDetails | null
  warnings?: string[]
  disclaimer: string
  retained_content_policy: string
}

export interface CnkiFeedbackResponse {
  feedback_id: string
  document_id: string
  predicted_run_id?: string | null
  calibration_updated: boolean
  calibration_version: string
  learning_sample_saved: boolean
  learning_skill_updated: boolean
  learning_scope: LearningScope
  auto_train_triggered: boolean
  auto_train_versions: string[]
  created_at: string
}

export type LearningScope = 'none' | 'private_account' | 'anonymous_global'

export interface CnkiFeedbackOcrPreviewResponse {
  filename: string
  cnki_dup_percent?: number | null
  cnki_aigc_percent?: number | null
  report_date?: string | null
  remove_reference_dup_percent?: number | null
  single_max_dup_percent?: number | null
  suspected_plagiarism?: Record<string, number> | null
  fragments: CnkiReportFragment[]
  extracted_text_preview: string
  matched_fields: string[]
  ocr_engine: string
  warnings: string[]
}

export interface RunSectionItem {
  section_index: number
  paragraph_index: number | null
  section_title: string | null
  section_type: string | null
  content: string
  char_count: number
  aigc_score: number
  dup_score: number
  risk_level: 'low' | 'medium' | 'high'
  reasons: string[]
}

// ------------------------------------------------------------------
// Document Blocks & Patches（新架构）
// ------------------------------------------------------------------

export interface ReportRiskData {
  source: 'cnki'
  riskType: 'similarity' | 'aigc'
  riskLevel: 'high' | 'medium' | 'low'
  similarity?: number
  aigcScore?: number
  matchedSource?: string
  spanId: string
  matchConfidence: number
}

export interface InternalRiskData {
  overallRisk: number
  aiLikelihood?: number
  templateScore?: number
  semanticEmptyScore?: number
  repetitionScore?: number
  citationRisk?: number
  reasons?: string[]
}

export interface DocumentBlock {
  blockId: string
  type: 'title' | 'heading' | 'paragraph' | 'table' | 'list' | 'image' | 'unknown'
  text: string
  html?: string
  effectiveText?: string
  riskScore?: number        // 系统自检分数 (0-100)
  reportRisk?: ReportRiskData  // 知网报告风险（优先）
  internalRisk?: InternalRiskData  // 系统自检详细数据
  rewriteStatus?: 'none' | 'rewritten'
  sourceType: 'docx' | 'pdf' | 'doc' | 'txt'
  sourceMap?: {
    paragraphIndex?: number
    runRange?: [number, number]
    pageNumber?: number
    bbox?: {
      x: number
      y: number
      width: number
      height: number
    }
  }
  sectionTitle?: string | null
  sectionType?: string | null
  charCount: number
  displayOrder: number
}

export interface OfficialReportSummary {
  reportType?: 'similarity' | 'aigc' | 'mixed' | null
  totalCopyRatio?: number | null
  aigcRatio?: number | null
  highRiskCount: number
  mediumRiskCount: number
  lowRiskCount: number
  unmatchedCount: number
}

export interface OfficialRiskSpan {
  spanId: string
  text: string
  riskType: 'similarity' | 'aigc'
  riskLevel: 'high' | 'medium' | 'low'
  similarity?: number
  aigcScore?: number
  matchedSource?: string
  pageNumber?: number
}

export interface DocumentPatch {
  blockId: string
  oldText: string
  newText: string
  createdAt: string
}

export interface OnlyOfficeConfigResponse {
  enabled: boolean
  supported: boolean
  reason?: string | null
  scriptUrl?: string | null
  documentServerUrl?: string | null
  editorConfig?: Record<string, any> | null
  documentId?: string
  runId?: string
  sourceFormat?: string | null
  workingCopyReady?: boolean
}

export interface OnlyOfficeApplyResponse {
  ok: boolean
  patchStats: {
    requested: number
    applied: number
    failed: number
    skipped: number
    highlighted: number
  }
  config?: OnlyOfficeConfigResponse | null
}

export interface RewriteWorkspaceHighlight {
  text: string
  riskLevel: 'high' | 'medium' | 'low' | 'normal'
}

export interface RewriteWorkspaceRiskItem {
  riskId: string
  blockId: string
  sectionId: string
  sectionIndex: number
  paragraphIndex?: number | null
  sectionTitle?: string | null
  displayOrder: number
  originalText: string
  currentText: string
  riskLevel: 'high' | 'medium' | 'low' | 'normal'
  aigcScore: number
  diagnosis: string
  rewriteHint: string
  principle: string
  reasons: string[]
  status: 'pending' | 'applied' | 'ignored'
  highlights: RewriteWorkspaceHighlight[]
  sourceMap?: DocumentBlock['sourceMap']
}

export interface RewriteWorkspaceSectionNode {
  sectionId: string
  sectionIndex: number
  paragraphIndex?: number | null
  title: string
  riskLevel: 'high' | 'medium' | 'low' | 'normal'
  itemIds: string[]
  itemCount: number
  riskCounts: Record<'high' | 'medium' | 'low' | 'normal', number>
}

export interface RewriteWorkspaceMetrics {
  currentAigcPercent: number
  estimatedOptimizedPercent: number
  rewrittenCount: number
  ignoredCount: number
  totalRiskCount: number
  highCount: number
  mediumCount: number
  lowCount: number
}

export interface RewriteWorkspaceResponse {
  runId: string
  documentId: string
  title?: string | null
  filename: string
  mode: 'estimate' | 'report'
  sourceFormat?: string | null
  warnings: string[]
  metrics: RewriteWorkspaceMetrics
  sections: RewriteWorkspaceSectionNode[]
  riskItems: RewriteWorkspaceRiskItem[]
}

export interface RiskStyle {
  level: 'high' | 'medium' | 'low' | 'normal'
  bg: string
  border: string
}

export interface ProviderResultImportResponse {
  payload_id: string
  document_id: string
  run_id: string
  provider: string
  accepted: boolean
  created_at: string
}

export interface ProviderConfigSummary {
  provider: string
  configured: boolean
  mode?: string | null
  version?: string | null
}

export interface ProviderCatalogResponse {
  providers: ProviderConfigSummary[]
}

export interface ProviderConfigDetail {
  provider: string
  supports_auto_fetch: boolean
  configured: boolean
  source: 'default' | 'override' | 'merged' | 'none'
  mode?: 'http' | 'file' | null
  method?: string | null
  url?: string | null
  path?: string | null
  auth_type?: string | null
  token_env?: string | null
  has_inline_token: boolean
  version?: string | null
  timeout_seconds?: number | null
  headers: Record<string, string>
  field_map: Record<string, string>
  validation_errors: string[]
  updated_in_registry: boolean
}

export interface ProviderConfigListResponse {
  providers: ProviderConfigDetail[]
}

export interface ReportMarkdownResponse {
  content: string
}

export interface ProviderFetchResponse {
  payload_id: string
  document_id: string
  run_id: string
  provider: string
  accepted: boolean
  created_at: string
}

export interface TrainedModelSummary {
  model_type: string
  version: string
  train_count: number
  mae: number
  rmse: number
  artifact_path: string
  scene_key?: string | null
  activated: boolean
}

export interface ProxyModelTrainResponse {
  trained_models: TrainedModelSummary[]
  dataset_rows: number
}

export interface ModelStatusItem {
  model_type: string
  version: string
  scene_key?: string | null
  is_active: boolean
  metrics: Record<string, unknown>
  artifact_path?: string | null
  created_at: string
}

export interface RewriteSentenceItem {
  original: string
  risk: 'high' | 'medium' | 'low'
  rewritten: string
  explanation: string
}

export interface RewriteAdviceResponse {
  run_id: string
  section_index: number
  diagnosis: string
  sentences: RewriteSentenceItem[]
  rewritten_paragraph: string
  overall_advice: string
  error?: string | null
  fallback?: boolean
}

export interface ModelStatusResponse {
  feedback_count: number
  calibration_version: string
  auto_train_enabled: boolean
  auto_train_every_feedbacks: number
  active_models: ModelStatusItem[]
  recent_models: ModelStatusItem[]
}

export interface ReanalyzeSectionResult {
  section_index: number
  section_title: string | null
  aigc_score: number
  duplication_score: number
  risk_level: 'low' | 'medium' | 'high'
}

export interface ReanalyzeResponse {
  ai_like_score: number
  ai_like_percent: number
  duplication_score: number
  duplication_percent: number
  risk_level: 'low' | 'medium' | 'high'
  predicted_cnki_range: string
  confidence: string
  segment_count: number
  total_chars: number
  sections: ReanalyzeSectionResult[]
  disclaimer: string
}

export type QuickRewriteMode = 'auto' | 'aigc' | 'similarity' | 'polish'

export interface QuickRewriteRisk {
  score: number
  level: 'high' | 'medium' | 'low' | 'normal'
}

export interface QuickRewritePhrase {
  text: string
  reason: string
  start?: number
  end?: number
}

export interface QuickRewriteResult {
  originalText: string
  rewrittenText: string
  beforeRisk: QuickRewriteRisk
  afterRisk: QuickRewriteRisk
  riskyPhrases: QuickRewritePhrase[]
  improvedPhrases: QuickRewritePhrase[]
  rewritePrinciples: string[]
  summary: string
  recommendedMode: QuickRewriteMode
  remainingFreeUses?: number | null
  disclaimer: string
}
