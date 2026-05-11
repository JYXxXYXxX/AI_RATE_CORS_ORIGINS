<template>
  <div class="app-layout">
    <header class="app-header">
      <div class="app-header-left">
        <router-link to="/app" class="app-logo">
          <img src="/logo-icon.png" width="28" height="28" alt="PataFix" />
          <span>PataFix论文检测</span>
        </router-link>
        <nav class="app-nav">
          <router-link to="/app" class="nav-link" exact-active-class="active">
            <el-icon><HomeFilled /></el-icon>工作台
          </router-link>
          <router-link to="/app/new" class="nav-link" active-class="active">
            <el-icon><CirclePlusFilled /></el-icon>新建分析
          </router-link>
          <router-link to="/app" class="nav-link" active-class="active">
            <el-icon><EditPen /></el-icon>在线改写
          </router-link>
          <router-link to="/app/account" class="nav-link" active-class="active">
            <el-icon><UserFilled /></el-icon>账户
          </router-link>
        </nav>
      </div>
      <div class="app-header-right">
        <div class="credits-badge" v-if="auth.billing">
          <el-icon><Coin /></el-icon>
          <span class="credits-num">{{ auth.credits }}</span>
          <span class="credits-label">剩余次数</span>
        </div>
        <div class="user-info">
          <el-avatar :size="28" class="user-avatar">{{ userInitial }}</el-avatar>
          <span class="user-name">{{ auth.user?.display_name || auth.user?.email }}</span>
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
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { HomeFilled, CirclePlusFilled, UserFilled, Coin, EditPen } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const userInitial = computed(() => {
  const name = auth.user?.display_name || auth.user?.email || 'U'
  return name.charAt(0).toUpperCase()
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
  background: #FAF9F6;
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
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid #E8E6E1;
}

.app-header-left {
  display: flex;
  align-items: center;
  gap: 40px;
}

.app-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 18px;
  font-weight: 700;
  color: #1A1A1A;
  text-decoration: none;
  letter-spacing: -0.3px;
}

.app-logo svg {
  flex-shrink: 0;
}

.app-nav {
  display: flex;
  gap: 8px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #6B6B6B;
  text-decoration: none;
  transition: all 0.15s ease;
}

.nav-link:hover {
  color: #2E7D5A;
  background: #E8F5E9;
}

.nav-link.active {
  color: #2E7D5A;
  background: #E8F5E9;
  font-weight: 600;
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
  background: #2E7D5A;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
}

.user-name {
  font-size: 14px;
  color: #1A1A1A;
  font-weight: 500;
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
