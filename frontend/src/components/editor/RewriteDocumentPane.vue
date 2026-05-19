<template>
  <section class="document-pane">
    <div class="document-pane__header">
      <div>
        <p class="document-pane__eyebrow">正文改写区</p>
        <h3>文档阅读视图</h3>
      </div>
      <div class="document-pane__legend">
        <span class="legend-chip is-high">高风险</span>
        <span class="legend-chip is-medium">中风险</span>
        <span class="legend-chip is-low">低风险</span>
        <span class="legend-chip is-normal">已处理 / 正常</span>
      </div>
    </div>

    <div class="document-scroll">
      <article
        v-for="(page, pageIndex) in pages"
        :key="`page-${pageIndex}`"
        class="doc-page"
      >
        <div class="doc-page__index">第 {{ pageIndex + 1 }} 页</div>
        <div
          v-for="block in page"
          :key="block.blockId"
          :ref="(el) => setBlockRef(block.blockId, el as Element | null)"
          class="doc-block"
          :class="[
            `type-${normalizeType(block.type)}`,
            `risk-${riskLevelFor(block.blockId)}`,
            {
              'is-active': block.blockId === activeBlockId,
              'is-selectable': !!riskItemByBlockId[block.blockId],
              'is-rewritten': statusFor(block.blockId) === 'applied',
              'is-ignored': statusFor(block.blockId) === 'ignored'
            }
          ]"
          @click="selectBlock(block.blockId)"
        >
          <template v-if="normalizeType(block.type) === 'table'">
            <table class="doc-table">
              <tbody>
                <tr v-for="(row, rowIndex) in parseTableRows(block.currentText)" :key="`${block.blockId}-row-${rowIndex}`">
                  <td v-for="(cell, cellIndex) in row" :key="`${block.blockId}-cell-${rowIndex}-${cellIndex}`">{{ cell }}</td>
                </tr>
              </tbody>
            </table>
          </template>

          <template v-else-if="normalizeType(block.type) === 'heading' || normalizeType(block.type) === 'title'">
            <component :is="headingTag(block.currentText, block.displayOrder)">{{ block.currentText }}</component>
          </template>

          <template v-else>
            <p>{{ block.currentText }}</p>
          </template>

          <button
            v-if="riskItemByBlockId[block.blockId]"
            type="button"
            class="doc-comment"
            @click.stop="selectBlock(block.blockId)"
          >
            批注
          </button>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, watch } from 'vue'
import type { DocumentBlock, RewriteWorkspaceRiskItem } from '../../types'

export interface RenderBlock extends DocumentBlock {
  currentText: string
}

const props = defineProps<{
  blocks: RenderBlock[]
  riskItemByBlockId: Record<string, RewriteWorkspaceRiskItem | undefined>
  statusByRiskId: Record<string, RewriteWorkspaceRiskItem['status']>
  activeBlockId: string
}>()

const emit = defineEmits<{
  (e: 'select-block', blockId: string): void
}>()

const blockRefs = new Map<string, HTMLElement>()

function setBlockRef(blockId: string, el: Element | null) {
  if (el instanceof HTMLElement) {
    blockRefs.set(blockId, el)
  } else {
    blockRefs.delete(blockId)
  }
}

function normalizeType(type: DocumentBlock['type']) {
  return type === 'heading' || type === 'title' || type === 'table' ? type : 'paragraph'
}

function riskLevelFor(blockId: string): 'high' | 'medium' | 'low' | 'normal' {
  const item = props.riskItemByBlockId[blockId]
  if (!item) return 'normal'
  const status = props.statusByRiskId[item.riskId]
  if (status === 'applied') return 'normal'
  if (status === 'ignored') return 'normal'
  return item.riskLevel
}

function statusFor(blockId: string): RewriteWorkspaceRiskItem['status'] {
  const item = props.riskItemByBlockId[blockId]
  if (!item) return 'pending'
  return props.statusByRiskId[item.riskId] || item.status
}

function selectBlock(blockId: string) {
  if (!props.riskItemByBlockId[blockId]) return
  emit('select-block', blockId)
}

function parseTableRows(text: string) {
  return text
    .split('\n')
    .map((line) => line.split('|').map((cell) => cell.trim()).filter(Boolean))
    .filter((row) => row.length)
}

function headingTag(text: string, order: number) {
  if (order === 0 && text.length <= 42) return 'h1'
  if (/^\d+(\.\d+){2,}/.test(text)) return 'h4'
  if (/^\d+\.\d+/.test(text)) return 'h3'
  if (/^\d+/.test(text) || /^第.+章/.test(text)) return 'h2'
  return order === 0 ? 'h1' : 'h2'
}

function splitIntoPages(blocks: RenderBlock[]) {
  const result: RenderBlock[][] = []
  let current: RenderBlock[] = []
  let charCount = 0

  for (const block of blocks) {
    const weight = block.currentText.length + (block.type === 'table' ? 280 : 0) + (block.type === 'heading' ? 180 : 0)
    if (current.length && charCount + weight > 2300) {
      result.push(current)
      current = []
      charCount = 0
    }
    current.push(block)
    charCount += weight
  }

  if (current.length) result.push(current)
  return result
}

