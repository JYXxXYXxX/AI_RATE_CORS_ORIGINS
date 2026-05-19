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
        :class="{ 'is-active': activeTab === tab.value }"
        @click="$emit('change-tab', tab.value)"
      >
        {{ tab.label }}
      </button>
    </div>

    <section v-if="activeItem" class="focus-card" :class="`is-${effectiveLevel(activeItem)}`">
      <div class="focus-card__meta">
        <span class="focus-card__level">{{ levelLabel(effectiveLevel(activeItem)) }}</span>
        <span class="focus-card__score">AIGC {{ Math.round(activeItem.aigcScore) }}%</span>
      </div>

      <div class="focus-card__section">
        <h4>风险说明</h4>
        <p>{{ activeItem.diagnosis }}</p>
      </div>

      <div class="focus-card__section">
        <h4>原文</h4>
        <p>{{ activeItem.originalText }}</p>
      </div>

      <div class="focus-card__section">
        <h4>改写建议</h4>
        <p>{{ suggestionText }}</p>
      </div>

      <div class="focus-card__section">
        <h4>改写原理</h4>
        <p>{{ principleText }}</p>
      </div>

      <div class="focus-card__actions">
        <el-button @click="$emit('previous')" :disabled="!hasPrevious">上一条</el-button>
        <el-button @click="$emit('next')" :disabled="!hasNext">下一条</el-button>
        <el-button type="primary" @click="$emit('apply')" :loading="applyLoading">替换原文</el-button>
        <el-button @click="$emit('ignore')">忽略</el-button>
      </div>
    </section>

    <div class="suggestion-panel__list">
      <button
        v-for="item in visibleItems"
        :key="item.riskId"
        type="button"
        class="suggestion-item"
        :class="{
          'is-active': item.riskId === activeRiskId,
          [`is-${effectiveLevel(item)}`]: true
        }"
        @click="$emit('select-risk', item.riskId)"
      >
        <div class="suggestion-item__top">
          <span class="suggestion-item__level">{{ levelLabel(effectiveLevel(item)) }}</span>
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

function levelLabel(level: 'high' | 'medium' | 'low' | 'normal') {
  if (level === 'high') return '高风险'
  if (level === 'medium') return '中风险'
  if (level === 'low') return '低风险'
  return props.activeStatus === 'applied' ? '已改写' : '正常'
}

const suggestionText = computed(() =>
  props.suggestion?.rewritten_paragraph || props.activeItem?.rewriteHint || '正在生成改写建议...'
)

const principleText = computed(() =>
  props.suggestion?.overall_advice || props.activeItem?.principle || '通过调整句式结构、补充语义细节来降低模板化痕迹。'
)
</script>

<style scoped>
.suggestion-panel {
  display: grid;
  gap: 16px;
  min-height: 0;
}

.suggestion-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.suggestion-panel__eyebrow {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 700;
  color: #6b7280;
}

.suggestion-panel__header h3 {
  margin: 0;
  font-size: 20px;
  color: #111827;
}

.suggestion-panel__count {
  min-width: 32px;
  height: 32px;
  border-radius: 999px;
  background: #f3f4f6;
  color: #374151;
  font-size: 13px;
  font-weight: 700;
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
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #374151;
  border-radius: 12px;
  min-height: 40px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.risk-tab.is-active {
  border-color: rgba(46, 125, 90, 0.36);
  background: #effaf4;
  color: #166534;
}

.focus-card {
  border-radius: 18px;
  border: 1px solid #e5e7eb;
  background: #fff;
  padding: 18px;
  display: grid;
  gap: 14px;
}

.focus-card.is-high {
  border-color: rgba(220, 38, 38, 0.2);
  background: linear-gradient(180deg, rgba(254, 242, 242, 0.95) 0%, #ffffff 100%);
}

.focus-card.is-medium {
  border-color: rgba(249, 115, 22, 0.2);
  background: linear-gradient(180deg, rgba(255, 247, 237, 0.95) 0%, #ffffff 100%);
}

.focus-card.is-low {
  border-color: rgba(147, 51, 234, 0.2);
  background: linear-gradient(180deg, rgba(250, 245, 255, 0.95) 0%, #ffffff 100%);
}

.focus-card.is-normal {
  border-color: rgba(22, 163, 74, 0.18);
  background: linear-gradient(180deg, rgba(240, 253, 244, 0.95) 0%, #ffffff 100%);
}

.focus-card__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.focus-card__level,
.focus-card__score {
  font-size: 13px;
  font-weight: 700;
  color: #374151;
}

.focus-card__section h4 {
  margin: 0 0 6px;
  font-size: 13px;
  color: #6b7280;
}

.focus-card__section p {
  margin: 0;
  color: #111827;
  font-size: 14px;
  line-height: 1.75;
}

.focus-card__actions {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
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
  border-radius: 14px;
  background: #fff;
  padding: 14px;
  text-align: left;
  display: grid;
  gap: 8px;
  cursor: pointer;
}

.suggestion-item.is-active {
  border-color: rgba(46, 125, 90, 0.32);
  box-shadow: 0 12px 24px rgba(46, 125, 90, 0.1);
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
}

.suggestion-item p {
  margin: 0;
  color: #4b5563;
  font-size: 13px;
  line-height: 1.7;
}

@media (max-width: 1100px) {
  .focus-card__actions {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
