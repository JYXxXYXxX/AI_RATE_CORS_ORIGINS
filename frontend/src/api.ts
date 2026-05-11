import type {
  AnalysisRunStatusResponse,
  AnalysisTaskCreateResponse,
  AnalysisTaskStatusResponse,
  AnalyzeDocumentResponse,
  AuthSessionResponse,
  BillingOrderDetailResponse,
  BillingOrderPaymentResponse,
  BillingSummaryResponse,
  CnkiFeedbackOcrPreviewResponse,
  CnkiFeedbackResponse,
  CnkiReportFragment,
  DocumentBlock,
  DocumentPatch,
  DocumentUploadResponse,
  ModelStatusResponse,
  ProviderCatalogResponse,
  ProviderConfigDetail,
  ProviderConfigListResponse,
  ProviderFetchResponse,
  ProviderResultImportResponse,
  ProxyModelTrainResponse,
  ReanalyzeResponse,
  RewriteAdviceResponse,
  RunSectionItem,
  UnifiedReportResponse,
  UserSummary
} from './types'

const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
const MAX_RETRIES = 3
const RETRY_DELAY_MS = 500

async function fetchWithRetry(
  url: string,
  options: RequestInit,
  retries = MAX_RETRIES
): Promise<Response> {
  try {
    const response = await fetch(url, options)
    // 只重试服务端错误或网络错误（无响应）
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
          let detail = `请求失败：${xhr.status}`
          try {
            const body = JSON.parse(xhr.responseText)
            detail = body.detail || detail
          } catch { /* ignore */ }
          reject(new Error(detail))
        }
      }
      xhr.onerror = () => reject(new Error('网络请求失败'))
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
    throw new Error(payload.detail || `请求失败：${response.status}`)
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
): Promise<Blob> {
  const response = await fetchWithRetry(`${baseUrl}/v1/runs/${runId}/export`, {
    method: 'POST',
    headers: jsonHeaders(true),
    credentials: 'include',
    body: JSON.stringify({ sections, format })
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(payload.detail || `请求失败：${response.status}`)
  }
  return response.blob()
}

export async function getRunBlocks(runId: string): Promise<{ blocks: DocumentBlock[] }> {
  const response = await fetchWithRetry(`${baseUrl}/v1/runs/${runId}/blocks`, {
    headers: authHeaders(),
    credentials: 'include'
  })
  return parseResponse<{ blocks: DocumentBlock[] }>(response)
}

export async function uploadDocumentWithReport(payload: {
  file: File
  reportFile: File
  title?: string
  subject?: string
  degreeLevel?: string
  onProgress?: (percent: number) => void
}): Promise<{
  fileId: string
  runId: string
  reportMode: boolean
  reportSummary: {
    reportId: string
    reportType: 'similarity' | 'aigc' | 'mixed'
    totalCopyRatio?: number
    aigcRatio?: number
    highRiskCount: number
    mediumRiskCount: number
    lowRiskCount: number
    unmatchedCount: number
  }
  blocks: DocumentBlock[]
  unmatchedRiskSpans: Array<{
    spanId: string
    text: string
    riskType: 'similarity' | 'aigc'
    riskLevel: 'high' | 'medium' | 'low'
    similarity?: number
    aigcScore?: number
    matchedSource?: string
    pageNumber?: number
  }>
}> {
  const formData = new FormData()
  formData.append('file', payload.file)
  formData.append('report_file', payload.reportFile)
  if (payload.title) formData.append('title', payload.title)
  if (payload.subject) formData.append('subject', payload.subject)
  if (payload.degreeLevel) formData.append('degree_level', payload.degreeLevel)

  if (payload.onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      xhr.open('POST', `${baseUrl}/v1/documents/upload-with-report`)
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
          let detail = `请求失败：${xhr.status}`
          try {
            const body = JSON.parse(xhr.responseText)
            detail = body.detail || detail
          } catch { /* ignore */ }
          reject(new Error(detail))
        }
      }
      xhr.onerror = () => reject(new Error('网络请求失败'))
      xhr.send(formData)
    })
  }

  const response = await fetchWithRetry(`${baseUrl}/v1/documents/upload-with-report`, {
    method: 'POST',
    headers: authHeaders(),
    credentials: 'include',
    body: formData
  })
  return parseResponse(response)
}

export async function attachReportToDocument(documentId: string, reportFile: File): Promise<{
  reportId: string
  mappedCount: number
  unmatchedCount: number
  unmatchedSpans: Array<{
    spanId: string
    text: string
    riskType: 'similarity' | 'aigc'
    riskLevel: 'high' | 'medium' | 'low'
    similarity?: number
    aigcScore?: number
    matchedSource?: string
    pageNumber?: number
  }>
}> {
  const formData = new FormData()
  formData.append('report_file', reportFile)
  const response = await fetchWithRetry(`${baseUrl}/v1/documents/${documentId}/report`, {
    method: 'POST',
    headers: authHeaders(),
    credentials: 'include',
    body: formData
  })
  return parseResponse(response)
}

export async function remapReport(documentId: string): Promise<{
  mappedCount: number
  unmatchedCount: number
  unmatchedSpans: Array<{
    spanId: string
    text: string
    riskType: 'similarity' | 'aigc'
    riskLevel: 'high' | 'medium' | 'low'
    similarity?: number
    aigcScore?: number
    matchedSource?: string
    pageNumber?: number
  }>
}> {
  const response = await fetchWithRetry(`${baseUrl}/v1/documents/${documentId}/remap-report`, {
    method: 'POST',
    headers: authHeaders(),
    credentials: 'include'
  })
  return parseResponse(response)
}

export async function createPatch(
  runId: string,
  payload: { block_id: string; old_text: string; new_text: string }
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

function authHeaders() {
  return new Headers()
}

function jsonHeaders(includeAuth = false) {
  const headers = new Headers()
  headers.set('Content-Type', 'application/json')
  return headers
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(payload.detail || `请求失败：${response.status}`)
  }
  return response.json() as Promise<T>
}
