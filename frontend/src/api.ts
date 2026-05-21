import type {
  AnalysisRunStatusResponse,
  AnalysisTaskCreateResponse,
  AnalysisTaskStatusResponse,
  AnalyzeDocumentResponse,
  AuthResendVerificationResponse,
  AuthSessionResponse,
  AuthVerifyEmailResponse,
  BillingOrderDetailResponse,
  BillingOrderPaymentResponse,
  BillingSummaryResponse,
  CnkiFeedbackOcrPreviewResponse,
  CnkiFeedbackResponse,
  CnkiReportFragment,
  DocumentConversionResponse,
  DocumentBlock,
  DocumentPatch,
  DocumentUploadResponse,
  ModelStatusResponse,
  LearningScope,
  OnlyOfficeApplyResponse,
  OnlyOfficeConfigResponse,
  OfficialReportSummary,
  OfficialRiskSpan,
  ProviderCatalogResponse,
  ProviderConfigDetail,
  ProviderConfigListResponse,
  ProviderFetchResponse,
  ProviderResultImportResponse,
  ProxyModelTrainResponse,
  QuickRewriteMode,
  QuickRewriteResult,
  ReanalyzeResponse,
  RewriteAdviceResponse,
  RewriteWorkspaceResponse,
  RunSectionItem,
  UnifiedReportResponse,
  UnlockOrder,
  UnlockPackage,
  UnlockStatus,
  UserSummary
} from './types'

export const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
const MAX_RETRIES = 3
const RETRY_DELAY_MS = 500

async function fetchWithRetry(
  url: string,
  options: RequestInit,
  retries = MAX_RETRIES
): Promise<Response> {
  try {
    const response = await fetch(url, options)
    // 鍙噸璇曟湇鍔＄閿欒鎴栫綉缁滈敊璇紙鏃犲搷搴旓級
    if (response.status >= 500 && retries > 0) {
      await new Promise((r) => setTimeout(r, RETRY_DELAY_MS * (MAX_RETRIES - retries + 1)))
      return fetchWithRetry(url, options, retries - 1)
    }
    return response
  } catch (err) {
    if (retries > 0) {
      await new Promise((r) => setTimeout(r, RETRY_DELAY_MS * (MAX_RETRIES - retries + 1)))
      return fetchWithRetry(url, options, retries - 1)
    }
    throw err
  }
}

export async function registerAccount(payload: {
  email: string
  password: string
  displayName?: string
}): Promise<AuthSessionResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/auth/register`, {
    method: 'POST',
    headers: jsonHeaders(),
    credentials: 'include',
    body: JSON.stringify({
      email: payload.email,
      password: payload.password,
      display_name: payload.displayName || null
    })
  })
  return parseResponse<AuthSessionResponse>(response)
}

export async function loginAccount(payload: {
  email: string
  password: string
}): Promise<AuthSessionResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/auth/login`, {
    method: 'POST',
    headers: jsonHeaders(),
    credentials: 'include',
    body: JSON.stringify(payload)
  })
  return parseResponse<AuthSessionResponse>(response)
}

export async function resendVerificationEmail(email: string): Promise<AuthResendVerificationResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/auth/email/resend`, {
    method: 'POST',
    headers: jsonHeaders(),
    credentials: 'include',
    body: JSON.stringify({ email })
  })
  return parseResponse<AuthResendVerificationResponse>(response)
}

export async function verifyEmailToken(token: string): Promise<AuthVerifyEmailResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/auth/email/verify`, {
    method: 'POST',
    headers: jsonHeaders(),
    credentials: 'include',
    body: JSON.stringify({ token })
  })
  return parseResponse<AuthVerifyEmailResponse>(response)
}

export async function getCurrentAccount(): Promise<UserSummary> {
  const response = await fetchWithRetry(`${baseUrl}/v1/auth/me`, {
    headers: authHeaders(),
    credentials: 'include'
  })
  return parseResponse<UserSummary>(response)
}

export async function logoutAccount(): Promise<void> {
  const response = await fetchWithRetry(`${baseUrl}/v1/auth/logout`, {
    method: 'POST',
    headers: authHeaders(),
    credentials: 'include'
  })
  await parseResponse<{ ok: boolean }>(response)
}

export async function getBillingSummary(): Promise<BillingSummaryResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/billing/summary`, {
    headers: authHeaders(),
    credentials: 'include'
  })
  return parseResponse<BillingSummaryResponse>(response)
}

export async function createMockCheckout(packageCode: string): Promise<BillingSummaryResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/billing/mock-checkout`, {
    method: 'POST',
    headers: jsonHeaders(true),
    credentials: 'include',
    body: JSON.stringify({ package_code: packageCode })
  })
  await parseResponse(response)
  return getBillingSummary()
}

