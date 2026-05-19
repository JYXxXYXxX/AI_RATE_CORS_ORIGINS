<template>
  <aside class="suggestion-panel">
    <div class="panel-head">
      <div>
        <span>批注与改写建议</span>
        <h2>风险处理面板</h2>
      </div>
      <strong>{{ visibleItems.length }}</strong>
    </div>

    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        type="button"
        class="tab"
        :class="[`risk-${tab.value}`, { active: activeTab === tab.value }]"
        @click="$emit('change-tab', tab.value)"
      >
        <span>{{ tab.label }}</span>
        <b>{{ counts[tab.value] }}</b>
      </button>
    </div>

    <div ref="cardListRef" class="card-list">
      <article
        v-for="item in visibleItems"
        :key="item.riskId"
        class="suggestion-card"
        :class="[`risk-${effectiveLevel(item)}`, { active: item.riskId === activeRiskId }]"
        :data-risk-id="item.riskId"
        @click="$emit('select-risk', item.riskId)"
      >
        <div class="card-top">
          <span class="level-pill">{{ levelLabel(item) }}</span>
          <strong>AIGC 疑似度 {{ Math.round(item.aigcScore) }}%</strong>
        </div>

        <section class="card-section">
          <h3>风险说明</h3>
          <p>{{ item.diagnosis || fallbackDiagnosis(item.riskLevel) }}</p>
        </section>

        <section class="card-section original">
          <h3>原文</h3>
          <p>{{ item.originalText }}</p>
        </section>

        <section class="card-section rewrite">
          <h3>改写后的句子</h3>
          <p v-if="item.riskId === activeRiskId && suggestionLoading" class="loading-text">
            正在生成改写后的句子...
          </p>
          <p v-else>{{ item.riskId === activeRiskId ? activeSuggestionText : previewSuggestion(item) }}</p>
        </section>

        <section
          v-if="item.riskId === activeRiskId ? activePrincipleText : item.principle"
          class="card-section principle"
        >
          <h3>改写原理</h3>
          <p>{{ item.riskId === activeRiskId ? activePrincipleText : item.principle }}</p>
        </section>

        <div class="card-actions">
          <button
            class="primary"
            type="button"
            :disabled="item.status !== 'pending'"
            @click.stop="applyItem(item.riskId)"
          >
            替换原文
          </button>
          <button
            type="button"
            :disabled="item.status !== 'pending'"
            @click.stop="ignoreItem(item.riskId)"
          >
            忽略
          </button>
        </div>
      </article>
    </div>

    <div class="panel-footer">
      <button type="button" :disabled="!hasPrevious" @click="$emit('previous')">上一条</button>
      <span>{{ activePosition }}</span>
      <button type="button" :disabled="!hasNext" @click="$emit('next')">下一条</button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref, watch, nextTick } from 'vue'
import type { RewriteAdviceResponse } from '../../types'
import type { RewriteRiskItem, RiskLevel } from './types'

const tabs = [
  { label: '高风险', value: 'high' },
  { label: '中风险', value: 'medium' },
  { label: '低风险', value: 'low' },
  { label: '正常', value: 'normal' },
] as const

const props = defineProps<{
  activeTab: RiskLevel
  activeRiskId: string
  activeItem: RewriteRiskItem | null
  visibleItems: RewriteRiskItem[]
  counts: Record<RiskLevel, number>
  hasPrevious: boolean
  hasNext: boolean
  suggestion: RewriteAdviceResponse | null
  suggestionLoading?: boolean
}>()

const emit = defineEmits<{
  (e: 'change-tab', level: RiskLevel): void
  (e: 'select-risk', riskId: string): void
  (e: 'previous'): void
  (e: 'next'): void
  (e: 'apply'): void
  (e: 'ignore'): void
}>()

const activePosition = computed(() => {
  if (!props.activeItem) return `0 / ${props.visibleItems.length}`
  const index = props.visibleItems.findIndex((item) => item.riskId === props.activeItem?.riskId)
  return `${Math.max(0, index) + 1} / ${props.visibleItems.length}`
})

const activeSuggestionText = computed(() => {
  const advice = props.suggestion
  if (advice?.rewritten_paragraph?.trim()) return advice.rewritten_paragraph.trim()
  const rebuilt = advice?.sentences
    ?.map((sentence) => sentence.rewritten?.trim())
    .filter((sentence): sentence is string => Boolean(sentence))
    .join(' ')
  if (rebuilt) return rebuilt
  return props.activeItem?.rewriteHint || props.activeItem?.currentText || ''
})

const activePrincipleText = computed(() => {
  if (props.suggestion?.overall_advice?.trim()) return props.suggestion.overall_advice.trim()
  return props.activeItem?.principle || ''
})

function effectiveLevel(item: RewriteRiskItem): RiskLevel {
  if (item.status === 'applied' || item.status === 'ignored') return 'normal'
  return item.riskLevel
}

function levelLabel(item: RewriteRiskItem) {
  if (item.status === 'applied') return '已改写'
  if (item.status === 'ignored') return '已忽略'
  if (item.riskLevel === 'high') return '高风险'
  if (item.riskLevel === 'medium') return '中风险'
  if (item.riskLevel === 'low') return '低风险'
  return '正常'
}

