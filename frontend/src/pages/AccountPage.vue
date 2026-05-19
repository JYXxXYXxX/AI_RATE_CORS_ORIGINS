<template>
  <div class="account-page">
    <section class="account-hero">
      <div>
        <p class="eyebrow">{{ copy.eyebrow }}</p>
        <h1>{{ copy.title }}</h1>
        <p>{{ copy.subtitle }}</p>
      </div>
      <div class="identity-card">
        <div class="identity-avatar">{{ userInitial }}</div>
        <div>
          <strong>{{ auth.user?.display_name || copy.defaultUser }}</strong>
          <span>{{ auth.user?.email }}</span>
        </div>
      </div>
    </section>

    <div class="account-grid">
      <section class="card profile-card">
        <h2>{{ copy.profile }}</h2>
        <div class="info-list">
          <div class="info-item">
            <span class="info-label">{{ copy.nickname }}</span>
            <span>{{ auth.user?.display_name || copy.notSet }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ copy.email }}</span>
            <span>{{ auth.user?.email }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ copy.created }}</span>
            <span>{{ formatDate(auth.user?.created_at) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ copy.status }}</span>
            <span class="status-badge">{{ auth.user?.status || copy.normal }}</span>
          </div>
        </div>
      </section>

      <section class="card action-card">
        <h2>{{ copy.actions }}</h2>
        <div class="action-list">
          <router-link to="/app/new" class="action-item">
            <strong>{{ copy.uploadNew }}</strong>
            <span>{{ copy.uploadDesc }}</span>
          </router-link>
          <router-link to="/app/dashboard" class="action-item">
            <strong>{{ copy.history }}</strong>
            <span>{{ copy.historyDesc }}</span>
          </router-link>
        </div>
      </section>
    </div>

    <section class="card note-card">
      <h2>{{ copy.version }}</h2>
      <p>{{ copy.versionDesc }}</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
type Locale = 'zh' | 'en'
const locale = ref<Locale>((localStorage.getItem('patafix-language') as Locale) || 'zh')

const copy = computed(() => locale.value === 'en'
  ? {
      eyebrow: 'Account',
      title: 'Account',
      subtitle: 'Review account status, quick actions, and document workflow.',
      defaultUser: 'PataFix user',
      profile: 'Profile',
      nickname: 'Nickname',
      notSet: 'Not set',
      email: 'Email',
      created: 'Created',
      status: 'Status',
      normal: 'Active',
      actions: 'Quick actions',
      uploadNew: 'Upload new paper',
      uploadDesc: 'Start a new similarity / AIGC scan',
      history: 'View history',
      historyDesc: 'Return to the workspace and continue existing papers',
      version: 'Current version',
      versionDesc: 'This account center currently focuses on paper scan records, report access, and rewrite progress.'
    }
  : {
      eyebrow: 'Account',
      title: '账户',
      subtitle: '查看账号状态、最近使用入口和文档工作流。',
      defaultUser: 'PataFix 用户',
      profile: '基本信息',
      nickname: '昵称',
      notSet: '未设置',
      email: '邮箱',
      created: '注册时间',
      status: '状态',
      normal: '正常',
      actions: '快捷操作',
      uploadNew: '上传新论文',
      uploadDesc: '开始一次新的查重 / AIGC 分析',
      history: '查看历史报告',
      historyDesc: '回到工作台继续处理已有论文',
      version: '当前版本说明',
      versionDesc: '当前账户中心只保留检测记录、报告查看和在线改写相关信息。'
    })

const userInitial = computed(() => {
  const name = auth.user?.display_name || auth.user?.email || 'U'
  return name.charAt(0).toUpperCase()
})

onMounted(() => {
  window.addEventListener('patafix:language-change', handleLanguageChange)
})

onBeforeUnmount(() => {
  window.removeEventListener('patafix:language-change', handleLanguageChange)
})

function formatDate(iso: string | undefined) {
  if (!iso) return '-'
  return new Date(iso).toLocaleDateString(locale.value === 'en' ? 'en-US' : 'zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

function handleLanguageChange(event: Event) {
  locale.value = (event as CustomEvent<Locale>).detail || 'zh'
}
</script>

<style scoped>
.account-page {
  max-width: 1060px;
  margin: 0 auto;
  padding: 34px 28px 48px;
}

.account-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
  padding: 28px;
  border-radius: 24px;
  background: #fffdf7;
  border: 1px solid rgba(58, 67, 61, 0.1);
  box-shadow: 0 18px 50px rgba(46, 56, 48, 0.08);
}

.eyebrow {
  color: #9b7750;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.account-hero h1 {
  font-size: 34px;
  color: #20251f;
  margin: 0 0 6px;
}

.account-hero p {
  color: #62695f;
  font-size: 15px;
  margin: 0;
}

.identity-card {
  min-width: 280px;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px;
  border-radius: 18px;
  background: #f0eadf;
}

.identity-avatar {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  color: #fff;
  background: #2f6f53;
  font-weight: 900;
}

.identity-card strong,
.identity-card span {
  display: block;
}

.identity-card span {
  margin-top: 4px;
  color: #62695f;
  font-size: 13px;
}

.account-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}