export async function createBillingOrder(payload: {
  packageCode: string
  provider?: 'mock_qr' | 'alipay' | 'wechat'
}): Promise<BillingOrderDetailResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/billing/orders`, {
    method: 'POST',
    headers: jsonHeaders(true),
    credentials: 'include',
    body: JSON.stringify({
      package_code: payload.packageCode,
      provider: payload.provider || 'mock_qr'
    })
  })
  return parseResponse<BillingOrderDetailResponse>(response)
}

export async function getBillingOrder(orderNo: string): Promise<BillingOrderDetailResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/billing/orders/${orderNo}`, {
    headers: authHeaders(),
    credentials: 'include'
  })
  return parseResponse<BillingOrderDetailResponse>(response)
}

export async function mockPayBillingOrder(orderNo: string): Promise<BillingOrderPaymentResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/billing/orders/${orderNo}/mock-pay`, {
    method: 'POST',
    headers: authHeaders(),
    credentials: 'include'
  })
  return parseResponse<BillingOrderPaymentResponse>(response)
}

export async function uploadDocument(payload: {
  file: File
  title?: string
  subject?: string
  degreeLevel?: string
  onProgress?: (percent: number) => void
}): Promise<DocumentUploadResponse> {
  const formData = new FormData()
  formData.append('file', payload.file)
  if (payload.title) formData.append('title', payload.title)
  if (payload.subject) formData.append('subject', payload.subject)
  if (payload.degreeLevel) formData.append('degree_level', payload.degreeLevel)

  if (payload.onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      xhr.open('POST', `${baseUrl}/v1/documents/upload`)
      xhr.withCredentials = true
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          payload.onProgress!(Math.round((event.loaded / event.total) * 100))
        }
      }
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText))
        } else {
          let detail = formatApiError(xhr.status)
          try {
            const body = JSON.parse(xhr.responseText)
            detail = body.detail || detail
          } catch { /* ignore */ }
          reject(new Error(detail))
        }
      }
      xhr.onerror = () => reject(new Error('无法连接到分析服务，请确认本地后端已启动且前端代理已连通'))
      xhr.send(formData)
    })
  }

  const response = await fetchWithRetry(`${baseUrl}/v1/documents/upload`, {
    method: 'POST',
    headers: authHeaders(),
    credentials: 'include',
    body: formData
  })
  return parseResponse<DocumentUploadResponse>(response)
}

export async function convertDocumentToDocx(file: File): Promise<DocumentConversionResponse> {
  const formData = new FormData()
  formData.append('file', file)
  let response: Response
  try {
    response = await fetch(`${baseUrl}/v1/documents/convert-to-docx`, {
      method: 'POST',
      headers: authHeaders(),
      credentials: 'include',
      body: formData
    })
  } catch {
    throw new Error('转换请求被中断，请稍后重试；如果是较大的 .doc 文件，建议先用 Word/WPS 另存为 .docx 后再上传。')
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(formatApiError(response.status, payload.detail))
  }
  return {
    blob: await response.blob(),
    filename: parseDownloadFilename(response.headers.get('Content-Disposition')) || toDocxName(file.name),
    engine: response.headers.get('X-Conversion-Engine')
  }
}

export async function analyzeDocument(documentId: string, force = true): Promise<AnalyzeDocumentResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/documents/${documentId}/analyze?force=${force}`, {
    method: 'POST',
    headers: authHeaders(),
    credentials: 'include'
  })
  return parseResponse<AnalyzeDocumentResponse>(response)
}

export async function analyzeDocumentAsync(documentId: string): Promise<AnalysisTaskCreateResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/documents/${documentId}/analyze-async`, {
    method: 'POST',
    headers: authHeaders(),
    credentials: 'include'
  })
  return parseResponse<AnalysisTaskCreateResponse>(response)
}

export async function getAnalysisTask(taskId: string): Promise<AnalysisTaskStatusResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/tasks/${taskId}`, {
    headers: authHeaders(),
    credentials: 'include'
  })
  return parseResponse<AnalysisTaskStatusResponse>(response)
}

export async function getRun(runId: string): Promise<AnalysisRunStatusResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/runs/${runId}`, {
    headers: authHeaders(),
    credentials: 'include'
  })
  return parseResponse<AnalysisRunStatusResponse>(response)
}

export async function getUnifiedReport(runId: string): Promise<UnifiedReportResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/runs/${runId}/report`, {
    headers: authHeaders(),
    credentials: 'include'
  })
  return parseResponse<UnifiedReportResponse>(response)
}

export async function getUnifiedReportMarkdown(runId: string): Promise<string> {
  const response = await fetchWithRetry(`${baseUrl}/v1/runs/${runId}/report/markdown`, {
    headers: authHeaders(),
    credentials: 'include'
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(payload.detail || formatApiError(response.status))
  }
  return response.text()
}

export async function previewCnkiFeedbackOcr(file: File): Promise<CnkiFeedbackOcrPreviewResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await fetchWithRetry(`${baseUrl}/v1/cnki-feedback/ocr-preview`, {
    method: 'POST',
    headers: authHeaders(),
    credentials: 'include',
    body: formData
  })
  return parseResponse<CnkiFeedbackOcrPreviewResponse>(response)
}

