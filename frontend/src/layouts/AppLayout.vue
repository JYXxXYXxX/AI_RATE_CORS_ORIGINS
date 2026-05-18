<template>
  <div class="app-layout">
    <div class="page-load-bar" :class="{ loaded: pageLoaded }" aria-hidden="true" />
    <header class="app-header">
      <div class="app-header-left">
        <router-link to="/app" class="app-logo">
          <img class="app-logo-mark" :src="logoSrc" width="28" height="28" alt="PataFix" />
          <span>PataFix</span>
        </router-link>
        <nav class="app-nav">
          <router-link to="/app" class="nav-link" exact-active-class="active">
            <el-icon><HomeFilled /></el-icon>{{ ui.home }}
          </router-link>
          <router-link to="/app/dashboard" class="nav-link" active-class="active">
            <el-icon><DataBoard /></el-icon>{{ ui.dashboard }}
          </router-link>
          <router-link to="/app/new" class="nav-link" active-class="active">
            <el-icon><CirclePlusFilled /></el-icon>{{ ui.newAnalysis }}
          </router-link>
          <router-link v-if="latestRunId" :to="`/app/rewrite/${latestRunId}`" class="nav-link" active-class="active">
            <el-icon><EditPen /></el-icon>{{ ui.rewrite }}
          </router-link>
          <router-link to="/app/account" class="nav-link" active-class="active">
            <el-icon><UserFilled /></el-icon>{{ ui.account }}
          </router-link>
        </nav>
      </div>
      <div class="app-header-right">
        <button class="header-toggle theme-toggle" type="button" :class="{ active: theme === 'dark' }" :aria-label="ui.themeToggle" @click="toggleTheme">
          <span class="toggle-switch" aria-hidden="true">
            <span class="toggle-knob">{{ theme === 'dark' ? '夜' : '日' }}</span>
          </span>
          <span class="toggle-label">{{ theme === 'dark' ? ui.dark : ui.light }}</span>
        </button>
        <button class="header-toggle language-toggle" type="button" :class="{ active: language === 'en' }" :aria-label="ui.languageToggle" @click="toggleLanguage">
          <span class="language-pill" aria-hidden="true">
            <span class="language-slider" />
            <span>中</span>
            <span>EN</span>
          </span>
        </button>
        <!-- 付费功能已隐藏 -->
        <!-- <div class="credits-badge" v-if="auth.billing">
          <el-icon><Coin /></el-icon>
          <span class="credits-num">{{ auth.credits }}</span>
          <span class="credits-label">剩余次数</span>
        </div> -->
        <div class="user-info">
          <el-avatar :size="28" class="user-avatar">{{ userInitial }}</el-avatar>
          <router-link to="/app/account" class="user-name">{{ auth.user?.display_name || auth.user?.email }}</router-link>
          <button class="btn-text" @click="handleLogout">{{ ui.logout }}</button>
        </div>
      </div>
    </header>
    <main class="app-main">
      <router-view />
    </main>
    <footer class="app-footer">
      <div class="footer-brand">
        <strong>PataFix</strong>
        <span>{{ ui.footerTagline }}</span>
      </div>
      <div class="footer-links">
        <router-link to="/app/new">{{ ui.footerUpload }}</router-link>
        <router-link to="/app/dashboard">{{ ui.footerDashboard }}</router-link>
        <router-link to="/app/account">{{ ui.footerAccount }}</router-link>
      </div>
      <p>{{ ui.footerPrivacy }}</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { HomeFilled, CirclePlusFilled, UserFilled, Coin, EditPen, DataBoard } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import { useAnalysisStore } from '../stores/analysis'

const auth = useAuthStore()
const analysis = useAnalysisStore()
const router = useRouter()
type ThemeMode = 'light' | 'dark'
type LanguageMode = 'zh' | 'en'

const theme = ref<ThemeMode>((localStorage.getItem('patafix-theme') as ThemeMode) || 'light')
const language = ref<LanguageMode>((localStorage.getItem('patafix-language') as LanguageMode) || 'zh')
const pageLoaded = ref(false)

const userInitial = computed(() => {
  const name = auth.user?.display_name || auth.user?.email || 'U'
  return name.charAt(0).toUpperCase()
})

