<template>
  <div class="new-analysis">
    <div class="page-header">
      <h1>{{ copy.title }}</h1>
      <p>{{ copy.subtitle }}</p>
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
          accept=".docx,.doc,.pdf,.rtf,.odt"
          class="file-input-hidden"
          @change="handleFileSelect"
        />
        <template v-if="selectedFile || activeFileMeta">
          <div class="file-preview">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            <div>
              <strong>{{ selectedFile?.name || activeFileMeta?.fileName }}</strong>
              <span>{{ formatFileSize(selectedFile?.size || activeFileMeta?.fileSize || 0) }}</span>
            </div>
            <button v-if="selectedFile && !analysis.isAnalysisActive" type="button" class="btn-icon" @click.stop="removeFile" title="移除文件">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
        </template>
        <template v-else>
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          <p class="drop-text" v-html="copy.dropText"></p>
          <p class="drop-hint">{{ copy.dropHint }}</p>
        </template>
      </div>

      <section class="format-converter">
        <div class="converter-head">
          <div>
            <strong>{{ copy.converterTitle }}</strong>
            <p>{{ copy.converterHint }}</p>
          </div>
          <button type="button" class="btn btn-secondary btn-sm" @click="triggerConverterInput">
            {{ copy.converterChoose }}
          </button>
        </div>
        <input
          ref="converterInputRef"
          type="file"
          accept=".doc,.pdf,.rtf,.odt"
          class="file-input-hidden"
          @change="handleConverterSelect"
        />
        <div v-if="converterFile" class="converter-body">
          <div class="file-preview">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            <div>
              <strong>{{ converterFile.name }}</strong>
              <span>{{ formatFileSize(converterFile.size) }}</span>
            </div>
            <button type="button" class="btn-icon" @click="clearConverter" :title="copy.remove">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <div class="converter-actions">
            <button type="button" class="btn btn-primary" :disabled="converterLoading" @click="handleConvertToDocx">
              {{ converterLoading ? copy.converting : copy.convertNow }}
            </button>
            <button
              v-if="convertedDownloadUrl"
              type="button"
              class="btn btn-secondary"
              @click="downloadConvertedFile"
            >
              {{ copy.downloadConverted }}
            </button>
          </div>
          <div v-if="converterLoading || converterProgress > 0" class="converter-progress">
            <div class="converter-progress-head">
              <span>{{ converterLoading ? copy.converting : copy.convertComplete }}</span>
              <strong>{{ converterProgress }}%</strong>
            </div>
            <div class="progress-bar converter-progress-bar">
              <div class="progress-fill" :style="{ width: `${converterProgress}%` }"></div>
            </div>
          </div>
          <p v-if="convertedFile" class="converter-success">
            {{ copy.convertedReady }} <strong>{{ convertedFile.name }}</strong>
          </p>
          <p v-if="converterError" class="converter-error">{{ converterError }}</p>
        </div>
      </section>

      <!-- 知网报告上传（可选） -->
      <div class="cnki-section">
        <div class="cnki-header" @click="cnkiExpanded = !cnkiExpanded">
          <div class="cnki-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            <span>{{ copy.cnkiTitle }}</span>
            <el-tag v-if="cnkiReportFile" type="success" size="small" effect="dark">{{ copy.uploaded }}</el-tag>
          </div>
          <svg
            width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
            :class="{ 'rotate-180': cnkiExpanded }" class="chevron"
          ><polyline points="6 9 12 15 18 9"/></svg>
        </div>

        <div v-show="cnkiExpanded" class="cnki-body">
          <p class="cnki-hint">{{ copy.cnkiHint }}</p>

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
              accept=".pdf,.html,.htm,.docx"
              class="file-input-hidden"
              @change="handleCnkiSelect"
            />
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            <p class="drop-text">{{ copy.cnkiDrop }}</p>
            <p class="drop-hint">{{ copy.cnkiDropHint }}</p>
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

            <div v-else>
              <div v-if="cnkiOcrError" class="cnki-ocr-error">
                <el-alert :title="cnkiOcrError" type="warning" :closable="false" show-icon />
              </div>
              <div class="cnki-form">
              <div v-if="cnkiPreview" class="cnki-ocr-result">
                <div class="ocr-summary">
                  <div class="ocr-summary-head">
                    <span class="ocr-summary-label">{{ copy.recognitionSummary }}</span>
                    <el-tag size="small" effect="plain" :type="cnkiDetectedTagType">{{ cnkiDetectedTypeLabel }}</el-tag>
                  </div>
                  <div class="ocr-metric-list">
                    <span v-if="typeof cnkiPreview.cnki_dup_percent === 'number'" class="ocr-metric-chip">
                      {{ copy.cnkiDup }}: <strong>{{ cnkiPreview.cnki_dup_percent.toFixed(2) }}%</strong>
                    </span>
                    <span v-if="typeof cnkiPreview.cnki_aigc_percent === 'number'" class="ocr-metric-chip">
                      {{ copy.cnkiAigc }}: <strong>{{ cnkiPreview.cnki_aigc_percent.toFixed(2) }}%</strong>
                    </span>
                    <span v-if="cnkiPreview.report_date" class="ocr-metric-chip">
                      {{ copy.reportDate }}: <strong>{{ cnkiPreview.report_date }}</strong>
                    </span>
                  </div>
                </div>
                <p class="ocr-preview">{{ cnkiPreview.extracted_text_preview }}</p>
                <div class="ocr-matched">
                  <el-tag v-for="f in cnkiPreview.matched_fields" :key="f" type="success" size="small" effect="plain">
                    {{ fieldLabel(f) }}
                  </el-tag>
                  <span v-if="!cnkiPreview.matched_fields.length" class="ocr-warning">{{ copy.noOcr }}</span>
                </div>
                <ul v-if="cnkiPreview.warnings?.length" class="ocr-warning-list">
                  <li v-for="warning in cnkiPreview.warnings" :key="warning">{{ warning }}</li>
                </ul>
              </div>
              <div class="form-row">
                <div class="form-field">
                  <label>{{ copy.cnkiDup }}</label>
                  <input
                    v-model.number="cnkiForm.cnkiDupPercent"
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    :placeholder="copy.percentPlaceholder"
                  />
                </div>
                <div class="form-field">
                  <label>{{ copy.cnkiAigc }}</label>
                  <input
                    v-model.number="cnkiForm.cnkiAigcPercent"
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    :placeholder="copy.aigcPlaceholder"
                  />
                </div>
              </div>
              <div class="form-field">
                <label>{{ copy.reportDate }}</label>
                <input v-model="cnkiForm.reportDate" type="date" />
              </div>
              <div class="form-field">
                <label>{{ copy.notes }}</label>
                <input v-model="cnkiForm.notes" type="text" :placeholder="copy.notesPlaceholder" />
              </div>
              <div class="learning-consent">
                <div class="learning-options">
                  <label class="learning-option learning-option-default" :class="{ active: cnkiForm.learningScope === 'none' }">
                    <input v-model="cnkiForm.learningScope" type="radio" value="none" />
                    <span>{{ copy.learningNone }}<em>{{ copy.recommended }}</em></span>
                    <small>{{ copy.learningNoneDesc }}</small>
                  </label>
                  <label class="learning-option" :class="{ active: cnkiForm.learningScope === 'private_account' }">
                    <input v-model="cnkiForm.learningScope" type="radio" value="private_account" />
                    <span>{{ copy.learningPrivate }}</span>
                    <small>{{ copy.learningPrivateDesc }}</small>
                  </label>
                  <label class="learning-option" :class="{ active: cnkiForm.learningScope === 'anonymous_global' }">
                    <input v-model="cnkiForm.learningScope" type="radio" value="anonymous_global" />
                    <span>{{ copy.learningGlobal }}</span>
                    <small>{{ copy.learningGlobalDesc }}</small>
                  </label>
                </div>
                <p>{{ copy.learningPrivacy }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
      </div>

      <form class="analysis-form" @submit.prevent="handleSubmit">
        <div class="form-field">
          <label>{{ copy.paperTitle }}</label>
          <input v-model="form.title" type="text" :placeholder="copy.paperTitlePlaceholder" />
        </div>
        <div class="form-row">
          <div class="form-field">
            <label>{{ copy.subject }}</label>
            <input v-model="form.subject" type="text" :placeholder="copy.subjectPlaceholder" />
          </div>
          <div class="form-field">
            <label>{{ copy.degree }}</label>
            <select v-model="form.degreeLevel">
              <option value="">{{ copy.select }}</option>
              <option value="本科">{{ copy.undergraduate }}</option>
              <option value="硕士">{{ copy.master }}</option>
              <option value="博士">{{ copy.doctor }}</option>
              <option value="期刊论文">{{ copy.journal }}</option>
            </select>
          </div>
        </div>

        <button
          type="submit"
          class="btn btn-primary btn-full btn-lg"
          :disabled="!selectedFile || analysis.isAnalysisActive"
        >
          {{ isSubmitActive ? copy.analyzing : copy.start }}
        </button>

        <button
          v-if="analysis.isAnalysisActive"
          type="button"
          class="btn btn-secondary btn-full btn-lg"
          style="margin-top: 8px;"
          @click="handleCancel"
        >
          {{ copy.cancel }}
        </button>

        <p v-if="analysis.error" class="form-error">{{ analysis.error }}</p>
      </form>

      <!-- 上传进度条 -->
      <div v-if="isSubmitActive && analysis.uploadProgress > 0 && analysis.uploadProgress < 100" class="progress-section">
        <div class="progress-header">
          <span>{{ copy.uploading }}</span>
          <strong>{{ analysis.uploadProgress }}%</strong>
        </div>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: `${analysis.uploadProgress}%` }"></div>
        </div>
      </div>

      <!-- 分析进度条 -->
      <div v-if="analysis.taskStatus && isSubmitActive" class="progress-section">
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
import { computed, onBeforeUnmount, onMounted, ref, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAnalysisStore } from '../stores/analysis'
import { convertDocumentToDocx, previewCnkiFeedbackOcr } from '../api'
import type { CnkiFeedbackOcrPreviewResponse, LearningScope } from '../types'