function previewSuggestion(item: RewriteRiskItem) {
  return item.rewriteHint || item.currentText || item.originalText
}

function fallbackDiagnosis(level: RiskLevel) {
  if (level === 'high') return '该句存在明显模板化或泛化表达，建议优先处理。'
  if (level === 'medium') return '该句有一定机械化表达特征，建议调整句式和信息密度。'
  if (level === 'low') return '该句风险较低，可按需做轻量润色。'
  return '该句暂未发现明显风险。'
}

const cardListRef = ref<HTMLElement | null>(null)

watch(
  () => props.activeRiskId,
  async () => {
    await nextTick()
    if (!cardListRef.value || !props.activeRiskId) return
    const card = cardListRef.value.querySelector<HTMLElement>(
      `.suggestion-card[data-risk-id="${props.activeRiskId}"]`
    )
    if (!card) return
    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }
)

function applyItem(riskId: string) {
  emit('select-risk', riskId)
  emit('apply')
}

function ignoreItem(riskId: string) {
  emit('select-risk', riskId)
  emit('ignore')
}
</script>

<style scoped>
.suggestion-panel {
  min-height: 0;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  gap: 14px;
  padding: 18px;
  border: 1px solid #e5e7eb;
  border-radius: 18px;
  background: #fff;
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.05);
}

.panel-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.panel-head span {
  color: #0f8f4f;
  font-size: 12px;
  font-weight: 900;
}

.panel-head h2 {
  margin: 4px 0 0;
  color: #111827;
  font-size: 20px;
}

.panel-head strong {
  min-width: 32px;
  height: 32px;
  border-radius: 999px;
  display: inline-grid;
  place-items: center;
  background: #edf7f0;
  color: #0f8f4f;
  font-size: 13px;
}

.tabs {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.tab {
  min-height: 52px;
  display: grid;
  gap: 3px;
  padding: 9px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
  text-align: left;
  cursor: pointer;
}

.tab span {
  color: #64748b;
  font-size: 12px;
  font-weight: 750;
}

.tab b {
  color: #111827;
  font-size: 18px;
}

.tab.active.risk-high {
  background: #fee2e2;
  border-color: rgba(239, 68, 68, 0.3);
}

.tab.active.risk-medium {
  background: #fef3c7;
  border-color: rgba(245, 158, 11, 0.35);
}

.tab.active.risk-low {
  background: #ede9fe;
  border-color: rgba(139, 92, 246, 0.3);
}

.tab.active.risk-normal {
  background: #dcfce7;
  border-color: rgba(34, 197, 94, 0.3);
}

.card-list {
  min-height: 0;
  overflow: auto;
  display: grid;
  align-content: start;
  gap: 12px;
  padding-right: 3px;
}

.suggestion-card {
  display: grid;
  gap: 12px;
  padding: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #fff;
  cursor: pointer;
}

.suggestion-card.active {
  border-color: rgba(15, 143, 79, 0.34);
  box-shadow: 0 14px 26px rgba(15, 143, 79, 0.1);
}

.suggestion-card.risk-high {
  background: linear-gradient(180deg, #fff5f5 0%, #fff 100%);
  border-color: rgba(239, 68, 68, 0.22);
}

.suggestion-card.risk-medium {
  background: linear-gradient(180deg, #fff9ed 0%, #fff 100%);
  border-color: rgba(245, 158, 11, 0.22);
}

.suggestion-card.risk-low {
  background: linear-gradient(180deg, #f7f2ff 0%, #fff 100%);
  border-color: rgba(139, 92, 246, 0.2);
}

.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.level-pill {
  min-height: 26px;
  display: inline-flex;
  align-items: center;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.07);
  color: #111827;
  font-size: 12px;
  font-weight: 900;
}

.card-top strong {
  color: #ef4444;
  font-size: 13px;
}

.card-section {
  display: grid;
  gap: 6px;
}

.card-section h3 {
  margin: 0;
  color: #64748b;
  font-size: 13px;
  font-weight: 900;
}

.card-section p {
  margin: 0;
  color: #1f2937;
  font-size: 14px;
  line-height: 1.76;
}

.card-section.original p {
  max-height: 138px;
  overflow: auto;
}

.card-section.rewrite {
  padding-left: 10px;
  border-left: 3px solid #0f8f4f;
}

.card-section.rewrite p {
  color: #0f8f4f;
  font-weight: 760;
}

.loading-text {
  color: #64748b !important;
  font-weight: 600 !important;
}

.card-section.principle p {
  color: #475569;
}

.card-actions {
  display: grid;
  grid-template-columns: 1fr 92px;
  gap: 10px;
}

.card-actions button,
.panel-footer button {
  min-height: 40px;
  border: 1px solid #d1d5db;
  border-radius: 10px;
  background: #fff;
  color: #374151;
  font-size: 14px;
  font-weight: 850;
  cursor: pointer;
}

.card-actions button.primary {
  border-color: #0f8f4f;
  background: #0f8f4f;
  color: #fff;
}

.card-actions button:disabled,
.panel-footer button:disabled {
  opacity: 0.48;
  cursor: not-allowed;
}

.panel-footer {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 10px;
  padding-top: 4px;
}

.panel-footer span {
  color: #64748b;
  font-size: 13px;
  font-weight: 800;
}
</style>