const latestRunId = computed(() => analysis.history.find(item => item.run_id)?.run_id || '')
const logoSrc = computed(() => (theme.value === 'dark' ? '/logo-icon1.png?v=3' : '/logo-icon.png?v=3'))
const ui = computed(() => {
  if (language.value === 'en') {
    return {
      home: 'Home',
      dashboard: 'Workspace',
      newAnalysis: 'New scan',
      rewrite: 'Rewrite',
      account: 'Account',
      logout: 'Sign out',
      light: 'Light',
      dark: 'Dark',
      themeToggle: 'Switch color theme',
      languageToggle: 'Switch language',
      footerTagline: 'Risk-aware thesis rewriting with document-format preservation.',
      footerUpload: 'Upload paper',
      footerDashboard: 'Workspace',
      footerAccount: 'Account',
      footerPrivacy: 'Default: no shared learning. Official reports and feedback are used only under the permission mode selected by the user.'
    }
  }
  return {
    home: '首页',
    dashboard: '工作台',
    newAnalysis: '新建分析',
    rewrite: '在线改写',
    account: '账户',
    logout: '退出',
    light: '日间',
    dark: '夜间',
    themeToggle: '切换日夜模式',
    languageToggle: '切换中英文',
    footerTagline: '面向论文查重与 AIGC 风险优化的格式保留改写工作台。',
    footerUpload: '上传论文',
    footerDashboard: '查看工作台',
    footerAccount: '账户设置',
    footerPrivacy: '默认不参与共享学习；官方报告与回填结果仅按用户选择的授权范围用于校准。'
  }
})

onMounted(() => {
  applyTheme()
  applyLanguage()
  requestAnimationFrame(() => {
    pageLoaded.value = true
  })
  analysis.refreshHistory()
})

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  localStorage.setItem('patafix-theme', theme.value)
  applyTheme()
}

function toggleLanguage() {
  language.value = language.value === 'zh' ? 'en' : 'zh'
  localStorage.setItem('patafix-language', language.value)
  applyLanguage()
}

function applyTheme() {
  document.documentElement.dataset.theme = theme.value
}

function applyLanguage() {
  document.documentElement.dataset.lang = language.value
  window.dispatchEvent(new CustomEvent('patafix:language-change', { detail: language.value }))
}
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background:
    linear-gradient(180deg, #f7f3ea 0%, #f2f6ef 42%, #f7f4ee 100%);
  color: #20251f;
  transition:
    background 0.28s ease,
    color 0.28s ease;
}

.page-load-bar {
  position: fixed;
  top: 0;
  left: 0;
  z-index: 200;
  width: 100%;
  height: 4px;
  background: linear-gradient(90deg, #ffd166, #ff8f7f, #8ab4ff);
  box-shadow: 0 0 18px rgba(138, 180, 255, 0.38);
  opacity: 0;
  transform: scaleX(0);
  transform-origin: left center;
  transition:
    transform 1.15s cubic-bezier(0.18, 0.82, 0.25, 1),
    opacity 0.25s ease;
}

.page-load-bar.loaded {
  opacity: 1;
  transform: scaleX(1);
}

.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  padding: 0 28px;
  background: rgba(255, 253, 247, 0.94);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(60, 72, 61, 0.1);
  box-shadow: 0 10px 34px rgba(46, 56, 48, 0.06);
  transition:
    background 0.25s ease,
    border-color 0.25s ease,
    box-shadow 0.25s ease;
}

.app-header-left {
  display: flex;
  align-items: center;
  gap: 34px;
}

.app-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 700;
  color: #20251f;
  text-decoration: none;
  letter-spacing: -0.3px;
  transition:
    color 0.22s ease,
    transform 0.22s ease;
}

.app-logo:hover {
  transform: translateY(-1px);
}

.app-logo-mark {
  flex-shrink: 0;
  display: block;
  border-radius: 9px;
  transition:
    opacity 0.24s ease,
    transform 0.24s ease,
    filter 0.24s ease,
    box-shadow 0.24s ease;
}

.app-logo:hover .app-logo-mark {
  transform: rotate(-3deg) scale(1.04);
}

.app-nav {
  display: flex;
  gap: 6px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  color: #64685f;
  text-decoration: none;
  transition: all 0.15s ease;
}

.nav-link:hover {
  color: #285d47;
  background: #ece8da;
}

