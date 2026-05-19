<template>
  <aside class="outline-nav">
    <div class="outline-nav__header">
      <div>
        <p class="outline-nav__eyebrow">章节导航</p>
        <h3>论文结构</h3>
      </div>
      <span class="outline-nav__count">{{ items.length }}</span>
    </div>

    <div v-if="warnings.length" class="outline-nav__warnings">
      <div v-for="warning in warnings" :key="warning" class="outline-nav__warning">{{ warning }}</div>
    </div>

    <div class="outline-nav__list">
      <button
        v-for="item in items"
        :key="item.id"
        type="button"
        class="outline-item"
        :class="{
          'is-active': item.id === activeId,
          [`is-${item.riskLevel}`]: true
        }"
        @click="$emit('select', item.id)"
      >
        <div class="outline-item__row">
          <span class="outline-item__dot"></span>
          <span class="outline-item__title">{{ item.title }}</span>
        </div>
        <div class="outline-item__meta">
          <span>高 {{ item.counts.high }}</span>
          <span>中 {{ item.counts.medium }}</span>
          <span>低 {{ item.counts.low }}</span>
        </div>
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
export interface OutlineItem {
  id: string
  title: string
  riskLevel: 'high' | 'medium' | 'low' | 'normal'
  counts: Record<'high' | 'medium' | 'low' | 'normal', number>
}

defineProps<{
  items: OutlineItem[]
  activeId: string
  warnings: string[]
}>()

defineEmits<{
  (e: 'select', id: string): void
}>()
</script>

<style scoped>
.outline-nav {
  display: grid;
  gap: 16px;
}

.outline-nav__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.outline-nav__eyebrow {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 700;
  color: #6b7280;
}

.outline-nav__header h3 {
  margin: 0;
  font-size: 20px;
  color: #111827;
}

.outline-nav__count {
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

.outline-nav__warnings {
  display: grid;
  gap: 8px;
}

.outline-nav__warning {
  padding: 10px 12px;
  border-radius: 12px;
  background: #fff7ed;
  color: #9a3412;
  font-size: 13px;
  line-height: 1.6;
}

.outline-nav__list {
  display: grid;
  gap: 10px;
  max-height: calc(100vh - 240px);
  overflow: auto;
  padding-right: 4px;
}

.outline-item {
  width: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #ffffff;
  text-align: left;
  padding: 14px 14px 12px;
  cursor: pointer;
  display: grid;
  gap: 8px;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    transform 0.18s ease;
}

.outline-item:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

.outline-item__row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.outline-item__dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  margin-top: 5px;
  flex: none;
  background: #9ca3af;
}

.outline-item__title {
  color: #111827;
  font-size: 14px;
  line-height: 1.6;
  font-weight: 600;
}

.outline-item__meta {
  display: flex;
  gap: 10px;
  color: #6b7280;
  font-size: 12px;
}

.outline-item.is-active {
  border-color: rgba(46, 125, 90, 0.32);
  box-shadow: 0 14px 28px rgba(46, 125, 90, 0.12);
  background: linear-gradient(180deg, #ffffff 0%, #f8fffb 100%);
}

.outline-item.is-high .outline-item__dot {
  background: #dc2626;
}

.outline-item.is-medium .outline-item__dot {
  background: #f97316;
}

.outline-item.is-low .outline-item__dot {
  background: #9333ea;
}

.outline-item.is-normal .outline-item__dot {
  background: #16a34a;
}
</style>
