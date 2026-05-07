<template>
  <section class="report-sidebar-stack">
    <div class="feedback-card">
      <div class="card-head">
        <p class="eyebrow">知网结果回填</p>
        <h3>让系统越来越接近真实送检结果</h3>
      </div>
      <el-form label-position="top" class="feedback-form">
        <div class="field-grid">
          <el-form-item label="知网查重 %">
            <el-input-number v-model="feedbackForm.cnkiDupPercent" :min="0" :max="100" :precision="1" />
          </el-form-item>
          <el-form-item label="知网 AIGC %">
            <el-input-number v-model="feedbackForm.cnkiAigcPercent" :min="0" :max="100" :precision="1" />
          </el-form-item>
        </div>
        <el-form-item label="报告日期">
          <el-date-picker
            v-model="feedbackForm.reportDate"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="feedbackForm.notes"
            type="textarea"
            :rows="3"
            placeholder="例如：正式送检版本做了哪些调整"
          />
        </el-form-item>
        <el-form-item label="证据截图或 PDF（可选）">
          <el-upload
            :auto-upload="false"
            :limit="1"
            :on-change="handleEvidenceChange"
            :on-remove="handleEvidenceRemove"
            accept=".png,.jpg,.jpeg,.pdf,.txt,.md,.docx"
          >
            <el-button>选择文件</el-button>
          </el-upload>
        </el-form-item>
        <el-button plain :loading="ocrPreviewLoading" :disabled="!evidenceFile" @click="previewEvidenceOcr">
          自动识别回填数据
        </el-button>
        <div v-if="ocrPreview" class="ocr-preview">
          <p class="helper-text">识别引擎：{{ ocrPreview.ocr_engine }}</p>
          <p class="helper-text">识别预览：{{ ocrPreview.extracted_text_preview }}</p>
          <p v-for="warning in ocrPreview.warnings" :key="warning" class="helper-text">{{ warning }}</p>
        </div>

        <el-button type="success" :loading="submittingFeedback" @click="submitFeedbackForm">
          提交真实结果并更新校准
        </el-button>
        <p v-if="feedbackResult" class="helper-text">
          已回填成功，当前校准版本：{{ feedbackResult.calibration_version }}
        </p>
        <p v-if="feedbackResult?.auto_train_triggered" class="helper-text">
          已触发自动重训：{{ feedbackResult.auto_train_versions.join(' / ') }}
        </p>
      </el-form>
    </div>

    <div class="feedback-card">
      <div class="card-head">
        <p class="eyebrow">自动拉取外部结果</p>
        <h3>对已配置供应商直接发起抓取</h3>
      </div>
      <el-form label-position="top" class="feedback-form">
        <div class="field-grid">
          <el-form-item label="供应商">
            <el-select v-model="fetchForm.provider">
              <el-option
                v-for="item in providerCatalog"
                :key="item.provider"
                :label="`${providerLabel(item.provider)}${item.configured ? '' : '（未配置）'}`"
                :value="item.provider"
                :disabled="!item.configured"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="配置状态">
            <div class="provider-state">
              <el-tag :type="selectedFetchProvider?.configured ? 'success' : 'info'">
                {{ selectedFetchProvider?.configured ? '已配置' : '未配置' }}
              </el-tag>
              <span v-if="selectedFetchProvider?.mode" class="helper-text">模式：{{ selectedFetchProvider.mode }}</span>
            </div>
          </el-form-item>
        </div>
        <el-form-item label="额外参数 JSON（可选）">
          <el-input
            v-model="fetchForm.extraPayloadText"
            type="textarea"
            :rows="3"
            placeholder='例如 {"task_id":"abc123"}'
          />
        </el-form-item>
        <el-button
          type="primary"
          plain
          :loading="fetchingProvider"
          :disabled="!selectedFetchProvider?.configured"
          @click="fetchProviderNow"
        >
          自动拉取结果
        </el-button>
        <p v-if="fetchedProviderResult" class="helper-text">
          已自动拉取 {{ fetchedProviderResult.provider }} 结果，记录时间 {{ formatDate(fetchedProviderResult.created_at) }}
        </p>
      </el-form>
    </div>

    <div class="feedback-card">
      <div class="card-head">
        <p class="eyebrow">外部结果导入</p>
        <h3>把万方、维普、Turnitin 或人工结果接进来</h3>
      </div>
      <el-form label-position="top" class="feedback-form">
        <div class="field-grid">
          <el-form-item label="来源">
            <el-select v-model="providerForm.provider">
              <el-option label="手工结果" value="manual" />
              <el-option label="万方" value="wanfang" />
              <el-option label="维普" value="vip" />
              <el-option label="Turnitin" value="turnitin" />
            </el-select>
          </el-form-item>
          <el-form-item label="置信度">
            <el-input-number v-model="providerForm.confidence" :min="0" :max="1" :step="0.05" :precision="2" />
          </el-form-item>
        </div>
        <div class="field-grid">
          <el-form-item label="查重 %">
            <el-input-number v-model="providerForm.duplicationPercent" :min="0" :max="100" :precision="1" />
          </el-form-item>
          <el-form-item label="AIGC %">
            <el-input-number v-model="providerForm.aigcPercent" :min="0" :max="100" :precision="1" />
          </el-form-item>
        </div>
        <el-form-item label="版本或来源说明">
          <el-input v-model="providerForm.version" placeholder="例如 2026Q2 / 官方网页版" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="providerForm.notes" type="textarea" :rows="2" placeholder="例如：这是老师推荐的预检结果" />
        </el-form-item>
        <el-button type="warning" :loading="submittingProvider" @click="submitProviderForm">
          导入外部结果
        </el-button>
        <p v-if="providerResult" class="helper-text">
          外部结果已导入：{{ providerResult.provider }}，记录时间 {{ formatDate(providerResult.created_at) }}
        </p>
      </el-form>
    </div>

    <div class="feedback-card">
      <div class="card-head">
        <p class="eyebrow">代理模型训练</p>
        <h3>有样本后，一键开始让系统更接近真实结果</h3>
      </div>
      <el-form label-position="top" class="feedback-form">
        <div class="field-grid">
          <el-form-item label="训练范围">
            <el-select v-model="trainingForm.modelType">
              <el-option label="查重 + AIGC 一起训练" value="both" />
              <el-option label="仅查重代理" value="cnki_dup_proxy" />
              <el-option label="仅 AIGC 代理" value="cnki_aigc_proxy" />
            </el-select>
          </el-form-item>
          <el-form-item label="最少样本数">
            <el-input-number v-model="trainingForm.minSamples" :min="1" :max="1000" />
          </el-form-item>
        </div>
        <el-button type="primary" plain :loading="trainingModels" @click="trainModelsNow">
          开始训练代理模型
        </el-button>
        <div v-if="trainingResult" class="training-result">
          <p class="helper-text">本次使用 {{ trainingResult.dataset_rows }} 条样本。</p>
          <article v-for="item in trainingResult.trained_models" :key="item.version" class="train-card">
            <strong>{{ item.model_type }}</strong>
            <p>版本：{{ item.version }}</p>
            <p>样本数：{{ item.train_count }}</p>
            <p>MAE：{{ item.mae.toFixed(4) }}，RMSE：{{ item.rmse.toFixed(4) }}</p>
          </article>
        </div>
      </el-form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus/es/components/message/index'