export async function submitCnkiFeedback(payload: {
  documentId: string
  predictedRunId?: string
  cnkiDupPercent?: number | null
  cnkiAigcPercent?: number | null
  reportDate?: string
  notes?: string
  removeReferenceDupPercent?: number | null
  singleMaxDupPercent?: number | null
  suspectedPlagiarism?: Record<string, number> | null
  fragments?: CnkiReportFragment[] | null
  learningConsent?: boolean
  learningScope?: LearningScope
  evidenceFile?: File | null
}): Promise<CnkiFeedbackResponse> {
  const formData = new FormData()
  formData.append('document_id', payload.documentId)
  if (payload.predictedRunId) formData.append('predicted_run_id', payload.predictedRunId)
  if (typeof payload.cnkiDupPercent === 'number') formData.append('cnki_dup_percent', String(payload.cnkiDupPercent))
  if (typeof payload.cnkiAigcPercent === 'number') formData.append('cnki_aigc_percent', String(payload.cnkiAigcPercent))
  if (payload.reportDate) formData.append('report_date', payload.reportDate)
  if (payload.notes) formData.append('notes', payload.notes)
  if (typeof payload.removeReferenceDupPercent === 'number') formData.append('remove_reference_dup_percent', String(payload.removeReferenceDupPercent))
  if (typeof payload.singleMaxDupPercent === 'number') formData.append('single_max_dup_percent', String(payload.singleMaxDupPercent))
  if (payload.suspectedPlagiarism) formData.append('suspected_plagiarism_json', JSON.stringify(payload.suspectedPlagiarism))
  if (payload.fragments) formData.append('fragments_json', JSON.stringify(payload.fragments))
  const learningScope = payload.learningScope || (payload.learningConsent ? 'anonymous_global' : 'none')
  formData.append('learning_scope', learningScope)
  formData.append('learning_consent', String(learningScope === 'anonymous_global'))
  if (payload.evidenceFile) formData.append('evidence_file', payload.evidenceFile)

  const response = await fetchWithRetry(`${baseUrl}/v1/cnki-feedback`, {
    method: 'POST',
    headers: authHeaders(),
    credentials: 'include',
    body: formData
  })
  return parseResponse<CnkiFeedbackResponse>(response)
}

export async function importManualProviderResult(payload: {
  documentId: string
  runId: string
  provider: 'wanfang' | 'vip' | 'turnitin' | 'manual'
  duplicationPercent?: number | null
  aigcPercent?: number | null
  confidence?: number | null
  version?: string
  notes?: string
  rawPayload?: Record<string, unknown>
}): Promise<ProviderResultImportResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/provider-results/manual`, {
    method: 'POST',
    headers: jsonHeaders(true),
    credentials: 'include',
    body: JSON.stringify({
      document_id: payload.documentId,
      run_id: payload.runId,
      provider: payload.provider,
      duplication_percent: payload.duplicationPercent ?? null,
      aigc_percent: payload.aigcPercent ?? null,
      confidence: payload.confidence ?? null,
      version: payload.version || null,
      notes: payload.notes || null,
      raw_payload: payload.rawPayload || {}
    })
  })
  return parseResponse<ProviderResultImportResponse>(response)
}

export async function fetchProviderResult(payload: {
  documentId: string
  runId: string
  provider: 'wanfang' | 'vip' | 'turnitin' | 'manual'
  extraPayload?: Record<string, unknown>
}): Promise<ProviderFetchResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/provider-results/fetch`, {
    method: 'POST',
    headers: jsonHeaders(true),
    credentials: 'include',
    body: JSON.stringify({
      document_id: payload.documentId,
      run_id: payload.runId,
      provider: payload.provider,
      extra_payload: payload.extraPayload || {}
    })
  })
  return parseResponse<ProviderFetchResponse>(response)
}

export async function getProviderCatalog(): Promise<ProviderCatalogResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/providers`, {
    headers: authHeaders(),
    credentials: 'include'
  })
  return parseResponse<ProviderCatalogResponse>(response)
}

export async function getProviderConfigs(): Promise<ProviderConfigListResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/providers/config`, {
    headers: authHeaders(),
    credentials: 'include'
  })
  return parseResponse<ProviderConfigListResponse>(response)
}

