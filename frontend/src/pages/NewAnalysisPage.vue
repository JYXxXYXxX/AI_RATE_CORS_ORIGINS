<template>
  <div class="new-analysis">
    <div class="page-header">
      <h1>新建分析</h1>
      <p>上传论文文件，系统将自动生成详细风险预检报告</p>
    </div>

    <div class="upload-card">
      <!-- 论文文件上传 -->
      <div
        class="drop-zone"
        :class="{ dragging: isDragging, 'has-file': !!selectedFile }"
        @dragover.prevent="isDragging = true"
        @dragleave="isDragging = false"
        @drop.prevent="handleDrop"
        @click="triggerFileInput"
      >
        <input
          ref="fileInputRef"
          type="file"
          accept=".txt,.md,.docx,.pdf"
          class="file-input-hidden"
          @change="handleFileSelect"
        />
        <template v-if="selectedFile">
          <div class="file-preview">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            <div>
              <strong>{{ selectedFile.name }}</strong>
              <span>{{ formatFileSize(selectedFile.size) }}</span>
            </div>
            <button type="button" class="btn-icon" @click.stop="removeFile" title="移除文件">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
        </template>
        <template v-else>
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          <p class="drop-text">拖入文件或<strong>点击选择</strong></p>
          <p class="drop-hint">支持 .txt、.md、.docx、.pdf，最大 10MB</p>
        </template>
      </div>

      <!-- 知网报告上传（可选） -->
      <div class="cnki-section">
        <div class="cnki-header" @click="cnkiExpanded = !cnkiExpanded">
          <div class="cnki-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            <span>上传知网检测报告（可选）</span>
            <el-tag v-if="cnkiReportFile" type="success" size="small" effect="dark">已上传</el-tag>
          </div>
          <svg
            width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            :class="{ 'rotate-180': cnkiExpanded }" class="chevron"
          ><polyline points="6 9 12 15 18 9"/></svg>
        </div>

        <div v-show="cnkiExpanded" class="cnki-body">
          <p class="cnki-hint">如果你已经有知网的查重/AIGC检测报告，上传后系统会将其与本地预测对比，给出更精准的改写优先级建议。</p>

          <div
            v-if="!cnkiReportFile"
            class="drop-zone cnki-drop"
            :class="{ dragging: cnkiDragging }"
            @dragover.prevent="cnkiDragging = true"
            @dragleave="cnkiDragging = false"
            @drop.prevent="handleCnkiDrop"
            @click="triggerCnkiInput"
          >
            <input
              ref="cnkiInputRef"
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.bmp"
              class="file-input-hidden"
              @change="handleCnkiSelect"
            />
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            <p class="drop-text">拖入知网报告截图或 PDF</p>
            <p class="drop-hint">支持 .pdf、.png、.jpg，最大 10MB</p>
          </div>

          <div v-else class="cnki-preview">
            <div class="file-preview">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              <div>
                <strong>{{ cnkiReportFile.name }}</strong>
                <span>{{ formatFileSize(cnkiReportFile.size) }}</span>
              </div>
              <button type="button" class="btn-icon" @click="removeCnkiFile" title="移除">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
            </div>

            <div v-if="cnkiOcrLoading" class="cnki-ocr-loading">
              <el-skeleton :rows="2" animated />
            </div>

            <div v-else-if="cnkiOcrError" class="cnki-ocr-error">
              <el-alert :title="cnkiOcrError" type="warning" :closable="false" show-icon />
            </div>

            <div v-else-if="cnkiPreview" class="cnki-form">
              <div class="cnki-ocr-result">
                <p class="ocr-preview">{{ cnkiPreview.extracted_text_preview }}</p>
                <div class="ocr-matched">
                  <el-tag v-for="f in cnkiPreview.matched_fields" :key="f" type="success" size="small" effect="plain">
                    {{ fieldLabel(f) }}
                  </el-tag>
                  <span v-if="!cnkiPreview.matched_fields.length" class="ocr-warning">未自动识别到关键指标</span>
                </div>
              </div>
              <div class="form-row">
                <div class="form-field">
                  <label>知网查重率（%）</label>
                  <input
                    v-model.number="cnkiForm.cnkiDupPercent"
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    placeholder="例如 12.5"
                  />
                </div>
                <div class="form-field">
                  <label>知网 AIGC 率（%）</label>
                  <input
                    v-model.number="cnkiForm.cnkiAigcPercent"
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    placeholder="例如 8.3"
                  />
                </div>
              </div>
              <div class="form-field">
                <label>报告日期</label>
                <input v-model="cnkiForm.reportDate" type="date" />
              </div>
              <div class="form-field">
                <label>备注（可选）</label>
                <input v-model="cnkiForm.notes" type="text" placeholder="例如：第 1 次正式检测" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <form class="analysis-form" @submit.prevent="handleSubmit">
        <div class="form-field">
          <label>标题（可选）</label>
          <input v-model="form.title" type="text" placeholder="默认使用文件名" />
        </div>
        <div class="form-row">
          <div class="form-field">
            <label>学科</label>
            <input v-model="form.subject" type="text" placeholder="例如 教育学" />
          </div>
          <div class="form-field">
            <label>层级</label>
            <select v-model="form.degreeLevel">
              <option value="">请选择</option>
              <option value="本科">本科</option>
              <option value="硕士">硕士</option>
              <option value="博士">博士</option>
              <option value="期刊论文">期刊论文</option>
            </select>
          </div>
        </div>

        <button
          type="submit"
          class="btn btn-primary btn-full btn-lg"
          :disabled="!selectedFile || analysis.submitting"
        >
          {{ analysis.submitting ? '分析中...' : '开始分析' }}
        </button>

        <p v-if="analysis.error" class="form-error">{{ analysis.error }}</p>
      </form>

      <!-- 上传进度条 -->
      <div v-if="analysis.submitting && analysis.uploadProgress > 0 && analysis.uploadProgress < 100" class="progress-section">
        <div class="progress-header">
          <span>正在上传文件...</span>
          <strong>{{ analysis.uploadProgress }}%</strong>
        </div>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: `${analysis.uploadProgress}%` }"></div>
        </div>
      </div>

      <!-- 分析进度条 -->
      <div v-if="analysis.taskStatus && analysis.submitting" class="progress-section">
        <div class="progress-header">
          <span>{{ stageLabel(analysis.taskStatus.stage) }}</span>
          <strong>{{ analysis.taskStatus.progress }}%</strong>
        </div>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: `${analysis.taskStatus.progress}%` }"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAnalysisStore } from '../stores/analysis'