const router = useRouter()
const analysis = useAnalysisStore()
type Locale = 'zh' | 'en'
const locale = ref<Locale>((localStorage.getItem('patafix-language') as Locale) || 'zh')

const copy = computed(() => locale.value === 'en'
  ? {
      title: 'New scan',
      subtitle: 'Upload a paper and let the system generate a detailed risk precheck report.',
      dropText: 'Drop a file or <strong>click to choose</strong>',
      dropHint: 'Supports .docx directly; .doc, .pdf, .rtf and .odt can be converted first',
      converterTitle: 'Format converter',
      converterHint: 'Convert .doc, .pdf, .rtf or .odt to .docx before uploading.',
      converterChoose: 'Choose file',
      convertNow: 'Convert to DOCX',
      converting: 'Converting...',
      convertComplete: 'Conversion complete',
      convertedReady: 'Ready for upload:',
      downloadConverted: 'Download DOCX',
      remove: 'Remove',
      cnkiTitle: 'Upload official report (optional, enables report-driven mode)',
      uploaded: 'Uploaded',
      cnkiHint: 'After uploading an official similarity or AIGC report, the system treats it as the highest-priority risk source and locates paragraphs that need rewriting.',
      cnkiDrop: 'Drop official report',
      cnkiDropHint: 'Supports .pdf, .html, .docx, up to 10MB',
      noOcr: 'No key metrics recognized automatically',
      recognitionSummary: 'Recognition result',
      reportTypeAigc: 'AIGC report',
      reportTypeDup: 'Similarity report',
      reportTypeMixed: 'Mixed report',
      reportTypeUnknown: 'Need manual check',
      cnkiDup: 'Official similarity rate (%)',
      cnkiAigc: 'Official AIGC rate (%)',
      percentPlaceholder: 'e.g. 12.5',
      aigcPlaceholder: 'e.g. 8.3',
      reportDate: 'Report date',
      notes: 'Notes (optional)',
      notesPlaceholder: 'e.g. first official scan',
      learningNone: 'Default: no shared learning',
      learningNoneDesc: 'Only used for this scan and rewrite; not added to calibration samples.',
      recommended: 'Recommended',
      learningPrivate: 'Optimize only my account',
      learningPrivateDesc: 'Helps future scans match your school standard without contributing globally.',
      learningGlobal: 'Contribute anonymous calibration',
      learningGlobalDesc: 'Stores only anonymous features, official risk levels, and rewrite outcome signals.',
      learningPrivacy: 'The system does not save paper text as training samples. Official reports are used to align colors, locate high-risk sentences, and improve suggestions.',
      paperTitle: 'Title (optional)',
      paperTitlePlaceholder: 'Defaults to file name',
      subject: 'Subject',
      subjectPlaceholder: 'e.g. Education',
      degree: 'Level',
      select: 'Select',
      undergraduate: 'Undergraduate',
      master: 'Master',
      doctor: 'Doctorate',
      journal: 'Journal paper',
      analyzing: 'Analyzing...',
      start: 'Start scan',
      uploading: 'Uploading file...',
      oversizedPaper: 'File size cannot exceed 50MB',
      unsupportedPaper: 'Unsupported file type: ',
      supportedPaper: 'Please upload .docx, or convert .doc/.pdf/.rtf/.odt first',
      oversizedReport: 'Report size cannot exceed 10MB',
      unsupportedReport: 'Unsupported report type: ',
      supportedReport: 'Please upload .pdf, .html, or .docx',
      stages: {
        queued: 'Queued...',
        extracting_text: 'Extracting text...',
        segmenting_and_scoring: 'Scoring sections...',
        analyzing: 'Deep analysis...',
        completed: 'Completed',
        failed: 'Failed'
      },
      fields: {
        cnki_dup_percent: 'Similarity',
        cnki_aigc_percent: 'AIGC',
        report_date: 'Report date'
      }
    }
  : {
      title: '新建分析',
      subtitle: '上传论文文件，系统将自动生成详细风险预检报告',
      dropText: '拖入文件或<strong>点击选择</strong>',
      dropHint: '可直接上传 .docx；.doc、.pdf、.rtf、.odt 可先在下方转换',
      converterTitle: '格式转换工具',
      converterHint: '格式不对时，先把 .doc、.pdf、.rtf 或 .odt 转成 .docx，再继续上传论文。',
      converterChoose: '选择文件',
      convertNow: '转成 DOCX',
      converting: '转换中...',
      convertComplete: '转换完成',
      convertedReady: '已放入上传区：',
      downloadConverted: '下载 DOCX',
      remove: '移除',
      cnkiTitle: '上传检测报告（可选，启用报告驱动模式）',
      uploaded: '已上传',
      cnkiHint: '上传知网查重报告或 AIGC 检测报告后，系统会以知网结果为最高优先级风险来源，直接定位需要改写的段落。支持 PDF、HTML、Word 格式。',
      cnkiDrop: '拖入检测报告',
      cnkiDropHint: '支持 .pdf、.html、.docx，最大 10MB',
      noOcr: '未自动识别到关键指标',
      recognitionSummary: '识别结果',
      reportTypeAigc: 'AIGC 报告',
      reportTypeDup: '查重报告',
      reportTypeMixed: '综合报告',
      reportTypeUnknown: '需要人工确认',
      cnkiDup: '知网查重率（%）',
      cnkiAigc: '知网 AIGC 率（%）',
      percentPlaceholder: '例如 12.5',
      aigcPlaceholder: '例如 8.3',
      reportDate: '报告日期',
      notes: '备注（可选）',
      notesPlaceholder: '例如：第 1 次正式检测',
      learningNone: '默认不参与共享学习',
      learningNoneDesc: '仅用于本次检测与改写，不进入校准样本。',
      recommended: '推荐',
      learningPrivate: '仅用于本人账号优化',
      learningPrivateDesc: '帮助后续更贴合你的学校标准，不贡献给全局模型。',
      learningGlobal: '匿名贡献给系统校准',
      learningGlobalDesc: '只保存匿名特征、官方风险等级和改写效果信号。',
      learningPrivacy: '系统不保存论文原文作为训练样本；官方报告只用于本次对齐风险颜色、定位高风险句子和生成更准确的改写建议。',
      paperTitle: '标题（可选）',
      paperTitlePlaceholder: '默认使用文件名',
      subject: '学科',
      subjectPlaceholder: '例如 教育学',
      degree: '层级',
      select: '请选择',
      undergraduate: '本科',
      master: '硕士',
      doctor: '博士',
      journal: '期刊论文',
      analyzing: '分析中...',
      cancel: '取消 / 重置',
      start: '开始分析',
      uploading: '正在上传文件...',
      oversizedPaper: '文件大小不能超过 50MB',
      unsupportedPaper: '不支持的文件格式：',
      supportedPaper: '请上传 .docx，或先把 .doc/.pdf/.rtf/.odt 转成 .docx',
      oversizedReport: '文件大小不能超过 10MB',
      unsupportedReport: '不支持的文件格式：',
      supportedReport: '请上传 .pdf、.html、.docx 格式',
      stages: {
        queued: '排队中...',
        extracting_text: '提取正文...',
        segmenting_and_scoring: '分段评分中...',
        analyzing: '深度分析中...',
        completed: '完成',
        failed: '失败'
      },
      fields: {
        cnki_dup_percent: '查重率',
        cnki_aigc_percent: 'AIGC 率',
        report_date: '报告日期'
      }
    })

