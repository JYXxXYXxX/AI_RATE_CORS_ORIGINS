<template>
  <div class="app-layout">
    <header class="app-header">
      <div class="app-header-left">
        <router-link to="/app" class="app-logo">
          <img src="/logo-icon.png?v=2" width="28" height="28" alt="PataFix" />
          <span>PataFix论文检测</span>
        </router-link>
        <nav class="app-nav">
          <router-link to="/app" class="nav-link" exact-active-class="active">
            <el-icon><HomeFilled /></el-icon>首页
          </router-link>
          <router-link to="/app/dashboard" class="nav-link" active-class="active">
            <el-icon><DataBoard /></el-icon>工作台
          </router-link>
          <router-link to="/app/new" class="nav-link" active-class="active">
            <el-icon><CirclePlusFilled /></el-icon>新建分析
          </router-link>
          <router-link v-if="latestRunId" :to="`/app/rewrite/${latestRunId}`" class="nav-link" active-class="active">
            <el-icon><EditPen /></el-icon>在线改写
          </router-link>
          <router-link to="/app/account" class="nav-link" active-class="active">
            <el-icon><UserFilled /></el-icon>账户
          </router-link>
        </nav>
      </div>
      <div class="app-header-right">
        <!-- 付费功能已隐藏 -->
        <!-- <div class="credits-badge" v-if="auth.billing">
          <el-icon><Coin /></el-icon>
          <span class="credits-num">{{ auth.credits }}</span>
          <span class="credits-label">剩余次数</span>
        </div> -->
        <div class="user-info">
          <el-avatar :size="28" class="user-avatar">{{ userInitial }}</el-avatar>
          <router-link to="/app/account" class="user-name">{{ auth.user?.display_name || auth.user?.email }}</router-link>
          <button class="btn-text" @click="handleLogout">退出</button>
        </div>
      </div>
    </header>
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { HomeFilled, CirclePlusFilled, UserFilled, Coin, EditPen, DataBoard } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import { useAnalysisStore } from '../stores/analysis'

const auth = useAuthStore()
const analysis = useAnalysisStore()
const router = useRouter()

const userInitial = computed(() => {
  const name = auth.user?.display_name || auth.user?.email || 'U'
  return name.charAt(0).toUpperCase()
})

const latestRunId = computed(() => analysis.history.find(item => item.run_id)?.run_id || '')

onMounted(() => {
  analysis.refreshHistory()
})

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background:
    linear-gradient(180deg, #f7f3ea 0%, #f2f6ef 42%, #f7f4ee 100%);
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
}

.app-logo svg {
  flex-shrink: 0;
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
  gap: 20px;
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
</style>
