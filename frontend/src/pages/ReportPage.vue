<template>
  <div class="report-page">
    <div class="report-topbar">
      <router-link to="/app" class="back-link">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg>
        返回工作台
      </router-link>
    </div>

    <div v-if="loading" class="report-loading">
      <div class="spinner"></div>
      <h2>正在加载报告...</h2>
    </div>

    <div v-else-if="error" class="report-error">
      <h2>加载失败</h2>
      <p>{{ error }}</p>
      <button class="btn btn-primary" @click="loadData">重试</button>
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
        <summary class="advanced-toggle">高级操作：知网回填 & 供应商配置</summary>
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
import { onMounted, ref } from 'vue'
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
    error.value = err instanceof Error ? err.message : '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.report-page {
  max-width: 1100px;
  margin: 0 auto;
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
</style>
