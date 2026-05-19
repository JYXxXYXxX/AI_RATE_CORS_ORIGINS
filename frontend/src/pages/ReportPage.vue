<template>
  <div class="report-page">
    <div class="report-topbar">
      <router-link to="/app/dashboard" class="back-link">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg>
        {{ locale === 'en' ? 'Back to workspace' : '返回工作台' }}
      </router-link>
    </div>

    <div v-if="loading" class="report-loading">
      <div class="spinner"></div>
      <h2>{{ locale === 'en' ? 'Loading report...' : '正在加载报告...' }}</h2>
    </div>

    <div v-else-if="error" class="report-error">
      <h2>{{ locale === 'en' ? 'Failed to load' : '加载失败' }}</h2>
      <p>{{ error }}</p>
      <button class="btn btn-primary" @click="loadData">{{ locale === 'en' ? 'Retry' : '重试' }}</button>
    </div>

    <template v-else-if="analysis.report">
      <ReportView
        :report="analysis.report"
        :run-status="analysis.runStatus"
        :model-status="modelStatus"
        @refresh="loadData"
      />

      <!-- 高级工作流操作折叠区 -->
      <details class="advanced-section">
        <summary class="advanced-toggle">{{ locale === 'en' ? 'Advanced tools: CNKI feedback & provider settings' : '高级操作：知网回填 & 供应商配置' }}</summary>
        <div class="advanced-content">
          <ReportWorkflowSidebar
            :report="analysis.report"
            :provider-catalog="providerCatalog"
            @status-refresh="loadData"
          />
        </div>
      </details>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { useAnalysisStore } from '../stores/analysis'
import { getModelStatus, getProviderCatalog } from '../api'
import ReportView from '../components/ReportView.vue'
import ReportWorkflowSidebar from '../components/ReportWorkflowSidebar.vue'
import type { ModelStatusResponse, ProviderConfigSummary } from '../types'

const props = defineProps<{ runId: string }>()

const analysis = useAnalysisStore()
const loading = ref(false)
const error = ref('')
const modelStatus = ref<ModelStatusResponse | null>(null)
const providerCatalog = ref<ProviderConfigSummary[]>([])
const locale = ref<'zh' | 'en'>((document.documentElement.dataset.lang as 'zh' | 'en') || (localStorage.getItem('patafix-language') as 'zh' | 'en') || 'zh')

function syncLocale(next?: string) {
  locale.value = next === 'en' ? 'en' : 'zh'
}

function handleLanguageChange(event: Event) {
  syncLocale((event as CustomEvent<'zh' | 'en'>).detail)
}

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    await analysis.loadReport(props.runId)
    if (analysis.error) {
      error.value = analysis.error
      return
    }
    const [status, catalog] = await Promise.all([getModelStatus(), getProviderCatalog()])
    modelStatus.value = status
    providerCatalog.value = catalog.providers
  } catch (err) {
    error.value = err instanceof Error ? err.message : (locale.value === 'en' ? 'Failed to load' : '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  syncLocale(document.documentElement.dataset.lang || localStorage.getItem('patafix-language') || 'zh')
  document.documentElement.dataset.reportPage = 'true'
  window.addEventListener('patafix:language-change', handleLanguageChange as EventListener)
  loadData()
})

onBeforeUnmount(() => {
  delete document.documentElement.dataset.reportPage
  window.removeEventListener('patafix:language-change', handleLanguageChange as EventListener)
})
</script>

<style scoped>
.report-page {
  max-width: 1380px;
  margin: 0 auto;
  padding: 8px 0 28px;
  position: relative;
}

.report-topbar {
  margin-bottom: 20px;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #53606f;
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  padding: 6px 10px;
  border-radius: 8px;
  transition: all 0.15s;
}

.back-link:hover {
  color: #2f7d67;
  background: rgba(47, 125, 103, 0.06);
}

.report-loading,
.report-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  text-align: center;
}

.report-loading h2,
.report-error h2 {
  font-size: 20px;
  color: #344150;
  margin: 16px 0 8px;
}

.report-error p {
  color: #c84b52;
  font-size: 14px;
  margin: 0 0 20px;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid #e8edf0;
  border-top-color: #2f7d67;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10px 22px;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 0.18s ease;
}

.btn-primary {
  background: linear-gradient(135deg, #2f7d67, #236451);
  color: #fff;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(47, 125, 103, 0.25);
}

.advanced-section {
  margin-top: 28px;
}

.advanced-toggle {
  padding: 14px 20px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(31, 54, 73, 0.08);
  font-size: 14px;
  font-weight: 600;
  color: #53606f;
  cursor: pointer;
  transition: all 0.15s;
}

.advanced-toggle:hover {
  color: #2f7d67;
  border-color: rgba(47, 125, 103, 0.2);
}

.advanced-content {
  margin-top: 14px;
}

:global(html[data-theme='dark'][data-report-page='true']) .app-layout {
  background: linear-gradient(180deg, #060d13 0%, #09121a 52%, #0a1118 100%) !important;
}

:global(html[data-theme='dark'][data-report-page='true']) .app-main {
  background: transparent !important;
}

:global(html[data-theme='dark'][data-report-page='true']) .report-page {
  color: #f2f6fb;
}

:global(html[data-theme='dark'][data-report-page='true']) .report-page .back-link {
  color: #b9c6d8 !important;
}

:global(html[data-theme='dark'][data-report-page='true']) .report-page .back-link:hover {
  color: #f5f7fa !important;
  background: rgba(255, 255, 255, 0.05) !important;
}

:deep(:root[data-theme='dark']) .back-link {
  color: #c8d4e3;
}

:deep(:root[data-theme='dark']) .back-link:hover {
  color: #91d6c2;
  background: rgba(95, 170, 150, 0.12);
}

:deep(:root[data-theme='dark']) .report-loading h2,
:deep(:root[data-theme='dark']) .report-error h2 {
  color: #f5f8fc;
}

:deep(:root[data-theme='dark']) .advanced-toggle {
  background: linear-gradient(180deg, rgba(18, 22, 32, 0.94), rgba(12, 16, 24, 0.98));
  border-color: rgba(124, 151, 214, 0.16);
  color: #ccd6e3;
}

:deep(:root[data-theme='dark']) .advanced-toggle:hover {
  color: #8fe0c6;
  border-color: rgba(107, 201, 176, 0.26);
}
</style>