const selectedFile = ref<File | null>(null)
const isDragging = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const converterInputRef = ref<HTMLInputElement | null>(null)
const converterFile = ref<File | null>(null)
const convertedFile = ref<File | null>(null)
const convertedDownloadUrl = ref('')
const converterLoading = ref(false)
const converterProgress = ref(0)
const converterError = ref('')
let converterProgressTimer: number | undefined

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
  learningScope: 'none' as LearningScope,
})

const form = reactive({
  title: '',
  subject: '',
  degreeLevel: ''
})

const activeFileMeta = computed(() => analysis.activeMeta)
const isSubmitActive = computed(() => analysis.isAnalysisActive)

const MAX_SIZE = 50 * 1024 * 1024

onMounted(() => {
  analysis.hydrateActiveState()
  analysis.resumeActiveAnalysis()
  window.addEventListener('patafix:language-change', handleLanguageChange)
})

onBeforeUnmount(() => {
  window.removeEventListener('patafix:language-change', handleLanguageChange)
  stopConverterProgress()
  revokeConvertedUrl()
})

watch(
  () => analysis.runStatus?.run_id,
  (runId) => {
    if (!runId || analysis.isAnalysisActive) return
    if (analysis.runStatus?.mode === 'report') {
      router.push(`/app/rewrite/${runId}`)
      return
    }
    router.push(`/app/report/${runId}`)
  }
)

