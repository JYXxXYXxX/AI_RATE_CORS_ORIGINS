<template>
  <section class="rewrite-stats">
    <div class="rewrite-stats__left">
      <button type="button" class="stats-link" @click="$emit('back')">
        返回报告
      </button>

      <div class="stats-metrics">
        <article
          v-for="metric in metrics"
          :key="metric.label"
          class="stats-metric"
          :class="metric.tone ? `is-${metric.tone}` : ''"
        >
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value }}</strong>
          <small v-if="metric.helper">{{ metric.helper }}</small>
        </article>
      </div>
    </div>

    <div class="rewrite-stats__actions">
      <button
        type="button"
        class="tool-btn tool-btn--primary"
        :disabled="rewriteAllLoading"
        @click="$emit('rewrite-all')"
      >
        一键改写
      </button>
      <button type="button" class="tool-btn" :disabled="!canUndo" @click="$emit('undo')">
        撤销
      </button>
      <button type="button" class="tool-btn" :disabled="!canRedo" @click="$emit('redo')">
        重做
      </button>
      <button
        type="button"
        class="tool-btn tool-btn--success"
        :disabled="saveLoading"
        @click="$emit('save')"
      >
        保存
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  metrics: Array<{
    label: string
    value: string
    helper?: string
    tone?: 'high' | 'medium' | 'low' | 'brand'
  }>
  canUndo: boolean
  canRedo: boolean
  saveLoading: boolean
  rewriteAllLoading: boolean
}>()

defineEmits<{
  (e: 'back'): void
  (e: 'rewrite-all'): void
  (e: 'undo'): void
  (e: 'redo'): void
  (e: 'save'): void
}>()
</script>

<style scoped>
.rewrite-stats {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 18px;
  padding: 16px 24px 18px;
  background: linear-gradient(180deg, rgba(252, 252, 249, 0.98) 0%, rgba(247, 248, 244, 0.98) 100%);
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
}

.rewrite-stats__left {
  min-width: 0;
  display: grid;
  gap: 14px;
  flex: 1;
}

.stats-link {
  justify-self: start;
  border: 0;
  background: rgba(15, 143, 79, 0.08);
  color: #0f8f4f;
  border-radius: 999px;
  padding: 9px 14px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.stats-metrics {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
}

.stats-metric {
  padding: 14px 16px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.05);
  display: grid;
  gap: 4px;
}

.stats-metric span {
  font-size: 12px;
  color: #6b7280;
  font-weight: 600;
}

.stats-metric strong {
  font-size: 24px;
  line-height: 1.1;
  color: #111827;
}

.stats-metric small {
  font-size: 12px;
  color: #94a3b8;
}

.stats-metric.is-high strong {
  color: #dc2626;
}

.stats-metric.is-medium strong {
  color: #d97706;
}

.stats-metric.is-low strong {
  color: #7c3aed;
}

.stats-metric.is-brand strong {
  color: #0f8f4f;
}

.rewrite-stats__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.tool-btn {
  min-height: 44px;
  padding: 0 18px;
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: #ffffff;
  color: #1f2937;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition:
    transform 0.16s ease,
    box-shadow 0.16s ease,
    border-color 0.16s ease,
    background 0.16s ease;
}

.tool-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 12px 22px rgba(15, 23, 42, 0.08);
}

.tool-btn:disabled {
  opacity: 0.48;
  cursor: not-allowed;
}

.tool-btn--primary {
  background: linear-gradient(180deg, #11a75a 0%, #0f8f4f 100%);
  border-color: #0f8f4f;
  color: #ffffff;
}

.tool-btn--success {
  border-color: rgba(15, 143, 79, 0.24);
  background: rgba(15, 143, 79, 0.08);
  color: #0f8f4f;
}

@media (max-width: 1440px) {
  .rewrite-stats {
    flex-direction: column;
  }

  .stats-metrics {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .rewrite-stats__actions {
    justify-content: flex-start;
  }
}

@media (max-width: 900px) {
  .stats-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