import { previewCnkiFeedbackOcr } from '../api'
import type { CnkiFeedbackOcrPreviewResponse } from '../types'

const router = useRouter()
const analysis = useAnalysisStore()

const selectedFile = ref<File | null>(null)
const isDragging = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)

const cnkiReportFile = ref<File | null>(null)
const cnkiExpanded = ref(false)
const cnkiDragging = ref(false)
const cnkiInputRef = ref<HTMLInputElement | null>(null)
const cnkiPreview = ref<CnkiFeedbackOcrPreviewResponse | null>(null)
const cnkiOcrLoading = ref(false)
const cnkiOcrError = ref('')

const cnkiForm = reactive({
  cnkiDupPercent: undefined as number | undefined,
  cnkiAigcPercent: undefined as number | undefined,
  reportDate: '',
  notes: '',
  removeReferenceDupPercent: undefined as number | undefined,
  singleMaxDupPercent: undefined as number | undefined,
  suspectedPlagiarism: undefined as Record<string, number> | undefined,
  fragments: undefined as any[] | undefined,
})

const form = reactive({
  title: '',
  subject: '',
  degreeLevel: ''
})

const MAX_SIZE = 10 * 1024 * 1024

function triggerFileInput() {
  if (selectedFile.value) return
  fileInputRef.value?.click()
}

function handleFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) setFile(file)
  input.value = ''
}

function handleDrop(e: DragEvent) {
  isDragging.value = false
  const file = e.dataTransfer?.files[0]
  if (file) setFile(file)
}

function setFile(file: File) {
  if (file.size > MAX_SIZE) {
    alert('文件大小不能超过 10MB')
    return
  }
  const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
  const allowed = ['.txt', '.md', '.docx', '.pdf']
  if (!allowed.includes(ext)) {
    alert('不支持的文件格式：' + ext + '\n请上传 .txt、.md、.docx 或 .pdf 格式')
    return
  }
  selectedFile.value = file
}

function removeFile() {
  selectedFile.value = null
}

// CNKI report upload
function triggerCnkiInput() {
  if (cnkiReportFile.value) return
  cnkiInputRef.value?.click()
}

function handleCnkiSelect(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) setCnkiFile(file)
  input.value = ''
}

function handleCnkiDrop(e: DragEvent) {
  cnkiDragging.value = false
  const file = e.dataTransfer?.files[0]
  if (file) setCnkiFile(file)
}