function triggerFileInput() {
  if (analysis.isAnalysisActive) return
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
  if (analysis.isAnalysisActive) return
  if (file.size > MAX_SIZE) {
    alert(copy.value.oversizedPaper)
    return
  }
  const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
  if (ext === '.docx') {
    selectedFile.value = file
    return
  }
  const convertible = ['.doc', '.pdf', '.rtf', '.odt']
  if (convertible.includes(ext)) {
    setConverterFile(file)
    return
  }
  if (!ext) {
    alert(copy.value.unsupportedPaper + file.name + '\n' + copy.value.supportedPaper)
    return
  }
  alert(copy.value.unsupportedPaper + ext + '\n' + copy.value.supportedPaper)
}

function removeFile() {
  selectedFile.value = null
}

function triggerConverterInput() {
  if (analysis.isAnalysisActive || converterLoading.value) return
  converterInputRef.value?.click()
}

function handleConverterSelect(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) setConverterFile(file)
  input.value = ''
}

function setConverterFile(file: File) {
  if (file.size > MAX_SIZE) {
    alert(copy.value.oversizedPaper)
    return
  }
  const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
  const allowed = ['.doc', '.pdf', '.rtf', '.odt']
  if (!allowed.includes(ext)) {
    alert(copy.value.unsupportedPaper + ext + '\n' + copy.value.supportedPaper)
    return
  }
  converterFile.value = file
  convertedFile.value = null
  converterError.value = ''
  converterProgress.value = 0
  revokeConvertedUrl()
}

