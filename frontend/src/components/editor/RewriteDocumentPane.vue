<template>
  <section class="document-pane">
    <div class="document-pane__header">
      <div>
        <p class="document-pane__eyebrow">论文文档</p>
        <h3>嵌入式改写视图</h3>
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
        <header class="doc-page__header">
          <span>{{ title || '论文正文' }}</span>
          <span>第 {{ pageIndex + 1 }} 页</span>
        </header>

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
          <span v-if="riskItemByBlockId[block.blockId]" class="doc-risk-index">
            {{ (riskItemByBlockId[block.blockId]?.displayOrder || 0) + 1 }}
          </span>

          <template v-if="normalizeType(block.type) === 'table'">
            <table class="doc-table">
              <tbody>
                <tr v-for="(row, rowIndex) in parseTableRows(block.currentText)" :key="`${block.blockId}-${rowIndex}`">
                  <td v-for="(cell, cellIndex) in row" :key="`${block.blockId}-${rowIndex}-${cellIndex}`">{{ cell }}</td>
                </tr>
              </tbody>
            </table>
          </template>

          <template v-else-if="normalizeType(block.type) === 'heading' || normalizeType(block.type) === 'title'">
            <component
              :is="headingTag(block.currentText, block.displayOrder)"
              class="doc-heading"
              v-html="highlightedHtml(block)"
            />
          </template>

          <template v-else>
            <p v-html="highlightedHtml(block)"></p>
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

        <footer class="doc-page__footer">
          <span>字数 {{ pageWordCount(page) }}</span>
          <span>检测范围 全文</span>
          <span>缩放 100%</span>
        </footer>
      </article>
    </div>

    <div class="document-pane__summary">
      <span>页数 {{ pages.length }}</span>
      <span>字数 {{ wordCount }}</span>
      <span>预估行数 {{ estimatedLines }}</span>
      <span>格式 {{ sourceFormat.toUpperCase() }}</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, watch } from 'vue'
import type { DocumentBlock, RewriteWorkspaceHighlight, RewriteWorkspaceRiskItem } from '../../types'

export interface RenderBlock extends DocumentBlock {
  currentText: string
}

const props = defineProps<{
  title: string
  blocks: RenderBlock[]
  wordCount: number
  sourceFormat: string
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
  if (status === 'applied' || status === 'ignored') return 'normal'
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
  if (order === 0 && text.length <= 48) return 'h1'
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
    const weight = block.currentText.length + (block.type === 'table' ? 280 : 0) + (block.type === 'heading' ? 200 : 0)
    if (current.length && charCount + weight > 2100) {
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
const estimatedLines = computed(() =>
  props.blocks.reduce((sum, block) => sum + Math.max(1, Math.ceil(block.currentText.length / 28)), 0)
)

function escapeHtml(text: string) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function replaceAllSafe(text: string, target: string, replacement: string) {
  if (!target) return text
  return text.split(target).join(replacement)
}

function markLevelClass(level: RewriteWorkspaceHighlight['riskLevel']) {
  return `mark-${level}`
}

function highlightedHtml(block: RenderBlock) {
  const item = props.riskItemByBlockId[block.blockId]
  if (!item || statusFor(block.blockId) !== 'pending' || !item.highlights?.length) {
    return escapeHtml(block.currentText)
  }

  const unique = item.highlights
    .filter((highlight) => highlight.text.trim())
    .sort((a, b) => b.text.length - a.text.length)

  let html = escapeHtml(block.currentText)
  for (const highlight of unique) {
    const escaped = escapeHtml(highlight.text)
    html = replaceAllSafe(
      html,
      escaped,
      `<mark class="doc-inline-mark ${markLevelClass(highlight.riskLevel)}">${escaped}</mark>`
    )
  }
  return html
}

function pageWordCount(page: RenderBlock[]) {
  return page.reduce((sum, block) => sum + block.currentText.replace(/\s+/g, '').length, 0)
}

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
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 16px;
}

.document-pane__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.document-pane__eyebrow {
  margin: 0 0 6px;
  color: #0f8f4f;
  font-size: 12px;
  font-weight: 800;
}

.document-pane__header h3 {
  margin: 0;
  color: #111827;
  font-size: 22px;
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
  font-weight: 700;
  background: #eef2f7;
  color: #374151;
}

.legend-chip.is-high {
  background: #fee2e2;
  color: #b91c1c;
}

.legend-chip.is-medium {
  background: #fef3c7;
  color: #b45309;
}

.legend-chip.is-low {
  background: #ede9fe;
  color: #6d28d9;
}

.legend-chip.is-normal {
  background: #dcfce7;
  color: #166534;
}

.document-scroll {
  min-height: 0;
  overflow: auto;
  padding: 6px 10px 6px 4px;
  display: grid;
  gap: 26px;
  background: linear-gradient(180deg, #eef0ea 0%, #e7ebf0 100%);
  border-radius: 26px;
}

.doc-page {
  width: min(920px, 100%);
  margin: 0 auto;
  background: #ffffff;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 0 26px 54px rgba(15, 23, 42, 0.08);
  padding: 26px 74px 32px;
}

.doc-page__header,
.doc-page__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #94a3b8;
  font-size: 12px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.18);
  padding-bottom: 14px;
}

