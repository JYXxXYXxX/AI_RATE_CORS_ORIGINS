import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  uploadDocument,
  uploadDocumentWithReport,
  analyzeDocumentAsync,
  getAnalysisTask,
  getRun,
  getUnifiedReport,
  getBillingSummary
} from '../api'
import type {
  AnalysisRunStatusResponse,
  AnalysisTaskStatusResponse,
  UnifiedReportResponse,
  RecentAnalysisTaskSummary,
  LearningScope
} from '../types'

export interface CnkiReportPayload {
  file: File
  cnkiDupPercent: number | null
  cnkiAigcPercent: number | null
  reportDate: string | null
  notes: string | null
  removeReferenceDupPercent?: number | null
  singleMaxDupPercent?: number | null
  suspectedPlagiarism?: Record<string, number> | null
  fragments?: any[] | null
  learningConsent?: boolean
  learningScope?: LearningScope
}

export interface ActiveAnalysisMeta {
  fileName: string
  fileSize: number
  title?: string
  subject?: string
  degreeLevel?: string
  hasCnkiReport: boolean
}

interface PersistedAnalysisState {
  submitting: boolean
  uploadProgress: number
  taskStatus: AnalysisTaskStatusResponse | null
  runStatus: AnalysisRunStatusResponse | null
  error: string
  activeTaskId: string | null
  activeMeta: ActiveAnalysisMeta | null
}

const ACTIVE_ANALYSIS_STORAGE_KEY = 'patafix-active-analysis'