async function handleConvertToDocx() {
  if (!converterFile.value || converterLoading.value) return
  converterLoading.value = true
  converterProgress.value = 1
  converterError.value = ''
  startConverterProgress()
  try {
    const result = await convertDocumentToDocx(converterFile.value, {
      onProgress: (percent) => {
        converterProgress.value = Math.max(converterProgress.value, percent)
      }
    })
    const docxFile = new File([result.blob], result.filename, {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    })
    convertedFile.value = docxFile
    selectedFile.value = docxFile
    revokeConvertedUrl()
    convertedDownloadUrl.value = URL.createObjectURL(result.blob)
    converterProgress.value = 100
  } catch (err) {
    convertedFile.value = null
    converterProgress.value = 0
    converterError.value = err instanceof Error ? err.message : '转换失败，请确认文件未加密或损坏'
  } finally {
    stopConverterProgress()
    converterLoading.value = false
  }
}

function clearConverter() {
  converterFile.value = null
  convertedFile.value = null
  converterError.value = ''
  converterProgress.value = 0
  stopConverterProgress()
  revokeConvertedUrl()
}

function startConverterProgress() {
  stopConverterProgress()
  converterProgressTimer = window.setInterval(() => {
    if (!converterLoading.value) return
    if (converterProgress.value < 70) {
      converterProgress.value += 2
    } else if (converterProgress.value < 92) {
      converterProgress.value += 1
    }
  }, 700)
}

