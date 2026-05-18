<template>
  <div class="dashboard">
    <div class="dash-header">
      <div>
        <h1>{{ copy.title }}</h1>
        <p class="dash-subtitle">{{ copy.subtitle }}</p>
      </div>
      <router-link to="/app/new" class="btn btn-primary">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        {{ copy.newAnalysis }}
      </router-link>
    </div>

    <!-- 统计卡片 -->
    <div class="stat-row">
      <div class="stat-card">
        <span class="stat-label">{{ copy.total }}</span>
        <strong class="stat-value">{{ analysis.history.length }}</strong>
      </div>
      <!-- 付费功能已隐藏 -->
      <!-- <div class="stat-card">
        <span class="stat-label">剩余额度</span>
        <strong class="stat-value accent">{{ auth.credits }}</strong>
      </div> -->
      <div class="stat-card">
        <span class="stat-label">{{ copy.accountStatus }}</span>
        <strong class="stat-value">{{ auth.user?.status || copy.normal }}</strong>
      </div>
    </div>

    <!-- 历史列表 -->
    <section class="history-section" v-if="analysis.history.length">
      <h2>{{ copy.recent }}</h2>
      <div class="history-list">
        <article
          v-for="item in analysis.history"
          :key="item.task_id"
          class="history-row"
          :class="{ clickable: !!item.run_id }"
          @click="item.run_id && router.push(`/app/report/${item.run_id}`)"
        >
          <div class="history-info">
            <strong>{{ item.title || item.filename || copy.untitled }}</strong>
            <span class="history-id">{{ item.task_id.slice(0, 8) }}...</span>
          </div>
          <span class="history-time">{{ formatTime(item.created_at) }}</span>
          <span v-if="!item.run_id" class="history-status">{{ statusLabel(item.status, item.progress) }}</span>
          <svg v-else class="history-arrow" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="9 18 15 12 9 6"/></svg>
        </article>
      </div>
    </section>

    <!-- 空状态 -->
    <section v-else class="empty-state">
      <div class="empty-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
      </div>
      <h2>{{ copy.emptyTitle }}</h2>
      <p>{{ copy.emptyDesc }}</p>
      <router-link to="/app/new" class="btn btn-primary">{{ copy.first }}</router-link>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useAnalysisStore } from '../stores/analysis'

const router = useRouter()
const auth = useAuthStore()
const analysis = useAnalysisStore()
type Locale = 'zh' | 'en'
const locale = ref<Locale>((localStorage.getItem('patafix-language') as Locale) || 'zh')

const copy = computed(() => locale.value === 'en'
  ? {
      title: 'Workspace',
      subtitle: 'Your paper analysis records',
      newAnalysis: 'New scan',
      total: 'Total scans',
      accountStatus: 'Account status',
      normal: 'Active',
      recent: 'Recent scans',
      untitled: 'Untitled document',
      emptyTitle: 'No analysis records yet',
      emptyDesc: 'Upload a paper and generate your first risk precheck report',
      first: 'Start first scan',
      justNow: 'Just now',
      minutes: 'min ago',
      hours: 'hr ago',
      days: 'd ago',
      status: {
        queued: 'Queued',
        processing: 'Processing',
        completed: 'Completed',
        failed: 'Failed'
      }
    }
  : {
      title: '工作台',
      subtitle: '你的论文分析记录',
      newAnalysis: '新建分析',
      total: '分析总数',
      accountStatus: '账户状态',
      normal: '正常',
      recent: '最近分析',
      untitled: '未命名文档',
      emptyTitle: '还没有分析记录',
      emptyDesc: '上传一篇论文，生成你的第一份风险预检报告',
      first: '开始第一次分析',
      justNow: '刚刚',
      minutes: '分钟前',
      hours: '小时前',
      days: '天前',
      status: {
        queued: '排队中',
        processing: '处理中',
        completed: '已完成',
        failed: '失败'
      }
    })

onMounted(() => {
  analysis.refreshHistory()
  window.addEventListener('patafix:language-change', handleLanguageChange)
})

onBeforeUnmount(() => {
  window.removeEventListener('patafix:language-change', handleLanguageChange)
})

function formatTime(iso: string) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 60000) return copy.value.justNow
  if (diff < 3600000) return locale.value === 'en' ? `${Math.floor(diff / 60000)} ${copy.value.minutes}` : `${Math.floor(diff / 60000)} ${copy.value.minutes}`
  if (diff < 86400000) return locale.value === 'en' ? `${Math.floor(diff / 3600000)} ${copy.value.hours}` : `${Math.floor(diff / 3600000)} ${copy.value.hours}`
  if (diff < 604800000) return locale.value === 'en' ? `${Math.floor(diff / 86400000)} ${copy.value.days}` : `${Math.floor(diff / 86400000)} ${copy.value.days}`
  return d.toLocaleDateString(locale.value === 'en' ? 'en-US' : 'zh-CN')
}

function statusLabel(status: string, progress: number) {
  const labels: Record<string, string> = copy.value.status
  const label = labels[status] || status
  if (status === 'processing') return `${label} ${progress}%`
  return label
}

function handleLanguageChange(event: Event) {
  locale.value = (event as CustomEvent<Locale>).detail || 'zh'
}
</script>

<style scoped>
.dashboard {
  max-width: 860px;
  margin: 0 auto;
}

.dash-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 28px;
}

.dash-header h1 {
  font-size: 28px;
  color: #172033;
  margin: 0;
}

.dash-subtitle {
  margin: 4px 0 0;
  color: #53606f;
  font-size: 14px;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 22px;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  text-decoration: none;
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

.stat-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 36px;
}

.stat-card {
  padding: 22px 24px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(31, 54, 73, 0.06);
  box-shadow: 0 4px 16px rgba(29, 45, 61, 0.04);
}

.stat-label {
  display: block;
  font-size: 13px;
  color: #53606f;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  color: #172033;
}

.stat-value.accent {
  color: #2f7d67;
}

.history-section h2 {
  font-size: 18px;
  color: #172033;
  margin: 0 0 14px;
}

.history-list {
  display: grid;
  gap: 8px;
}

.history-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(31, 54, 73, 0.06);
  transition: all 0.15s ease;
}

.history-row.clickable {
  cursor: pointer;
}

.history-row.clickable:hover {
  border-color: rgba(47, 125, 103, 0.2);
  box-shadow: 0 4px 16px rgba(47, 125, 103, 0.06);
}

.history-info {
  flex: 1;
  min-width: 0;
}

.history-info strong {
  display: block;
  font-size: 15px;
  color: #172033;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-id {
  font-size: 12px;
  color: #8b95a2;
  font-family: "JetBrains Mono", "Cascadia Code", monospace;
}

.history-time {
  font-size: 13px;
  color: #8b95a2;
  white-space: nowrap;
}

.history-status {
  font-size: 12px;
  color: #8b95a2;
  white-space: nowrap;
}

.history-arrow {
  color: #b0bec5;
  flex-shrink: 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 80px 28px;
  text-align: center;
}

.empty-icon {
  color: #b0bec5;
  margin-bottom: 20px;
}

.empty-state h2 {
  font-size: 22px;
  color: #344150;
  margin: 0 0 8px;
}

.empty-state p {
  color: #53606f;
  font-size: 15px;
  margin: 0 0 28px;
}

@media (max-width: 640px) {
  .dash-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .stat-row {
    grid-template-columns: 1fr;
  }
}
</style>
