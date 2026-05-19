<template>
  <aside class="suggestion-panel">
    <div class="suggestion-panel__header">
      <div>
        <p class="suggestion-panel__eyebrow">批注与改写建议</p>
        <h3>风险处理面板</h3>
      </div>
      <span class="suggestion-panel__count">{{ visibleItems.length }}</span>
    </div>

    <div class="risk-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        type="button"
        class="risk-tab"
        :class="[{ 'is-active': activeTab === tab.value }, `is-${tab.value}`]"
        @click="$emit('change-tab', tab.value)"
      >
        <span>{{ tab.label }}</span>
        <strong>{{ tabCounts[tab.value] }}</strong>
      </button>
    </div>

    <section v-if="activeItem" class="focus-card" :class="`is-${effectiveLevel(activeItem)}`">
      <div class="focus-card__meta">
        <span class="focus-card__level">{{ levelLabel(effectiveLevel(activeItem), activeStatus) }}</span>
        <span class="focus-card__score">AIGC 疑似度 {{ Math.round(activeItem.aigcScore) }}%</span>
      </div>

      <div class="focus-card__section">
        <h4>风险说明</h4>
        <p>{{ activeItem.diagnosis }}</p>
      </div>

      <div class="focus-card__section">
        <h4>原文</h4>
        <p>{{ activeItem.originalText }}</p>
      </div>

      <div class="focus-card__section focus-card__section--rewrite">
        <h4>改写建议</h4>
        <p>{{ suggestionText }}</p>
      </div>

      <div class="focus-card__section">
        <h4>改写原理</h4>
        <p>{{ principleText }}</p>
      </div>

      <div class="focus-card__actions">
        <button type="button" class="mini-btn" :disabled="!hasPrevious" @click="$emit('previous')">上一条</button>
        <button type="button" class="mini-btn" :disabled="!hasNext" @click="$emit('next')">下一条</button>
        <button
          type="button"
          class="mini-btn mini-btn--primary"
          :disabled="applyLoading"
          @click="$emit('apply')"
        >
          替换原文
        </button>
        <button type="button" class="mini-btn mini-btn--ghost" @click="$emit('ignore')">忽略</button>
      </div>
    </section>

    <div class="suggestion-panel__list">
      <button
        v-for="item in visibleItems"
        :key="item.riskId"
        type="button"
        class="suggestion-item"
        :class="[
          { 'is-active': item.riskId === activeRiskId },
          `is-${effectiveLevel(item)}`
        ]"
        @click="$emit('select-risk', item.riskId)"
      >
        <div class="suggestion-item__top">
          <span class="suggestion-item__level">{{ levelLabel(effectiveLevel(item), statusByRiskId[item.riskId] || item.status) }}</span>
          <span class="suggestion-item__score">{{ Math.round(item.aigcScore) }}%</span>
        </div>
        <strong>{{ item.sectionTitle || `段落 ${item.displayOrder + 1}` }}</strong>
        <p>{{ item.currentText }}</p>
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RewriteAdviceResponse, RewriteWorkspaceRiskItem } from '../../types'

const tabs = [
  { label: '高风险', value: 'high' },
  { label: '中风险', value: 'medium' },
  { label: '低风险', value: 'low' },
  { label: '正常', value: 'normal' },
] as const

const props = defineProps<{
  activeTab: 'high' | 'medium' | 'low' | 'normal'
  activeRiskId: string
  activeItem: RewriteWorkspaceRiskItem | null
  activeStatus: RewriteWorkspaceRiskItem['status']
  visibleItems: RewriteWorkspaceRiskItem[]
  suggestion: RewriteAdviceResponse | null
  hasPrevious: boolean
  hasNext: boolean
  applyLoading: boolean
  statusByRiskId: Record<string, RewriteWorkspaceRiskItem['status']>
  tabCounts: Record<'high' | 'medium' | 'low' | 'normal', number>
}>()

defineEmits<{
  (e: 'change-tab', value: 'high' | 'medium' | 'low' | 'normal'): void
  (e: 'select-risk', riskId: string): void
  (e: 'previous'): void
  (e: 'next'): void
  (e: 'apply'): void
  (e: 'ignore'): void
}>()

function effectiveLevel(item: RewriteWorkspaceRiskItem) {
  const status = props.statusByRiskId[item.riskId] || item.status
  if (status === 'applied' || status === 'ignored') return 'normal'
  return item.riskLevel
}

function levelLabel(level: 'high' | 'medium' | 'low' | 'normal', status: RewriteWorkspaceRiskItem['status']) {
  if (status === 'applied') return '已改写'
  if (status === 'ignored') return '已忽略'
  if (level === 'high') return '高风险'
  if (level === 'medium') return '中风险'
  if (level === 'low') return '低风险'
  return '正常'
}

const suggestionText = computed(() =>
  props.suggestion?.rewritten_paragraph || props.activeItem?.rewriteHint || '正在生成改写建议...'
)