function stopConverterProgress() {
  if (converterProgressTimer) {
    window.clearInterval(converterProgressTimer)
    converterProgressTimer = undefined
  }
}

function revokeConvertedUrl() {
  if (convertedDownloadUrl.value) {
    URL.revokeObjectURL(convertedDownloadUrl.value)
    convertedDownloadUrl.value = ''
  }
}

function downloadConvertedFile() {
  if (!convertedFile.value || !convertedDownloadUrl.value) return
  const anchor = document.createElement('a')
  anchor.href = convertedDownloadUrl.value
  anchor.download = convertedFile.value.name
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
}

function handleCancel() {
  analysis.resetSubmissionState()
  selectedFile.value = null
  cnkiReportFile.value = null
  clearConverter()
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
  if (file.size > 10 * 1024 * 1024) {
    alert(copy.value.oversizedReport)
    return
  }
  const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
  const allowed = ['.pdf', '.html', '.htm', '.docx']
  if (!allowed.includes(ext)) {
    alert(copy.value.unsupportedReport + ext + '\n' + copy.value.supportedReport)
    return
  }
  cnkiReportFile.value = file
  cnkiPreview.value = null
  cnkiOcrError.value = ''
  cnkiForm.cnkiDupPercent = undefined
  cnkiForm.cnkiAigcPercent = undefined
  cnkiForm.reportDate = ''
  cnkiForm.removeReferenceDupPercent = undefined
  cnkiForm.singleMaxDupPercent = undefined
  cnkiForm.suspectedPlagiarism = undefined
  cnkiForm.fragments = undefined
  cnkiOcrLoading.value = true
  try {
    const preview = await previewCnkiFeedbackOcr(file)
    cnkiPreview.value = preview
    applyCnkiPreview(preview)
    if (!preview.matched_fields.length) {
      cnkiOcrError.value = copy.value.noOcr
    }
  } catch (error) {
    cnkiPreview.value = null
    cnkiOcrError.value = error instanceof Error ? error.message : copy.value.noOcr
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
  cnkiForm.learningScope = 'none'
}

function fieldLabel(field: string): string {
  return copy.value.fields[field as keyof typeof copy.value.fields] || field
}

const cnkiDetectedTypeLabel = computed(() => {
  const preview = cnkiPreview.value
  if (!preview) return copy.value.reportTypeUnknown
  const hasDup = typeof preview.cnki_dup_percent === 'number'
  const hasAigc = typeof preview.cnki_aigc_percent === 'number'
  if (hasDup && hasAigc) return copy.value.reportTypeMixed
  if (hasAigc) return copy.value.reportTypeAigc
  if (hasDup) return copy.value.reportTypeDup
  return copy.value.reportTypeUnknown
})

const cnkiDetectedTagType = computed(() => {
  const preview = cnkiPreview.value
  if (!preview) return 'info'
  const hasDup = typeof preview.cnki_dup_percent === 'number'
  const hasAigc = typeof preview.cnki_aigc_percent === 'number'
  if (hasDup && hasAigc) return 'warning'
  if (hasDup || hasAigc) return 'success'
  return 'info'
})

function applyCnkiPreview(preview: CnkiFeedbackOcrPreviewResponse) {
  if (typeof preview.cnki_dup_percent === 'number') {
    cnkiForm.cnkiDupPercent = preview.cnki_dup_percent
  }
  if (typeof preview.cnki_aigc_percent === 'number') {
    cnkiForm.cnkiAigcPercent = preview.cnki_aigc_percent
  }
  if (preview.report_date) {
    cnkiForm.reportDate = preview.report_date
  }
  if (typeof preview.remove_reference_dup_percent === 'number') {
    cnkiForm.removeReferenceDupPercent = preview.remove_reference_dup_percent
  }
  if (typeof preview.single_max_dup_percent === 'number') {
    cnkiForm.singleMaxDupPercent = preview.single_max_dup_percent
  }
  if (preview.suspected_plagiarism) {
    cnkiForm.suspectedPlagiarism = preview.suspected_plagiarism
  }
  if (preview.fragments?.length) {
    cnkiForm.fragments = preview.fragments
  }
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function stageLabel(stage: string) {
  return copy.value.stages[stage as keyof typeof copy.value.stages] || stage
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
          learningScope: cnkiForm.learningScope,
        }
      : undefined
  })
  if (runId) {
    // Report Mode 直接跳到改写编辑器，Estimate Mode 先跳到报告页
    if (cnkiReportFile.value) {
      router.push(`/app/rewrite/${runId}`)
    } else {
      router.push(`/app/report/${runId}`)
    }
  }
}

