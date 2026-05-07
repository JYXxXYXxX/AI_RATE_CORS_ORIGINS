import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  uploadDocument,
  analyzeDocumentAsync,
  getAnalysisTask,
  getRun,
  getUnifiedReport,
  submitCnkiFeedback
} from '../api'
import type {
  DocumentUploadResponse,
  AnalysisTaskStatusResponse,
  AnalysisRunStatusResponse,
  UnifiedReportResponse
} from '../types'

export interface HistoryItem {
  runId: string
  documentId: string
  title: string
  time: string
}

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
}

const HISTORY_KEY = 'ai-rate-task-history'
const MAX_HISTORY = 20

export const useAnalysisStore = defineStore('analysis', () => {
  const submitting = ref(false)
  const uploadProgress = ref(0)
  const taskStatus = ref<AnalysisTaskStatusResponse | null>(null)
  const runStatus = ref<AnalysisRunStatusResponse | null>(null)
  const report = ref<UnifiedReportResponse | null>(null)
  const error = ref('')
  const history = ref<HistoryItem[]>(loadHistory())

  function loadHistory(): HistoryItem[] {
    try {
      return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]')
    } catch {
      return []
    }
  }

  function pushHistory(item: HistoryItem) {
    const list = history.value.filter((h) => h.runId !== item.runId)
    list.unshift(item)
    if (list.length > MAX_HISTORY) list.length = MAX_HISTORY
    history.value = list
    localStorage.setItem(HISTORY_KEY, JSON.stringify(list))
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
      const uploadResult = await uploadDocument({
        ...payload,
        onProgress: (percent) => { uploadProgress.value = percent }
      })
      uploadProgress.value = 100
      const task = await analyzeDocumentAsync(uploadResult.document_id)
      const finished = await pollTask(task.task_id)

      if (!finished.run_id) throw new Error('分析完成但未返回 run_id')

      // 如果用户上传了知网报告，自动关联为 feedback
      if (payload.cnkiReport) {
        try {
          await submitCnkiFeedback({
            documentId: uploadResult.document_id,
            predictedRunId: finished.run_id,
            cnkiDupPercent: payload.cnkiReport.cnkiDupPercent,
            cnkiAigcPercent: payload.cnkiReport.cnkiAigcPercent,
            reportDate: payload.cnkiReport.reportDate || undefined,
            notes: payload.cnkiReport.notes || undefined,
            removeReferenceDupPercent: payload.cnkiReport.removeReferenceDupPercent ?? null,
            singleMaxDupPercent: payload.cnkiReport.singleMaxDupPercent ?? null,
            suspectedPlagiarism: payload.cnkiReport.suspectedPlagiarism ?? null,
            fragments: payload.cnkiReport.fragments ?? null,
            evidenceFile: payload.cnkiReport.file
          })
        } catch (feedbackErr) {
          // feedback 提交失败不应阻塞主流程，静默记录
          console.warn('知网报告自动关联失败:', feedbackErr)
        }
      }

      runStatus.value = await getRun(finished.run_id)
      report.value = await getUnifiedReport(finished.run_id)

      pushHistory({
        runId: finished.run_id,
        documentId: uploadResult.document_id,
        title: payload.title || uploadResult.title || uploadResult.filename,
        time: new Date().toISOString()
      })

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
    const MAX_ATTEMPTS = 120
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

  return { submitting, uploadProgress, taskStatus, runStatus, report, error, history, startAnalysis, loadReport, clearCurrent, pushHistory }
})