async function setCnkiFile(file: File) {
  if (file.size > MAX_SIZE) {
    alert('文件大小不能超过 10MB')
    return
  }
  const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
  const allowed = ['.pdf', '.png', '.jpg', '.jpeg', '.bmp']
  if (!allowed.includes(ext)) {
    alert('不支持的文件格式：' + ext + '\n请上传 .pdf、.png、.jpg 格式')
    return
  }
  cnkiReportFile.value = file
  cnkiPreview.value = null
  cnkiOcrError.value = ''
  cnkiOcrLoading.value = true
  try {
    const preview = await previewCnkiFeedbackOcr(file)
    cnkiPreview.value = preview
    if (preview.cnki_dup_percent != null) cnkiForm.cnkiDupPercent = preview.cnki_dup_percent
    if (preview.cnki_aigc_percent != null) cnkiForm.cnkiAigcPercent = preview.cnki_aigc_percent
    if (preview.report_date) cnkiForm.reportDate = preview.report_date
    if (preview.remove_reference_dup_percent != null) cnkiForm.removeReferenceDupPercent = preview.remove_reference_dup_percent
    if (preview.single_max_dup_percent != null) cnkiForm.singleMaxDupPercent = preview.single_max_dup_percent
    if (preview.suspected_plagiarism) cnkiForm.suspectedPlagiarism = preview.suspected_plagiarism
    if (preview.fragments && preview.fragments.length > 0) cnkiForm.fragments = preview.fragments
  } catch (err) {
    cnkiOcrError.value = err instanceof Error ? err.message : 'OCR 识别失败'
  } finally {
    cnkiOcrLoading.value = false
  }
}

function removeCnkiFile() {
  cnkiReportFile.value = null
  cnkiPreview.value = null
  cnkiOcrError.value = ''
  cnkiForm.cnkiDupPercent = undefined
  cnkiForm.cnkiAigcPercent = undefined
  cnkiForm.reportDate = ''
  cnkiForm.notes = ''
  cnkiForm.removeReferenceDupPercent = undefined
  cnkiForm.singleMaxDupPercent = undefined
  cnkiForm.suspectedPlagiarism = undefined
  cnkiForm.fragments = undefined
}

function fieldLabel(field: string): string {
  const map: Record<string, string> = {
    cnki_dup_percent: '查重率',
    cnki_aigc_percent: 'AIGC 率',
    report_date: '报告日期'
  }
  return map[field] || field
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function stageLabel(stage: string) {
  const labels: Record<string, string> = {
    queued: '排队中...',
    extracting_text: '提取正文...',
    segmenting_and_scoring: '分段评分中...',
    analyzing: '深度分析中...',
    completed: '完成',
    failed: '失败'
  }
  return labels[stage] || stage
}

async function handleSubmit() {
  if (!selectedFile.value) return
  const runId = await analysis.startAnalysis({
    file: selectedFile.value,
    title: form.title,
    subject: form.subject,
    degreeLevel: form.degreeLevel,
    cnkiReport: cnkiReportFile.value
      ? {
          file: cnkiReportFile.value,
          cnkiDupPercent: cnkiForm.cnkiDupPercent ?? null,
          cnkiAigcPercent: cnkiForm.cnkiAigcPercent ?? null,
          reportDate: cnkiForm.reportDate || null,
          notes: cnkiForm.notes || null,
          removeReferenceDupPercent: cnkiForm.removeReferenceDupPercent ?? null,
          singleMaxDupPercent: cnkiForm.singleMaxDupPercent ?? null,
          suspectedPlagiarism: cnkiForm.suspectedPlagiarism ?? null,
          fragments: cnkiForm.fragments ?? null,
        }
      : undefined
  })
  if (runId) {
    router.push(`/app/report/${runId}`)
  }
}
</script>

<style scoped>
.new-analysis {
  max-width: 620px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 28px;
}

.page-header h1 {
  font-size: 28px;
  color: #172033;
  margin: 0 0 6px;
}

.page-header p {
  color: #53606f;
  font-size: 15px;
  margin: 0;
}

.upload-card {
  padding: 32px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(31, 54, 73, 0.06);
  box-shadow: 0 12px 36px rgba(29, 45, 61, 0.06);
}

.drop-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 160px;
  padding: 32px;
  border: 2px dashed rgba(31, 54, 73, 0.15);
  border-radius: 14px;
  cursor: pointer;
  color: #8b95a2;
  transition: all 0.2s ease;
  margin-bottom: 24px;
}