.nav-link.active {
  color: #1f6749;
  background: #dcecdf;
  font-weight: 800;
  box-shadow: inset 0 -2px 0 rgba(31, 103, 73, 0.16);
}

.app-header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-toggle {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 36px;
  min-width: 74px;
  padding: 0 11px;
  border: 1px solid rgba(60, 72, 61, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.68);
  color: #2f3b34;
  font: inherit;
  font-size: 12px;
  font-weight: 800;
  cursor: pointer;
  overflow: hidden;
  transition:
    transform 0.2s ease,
    color 0.22s ease,
    border-color 0.22s ease,
    background 0.22s ease,
    box-shadow 0.22s ease;
}

.header-toggle:hover {
  transform: translateY(-1px);
  border-color: rgba(47, 111, 83, 0.35);
  background: #f4eddd;
}

.theme-toggle {
  min-width: 84px;
  padding-left: 8px;
}

.toggle-switch {
  position: relative;
  width: 34px;
  height: 20px;
  border-radius: 999px;
  background: linear-gradient(135deg, #fff7df, #f2e4bc);
  box-shadow: inset 0 0 0 1px rgba(69, 72, 61, 0.1);
  transition:
    background 0.26s ease,
    box-shadow 0.26s ease;
}

.toggle-knob {
  position: absolute;
  top: 3px;
  left: 3px;
  display: grid;
  place-items: center;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #ffd166;
  color: #5b4212;
  font-size: 9px;
  line-height: 1;
  box-shadow: 0 3px 8px rgba(75, 58, 24, 0.18);
  transition:
    transform 0.32s cubic-bezier(0.2, 0.8, 0.2, 1),
    background 0.26s ease,
    color 0.26s ease,
    box-shadow 0.26s ease;
}

.theme-toggle.active .toggle-switch {
  background: linear-gradient(135deg, #111827, #202742);
  box-shadow: inset 0 0 0 1px rgba(159, 194, 255, 0.25);
}

.theme-toggle.active .toggle-knob {
  transform: translateX(14px);
  background: #8ab4ff;
  color: #050608;
  box-shadow: 0 3px 10px rgba(138, 180, 255, 0.3);
}

.toggle-label {
  min-width: 28px;
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}

.language-toggle {
  min-width: auto;
  width: 76px;
  padding: 0 7px;
}

.language-pill {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 1fr;
  align-items: center;
  width: 62px;
  height: 24px;
  padding: 2px;
  border-radius: 999px;
  background: rgba(32, 37, 31, 0.07);
  color: #657066;
  transition:
    background 0.24s ease,
    color 0.24s ease;
}

.language-pill span:not(.language-slider) {
  position: relative;
  z-index: 1;
  text-align: center;
  font-size: 11px;
  transition:
    color 0.24s ease,
    transform 0.24s ease;
}

.language-pill span:nth-child(2) {
  color: #20251f;
}

.language-toggle.active .language-pill span:nth-child(2) {
  color: #657066;
}

.language-toggle.active .language-pill span:nth-child(3) {
  color: #20251f;
}

.language-slider {
  position: absolute;
  inset: 3px auto 3px 3px;
  width: 28px;
  border-radius: 999px;
  background: #fffdf7;
  box-shadow: 0 4px 12px rgba(42, 47, 39, 0.12);
  transition:
    transform 0.32s cubic-bezier(0.2, 0.8, 0.2, 1),
    background 0.24s ease,
    box-shadow 0.24s ease;
}

.language-toggle.active .language-slider {
  transform: translateX(28px);
}

.credits-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: #FFF3E0;
  border-radius: 20px;
  font-size: 13px;
  color: #E65100;
  font-weight: 600;
}

.credits-label {
  font-weight: 400;
  opacity: 0.8;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-avatar {
  background: #2f6f53;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
}

.user-name {
  font-size: 14px;
  color: #2c332d;
  font-weight: 500;
  text-decoration: none;
  border-radius: 8px;
  padding: 5px 6px;
}

.user-name:hover {
  background: #ece8da;
  color: #1f6749;
}

.btn-text {
  background: none;
  border: none;
  color: #9E9E9E;
  font-size: 13px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: color 0.15s;
}

.btn-text:hover {
  color: #D32F2F;
  background: #FFEBEE;
}

.app-main {
  flex: 1;
  min-height: 0;
}

.app-footer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 14px 24px;
  align-items: center;
  padding: 24px 28px 30px;
  border-top: 1px solid rgba(60, 72, 61, 0.1);
  background: rgba(255, 253, 247, 0.74);
  color: #62695f;
}

.footer-brand {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}

.footer-brand strong {
  color: #20251f;
  font-size: 16px;
}

.footer-brand span,
.app-footer p {
  line-height: 1.7;
}

.footer-links {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.footer-links a {
  color: #2f6f53;
  font-size: 13px;
  font-weight: 800;
  text-decoration: none;
}

.footer-links a:hover {
  text-decoration: underline;
}

.app-footer p {
  grid-column: 1 / -1;
  font-size: 12px;
}

:global(html[data-theme='dark']) .app-layout {
  background:
    radial-gradient(circle at 12% 12%, rgba(138, 180, 255, 0.12), transparent 28%),
    radial-gradient(circle at 82% 10%, rgba(255, 122, 112, 0.1), transparent 26%),
    linear-gradient(180deg, #050608 0%, #0b0c10 52%, #030405 100%);
  color: #f4f1eb;
}

:global(html[data-theme='dark']) .app-header {
  background: rgba(7, 8, 11, 0.92);
  border-bottom-color: rgba(232, 235, 245, 0.1);
  box-shadow: 0 14px 38px rgba(0, 0, 0, 0.28);
}

:global(html[data-theme='dark']) .app-logo,
:global(html[data-theme='dark']) .user-name,
:global(html[data-theme='dark']) .footer-brand strong {
  color: #f5f1e8;
}

:global(html[data-theme='dark']) .app-logo-mark {
  box-shadow: 0 0 0 1px rgba(159, 194, 255, 0.12), 0 8px 22px rgba(138, 180, 255, 0.16);
}

:global(html[data-theme='dark']) .nav-link {
  color: #c9ced8;
}

:global(html[data-theme='dark']) .nav-link:hover {
  color: #9fc2ff;
  background: rgba(255, 255, 255, 0.08);
}

:global(html[data-theme='dark']) .nav-link.active {
  color: #9fc2ff;
  background: rgba(138, 180, 255, 0.14);
  box-shadow: inset 0 -2px 0 rgba(138, 180, 255, 0.28);
}

:global(html[data-theme='dark']) .header-toggle {
  color: #f4f0e7;
  border-color: rgba(255, 255, 255, 0.13);
  background: rgba(255, 255, 255, 0.08);
}

:global(html[data-theme='dark']) .header-toggle:hover {
  border-color: rgba(138, 180, 255, 0.4);
  background: rgba(138, 180, 255, 0.13);
}

:global(html[data-theme='dark']) .language-pill {
  background: rgba(255, 255, 255, 0.08);
  color: #c9ced8;
}

:global(html[data-theme='dark']) .language-pill span:nth-child(2),
:global(html[data-theme='dark']) .language-toggle.active .language-pill span:nth-child(3) {
  color: #f4f1eb;
}

:global(html[data-theme='dark']) .language-toggle.active .language-pill span:nth-child(2) {
  color: #c9ced8;
}

:global(html[data-theme='dark']) .language-slider {
  background: rgba(138, 180, 255, 0.22);
  box-shadow: 0 4px 14px rgba(138, 180, 255, 0.16);
}

:global(html[data-theme='dark']) .user-avatar {
  background: #8ab4ff;
  color: #050608;
}

:global(html[data-theme='dark']) .user-name:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #9fc2ff;
}

:global(html[data-theme='dark']) .app-footer {
  border-top-color: rgba(232, 235, 245, 0.1);
  background: rgba(5, 6, 8, 0.78);
  color: #c9ced8;
}

:global(html[data-theme='dark']) .footer-links a {
  color: #9fc2ff;
}

@media (max-width: 900px) {
  .app-header {
    align-items: flex-start;
    height: auto;
    min-height: 64px;
    padding: 12px 16px;
    gap: 12px;
  }

  .app-header-left,
  .app-header-right {
    flex-wrap: wrap;
  }

  .app-header-left {
    gap: 12px;
  }

  .app-nav {
    order: 3;
    width: 100%;
    overflow-x: auto;
    padding-bottom: 2px;
  }

  .user-name {
    max-width: 120px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .app-footer {
    grid-template-columns: 1fr;
  }

  .footer-links {
    justify-content: flex-start;
  }
}
</style>