.card {
  padding: 24px;
  border-radius: 18px;
  background: rgba(255, 253, 247, 0.94);
  border: 1px solid rgba(58, 67, 61, 0.1);
  box-shadow: 0 12px 34px rgba(46, 56, 48, 0.06);
  margin-bottom: 16px;
}

.card h2 {
  font-size: 18px;
  color: #20251f;
  margin: 0 0 16px;
}

.card h3 {
  font-size: 16px;
  color: #172033;
  margin: 0 0 8px;
}

.card-hint {
  color: #8b95a2;
  font-size: 13px;
  margin: 4px 0 16px;
}

.info-list {
  display: grid;
  gap: 12px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid rgba(31, 54, 73, 0.04);
  font-size: 14px;
  color: #344150;
}

.info-label {
  color: #8b95a2;
  font-size: 13px;
}

.status-badge {
  padding: 2px 10px;
  border-radius: 6px;
  background: rgba(47, 125, 103, 0.1);
  color: #2f7d67;
  font-size: 13px;
  font-weight: 600;
}

.action-list {
  display: grid;
  gap: 12px;
}

.action-item {
  display: grid;
  gap: 5px;
  padding: 16px;
  border-radius: 14px;
  text-decoration: none;
  color: #20251f;
  background: #f4efe3;
  border: 1px solid rgba(58, 67, 61, 0.08);
}

.action-item:hover {
  border-color: rgba(47, 111, 83, 0.28);
  background: #edf3e8;
}

.action-item span,
.note-card p {
  color: #62695f;
  line-height: 1.7;
}

.credits-display {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 6px;
}

.credits-display strong {
  font-size: 48px;
  color: #2f7d67;
  line-height: 1;
}

.credits-display span {
  font-size: 16px;
  color: #53606f;
}

.channel-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}

.channel-label {
  font-size: 13px;
  color: #53606f;
  font-weight: 600;
}

.channel-options {
  display: flex;
  gap: 8px;
}

.channel-btn {
  padding: 8px 16px;
  border: 1.5px solid rgba(31, 54, 73, 0.12);
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s;
  display: grid;
  gap: 2px;
}

.channel-btn strong {
  font-size: 14px;
  color: #344150;
}

.channel-btn small {
  font-size: 11px;
  color: #8b95a2;
}

.channel-btn.active {
  border-color: #2f7d67;
  background: rgba(47, 125, 103, 0.04);
}

.channel-btn.muted {
  opacity: 0.6;
}

.package-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 14px;
}

.package-card {
  padding: 20px;
  border-radius: 14px;
  border: 1px solid rgba(31, 54, 73, 0.06);
  background: #f9fbfa;
}

.package-desc {
  font-size: 13px;
  color: #53606f;
  margin: 0 0 12px;
  line-height: 1.5;
}

.package-price {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 14px;
}

.package-price strong {
  font-size: 24px;
  color: #172033;
}

.package-price span {
  font-size: 13px;
  color: #8b95a2;
}

.pending-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid rgba(31, 54, 73, 0.06);
}

.pending-card {
  padding: 16px;
  border-radius: 12px;
  background: #fffbf0;
  border: 1px solid rgba(212, 154, 75, 0.2);
}

.pending-info {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: #344150;
  margin-bottom: 10px;
}

.order-list {
  display: grid;
  gap: 6px;
}

.order-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(31, 54, 73, 0.04);
  font-size: 13px;
  color: #344150;
}

.order-no {
  font-family: "JetBrains Mono", monospace;
  color: #8b95a2;
  font-size: 12px;
}

.order-status {
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.order-status.paid,
.order-status.completed {
  background: rgba(47, 125, 103, 0.1);
  color: #2f7d67;
}

.order-status.pending {
  background: rgba(212, 154, 75, 0.15);
  color: #a1720d;
}

.order-time {
  color: #8b95a2;
  margin-left: auto;
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
  text-decoration: none;
  transition: all 0.18s ease;
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

@media (max-width: 640px) {
  .account-grid {
    grid-template-columns: 1fr;
  }

  .package-grid {
    grid-template-columns: 1fr;
  }
}
</style>
