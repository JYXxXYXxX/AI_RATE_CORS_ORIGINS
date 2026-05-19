<template>
  <aside class="chapter-sidebar">
    <div class="panel-title">
      <span>快速导航</span>
      <strong>{{ sections.length }}</strong>
    </div>

    <div v-if="warnings.length" class="warnings">
      <p v-for="warning in warnings" :key="warning">{{ warning }}</p>
    </div>

    <div class="chapter-list">
      <button
        v-for="section in sections"
        :key="section.sectionId"
        class="chapter-item"
        :class="[`level-${section.level}`, `risk-${section.riskLevel}`, { active: section.sectionId === activeSectionId }]"
        type="button"
        @click="$emit('select-section', section.sectionId)"
      >
        <span class="risk-dot" />
        <span class="chapter-title">{{ section.title }}</span>
        <span class="risk-counts">
          <b v-if="section.riskCounts.high">{{ section.riskCounts.high }}</b>
          <b v-if="section.riskCounts.medium" class="medium">{{ section.riskCounts.medium }}</b>
          <b v-if="section.riskCounts.low" class="low">{{ section.riskCounts.low }}</b>
        </span>
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import type { RewriteSection } from './types'

defineProps<{
  sections: RewriteSection[]
  activeSectionId: string
  warnings: string[]
}>()

defineEmits<{
  (e: 'select-section', sectionId: string): void
}>()
</script>

<style scoped>
.chapter-sidebar {
  min-height: 0;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  gap: 14px;
  padding: 18px 14px;
  border-radius: 18px;
  border: 1px solid #e5e7eb;
  background: #fff;
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.05);
}

.panel-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px;
}

.panel-title span {
  color: #111827;
  font-size: 18px;
  font-weight: 900;
}

.panel-title strong {
  min-width: 28px;
  height: 28px;
  display: inline-grid;
  place-items: center;
  border-radius: 999px;
  background: #edf7f0;
  color: #0f8f4f;
  font-size: 12px;
}

.warnings {
  display: grid;
  gap: 8px;
}

.warnings p {
  margin: 0;
  padding: 9px 10px;
  border-radius: 10px;
  background: #fff7ed;
  color: #9a3412;
  font-size: 12px;
  line-height: 1.55;
}

.chapter-list {
  min-height: 0;
  overflow: auto;
  display: grid;
  align-content: start;
  gap: 6px;
  padding-right: 2px;
}

.chapter-item {
  width: 100%;
  min-height: 42px;
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr) auto;
  align-items: center;
  gap: 9px;
  border: 1px solid transparent;
  border-radius: 12px;
  background: transparent;
  color: #374151;
  text-align: left;
  cursor: pointer;
  padding: 8px 10px;
}

.chapter-item:hover,
.chapter-item.active {
  background: #eef8f0;
  border-color: rgba(15, 143, 79, 0.18);
}

.chapter-item.level-2 {
  padding-left: 24px;
}

.chapter-item.level-3 {
  padding-left: 38px;
}

.chapter-title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 750;
  line-height: 1.4;
}

.chapter-item.level-1 .chapter-title {
  color: #111827;
  font-size: 14px;
  font-weight: 900;
}

.risk-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #22c55e;
}

.risk-high .risk-dot {
  background: #ef4444;
}

.risk-medium .risk-dot {
  background: #f59e0b;
}

.risk-low .risk-dot {
  background: #8b5cf6;
}

.risk-normal .risk-dot {
  background: #22c55e;
}

.risk-counts {
  display: flex;
  align-items: center;
  gap: 3px;
}

.risk-counts b {
  min-width: 18px;
  height: 18px;
  border-radius: 999px;
  display: inline-grid;
  place-items: center;
  background: #fee2e2;
  color: #b91c1c;
  font-size: 10px;
}

.risk-counts b.medium {
  background: #fef3c7;
  color: #b45309;
}

.risk-counts b.low {
  background: #ede9fe;
  color: #6d28d9;
}
</style>
