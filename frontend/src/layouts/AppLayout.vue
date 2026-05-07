<template>
  <div class="app-layout">
    <header class="app-header">
      <div class="app-header-left">
        <router-link to="/app" class="app-logo">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none"><circle cx="14" cy="14" r="13" stroke="currentColor" stroke-width="2"/><path d="M8 14.5l3.5 3.5L20 10" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          <span>论文风险预检</span>
        </router-link>
        <nav class="app-nav">
          <router-link to="/app" class="nav-link" exact-active-class="active">工作台</router-link>
          <router-link to="/app/new" class="nav-link" active-class="active">新建分析</router-link>
          <router-link to="/app/account" class="nav-link" active-class="active">账户</router-link>
        </nav>
      </div>
      <div class="app-header-right">
        <div class="credits-badge" v-if="auth.billing">
          <span class="credits-num">{{ auth.credits }}</span>
          <span class="credits-label">次额度</span>
        </div>
        <div class="user-info">
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
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

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
}

.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  padding: 0 28px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(31, 54, 73, 0.08);
}

.app-header-left {
  display: flex;
  align-items: center;
  gap: 32px;
}

.app-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 17px;
  font-weight: 700;
  color: #172033;
  text-decoration: none;
}

.app-logo svg {
  color: #2f7d67;
}

.app-nav {
  display: flex;
  gap: 4px;
}

.nav-link {
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #53606f;
  text-decoration: none;
  transition: all 0.15s ease;
}

.nav-link:hover {
  color: #172033;
  background: rgba(47, 125, 103, 0.06);
}

.nav-link.active {
  color: #2f7d67;
  background: rgba(47, 125, 103, 0.1);
  font-weight: 600;
}

.app-header-right {
  display: flex;
  align-items: center;
  gap: 18px;
}

.credits-badge {
  display: flex;
  align-items: baseline;
  gap: 4px;
  padding: 4px 12px;
  border-radius: 20px;
  background: rgba(47, 125, 103, 0.1);
}

.credits-num {
  font-size: 16px;
  font-weight: 700;
  color: #2f7d67;
}

.credits-label {
  font-size: 12px;
  color: #53606f;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-name {
  font-size: 14px;
  color: #344150;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-text {
  border: none;
  background: none;
  padding: 4px 8px;
  font-size: 13px;
  color: #8b95a2;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.15s;
}

.btn-text:hover {
  color: #c84b52;
  background: rgba(200, 75, 82, 0.06);
}

.app-main {
  flex: 1;
  padding: 28px;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
}

@media (max-width: 768px) {
  .app-header {
    padding: 0 16px;
    gap: 12px;
  }

  .app-header-left {
    gap: 16px;
  }

  .app-logo span {
    display: none;
  }

  .app-nav {
    gap: 2px;
  }

  .nav-link {
    padding: 6px 10px;
    font-size: 13px;
  }

  .user-name {
    display: none;
  }

  .app-main {
    padding: 16px;
  }
}
</style>
