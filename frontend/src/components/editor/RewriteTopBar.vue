<template>
  <header class="rewrite-topbar">
    <div class="rewrite-topbar__brand">
      <div class="brand-mark">P</div>
      <div class="brand-copy">
        <strong>PataFix</strong>
        <span>AIGC 在线改写工作区</span>
      </div>
    </div>

    <nav class="rewrite-topbar__nav">
      <button
        v-for="item in navItems"
        :key="item"
        type="button"
        class="nav-pill"
        :class="{ 'is-active': item === '改写' }"
      >
        {{ item }}
      </button>
    </nav>

    <div class="rewrite-topbar__progress">
      <span class="progress-label">AIGC 总体疑似度</span>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: `${progress}%` }"></div>
      </div>
      <strong>{{ progressLabel }}</strong>
    </div>

    <div class="rewrite-topbar__actions">
      <button type="button" class="action-btn" @click="$emit('download-report')">下载报告</button>
      <button
        type="button"
        class="action-btn action-btn--primary"
        :disabled="exportLoading"
        @click="$emit('export')"
      >
        导出文档
      </button>
      <div class="user-pill">
        <span class="user-avatar">PF</span>
        <div class="user-copy">
          <strong>{{ title }}</strong>
          <span>{{ filename }}</span>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
const navItems = ['检测', '改写', '降 AIGC', '工具箱']

defineProps<{
  title: string
  filename: string
  progress: number
  progressLabel: string
  exportLoading: boolean
}>()

defineEmits<{
  (e: 'download-report'): void
  (e: 'export'): void
}>()
</script>

<style scoped>
.rewrite-topbar {
  display: grid;
  grid-template-columns: auto auto minmax(260px, 340px) auto;
  align-items: center;
  gap: 18px;
  padding: 14px 24px;
  background: linear-gradient(180deg, #0a1511 0%, #0d1f18 100%);
  color: #f4f7f1;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.rewrite-topbar__brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(31, 164, 91, 0.9) 0%, rgba(15, 143, 79, 1) 100%);
  display: grid;
  place-items: center;
  font-size: 18px;
  font-weight: 800;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.18);
}

.brand-copy {
  display: grid;
  gap: 2px;
}

.brand-copy strong {
  font-size: 17px;
  letter-spacing: 0.02em;
}

.brand-copy span {
  color: rgba(226, 232, 240, 0.72);
  font-size: 12px;
}

.rewrite-topbar__nav {
  display: flex;
  align-items: center;
  gap: 10px;
}

.nav-pill {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  color: rgba(241, 245, 249, 0.78);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.nav-pill.is-active {
  background: rgba(31, 164, 91, 0.18);
  border-color: rgba(31, 164, 91, 0.34);
  color: #f8fffb;
}

.rewrite-topbar__progress {
  display: grid;
  gap: 6px;
}

.progress-label {
  font-size: 12px;
  color: rgba(226, 232, 240, 0.72);
}

.progress-track {
  width: 100%;
  height: 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #1fa45b 0%, #44d07c 100%);
}

.rewrite-topbar__progress strong {
  font-size: 16px;
  color: #ffffff;
}

.rewrite-topbar__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.action-btn {
  min-height: 40px;
  padding: 0 16px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.04);
  color: #eff6f0;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.action-btn--primary {
  background: linear-gradient(180deg, #1fa45b 0%, #128347 100%);
  border-color: rgba(31, 164, 91, 0.9);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.user-pill {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  min-width: 220px;
}

.user-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: rgba(31, 164, 91, 0.24);
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 800;
}

.user-copy {
  min-width: 0;
  display: grid;
}

.user-copy strong,
.user-copy span {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-copy strong {
  font-size: 13px;
}

.user-copy span {
  color: rgba(226, 232, 240, 0.68);
  font-size: 11px;
}

@media (max-width: 1500px) {
  .rewrite-topbar {
    grid-template-columns: 1fr;
  }

  .rewrite-topbar__actions {
    justify-content: flex-start;
    flex-wrap: wrap;
  }
}
</style>