import type { UploadFile } from 'element-plus'
import {
  fetchProviderResult,
  importManualProviderResult,
  previewCnkiFeedbackOcr,
  submitCnkiFeedback,
  trainProxyModels
} from '../api'
import type {
  CnkiFeedbackOcrPreviewResponse,
  CnkiFeedbackResponse,
  ProviderConfigSummary,
  ProviderFetchResponse,
  ProviderResultImportResponse,
  ProxyModelTrainResponse,
  UnifiedReportResponse
} from '../types'

type ProviderCode = 'wanfang' | 'vip' | 'turnitin' | 'manual'

const props = defineProps<{
  report: UnifiedReportResponse
  providerCatalog: ProviderConfigSummary[]
}>()

const emit = defineEmits<{
  statusRefresh: []
}>()

const evidenceFile = ref<File | null>(null)
const submittingFeedback = ref(false)
const feedbackResult = ref<CnkiFeedbackResponse | null>(null)
const ocrPreview = ref<CnkiFeedbackOcrPreviewResponse | null>(null)
const providerResult = ref<ProviderResultImportResponse | null>(null)
const fetchedProviderResult = ref<ProviderFetchResponse | null>(null)
const trainingResult = ref<ProxyModelTrainResponse | null>(null)
const submittingProvider = ref(false)
const trainingModels = ref(false)
const fetchingProvider = ref(false)
const ocrPreviewLoading = ref(false)

