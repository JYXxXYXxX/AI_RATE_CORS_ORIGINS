<template>
  <section class="rewrite-stats-bar">
    <button class="back-btn" type="button" @click="$emit('back-report')">返回报告</button>

    <div class="metrics">
      <article v-for="item in metricItems" :key="item.label" class="metric" :class="item.tone">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </article>
    </div>

    <div class="actions">
      <button class="action primary" type="button" @click="$emit('rewrite-all')">一键改写</button>
      <button class="action" type="button" :disabled="!canUndo" @click="$emit('undo')">撤销</button>
      <button class="action" type="button" :disabled="!canRedo" @click="$emit('redo')">重做</button>
      <button class="action success" type="button" @click="$emit('save')">保存</button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RewriteMetricsState } from './types'

const props = defineProps<{
  metrics: RewriteMetricsState
  canUndo: boolean
  canRedo: boolean
}>()

defineEmits<{
  (e: 'back-report'): void
  (e: 'rewrite-all'): void
  (e: 'undo'): void
  (e: 'redo'): void
  (e: 'save'): void
}>()

const metricItems = computed(() => [
  { label: 'AIGC 疑似度', value: `${Math.round(props.metrics.currentAigcPercent)}%`, tone: 'danger' },
  { label: '重复率', value: `${Math.round(props.metrics.duplicatePercent)}%`, tone: 'warning' },
  { label: '优化后预计', value: `${Math.round(props.metrics.estimatedOptimizedPercent)}%`, tone: 'brand' },
  {
    label: '已改写',
    value: `${props.metrics.rewrittenCount} / ${Math.max(props.metrics.totalRiskCount, 0)}`,
    tone: 'brand',
  },
  { label: '字数', value: props.metrics.wordCount.toLocaleString('zh-CN'), tone: 'plain' },
])
</script>

<style scoped>
.rewrite-stats-bar {
  min-height: 96px;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 18px;
  padding: 16px 24px;
  background: #fbfcf8;
  border-bottom: 1px solid #e5e7eb;
}

.back-btn {
  height: 42px;
  padding: 0 16px;
  border: 0;
  border-radius: 999px;
  background: rgba(15, 143, 79, 0.09);
  color: #0f8f4f;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(5, minmax(120px, 1fr));
  gap: 12px;
}

.metric {
  min-width: 0;
  padding: 13px 15px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid #e5e7eb;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
  display: grid;
  gap: 5px;
}

.metric span {
  color: #6b7280;
  font-size: 12px;
  font-weight: 700;
}

.metric strong {
  color: #111827;
  font-size: 23px;
  line-height: 1;
}

.metric.danger strong {
  color: #ef4444;
}

.metric.warning strong {
  color: #f59e0b;
}

.metric.brand strong {
  color: #0f8f4f;
}

.actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.action {
  height: 42px;
  padding: 0 15px;
  border: 1px solid #d1d5db;
  border-radius: 12px;
  background: #fff;
  color: #1f2937;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
}

.action.primary {
  border-color: #0f8f4f;
  background: #0f8f4f;
  color: #fff;
}

.action.success {
  border-color: rgba(15, 143, 79, 0.25);
  background: rgba(15, 143, 79, 0.08);
  color: #0f8f4f;
}

.action:disabled {
  opacity: 0.46;
  cursor: not-allowed;
}

@media (max-width: 1320px) {
  .rewrite-stats-bar {
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .metrics {
    grid-template-columns: repeat(3, minmax(120px, 1fr));
  }

  .actions {
    justify-content: flex-start;
  }
}

@media (max-width: 760px) {
  .metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