export async function saveProviderConfig(
  provider: string,
  payload: {
    mode: 'http' | 'file'
    method?: string
    url?: string
    path?: string
    authType?: string
    tokenEnv?: string
    version?: string
    timeoutSeconds?: number | null
    headers?: Record<string, string>
    fieldMap?: Record<string, string>
  }
): Promise<ProviderConfigDetail> {
  const response = await fetchWithRetry(`${baseUrl}/v1/providers/config/${provider}`, {
    method: 'PUT',
    headers: jsonHeaders(true),
    credentials: 'include',
    body: JSON.stringify({
      mode: payload.mode,
      method: payload.method || null,
      url: payload.url || null,
      path: payload.path || null,
      auth_type: payload.authType || null,
      token_env: payload.tokenEnv || null,
      version: payload.version || null,
      timeout_seconds: payload.timeoutSeconds ?? null,
      headers: payload.headers || {},
      field_map: payload.fieldMap || {}
    })
  })
  return parseResponse<ProviderConfigDetail>(response)
}

export async function resetProviderConfig(provider: string): Promise<ProviderConfigDetail> {
  const response = await fetchWithRetry(`${baseUrl}/v1/providers/config/${provider}`, {
    method: 'DELETE',
    headers: authHeaders(),
    credentials: 'include'
  })
  return parseResponse<ProviderConfigDetail>(response)
}

export async function getModelStatus(): Promise<ModelStatusResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/models/status`, {
    headers: authHeaders(),
    credentials: 'include'
  })
  return parseResponse<ModelStatusResponse>(response)
}

export async function trainProxyModels(payload?: {
  modelType?: 'cnki_dup_proxy' | 'cnki_aigc_proxy' | 'both'
  sceneKey?: string
  activate?: boolean
  minSamples?: number
}): Promise<ProxyModelTrainResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/models/train-proxy`, {
    method: 'POST',
    headers: jsonHeaders(true),
    credentials: 'include',
    body: JSON.stringify({
      model_type: payload?.modelType || 'both',
      scene_key: payload?.sceneKey || null,
      activate: payload?.activate ?? true,
      min_samples: payload?.minSamples || null
    })
  })
  return parseResponse<ProxyModelTrainResponse>(response)
}

export async function getRewriteAdvice(runId: string, sectionIndex: number): Promise<RewriteAdviceResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/runs/${runId}/sections/${sectionIndex}/rewrite-advice`, {
    method: 'POST',
    headers: authHeaders(),
    credentials: 'include'
  })
  return parseResponse<RewriteAdviceResponse>(response)
}

export async function quickRewrite(payload: {
  text: string
  mode?: QuickRewriteMode
}): Promise<QuickRewriteResult> {
  const response = await fetchWithRetry(`${baseUrl}/api/quick-rewrite`, {
    method: 'POST',
    headers: jsonHeaders(true),
    credentials: 'include',
    body: JSON.stringify({
      text: payload.text,
      mode: payload.mode || 'auto'
    })
  })
  return parseResponse<QuickRewriteResult>(response)
}

export async function getRunSections(runId: string): Promise<RunSectionItem[]> {
  const response = await fetchWithRetry(`${baseUrl}/v1/runs/${runId}/sections`, {
    headers: authHeaders(),
    credentials: 'include'
  })
  return parseResponse<RunSectionItem[]>(response)
}

export async function reanalyzeRun(
  runId: string,
  sections: { section_index: number; content: string }[]
): Promise<ReanalyzeResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/runs/${runId}/reanalyze`, {
    method: 'POST',
    headers: jsonHeaders(true),
    credentials: 'include',
    body: JSON.stringify({ sections })
  })
  return parseResponse<ReanalyzeResponse>(response)
}

