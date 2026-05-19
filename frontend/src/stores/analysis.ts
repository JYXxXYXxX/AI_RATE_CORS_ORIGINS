import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  uploadDocument,
  uploadDocumentWithReport,
  analyzeDocumentAsync,
  getAnalysisTask,
  getRun,
  getUnifiedReport,
  submitCnkiFeedback,
  getBillingSummary
} from '../api'
import type {
  DocumentUploadResponse,
  AnalysisTaskStatusResponse,
  AnalysisRunStatusResponse,
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

export const useAnalysisStore = defineStore('analysis', () => {
  const submitting = ref(false)
  const uploadProgress = ref(0)
  const taskStatus = ref<AnalysisTaskStatusResponse | null>(null)
  const runStatus = ref<AnalysisRunStatusResponse | null>(null)
  const report = ref<UnifiedReportResponse | null>(null)
  const error = ref('')
  const history = ref<RecentAnalysisTaskSummary[]>([])

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

    try {
      uploadProgress.value = 0

      // 如果用户上传了知网报告，走报告驱动模式
      if (payload.cnkiReport?.file) {
        const result = await uploadDocumentWithReport({
          file: payload.file,
          reportFile: payload.cnkiReport.file,
          title: payload.title,
          subject: payload.subject,
          degreeLevel: payload.degreeLevel,
          learningScope: payload.cnkiReport.learningScope,
          learningConsent: payload.cnkiReport.learningConsent === true,
          onProgress: (percent) => { uploadProgress.value = percent }
        })
        uploadProgress.value = 100
        runStatus.value = await getRun(result.runId)
        await refreshHistory()
        return result.runId
      }

      // 否则走系统自检模式
      const uploadResult = await uploadDocument({
        file: payload.file,
        title: payload.title,
        subject: payload.subject,
        degreeLevel: payload.degreeLevel,
        onProgress: (percent) => { uploadProgress.value = percent }
      })
      uploadProgress.value = 100
      const task = await analyzeDocumentAsync(uploadResult.document_id)
      const finished = await pollTask(task.task_id)

      if (!finished.run_id) throw new Error('分析完成但未返回 run_id')

      runStatus.value = await getRun(finished.run_id)
      report.value = await getUnifiedReport(finished.run_id)

      await refreshHistory()

      return finished.run_id
    } catch (err) {
      error.value = err instanceof Error ? err.message : '分析失败'
      return null
    } finally {
      submitting.value = false
      uploadProgress.value = 0
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
    const MAX_ATTEMPTS = 240
    for (let i = 0; i < MAX_ATTEMPTS; i++) {
      const task = await getAnalysisTask(taskId)
      taskStatus.value = task
      if (task.status === 'completed') return task
      if (task.status === 'failed') throw new Error(task.error_message || '分析失败')
      await new Promise((r) => setTimeout(r, Math.min(800 + i * 50, 3000)))
    }
    throw new Error('分析超时')
  }

  function clearCurrent() {
    report.value = null
    runStatus.value = null
    taskStatus.value = null
    error.value = ''
  }

  function resetSubmissionState() {
    submitting.value = false
    uploadProgress.value = 0
    taskStatus.value = null
    error.value = ''
  }

  return { submitting, uploadProgress, taskStatus, runStatus, report, error, history, startAnalysis, loadReport, clearCurrent, resetSubmissionState, refreshHistory }
})