const feedbackForm = reactive({
  cnkiDupPercent: undefined as number | undefined,
  cnkiAigcPercent: undefined as number | undefined,
  reportDate: '',
  notes: '',
  removeReferenceDupPercent: undefined as number | undefined,
  singleMaxDupPercent: undefined as number | undefined,
  suspectedPlagiarism: undefined as Record<string, number> | undefined,
  fragments: undefined as any[] | undefined,
})

const providerForm = reactive({
  provider: 'manual' as ProviderCode,
  duplicationPercent: undefined as number | undefined,
  aigcPercent: undefined as number | undefined,
  confidence: 0.8,
  version: '',
  notes: ''
})

const fetchForm = reactive({
  provider: 'wanfang' as ProviderCode,
  extraPayloadText: ''
})

const trainingForm = reactive({
  modelType: 'both' as 'cnki_dup_proxy' | 'cnki_aigc_proxy' | 'both',
  minSamples: 6
})

const selectedFetchProvider = computed(
  () => props.providerCatalog.find((item) => item.provider === fetchForm.provider) || null
)

watch(
  () => props.report.run_id,
  () => {
    resetWorkflowState()
  },
  { immediate: true }
)

watch(
  () => props.providerCatalog,
  () => {
    if (!selectedFetchProvider.value?.configured) {
      fetchForm.provider = firstConfiguredProvider()
    }
  },
  { immediate: true, deep: true }
)

function handleEvidenceChange(uploadFile: UploadFile) {
  evidenceFile.value = uploadFile.raw || null
  ocrPreview.value = null
}

function handleEvidenceRemove() {
  evidenceFile.value = null
  ocrPreview.value = null
}

async function submitFeedbackForm() {
  if (feedbackForm.cnkiDupPercent == null && feedbackForm.cnkiAigcPercent == null) {
    ElMessage.warning('至少填写一个真实知网结果。')
    return
  }

  submittingFeedback.value = true
  try {
    feedbackResult.value = await submitCnkiFeedback({
      documentId: props.report.document_id,
      predictedRunId: props.report.run_id,
      cnkiDupPercent: feedbackForm.cnkiDupPercent ?? null,
      cnkiAigcPercent: feedbackForm.cnkiAigcPercent ?? null,
      reportDate: feedbackForm.reportDate,
      notes: feedbackForm.notes,
      removeReferenceDupPercent: feedbackForm.removeReferenceDupPercent ?? null,
      singleMaxDupPercent: feedbackForm.singleMaxDupPercent ?? null,
      suspectedPlagiarism: feedbackForm.suspectedPlagiarism ?? null,
      fragments: feedbackForm.fragments ?? null,
      evidenceFile: evidenceFile.value
    })
    ElMessage.success(
      feedbackResult.value.calibration_updated ? '回填成功，已更新校准样本。' : '回填成功。'
    )
    emit('statusRefresh')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '提交回填失败')
  } finally {
    submittingFeedback.value = false
  }
}

async function previewEvidenceOcr() {
  if (!evidenceFile.value) {
    ElMessage.warning('请先选择证据文件')
    return
  }
  ocrPreviewLoading.value = true
  try {
    ocrPreview.value = await previewCnkiFeedbackOcr(evidenceFile.value)
    if (typeof ocrPreview.value.cnki_dup_percent === 'number') {
      feedbackForm.cnkiDupPercent = ocrPreview.value.cnki_dup_percent
    }
    if (typeof ocrPreview.value.cnki_aigc_percent === 'number') {
      feedbackForm.cnkiAigcPercent = ocrPreview.value.cnki_aigc_percent
    }
    if (ocrPreview.value.report_date) {
      feedbackForm.reportDate = ocrPreview.value.report_date
    }
    if (typeof ocrPreview.value.remove_reference_dup_percent === 'number') {
      feedbackForm.removeReferenceDupPercent = ocrPreview.value.remove_reference_dup_percent
    }
    if (typeof ocrPreview.value.single_max_dup_percent === 'number') {
      feedbackForm.singleMaxDupPercent = ocrPreview.value.single_max_dup_percent
    }
    if (ocrPreview.value.suspected_plagiarism) {
      feedbackForm.suspectedPlagiarism = ocrPreview.value.suspected_plagiarism
    }
    if (ocrPreview.value.fragments && ocrPreview.value.fragments.length > 0) {
      feedbackForm.fragments = ocrPreview.value.fragments
    }
    ElMessage.success('已尝试自动识别，可确认后直接提交回填')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'OCR 识别失败')
  } finally {
    ocrPreviewLoading.value = false
  }
}