export async function exportRun(
  runId: string,
  sections: { section_index: number; content: string; risk_level?: string }[],
  format: 'docx' | 'txt' = 'docx'
): Promise<{ blob: Blob; patchStats?: Record<string, number> }> {
  const response = await fetchWithRetry(`${baseUrl}/v1/runs/${runId}/export`, {
    method: 'POST',
    headers: jsonHeaders(true),
    credentials: 'include',
    body: JSON.stringify({ sections, format })
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    const detail = payload.detail
    if (typeof detail === 'string') {
      throw new Error(detail)
    }
    if (detail?.message) {
      const firstFailure = Array.isArray(detail.failures) && detail.failures.length
        ? `（${detail.failures[0].reason}）`
        : ''
      throw new Error(`${detail.message}${firstFailure}`)
    }
    throw new Error(formatApiError(response.status))
  }
  const patchStats = {
    requested: Number(response.headers.get('X-PataFix-Patch-Requested') || 0),
    applied: Number(response.headers.get('X-PataFix-Patch-Applied') || 0),
    failed: Number(response.headers.get('X-PataFix-Patch-Failed') || 0),
    skipped: Number(response.headers.get('X-PataFix-Patch-Skipped') || 0),
    highlighted: Number(response.headers.get('X-PataFix-Patch-Highlighted') || 0),
  }
  return {
    blob: await response.blob(),
    patchStats: response.headers.has('X-PataFix-Patch-Requested') ? patchStats : undefined,
  }
}

export async function getRunBlocks(runId: string): Promise<{
  blocks: DocumentBlock[]
  reportSummary?: OfficialReportSummary | null
  unmatchedSpans?: OfficialRiskSpan[]
}> {
  const response = await fetchWithRetry(`${baseUrl}/v1/runs/${runId}/blocks`, {
    headers: authHeaders(),
    credentials: 'include'
  })
  const payload = await parseResponse<{
    blocks: any[]
    reportSummary?: OfficialReportSummary | null
    unmatchedSpans?: any[]
    unmatched_spans?: any[]
  }>(response)
  return {
    ...payload,
    blocks: (payload.blocks || []).map(normalizeDocumentBlock),
    unmatchedSpans: (payload.unmatchedSpans || payload.unmatched_spans || []).map(normalizeOfficialRiskSpan)
  }
}

export async function getRewriteWorkspace(runId: string): Promise<RewriteWorkspaceResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/runs/${runId}/workspace`, {
    headers: authHeaders(),
    credentials: 'include'
  })
  const payload = await parseResponse<any>(response)
  return normalizeRewriteWorkspace(payload)
}

function normalizeOfficialRiskSpan(span: any): OfficialRiskSpan {
  return {
    spanId: span.spanId ?? span.span_id,
    text: span.text || '',
    riskType: span.riskType ?? span.risk_type,
    riskLevel: span.riskLevel ?? span.risk_level,
    similarity: span.similarity ?? undefined,
    aigcScore: span.aigcScore ?? span.aigc_score ?? undefined,
    matchedSource: span.matchedSource ?? span.matched_source ?? undefined,
    pageNumber: span.pageNumber ?? span.page_number ?? undefined,
  }
}

function normalizeDocumentBlock(block: any): DocumentBlock {
  const reportRisk = block.reportRisk || block.report_risk
  const internalRisk = block.internalRisk || block.internal_risk
  return {
    blockId: block.blockId ?? block.block_id,
    type: block.type ?? block.blockType ?? block.block_type,
    text: block.text || '',
    html: block.html ?? undefined,
    effectiveText: block.effectiveText ?? block.effective_text ?? undefined,
    riskScore: block.riskScore ?? block.risk_score ?? undefined,
    reportRisk: reportRisk ? {
      source: reportRisk.source || 'cnki',
      riskType: reportRisk.riskType ?? reportRisk.risk_type,
      riskLevel: reportRisk.riskLevel ?? reportRisk.risk_level,
      similarity: reportRisk.similarity ?? undefined,
      aigcScore: reportRisk.aigcScore ?? reportRisk.aigc_score ?? undefined,
      matchedSource: reportRisk.matchedSource ?? reportRisk.matched_source ?? undefined,
      spanId: reportRisk.spanId ?? reportRisk.span_id,
      matchConfidence: reportRisk.matchConfidence ?? reportRisk.match_confidence ?? 0
    } : undefined,
    internalRisk: internalRisk ? {
      overallRisk: internalRisk.overallRisk ?? internalRisk.overall_risk ?? 0,
      aiLikelihood: internalRisk.aiLikelihood ?? internalRisk.ai_likelihood ?? undefined,
      templateScore: internalRisk.templateScore ?? internalRisk.template_score ?? undefined,
      semanticEmptyScore: internalRisk.semanticEmptyScore ?? internalRisk.semantic_empty_score ?? undefined,
      repetitionScore: internalRisk.repetitionScore ?? internalRisk.repetition_score ?? undefined,
      citationRisk: internalRisk.citationRisk ?? internalRisk.citation_risk ?? undefined,
      reasons: internalRisk.reasons || []
    } : undefined,
    rewriteStatus: block.rewriteStatus ?? block.rewrite_status ?? 'none',
    sourceType: block.sourceType ?? block.source_type,
    sourceMap: block.sourceMap ?? block.source_map ?? undefined,
    sectionTitle: block.sectionTitle ?? block.section_title ?? undefined,
    sectionType: block.sectionType ?? block.section_type ?? undefined,
    charCount: block.charCount ?? block.char_count ?? 0,
    displayOrder: block.displayOrder ?? block.display_order ?? 0,
  }
}

function normalizeRewriteWorkspace(payload: any): RewriteWorkspaceResponse {
  return {
    runId: payload.runId ?? payload.run_id,
    documentId: payload.documentId ?? payload.document_id,
    title: payload.title ?? null,
    filename: payload.filename || '',
    mode: payload.mode || 'estimate',
    sourceFormat: payload.sourceFormat ?? payload.source_format ?? null,
    warnings: payload.warnings || [],
    metrics: {
      currentAigcPercent: payload.metrics?.currentAigcPercent ?? payload.metrics?.current_aigc_percent ?? 0,
      estimatedOptimizedPercent: payload.metrics?.estimatedOptimizedPercent ?? payload.metrics?.estimated_optimized_percent ?? 0,
      rewrittenCount: payload.metrics?.rewrittenCount ?? payload.metrics?.rewritten_count ?? 0,
      ignoredCount: payload.metrics?.ignoredCount ?? payload.metrics?.ignored_count ?? 0,
      totalRiskCount: payload.metrics?.totalRiskCount ?? payload.metrics?.total_risk_count ?? 0,
      highCount: payload.metrics?.highCount ?? payload.metrics?.high_count ?? 0,
      mediumCount: payload.metrics?.mediumCount ?? payload.metrics?.medium_count ?? 0,
      lowCount: payload.metrics?.lowCount ?? payload.metrics?.low_count ?? 0,
    },
    sections: (payload.sections || []).map((section: any) => ({
      sectionId: section.sectionId ?? section.section_id,
      sectionIndex: section.sectionIndex ?? section.section_index ?? 0,
      paragraphIndex: section.paragraphIndex ?? section.paragraph_index ?? null,
      title: section.title || '',
      riskLevel: section.riskLevel ?? section.risk_level ?? 'normal',
      itemIds: section.itemIds ?? section.item_ids ?? [],
      itemCount: section.itemCount ?? section.item_count ?? 0,
      riskCounts: {
        high: section.riskCounts?.high ?? section.risk_counts?.high ?? 0,
        medium: section.riskCounts?.medium ?? section.risk_counts?.medium ?? 0,
        low: section.riskCounts?.low ?? section.risk_counts?.low ?? 0,
        normal: section.riskCounts?.normal ?? section.risk_counts?.normal ?? 0,
      }
    })),
    riskItems: (payload.riskItems || payload.risk_items || []).map((item: any) => ({
      riskId: item.riskId ?? item.risk_id,
      blockId: item.blockId ?? item.block_id,
      sectionId: item.sectionId ?? item.section_id,
      sectionIndex: item.sectionIndex ?? item.section_index ?? 0,
      paragraphIndex: item.paragraphIndex ?? item.paragraph_index ?? null,
      sectionTitle: item.sectionTitle ?? item.section_title ?? null,
      displayOrder: item.displayOrder ?? item.display_order ?? 0,
      originalText: item.originalText ?? item.original_text ?? '',
      currentText: item.currentText ?? item.current_text ?? '',
      riskLevel: item.riskLevel ?? item.risk_level ?? 'normal',
      aigcScore: item.aigcScore ?? item.aigc_score ?? 0,
      diagnosis: item.diagnosis || '',
      rewriteHint: item.rewriteHint ?? item.rewrite_hint ?? '',
      principle: item.principle || '',
      reasons: item.reasons || [],
      status: item.status || 'pending',
      highlights: (item.highlights || []).map((highlight: any) => ({
        text: highlight.text || '',
        riskLevel: highlight.riskLevel ?? highlight.risk_level ?? 'normal',
      })),
      sourceMap: item.sourceMap ?? item.source_map ?? undefined,
    })),
  }
}

export async function uploadDocumentWithReport(payload: {
  file: File
  reportFile: File
  title?: string
  subject?: string
  degreeLevel?: string
  learningConsent?: boolean
  learningScope?: LearningScope
  onProgress?: (percent: number) => void
}): Promise<{
  fileId: string
  runId: string
  reportMode: boolean
  reportSummary: OfficialReportSummary & {
    reportId: string
  }
  blocks: DocumentBlock[]
  unmatchedRiskSpans: OfficialRiskSpan[]
}> {
  const formData = new FormData()
  formData.append('file', payload.file)
  formData.append('report_file', payload.reportFile)
  if (payload.title) formData.append('title', payload.title)
  if (payload.subject) formData.append('subject', payload.subject)
  if (payload.degreeLevel) formData.append('degree_level', payload.degreeLevel)
  const learningScope = payload.learningScope || (payload.learningConsent ? 'anonymous_global' : 'none')
  formData.append('learning_scope', learningScope)
  formData.append('learning_consent', String(learningScope === 'anonymous_global'))

  if (payload.onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      xhr.open('POST', `${baseUrl}/v1/documents/upload-with-report`)
      xhr.withCredentials = true
      xhr.timeout = 300000
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          payload.onProgress!(Math.round((event.loaded / event.total) * 100))
        }
      }
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          const result = JSON.parse(xhr.responseText)
          resolve(normalizeUploadWithReportResponse(result))
        } else {
          let detail = formatApiError(xhr.status)
          try {
            const body = JSON.parse(xhr.responseText)
            detail = body.detail || detail
          } catch { /* ignore */ }
          reject(new Error(detail))
        }
      }
      xhr.onerror = () => reject(new Error('无法连接到分析服务，请确认本地后端已启动且前端代理已连通'))
      xhr.ontimeout = () => reject(new Error('处理超时：文档或报告较大，请稍后重试'))
      xhr.send(formData)
    })
  }

  const response = await fetchWithRetry(`${baseUrl}/v1/documents/upload-with-report`, {
    method: 'POST',
    headers: authHeaders(),
    credentials: 'include',
    body: formData
  })
  const result = await parseResponse<any>(response)
  return normalizeUploadWithReportResponse(result)
}

function normalizeUploadWithReportResponse(result: any): {
  fileId: string
  runId: string
  reportMode: boolean
  reportSummary: OfficialReportSummary & {
    reportId: string
  }
  blocks: DocumentBlock[]
  unmatchedRiskSpans: OfficialRiskSpan[]
} {
  const summary = result.reportSummary || result.report_summary || {}
  return {
    fileId: result.fileId ?? result.file_id,
    runId: result.runId ?? result.run_id,
    reportMode: result.reportMode ?? result.report_mode ?? true,
    reportSummary: {
      reportId: summary.reportId ?? summary.report_id,
      reportType: summary.reportType ?? summary.report_type,
      totalCopyRatio: summary.totalCopyRatio ?? summary.total_copy_ratio ?? null,
      aigcRatio: summary.aigcRatio ?? summary.aigc_ratio ?? null,
      highRiskCount: summary.highRiskCount ?? summary.high_risk_count ?? 0,
      mediumRiskCount: summary.mediumRiskCount ?? summary.medium_risk_count ?? 0,
      lowRiskCount: summary.lowRiskCount ?? summary.low_risk_count ?? 0,
      unmatchedCount: summary.unmatchedCount ?? summary.unmatched_count ?? 0,
    },
    blocks: (result.blocks || []).map(normalizeDocumentBlock),
    unmatchedRiskSpans: (result.unmatchedRiskSpans || result.unmatched_risk_spans || []).map(normalizeOfficialRiskSpan),
  }
}

export async function attachReportToDocument(documentId: string, reportFile: File, learningScope: LearningScope = 'none'): Promise<{
  reportId: string
  mappedCount: number
  unmatchedCount: number
  unmatchedSpans: OfficialRiskSpan[]
}> {
  const formData = new FormData()
  formData.append('report_file', reportFile)
  formData.append('learning_scope', learningScope)
  formData.append('learning_consent', String(learningScope === 'anonymous_global'))
  const response = await fetchWithRetry(`${baseUrl}/v1/documents/${documentId}/report`, {
    method: 'POST',
    headers: authHeaders(),
    credentials: 'include',
    body: formData
  })
  const result = await parseResponse<any>(response)
  return {
    ...result,
    reportId: result.reportId ?? result.report_id,
    mappedCount: result.mappedCount ?? result.mapped_count,
    unmatchedCount: result.unmatchedCount ?? result.unmatched_count,
    unmatchedSpans: (result.unmatchedSpans || result.unmatched_spans || []).map(normalizeOfficialRiskSpan)
  }
}

export async function remapReport(documentId: string): Promise<{
  mappedCount: number
  unmatchedCount: number
  unmatchedSpans: OfficialRiskSpan[]
}> {
  const response = await fetchWithRetry(`${baseUrl}/v1/documents/${documentId}/remap-report`, {
    method: 'POST',
    headers: authHeaders(),
    credentials: 'include'
  })
  const result = await parseResponse<any>(response)
  return {
    ...result,
    mappedCount: result.mappedCount ?? result.mapped_count,
    unmatchedCount: result.unmatchedCount ?? result.unmatched_count,
    unmatchedSpans: (result.unmatchedSpans || result.unmatched_spans || []).map(normalizeOfficialRiskSpan)
  }
}

export async function bindReportSpan(
  runId: string,
  payload: { spanId: string; blockId: string }
): Promise<{
  reportId: string
  spanId: string
  blockId: string
  mappedCount: number
  unmatchedCount: number
  unmatchedSpans: OfficialRiskSpan[]
  block: DocumentBlock
}> {
  const response = await fetchWithRetry(`${baseUrl}/v1/runs/${runId}/report-spans/bind`, {
    method: 'POST',
    headers: jsonHeaders(true),
    credentials: 'include',
    body: JSON.stringify({
      span_id: payload.spanId,
      block_id: payload.blockId,
    })
  })
  const result = await parseResponse<any>(response)
  return {
    ...result,
    reportId: result.reportId ?? result.report_id,
    spanId: result.spanId ?? result.span_id,
    blockId: result.blockId ?? result.block_id,
    mappedCount: result.mappedCount ?? result.mapped_count,
    unmatchedCount: result.unmatchedCount ?? result.unmatched_count,
    unmatchedSpans: (result.unmatchedSpans || result.unmatched_spans || []).map(normalizeOfficialRiskSpan),
    block: normalizeDocumentBlock(result.block),
  }
}

export async function createPatch(
  runId: string,
  payload: { block_id: string; old_text: string; new_text: string; source_map?: Record<string, any> }
): Promise<DocumentPatch> {
  const response = await fetchWithRetry(`${baseUrl}/v1/runs/${runId}/patches`, {
    method: 'POST',
    headers: jsonHeaders(true),
    credentials: 'include',
    body: JSON.stringify(payload)
  })
  return parseResponse<DocumentPatch>(response)
}

export async function listPatches(runId: string): Promise<DocumentPatch[]> {
  const response = await fetchWithRetry(`${baseUrl}/v1/runs/${runId}/patches`, {
    headers: authHeaders(),
    credentials: 'include'
  })
  return parseResponse<DocumentPatch[]>(response)
}

export async function getOnlyOfficeConfig(runId: string): Promise<OnlyOfficeConfigResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/runs/${runId}/onlyoffice/config`, {
    headers: authHeaders(),
    credentials: 'include'
  })
  return parseResponse<OnlyOfficeConfigResponse>(response)
}