const principleText = computed(() =>
  props.suggestion?.overall_advice || props.activeItem?.principle || '通过调整句式结构、补充细节和弱化模板表达来降低风险。'
)
</script>

<style scoped>
.suggestion-panel {
  min-height: 0;
  display: grid;
  grid-template-rows: auto auto auto minmax(0, 1fr);
  gap: 14px;
}

.suggestion-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.suggestion-panel__eyebrow {
  margin: 0 0 6px;
  color: #0f8f4f;
  font-size: 12px;
  font-weight: 800;
}

.suggestion-panel__header h3 {
  margin: 0;
  font-size: 22px;
  color: #111827;
}

.suggestion-panel__count {
  min-width: 34px;
  height: 34px;
  border-radius: 999px;
  background: #eff6f0;
  color: #0f8f4f;
  font-size: 13px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.risk-tabs {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.risk-tab {
  min-height: 54px;
  border-radius: 14px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  padding: 10px 12px;
  display: grid;
  gap: 4px;
  text-align: left;
  cursor: pointer;
}

.risk-tab span {
  font-size: 12px;
  color: #6b7280;
}

.risk-tab strong {
  font-size: 18px;
  color: #111827;
}

.risk-tab.is-active {
  box-shadow: 0 14px 24px rgba(15, 23, 42, 0.08);
}

.risk-tab.is-active.is-high {
  border-color: rgba(239, 68, 68, 0.24);
  background: #fff4f4;
}

.risk-tab.is-active.is-medium {
  border-color: rgba(245, 158, 11, 0.24);
  background: #fff9ef;
}

.risk-tab.is-active.is-low {
  border-color: rgba(139, 92, 246, 0.24);
  background: #f7f2ff;
}

.risk-tab.is-active.is-normal {
  border-color: rgba(34, 197, 94, 0.24);
  background: #eefcf2;
}

.focus-card {
  border-radius: 20px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  padding: 18px;
  display: grid;
  gap: 14px;
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.06);
}

.focus-card.is-high {
  border-color: rgba(239, 68, 68, 0.22);
  background: linear-gradient(180deg, rgba(255, 245, 245, 0.98) 0%, #ffffff 100%);
}

.focus-card.is-medium {
  border-color: rgba(245, 158, 11, 0.22);
  background: linear-gradient(180deg, rgba(255, 249, 238, 0.98) 0%, #ffffff 100%);
}

.focus-card.is-low {
  border-color: rgba(139, 92, 246, 0.2);
  background: linear-gradient(180deg, rgba(247, 242, 255, 0.98) 0%, #ffffff 100%);
}

.focus-card.is-normal {
  border-color: rgba(34, 197, 94, 0.2);
  background: linear-gradient(180deg, rgba(239, 252, 243, 0.98) 0%, #ffffff 100%);
}

.focus-card__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.focus-card__level {
  border-radius: 999px;
  padding: 6px 10px;
  background: rgba(15, 23, 42, 0.06);
  color: #111827;
  font-size: 12px;
  font-weight: 800;
}

.focus-card__score {
  font-size: 13px;
  color: #475569;
  font-weight: 700;
}

.focus-card__section {
  display: grid;
  gap: 6px;
}

.focus-card__section h4 {
  margin: 0;
  font-size: 13px;
  color: #6b7280;
}

.focus-card__section p {
  margin: 0;
  font-size: 14px;
  color: #111827;
  line-height: 1.8;
}

.focus-card__section--rewrite p {
  color: #0f8f4f;
}

.focus-card__actions {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.mini-btn {
  min-height: 40px;
  border-radius: 10px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: #ffffff;
  color: #111827;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.mini-btn--primary {
  background: #0f8f4f;
  color: #ffffff;
  border-color: #0f8f4f;
}

.mini-btn--ghost {
  color: #64748b;
}

.mini-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.suggestion-panel__list {
  min-height: 0;
  overflow: auto;
  display: grid;
  gap: 10px;
  padding-right: 4px;
}

.suggestion-item {
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  background: #ffffff;
  padding: 14px;
  text-align: left;
  display: grid;
  gap: 8px;
  cursor: pointer;
}

.suggestion-item.is-active {
  border-color: rgba(15, 143, 79, 0.22);
  box-shadow: 0 14px 26px rgba(15, 143, 79, 0.1);
}

.suggestion-item__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.suggestion-item__level,
.suggestion-item__score {
  font-size: 12px;
  color: #6b7280;
}

.suggestion-item strong {
  color: #111827;
  font-size: 14px;
  line-height: 1.5;
}

.suggestion-item p {
  margin: 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.75;
}

.suggestion-item.is-high {
  border-left: 4px solid #ef4444;
}

.suggestion-item.is-medium {
  border-left: 4px solid #f59e0b;
}

.suggestion-item.is-low {
  border-left: 4px solid #8b5cf6;
}

.suggestion-item.is-normal {
  border-left: 4px solid #22c55e;
}

@media (max-width: 1100px) {
  .focus-card__actions {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