async function submitProviderForm() {
  if (providerForm.duplicationPercent == null && providerForm.aigcPercent == null) {
    ElMessage.warning('至少填写一个外部结果。')
    return
  }
  submittingProvider.value = true
  try {
    providerResult.value = await importManualProviderResult({
      documentId: props.report.document_id,
      runId: props.report.run_id,
      provider: providerForm.provider,
      duplicationPercent: providerForm.duplicationPercent ?? null,
      aigcPercent: providerForm.aigcPercent ?? null,
      confidence: providerForm.confidence,
      version: providerForm.version,
      notes: providerForm.notes,
      rawPayload: { imported_from_ui: true }
    })
    ElMessage.success('外部结果已导入。')
    emit('statusRefresh')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '导入外部结果失败')
  } finally {
    submittingProvider.value = false
  }
}

async function fetchProviderNow() {
  fetchingProvider.value = true
  try {
    const extraPayload = fetchForm.extraPayloadText.trim()
      ? (JSON.parse(fetchForm.extraPayloadText) as Record<string, unknown>)
      : {}
    fetchedProviderResult.value = await fetchProviderResult({
      documentId: props.report.document_id,
      runId: props.report.run_id,
      provider: fetchForm.provider,
      extraPayload
    })
    ElMessage.success('已完成自动拉取并写入统一结果。')
    emit('statusRefresh')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '自动拉取失败')
  } finally {
    fetchingProvider.value = false
  }
}

async function trainModelsNow() {
  trainingModels.value = true
  try {
    trainingResult.value = await trainProxyModels({
      modelType: trainingForm.modelType,
      activate: true,
      minSamples: trainingForm.minSamples
    })
    ElMessage.success('代理模型训练完成并已激活。')
    emit('statusRefresh')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '训练失败')
  } finally {
    trainingModels.value = false
  }
}

function firstConfiguredProvider(): ProviderCode {
  const provider = props.providerCatalog.find((item) => item.configured)?.provider
  return isProviderCode(provider) ? provider : 'wanfang'
}

function resetWorkflowState() {
  evidenceFile.value = null
  feedbackResult.value = null
  ocrPreview.value = null
  providerResult.value = null
  fetchedProviderResult.value = null
  trainingResult.value = null
  Object.assign(feedbackForm, {
    cnkiDupPercent: undefined,
    cnkiAigcPercent: undefined,
    reportDate: '',
    notes: '',
    removeReferenceDupPercent: undefined,
    singleMaxDupPercent: undefined,
    suspectedPlagiarism: undefined,
    fragments: undefined,
  })
  Object.assign(providerForm, {
    provider: 'manual',
    duplicationPercent: undefined,
    aigcPercent: undefined,
    confidence: 0.8,
    version: '',
    notes: ''
  })
  Object.assign(fetchForm, {
    provider: firstConfiguredProvider(),
    extraPayloadText: ''
  })
  Object.assign(trainingForm, {
    modelType: 'both',
    minSamples: 6
  })
}

function formatDate(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function providerLabel(provider: string) {
  const labels: Record<string, string> = {
    wanfang: '万方',
    vip: '维普',
    turnitin: 'Turnitin',
    manual: '手工结果'
  }
  return labels[provider] || provider
}

function isProviderCode(value: string | undefined): value is ProviderCode {
  return value === 'wanfang' || value === 'vip' || value === 'turnitin' || value === 'manual'
}
</script>