export const useAnalysisStore = defineStore('analysis', () => {
  const submitting = ref(false)
  const uploadProgress = ref(0)
  const taskStatus = ref<AnalysisTaskStatusResponse | null>(null)
  const runStatus = ref<AnalysisRunStatusResponse | null>(null)
  const report = ref<UnifiedReportResponse | null>(null)
  const error = ref('')
  const history = ref<RecentAnalysisTaskSummary[]>([])
  const activeTaskId = ref<string | null>(null)
  const activeMeta = ref<ActiveAnalysisMeta | null>(null)

  let currentPollPromise: Promise<AnalysisTaskStatusResponse> | null = null
  let currentPollingTaskId: string | null = null

  const isAnalysisActive = computed(() => {
    if (submitting.value) return true
    if (uploadProgress.value > 0 && uploadProgress.value < 100) return true
    const status = taskStatus.value?.status
    return status === 'queued' || status === 'processing'
  })

  function persistActiveState() {
    const payload: PersistedAnalysisState = {
      submitting: submitting.value,
      uploadProgress: uploadProgress.value,
      taskStatus: taskStatus.value,
      runStatus: runStatus.value,
      error: error.value,
      activeTaskId: activeTaskId.value,
      activeMeta: activeMeta.value,
    }

    const hasPendingTask = payload.taskStatus != null && ['queued', 'processing'].includes(payload.taskStatus.status)
    if (!payload.submitting && payload.uploadProgress === 0 && !payload.activeTaskId && !payload.activeMeta && !hasPendingTask) {
      localStorage.removeItem(ACTIVE_ANALYSIS_STORAGE_KEY)
      return
    }

    localStorage.setItem(ACTIVE_ANALYSIS_STORAGE_KEY, JSON.stringify(payload))
  }

  function hydrateActiveState() {
    const raw = localStorage.getItem(ACTIVE_ANALYSIS_STORAGE_KEY)
    if (!raw) return

    try {
      const parsed = JSON.parse(raw) as PersistedAnalysisState
      submitting.value = parsed.submitting ?? false
      uploadProgress.value = parsed.uploadProgress ?? 0
      taskStatus.value = parsed.taskStatus ?? null
      runStatus.value = parsed.runStatus ?? null
      error.value = parsed.error ?? ''
      activeTaskId.value = parsed.activeTaskId ?? null
      activeMeta.value = parsed.activeMeta ?? null
    } catch {
      localStorage.removeItem(ACTIVE_ANALYSIS_STORAGE_KEY)
    }
  }

  function rememberActiveMeta(payload: {
    file: File
    title?: string
    subject?: string
    degreeLevel?: string
    cnkiReport?: CnkiReportPayload
  }) {
    activeMeta.value = {
      fileName: payload.file.name,
      fileSize: payload.file.size,
      title: payload.title,
      subject: payload.subject,
      degreeLevel: payload.degreeLevel,
      hasCnkiReport: !!payload.cnkiReport?.file,
    }
    persistActiveState()
  }

  async function refreshHistory() {
    try {
      const billing = await getBillingSummary()
      history.value = billing.recent_tasks || []
    } catch {
      // silently ignore if billing API fails
    }
  }

  async function startAnalysis(payload: {
    file: File
    title?: string
    subject?: string
    degreeLevel?: string
    cnkiReport?: CnkiReportPayload
  }): Promise<string | null> {
    submitting.value = true
    error.value = ''
    report.value = null
    taskStatus.value = null
    runStatus.value = null
    activeTaskId.value = null
    rememberActiveMeta(payload)

    try {
      uploadProgress.value = 0
      persistActiveState()

      if (payload.cnkiReport?.file) {
        const result = await uploadDocumentWithReport({
          file: payload.file,
          reportFile: payload.cnkiReport.file,
          title: payload.title,
          subject: payload.subject,
          degreeLevel: payload.degreeLevel,
          learningScope: payload.cnkiReport.learningScope,
          learningConsent: payload.cnkiReport.learningConsent === true,
          onProgress: (percent) => {
            uploadProgress.value = percent
            persistActiveState()
          }
        })
        uploadProgress.value = 100
        if (!result.runId) throw new Error('报告驱动分析已返回，但缺少 run_id')
        runStatus.value = await getRun(result.runId)
        activeMeta.value = null
        persistActiveState()
        await refreshHistory()
        return result.runId
      }

      const uploadResult = await uploadDocument({
        file: payload.file,
        title: payload.title,
        subject: payload.subject,
        degreeLevel: payload.degreeLevel,
        onProgress: (percent) => {
          uploadProgress.value = percent
          persistActiveState()
        }
      })

      uploadProgress.value = 100
      const task = await analyzeDocumentAsync(uploadResult.document_id)
      taskStatus.value = {
        task_id: task.task_id,
        document_id: task.document_id,
        run_id: null,
        title: payload.title || uploadResult.title || null,
        filename: uploadResult.filename || payload.file.name,
        status: task.status,
        stage: 'queued',
        progress: task.progress,
        created_at: task.created_at,
        started_at: null,
        finished_at: null,
        error_message: null,
      }
      activeTaskId.value = task.task_id
      persistActiveState()

      const finished = await pollTask(task.task_id)
      if (!finished.run_id) throw new Error('分析完成但未返回 run_id')

      runStatus.value = await getRun(finished.run_id)
      report.value = await getUnifiedReport(finished.run_id)
      activeTaskId.value = null
      activeMeta.value = null
      persistActiveState()

      await refreshHistory()
      return finished.run_id
    } catch (err) {
      error.value = err instanceof Error ? err.message : '分析失败'
      persistActiveState()
      return null
    } finally {
      submitting.value = false
      uploadProgress.value = 0
      persistActiveState()
    }
  }

  async function loadReport(runId: string) {
    error.value = ''
    try {
      runStatus.value = await getRun(runId)
      report.value = await getUnifiedReport(runId)
    } catch (err) {
      error.value = err instanceof Error ? err.message : '加载报告失败'
    }
  }

  async function pollTask(taskId: string): Promise<AnalysisTaskStatusResponse> {
    if (currentPollPromise && currentPollingTaskId === taskId) {
      return currentPollPromise
    }

    currentPollingTaskId = taskId
    currentPollPromise = (async () => {
      const MAX_ATTEMPTS = 240
      for (let i = 0; i < MAX_ATTEMPTS; i++) {
        const task = await getAnalysisTask(taskId)
        taskStatus.value = task
        activeTaskId.value = task.task_id
        persistActiveState()

        if (task.status === 'completed') return task
        if (task.status === 'failed') throw new Error(task.error_message || '分析失败')

        await new Promise((r) => setTimeout(r, Math.min(800 + i * 50, 3000)))
      }
      throw new Error('分析超时')
    })()

    try {
      return await currentPollPromise
    } finally {
      currentPollPromise = null
      currentPollingTaskId = null
    }
  }

  async function resumeActiveAnalysis() {
    hydrateActiveState()
    const resumableTaskId = activeTaskId.value || taskStatus.value?.task_id || null
    const taskState = taskStatus.value?.status
    if (!resumableTaskId || (taskState !== 'queued' && taskState !== 'processing' && !submitting.value)) {
      return
    }

    submitting.value = true
    persistActiveState()

    try {
      const finished = await pollTask(resumableTaskId)
      if (finished.run_id) {
        runStatus.value = await getRun(finished.run_id)
        report.value = await getUnifiedReport(finished.run_id)
        activeTaskId.value = null
        activeMeta.value = null
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : '分析失败'
    } finally {
      submitting.value = false
      uploadProgress.value = 0
      persistActiveState()
    }
  }

  function clearCurrent() {
    report.value = null
    runStatus.value = null
    taskStatus.value = null
    error.value = ''
    activeTaskId.value = null
    activeMeta.value = null
    persistActiveState()
  }

  function resetSubmissionState() {
    submitting.value = false
    uploadProgress.value = 0
    taskStatus.value = null
    error.value = ''
    activeTaskId.value = null
    activeMeta.value = null
    localStorage.removeItem(ACTIVE_ANALYSIS_STORAGE_KEY)
  }

  hydrateActiveState()

  return {
    submitting,
    uploadProgress,
    taskStatus,
    runStatus,
    report,
    error,
    history,
    activeMeta,
    isAnalysisActive,
    startAnalysis,
    loadReport,
    clearCurrent,
    resetSubmissionState,
    refreshHistory,
    hydrateActiveState,
    resumeActiveAnalysis,
  }
})