.doc-page__footer {
  border-bottom: 0;
  border-top: 1px solid rgba(148, 163, 184, 0.18);
  padding-top: 14px;
  padding-bottom: 0;
  margin-top: 20px;
}

.doc-block {
  position: relative;
  margin: 18px 0;
  padding: 8px 10px 8px 16px;
  border-radius: 10px;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    background-color 0.18s ease;
}

.doc-risk-index {
  position: absolute;
  left: -30px;
  top: 12px;
  width: 22px;
  height: 22px;
  border-radius: 999px;
  background: #0f8f4f;
  color: #ffffff;
  font-size: 12px;
  font-weight: 800;
  display: grid;
  place-items: center;
}

.doc-heading {
  margin: 0;
}

.doc-block.type-title h1,
.doc-block.type-heading h1,
.doc-block.type-heading h2,
.doc-block.type-heading h3,
.doc-block.type-heading h4 {
  color: #111827;
  margin: 0;
}

.doc-block.type-title h1 {
  text-align: center;
  font-size: 28px;
  line-height: 1.45;
  margin-bottom: 18px;
}

.doc-block.type-heading h2 {
  font-size: 22px;
  line-height: 1.55;
}

.doc-block.type-heading h3 {
  font-size: 18px;
  line-height: 1.55;
}

.doc-block.type-heading h4 {
  font-size: 16px;
  line-height: 1.55;
}

.doc-block.type-paragraph p {
  margin: 0;
  color: #111827;
  font-size: 16px;
  line-height: 1.95;
  text-indent: 2em;
  font-family: 'Times New Roman', 'SimSun', serif;
}

:deep(.doc-inline-mark) {
  padding: 0 2px;
  border-radius: 4px;
}

:deep(.doc-inline-mark.mark-high) {
  background: rgba(239, 68, 68, 0.18);
  color: #991b1b;
}

:deep(.doc-inline-mark.mark-medium) {
  background: rgba(245, 158, 11, 0.18);
  color: #9a3412;
}

:deep(.doc-inline-mark.mark-low) {
  background: rgba(139, 92, 246, 0.16);
  color: #6d28d9;
}

:deep(.doc-inline-mark.mark-normal) {
  background: rgba(34, 197, 94, 0.16);
  color: #166534;
}

.doc-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.doc-table td {
  border: 1px solid #d1d5db;
  padding: 10px 12px;
  line-height: 1.7;
  vertical-align: top;
}

.doc-block.is-selectable {
  cursor: pointer;
}

.doc-block.is-active {
  outline: 2px solid rgba(15, 143, 79, 0.34);
  box-shadow: 0 14px 24px rgba(15, 143, 79, 0.1);
}

.doc-block.risk-high {
  background: #fff3f3;
}

.doc-block.risk-medium {
  background: #fff8ec;
}

.doc-block.risk-low {
  background: #f6f1ff;
}

.doc-block.is-rewritten {
  background: #eefcf2;
}

.doc-block.is-ignored {
  background: #f8fafc;
}

.doc-comment {
  position: absolute;
  top: 10px;
  right: -16px;
  border: 0;
  border-radius: 999px;
  padding: 6px 10px;
  background: #ffffff;
  color: #0f8f4f;
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.12);
  font-size: 12px;
  font-weight: 800;
  opacity: 0;
  transform: translateX(6px);
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

.document-pane__summary {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  padding: 12px 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(15, 23, 42, 0.08);
  color: #64748b;
  font-size: 13px;
}

@media (max-width: 1100px) {
  .doc-page {
    padding: 20px 24px 28px;
  }

  .doc-risk-index {
    left: auto;
    right: 8px;
  }

  .doc-comment {
    position: static;
    opacity: 1;
    transform: none;
    margin-top: 10px;
  }
}
</style>