export async function applyOnlyOfficePatches(
  runId: string,
  payload?: { blockId?: string }
): Promise<OnlyOfficeApplyResponse> {
  const response = await fetchWithRetry(`${baseUrl}/v1/runs/${runId}/onlyoffice/apply-patches`, {
    method: 'POST',
    headers: jsonHeaders(true),
    credentials: 'include',
    body: JSON.stringify(payload?.blockId ? { block_id: payload.blockId } : {})
  })
  return parseResponse<OnlyOfficeApplyResponse>(response)
}

export function getOnlyOfficeDownloadUrl(runId: string, variant: 'original' | 'edited' = 'edited'): string {
  return `${baseUrl}/v1/runs/${runId}/onlyoffice/download?variant=${variant}`
}

export function getOriginalDocumentUrl(documentId: string): string {
  return `${baseUrl}/v1/documents/${documentId}/original`
}

export async function getOriginalDocumentBlob(documentId: string): Promise<Blob> {
  const response = await fetchWithRetry(getOriginalDocumentUrl(documentId), {
    headers: authHeaders(),
    credentials: 'include'
  })
  if (!response.ok) {
    throw new Error(formatApiError(response.status))
  }
  return response.blob()
}

export async function getUnlockPackages(): Promise<UnlockPackage[]> {
  const response = await fetchWithRetry(`${baseUrl}/v1/unlocks/packages`, {
    headers: authHeaders(),
    credentials: 'include'
  })
  return parseResponse<UnlockPackage[]>(response)
}

