<template>
  <header class="rewrite-top-nav">
    <div class="brand" role="button" tabindex="0" @click="router.push({ name: 'app-home' })" @keydown.enter="router.push({ name: 'app-home' })">
      <img class="brand-logo" src="/logo-icon.png?v=3" width="36" height="36" alt="PataFix" />
      <strong>PataFix</strong>
    </div>

    <nav class="module-nav" aria-label="PataFix modules">
      <button
        v-for="item in navItems"
        :key="item.key"
        class="nav-item"
        :class="{ active: item.key === 'rewrite' }"
        type="button"
        @click="goModule(item)"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        {{ item.label }}
      </button>
    </nav>

    <div class="risk-overview" aria-label="AIGC 总体疑似度">
      <span>AIGC 总体疑似度</span>
      <div class="progress">
        <i :style="{ width: `${boundedProgress}%` }" />
      </div>
      <strong>{{ Math.round(aigcPercent) }}%</strong>
    </div>

    <div class="user-actions">
      <button class="language-pill" type="button">
        <span>中</span>
        <span>EN</span>
      </button>
      <span class="avatar">1</span>
      <span class="credit">11</span>
      <button class="logout" type="button">退出</button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const navItems = [
  { key: 'home', label: '首页', icon: '⌂', route: { name: 'app-home' } },
  { key: 'dashboard', label: '工作台', icon: '□', route: { name: 'dashboard' } },
  { key: 'new', label: '新建分析', icon: '+', route: { name: 'new-analysis' } },
  { key: 'rewrite', label: '在线改写', icon: '✎', route: null },
  { key: 'account', label: '账户', icon: '●', route: { name: 'account' } },
] as const

type NavItem = typeof navItems[number]

const props = defineProps<{
  aigcPercent: number
  exportLoading: boolean
}>()

defineEmits<{
  (e: 'download-report'): void
  (e: 'export-document'): void
}>()

const router = useRouter()
const boundedProgress = computed(() => Math.max(0, Math.min(100, props.aigcPercent)))

function goModule(item: NavItem) {
  if (item.route) router.push(item.route)
}
</script>

<style scoped>
.rewrite-top-nav {
  height: 64px;
  display: grid;
  grid-template-columns: auto minmax(420px, 1fr) minmax(360px, 520px) auto;
  align-items: center;
  gap: 24px;
  padding: 0 36px;
  background: rgba(255, 253, 247, 0.96);
  color: #20251f;
  border-top: 4px solid transparent;
  border-image: linear-gradient(90deg, #f4b45f 0%, #f48b7c 32%, #9c8bd8 66%, #7aaee8 100%) 1;
  border-bottom: 1px solid rgba(60, 72, 61, 0.12);
  box-shadow: 0 10px 28px rgba(45, 55, 48, 0.06);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 160px;
  cursor: pointer;
}

.brand-logo {
  display: block;
  border-radius: 10px;
}

.brand strong {
  color: #20251f;
  font-size: 22px;
  font-weight: 900;
  letter-spacing: 0;
}

.module-nav {
  display: flex;
  align-items: center;
  gap: 28px;
  min-width: 0;
}

.nav-item {
  height: 44px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 0;
  background: transparent;
  color: #656b61;
  font-size: 16px;
  font-weight: 750;
  cursor: pointer;
  white-space: nowrap;
}

.nav-item.active {
  color: #2f6f53;
}

.nav-icon {
  color: #6f756d;
  font-size: 15px;
  line-height: 1;
}

.risk-overview {
  display: grid;
  grid-template-columns: auto minmax(160px, 1fr) auto;
  align-items: center;
  gap: 14px;
  justify-self: end;
  width: min(520px, 100%);
  color: #1f2937;
  font-size: 15px;
  font-weight: 900;
}

.risk-overview strong {
  color: #07140f;
  font-size: 26px;
  line-height: 1;
  font-weight: 950;
}

.progress {
  height: 12px;
  overflow: hidden;
  border-radius: 999px;
  background: #dfe5dc;
}

.progress i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #f59e0b 0%, #ef4444 100%);
}

.user-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 16px;
  color: #60685f;
  font-size: 15px;
  font-weight: 750;
}

.language-pill {
  height: 38px;
  display: inline-grid;
  grid-template-columns: 1fr 1fr;
  align-items: center;
  gap: 2px;
  padding: 3px;
  border: 1px solid rgba(60, 72, 61, 0.12);
  border-radius: 999px;
  background: #fffefa;
  color: #687166;
  font-size: 13px;
  font-weight: 900;
  box-shadow: 0 8px 18px rgba(32, 37, 31, 0.06);
}

.language-pill span {
  min-width: 30px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 999px;
}

.language-pill span:first-child {
  background: #f0f4eb;
  color: #20251f;
}

.avatar {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: #2f7d59;
  color: #fff;
  font-size: 15px;
  font-weight: 900;
}

.credit {
  color: #2f3b34;
}

.logout {
  border: 0;
  background: transparent;
  color: #9ca3af;
  font-size: 14px;
  font-weight: 750;
  cursor: pointer;
}

@media (max-width: 1320px) {
  .rewrite-top-nav {
    grid-template-columns: auto 1fr;
    height: auto;
    padding: 12px 20px;
  }

  .risk-overview,
  .user-actions {
    justify-self: start;
  }

  .module-nav {
    flex-wrap: wrap;
    gap: 12px 20px;
  }
}

@media (max-width: 760px) {
  .rewrite-top-nav {
    grid-template-columns: 1fr;
  }

  .risk-overview {
    grid-template-columns: 1fr auto;
  }

  .progress {
    grid-column: 1 / -1;
  }
}
</style>