const pages = computed(() => splitIntoPages(props.blocks))

watch(
  () => props.activeBlockId,
  async (blockId) => {
    if (!blockId) return
    await nextTick()
    const el = blockRefs.get(blockId)
    el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  },
  { immediate: true }
)
</script>

<style scoped>
.document-pane {
  display: grid;
  gap: 18px;
  min-height: 0;
}

.document-pane__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.document-pane__eyebrow {
  margin: 0 0 6px;
  font-size: 12px;
  font-weight: 700;
  color: #6b7280;
}

.document-pane__header h3 {
  margin: 0;
  color: #111827;
  font-size: 20px;
}

.document-pane__legend {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.legend-chip {
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  color: #374151;
  background: #f3f4f6;
}

.legend-chip.is-high {
  background: rgba(220, 38, 38, 0.12);
  color: #b91c1c;
}

.legend-chip.is-medium {
  background: rgba(249, 115, 22, 0.12);
  color: #c2410c;
}

.legend-chip.is-low {
  background: rgba(147, 51, 234, 0.12);
  color: #7e22ce;
}

.legend-chip.is-normal {
  background: rgba(22, 163, 74, 0.12);
  color: #166534;
}

.document-scroll {
  min-height: 0;
  overflow: auto;
  padding-right: 8px;
  display: grid;
  gap: 28px;
}

.doc-page {
  width: min(860px, 100%);
  margin: 0 auto;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 0 24px 50px rgba(15, 23, 42, 0.08);
  border-radius: 10px;
  padding: 54px 72px 62px;
  position: relative;
}

.doc-page__index {
  position: absolute;
  top: 16px;
  right: 24px;
  color: #94a3b8;
  font-size: 12px;
}

.doc-block {
  position: relative;
  margin-bottom: 16px;
  border-radius: 8px;
  transition:
    box-shadow 0.18s ease,
    background-color 0.18s ease,
    outline-color 0.18s ease;
}

.doc-block.type-heading h1,
.doc-block.type-heading h2,
.doc-block.type-heading h3,
.doc-block.type-heading h4,
.doc-block.type-title h1,
.doc-block.type-title h2 {
  margin: 0;
  text-align: center;
  font-family: 'SimHei', 'Microsoft YaHei', sans-serif;
  color: #111827;
}

.doc-block.type-title h1 {
  font-size: 28px;
  line-height: 1.45;
  margin-bottom: 22px;
}

.doc-block.type-heading h2 {
  font-size: 22px;
  line-height: 1.5;
  margin: 20px 0 8px;
}

.doc-block.type-heading h3 {
  font-size: 18px;
  line-height: 1.5;
  margin: 16px 0 6px;
}

.doc-block.type-heading h4 {
  font-size: 16px;
  line-height: 1.5;
  margin: 14px 0 4px;
}

.doc-block.type-paragraph p {
  margin: 0;
  color: #111827;
  font-size: 16px;
  line-height: 1.95;
  text-indent: 2em;
  font-family: 'Times New Roman', 'SimSun', serif;
}

.doc-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.doc-table td {
  border: 1px solid #d1d5db;
  padding: 10px 12px;
  vertical-align: top;
  line-height: 1.7;
}

.doc-block.is-selectable {
  cursor: pointer;
}

.doc-block.is-active {
  outline: 2px solid rgba(46, 125, 90, 0.45);
  box-shadow: 0 10px 24px rgba(46, 125, 90, 0.1);
}

.doc-block.risk-high {
  background: rgba(220, 38, 38, 0.09);
}

.doc-block.risk-medium {
  background: rgba(249, 115, 22, 0.09);
}

.doc-block.risk-low {
  background: rgba(147, 51, 234, 0.08);
}

.doc-block.is-rewritten {
  background: rgba(22, 163, 74, 0.08);
}

.doc-block.is-ignored {
  background: rgba(148, 163, 184, 0.08);
}

.doc-comment {
  position: absolute;
  top: 10px;
  right: -18px;
  border: 0;
  border-radius: 999px;
  background: #ffffff;
  color: #2e7d5a;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.12);
  font-size: 12px;
  font-weight: 700;
  padding: 6px 10px;
  opacity: 0;
  transform: translateX(4px);
  transition:
    opacity 0.16s ease,
    transform 0.16s ease;
  cursor: pointer;
}

.doc-block:hover .doc-comment,
.doc-block.is-active .doc-comment {
  opacity: 1;
  transform: translateX(0);
}

@media (max-width: 1100px) {
  .doc-page {
    padding: 42px 26px 52px;
  }

  .doc-comment {
    position: static;
    margin-top: 10px;
    opacity: 1;
    transform: none;
  }
}
</style>