export async function createUnlockOrder(runId: string, packageCode: string): Promise<UnlockOrder> {
  const formData = new FormData()
  formData.append('package_code', packageCode)
  const response = await fetchWithRetry(`${baseUrl}/v1/unlocks/runs/${runId}/orders`, {
    method: 'POST',
    headers: authHeaders(),
    credentials: 'include',
    body: formData
  })
  return parseResponse<UnlockOrder>(response)
}

export async function getUnlockStatus(runId: string, packageCode?: string): Promise<UnlockStatus> {
  const params = packageCode ? `?package_code=${encodeURIComponent(packageCode)}` : ''
  const response = await fetchWithRetry(`${baseUrl}/v1/unlocks/runs/${runId}/status${params}`, {
    headers: authHeaders(),
    credentials: 'include'
  })
  return parseResponse<UnlockStatus>(response)
}

export async function uploadUnlockScreenshot(
  runId: string,
  orderNo: string,
  file: File,
  paymentMethod: 'alipay' | 'wechat'
): Promise<UnlockOrder> {
  const formData = new FormData()
  formData.append('payment_method', paymentMethod)
  formData.append('screenshot', file)
  const response = await fetchWithRetry(
    `${baseUrl}/v1/unlocks/runs/${runId}/orders/${orderNo}/screenshot`,
    {
      method: 'POST',
      headers: authHeaders(),
      credentials: 'include',
      body: formData
    }
  )
  return parseResponse<UnlockOrder>(response)
}

function authHeaders() {
  return new Headers()
}

function jsonHeaders(includeAuth = false) {
  const headers = new Headers()
  headers.set('Content-Type', 'application/json')
  return headers
}

function parseDownloadFilename(contentDisposition: string | null): string | null {
  if (!contentDisposition) return null
  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1])
    } catch {
      return utf8Match[1]
    }
  }
  const asciiMatch = contentDisposition.match(/filename="?([^";]+)"?/i)
  return asciiMatch?.[1] || null
}

function toDocxName(filename: string): string {
  const stem = filename.replace(/\.[^.]+$/, '') || 'converted'
  return `${stem}.docx`
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(formatApiError(response.status, payload.detail))
  }
  return response.json() as Promise<T>
}

function formatApiError(status: number, detail?: unknown) {
  if (typeof detail === 'string' && detail.trim()) return detail
  if (status >= 500) return '服务暂时不可用，请确认本地后端已启动后再试'
  if (status === 401) return '请先登录后再继续'
  if (status === 403) return '当前账号暂时无权限执行该操作'
  if (status === 404) return '没有找到对应的数据'
  return `请求失败：${status}`
}


