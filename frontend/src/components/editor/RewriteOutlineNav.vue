<template>
  <aside class="outline-nav">
    <div class="outline-nav__header">
      <div>
        <p class="outline-nav__eyebrow">快速导航</p>
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
        :class="[
          `is-${item.riskLevel}`,
          { 'is-active': item.id === activeId, 'is-heading': item.depth <= 1 }
        ]"
        :style="{ '--depth': item.depth }"
        @click="$emit('select', item.id)"
      >
        <span class="outline-item__dot"></span>
        <div class="outline-item__content">
          <strong>{{ item.title }}</strong>
          <small>
            高风险 {{ item.counts.high }} · 中风险 {{ item.counts.medium }} · 低风险 {{ item.counts.low }}
          </small>
        </div>
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
export interface OutlineItem {
  id: string
  title: string
  depth: number
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
  min-height: 0;
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
  font-weight: 800;
  color: #0f8f4f;
}

.outline-nav__header h3 {
  margin: 0;
  font-size: 22px;
  color: #111827;
}

.outline-nav__count {
  min-width: 32px;
  height: 32px;
  border-radius: 999px;
  background: #eff6f0;
  color: #0f8f4f;
  font-size: 13px;
  font-weight: 800;
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
  min-height: 0;
  overflow: auto;
  display: grid;
  gap: 8px;
  padding-right: 4px;
}

.outline-item {
  width: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  background: #ffffff;
  padding: 12px 14px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  text-align: left;
  cursor: pointer;
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.04);
  margin-left: calc(var(--depth) * 14px);
  width: calc(100% - (var(--depth) * 14px));
}

.outline-item__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-top: 6px;
  flex: none;
  background: #9ca3af;
}

.outline-item__content {
  min-width: 0;
  display: grid;
  gap: 4px;
}

.outline-item__content strong {
  font-size: 14px;
  line-height: 1.55;
  color: #111827;
}

.outline-item__content small {
  color: #94a3b8;
  font-size: 12px;
}

.outline-item.is-heading .outline-item__content strong {
  font-size: 15px;
}

.outline-item.is-active {
  border-color: rgba(15, 143, 79, 0.28);
  background: linear-gradient(180deg, #ffffff 0%, #f2fbf5 100%);
  box-shadow: 0 16px 28px rgba(15, 143, 79, 0.11);
}

.outline-item.is-high .outline-item__dot {
  background: #ef4444;
}

.outline-item.is-medium .outline-item__dot {
  background: #f59e0b;
}

.outline-item.is-low .outline-item__dot {
  background: #8b5cf6;
}

.outline-item.is-normal .outline-item__dot {
  background: #22c55e;
}
</style>