.drop-zone:hover,
.drop-zone.dragging {
  border-color: #2f7d67;
  background: rgba(47, 125, 103, 0.03);
  color: #2f7d67;
}

.drop-zone.has-file {
  border-style: solid;
  border-color: rgba(47, 125, 103, 0.25);
  background: rgba(47, 125, 103, 0.04);
  cursor: default;
}

.file-input-hidden {
  display: none;
}

.drop-text {
  margin: 12px 0 4px;
  font-size: 15px;
  color: #53606f;
}

.drop-text strong {
  color: #2f7d67;
}

.drop-hint {
  margin: 0;
  font-size: 13px;
  color: #8b95a2;
}

.file-preview {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
  color: #344150;
}

.file-preview svg {
  color: #2f7d67;
  flex-shrink: 0;
}

.file-preview div {
  flex: 1;
  min-width: 0;
}

.file-preview strong {
  display: block;
  font-size: 15px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-preview span {
  font-size: 13px;
  color: #8b95a2;
}

.btn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #8b95a2;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-icon:hover {
  color: #c84b52;
  background: rgba(200, 75, 82, 0.08);
}

.analysis-form {
  display: grid;
  gap: 18px;
}

.form-field {
  display: grid;
  gap: 6px;
}

.form-field label {
  font-size: 13px;
  font-weight: 600;
  color: #344150;
}

.form-field input,
.form-field select {
  width: 100%;
  padding: 10px 14px;
  border: 1.5px solid rgba(31, 54, 73, 0.15);
  border-radius: 10px;
  font-size: 15px;
  color: #172033;
  background: #fff;
  transition: border-color 0.15s;
  outline: none;
  box-sizing: border-box;
}

.form-field input:focus,
.form-field select:focus {
  border-color: #2f7d67;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 22px;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 0.18s ease;
}

.btn-lg {
  padding: 13px 24px;
  font-size: 16px;
  border-radius: 12px;
}

.btn-primary {
  background: linear-gradient(135deg, #2f7d67, #236451);
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(47, 125, 103, 0.25);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-full {
  width: 100%;
}

.form-error {
  color: #c84b52;
  font-size: 14px;
  margin: 0;
  text-align: center;
}

.progress-section {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid rgba(31, 54, 73, 0.06);
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  font-size: 14px;
  color: #344150;
}

.progress-bar {
  height: 8px;
  border-radius: 99px;
  background: #e8edf0;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #2f7d67, #3ba57f);
  transition: width 0.3s ease;
}

/* CNKI report section */
.cnki-section {
  margin-bottom: 24px;
  border: 1.5px solid rgba(31, 54, 73, 0.1);
  border-radius: 14px;
  overflow: hidden;
}
.cnki-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  cursor: pointer;
  background: rgba(47, 125, 103, 0.03);
  transition: background 0.15s;
}
.cnki-header:hover {
  background: rgba(47, 125, 103, 0.06);
}
.cnki-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  font-weight: 600;
  color: #344150;
}
.cnki-title svg {
  color: #2f7d67;
}
.cnki-header .chevron {
  color: #8b95a2;
  transition: transform 0.2s ease;
}
.cnki-header .chevron.rotate-180 {
  transform: rotate(180deg);
}
.cnki-body {
  padding: 18px;
  background: #fafbfc;
}
.cnki-hint {
  margin: 0 0 14px;
  font-size: 13px;
  color: #8b95a2;
  line-height: 1.6;
}
.cnki-drop {
  min-height: 100px;
  margin-bottom: 0;
  background: #fff;
}
.cnki-preview {
  display: grid;
  gap: 14px;
}
.cnki-ocr-loading {
  padding: 8px 0;
}
.cnki-ocr-error {
  margin-top: 4px;
}
.cnki-ocr-result {
  background: #fff;
  border-radius: 10px;
  padding: 14px;
  border: 1px solid rgba(31, 54, 73, 0.08);
}
.ocr-preview {
  margin: 0 0 10px;
  font-size: 12px;
  color: #8b95a2;
  line-height: 1.5;
}
.ocr-matched {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.ocr-warning {
  font-size: 12px;
  color: #c84b52;
}
.cnki-form {
  display: grid;
  gap: 14px;
}
.cnki-form .form-field input {
  background: #fff;
}

@media (max-width: 500px) {
  .upload-card {
    padding: 20px;
  }

  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