function handleLanguageChange(event: Event) {
  locale.value = (event as CustomEvent<Locale>).detail || 'zh'
}
</script>

<style scoped>
.new-analysis {
  max-width: 760px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 22px;
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
  padding: 26px;
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
  min-height: 136px;
  padding: 24px;
  border: 2px dashed rgba(31, 54, 73, 0.15);
  border-radius: 14px;
  cursor: pointer;
  color: #8b95a2;
  transition: all 0.2s ease;
  margin-bottom: 20px;
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
  margin-top: 4px;
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

.btn-sm {
  padding: 8px 12px;
  font-size: 13px;
  border-radius: 8px;
}

.btn-primary {
  background: linear-gradient(135deg, #2f7d67, #236451);
  color: #fff;
}

.btn-secondary {
  background: #fff;
  color: #2f7d67;
  border: 1px solid rgba(47, 125, 103, 0.24);
}

.btn-secondary:hover:not(:disabled) {
  background: rgba(47, 125, 103, 0.08);
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

.format-converter {
  margin: -4px 0 20px;
  padding: 16px;
  border: 1.5px solid rgba(47, 125, 103, 0.14);
  border-radius: 14px;
  background: rgba(47, 125, 103, 0.04);
}

.converter-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.converter-head strong {
  display: block;
  color: #263746;
  font-size: 14px;
  margin-bottom: 4px;
}

.converter-head p {
  margin: 0;
  color: #6f7a86;
  font-size: 13px;
  line-height: 1.5;
}

.converter-body {
  display: grid;
  gap: 12px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid rgba(31, 54, 73, 0.08);
}

.converter-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.converter-progress {
  display: grid;
  gap: 8px;
}

.converter-progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
  color: #53606f;
}

.converter-progress-head strong {
  color: #21755d;
}

.converter-progress-bar {
  height: 7px;
}

.converter-success,
.converter-error {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
}

.converter-success {
  color: #21755d;
}

.converter-error {
  color: #c84b52;
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
.ocr-summary {
  display: grid;
  gap: 10px;
  margin-bottom: 10px;
}
.ocr-summary-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.ocr-summary-label {
  font-size: 12px;
  font-weight: 700;
  color: #344150;
  letter-spacing: 0;
}
.ocr-metric-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.ocr-metric-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(47, 125, 103, 0.08);
  color: #2d4b44;
  font-size: 12px;
}
.ocr-metric-chip strong {
  color: #1b6b54;
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
.ocr-warning-list {
  margin: 10px 0 0;
  padding-left: 18px;
  color: #a45a18;
  font-size: 12px;
  line-height: 1.55;
}
.cnki-form {
  display: grid;
  gap: 14px;
}
.cnki-form .form-field input {
  background: #fff;
}
.learning-consent {
  padding: 12px;
  border: 1px solid rgba(47, 125, 103, 0.16);
  border-radius: 12px;
  background: rgba(47, 125, 103, 0.06);
}
.learning-options {
  display: grid;
  gap: 8px;
}
.learning-option {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 2px 8px;
  padding: 9px 10px;
  border: 1px solid rgba(31, 54, 73, 0.08);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.74);
  cursor: pointer;
}
.learning-option-default {
  border-color: rgba(224, 156, 52, 0.55);
  background: #fff7e6;
  box-shadow: 0 0 0 1px rgba(224, 156, 52, 0.12) inset;
}
.learning-option-default.active {
  border-color: #d8912e;
  background: #fff1cf;
}
.learning-option.active {
  border-color: rgba(47, 125, 103, 0.38);
  background: rgba(47, 125, 103, 0.1);
}
.learning-option-default.active {
  border-color: #d8912e;
  background: #fff1cf;
}
.learning-option input {
  grid-row: span 2;
  width: auto;
  margin-top: 2px;
}
.learning-option span {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 13px;
  font-weight: 700;
  color: #344150;
}
.learning-option span em {
  padding: 2px 7px;
  border-radius: 999px;
  background: #d8912e;
  color: #fff;
  font-size: 11px;
  font-style: normal;
  line-height: 1.4;
}
.learning-option small {
  font-size: 12px;
  line-height: 1.45;
  color: #6f7a86;
}
.learning-consent p {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: #6f7a86;
}

@media (max-width: 500px) {
  .upload-card {
    padding: 20px;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .converter-head,
  .converter-actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
