<template>
  <header class="rewrite-topbar">
    <div class="rewrite-topbar__left">
      <button type="button" class="topbar-link" @click="$emit('back')">
        <el-icon><ArrowLeft /></el-icon>
        <span>返回报告</span>
      </button>
      <div class="rewrite-topbar__title">
        <p class="rewrite-topbar__eyebrow">PataFix 在线改写</p>
        <h1>{{ title }}</h1>
        <p class="rewrite-topbar__filename">{{ filename }}</p>
      </div>
    </div>

    <div class="rewrite-topbar__metrics">
      <div v-for="metric in metrics" :key="metric.label" class="metric-chip">
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
      </div>
    </div>

    <div class="rewrite-topbar__actions">
      <el-button @click="$emit('rewrite-all')" :loading="rewriteAllLoading">一键改写</el-button>
      <el-button @click="$emit('undo')" :disabled="!canUndo">
        <el-icon><RefreshLeft /></el-icon>
        撤销
      </el-button>
      <el-button @click="$emit('redo')" :disabled="!canRedo">
        <el-icon><RefreshRight /></el-icon>
        重做
      </el-button>
      <el-button @click="$emit('save')" :loading="saveLoading">保存</el-button>
      <el-button type="primary" @click="$emit('export')" :loading="exportLoading">
        <el-icon><Download /></el-icon>
        导出文档
      </el-button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ArrowLeft, Download, RefreshLeft, RefreshRight } from '@element-plus/icons-vue'

defineProps<{
  title: string
  filename: string
  metrics: Array<{ label: string; value: string }>
  canUndo: boolean
  canRedo: boolean
  saveLoading: boolean
  exportLoading: boolean
  rewriteAllLoading: boolean
}>()

defineEmits<{
  (e: 'back'): void
  (e: 'rewrite-all'): void
  (e: 'undo'): void
  (e: 'redo'): void
  (e: 'save'): void
  (e: 'export'): void
}>()
</script>

<style scoped>
.rewrite-topbar {
  display: grid;
  grid-template-columns: minmax(260px, 1.1fr) minmax(360px, 1fr) auto;
  gap: 18px;
  padding: 18px 24px;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(14px);
}

.rewrite-topbar__left {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.topbar-link {
  border: 0;
  background: transparent;
  color: #2e7d5a;
  font-size: 14px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 0;
}

.rewrite-topbar__title {
  min-width: 0;
}

.rewrite-topbar__eyebrow,
.rewrite-topbar__filename {
  margin: 0;
  color: #6b7280;
}

.rewrite-topbar__eyebrow {
  font-size: 12px;
  font-weight: 700;
}

.rewrite-topbar__title h1 {
  margin: 4px 0;
  font-size: 24px;
  line-height: 1.25;
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.rewrite-topbar__filename {
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.rewrite-topbar__metrics {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

.metric-chip {
  min-height: 72px;
  border-radius: 16px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  padding: 12px;
  display: grid;
  gap: 8px;
}

.metric-chip span {
  font-size: 12px;
  color: #6b7280;
}

.metric-chip strong {
  font-size: 20px;
  color: #0f172a;
}

.rewrite-topbar__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

@media (max-width: 1440px) {
  .rewrite-topbar {
    grid-template-columns: 1fr;
  }

  .rewrite-topbar__metrics {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .rewrite-topbar__actions {
    justify-content: flex-start;
  }
}

@media (max-width: 900px) {
  .rewrite-topbar__metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
