<template>
  <section class="document-canvas">
    <div class="canvas-head">
      <div>
        <span>原文档预览区</span>
        <h2>{{ title || '论文文档' }}</h2>
      </div>
      <div class="legend">
        <i class="high" />高风险
        <i class="medium" />中风险
        <i class="low" />低风险
      </div>
    </div>

    <div class="preview-shell">
      <div v-if="loading" class="preview-waiting">
        <div class="preview-waiting__notice">
          正在按原始文件渲染文档，图片、表格和段落格式会随原文件保留。
        </div>
        <iframe
          class="preview-waiting__game"
          src="/rewrite-wait-game.html"
          sandbox="allow-scripts"
          title="PataFix 等待小游戏"
        />
      </div>
      <div v-else-if="highlighting" class="preview-state sub">
        正在标记风险段落，请稍候…
      </div>

      <div v-else-if="errorMessage" class="preview-state error">
        <strong>原文档预览失败</strong>
        <p>{{ errorMessage }}</p>
      </div>

      <iframe
        v-if="!loading && !errorMessage && previewKind === 'pdf' && objectUrl"
        class="pdf-preview"
        :src="objectUrl"
        title="PDF 原文档预览"
      />

      <div
        v-show="!errorMessage && previewKind === 'docx'"
        ref="docxContainer"
        class="docx-preview-host"
      />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { renderAsync } from 'docx-preview'
import { getOriginalDocumentBlob } from '../../api'
import type { RewriteRiskItem, RiskLevel } from './types'

const props = defineProps<{
  documentId: string
  title: string
  filename: string
  sourceFormat: string
  riskItems: RewriteRiskItem[]
  activeRiskId: string
}>()

const emit = defineEmits<{
  (e: 'select-risk', riskId: string): void
}>()

defineExpose({
  scrollToSection,
})

const docxContainer = ref<HTMLElement | null>(null)
const loading = ref(false)
const highlighting = ref(false)
const errorMessage = ref('')
const objectUrl = ref('')
const renderedKey = ref('')

const previewKind = computed(() => {
  const format = (props.sourceFormat || '').toLowerCase()
  const lowerName = (props.filename || '').toLowerCase()
  if (format === 'pdf' || lowerName.endsWith('.pdf')) return 'pdf'
  if (format === 'docx' || lowerName.endsWith('.docx')) return 'docx'
  if (format === 'doc' || lowerName.endsWith('.doc')) return 'doc'
  return 'unknown'
})

watch(
  () => [props.documentId, props.filename, props.sourceFormat],
  () => {
    void renderOriginalDocument()
  },
  { immediate: true }
)

watch(
  () => props.activeRiskId,
  async () => {
    await nextTick()
    activateRiskMark()
  }
)

watch(
  () => props.riskItems.map((item) => `${item.riskId}:${item.status}:${item.currentText}`).join('|'),
  async () => {
    await nextTick()
    syncRiskMarks()
  }
)

onBeforeUnmount(() => {
  revokeObjectUrl()
})

async function renderOriginalDocument() {
  if (!props.documentId) {
    errorMessage.value = '没有找到原始文档，无法进行保格式预览。'
    return
  }

  const key = `${props.documentId}:${props.filename}:${props.sourceFormat}`
  if (renderedKey.value === key) return
  renderedKey.value = key

  loading.value = true
  errorMessage.value = ''
  revokeObjectUrl()
  if (docxContainer.value) docxContainer.value.innerHTML = ''

  try {
    const blob = await getOriginalDocumentBlob(props.documentId)

    if (previewKind.value === 'pdf') {
      objectUrl.value = URL.createObjectURL(blob)
      return
    }

    if (previewKind.value === 'doc') {
      errorMessage.value = '老式 .doc 已在上传分析链路中优先转换为 .docx；如果这里仍是 .doc，请重新上传转换后的 docx，避免浏览器把二进制内容渲染成乱码。'
      return
    }

    if (previewKind.value !== 'docx') {
      errorMessage.value = '当前文件格式暂不能在页面中保格式预览，请上传 docx 或 pdf。'
      return
    }

    await nextTick()
    if (!docxContainer.value) return
    await renderAsync(blob, docxContainer.value, docxContainer.value, {
      className: 'docx',
      inWrapper: true,
      ignoreWidth: false,
      ignoreHeight: false,
      ignoreFonts: true,
      breakPages: true,
      renderHeaders: true,
      renderFooters: true,
      renderFootnotes: true,
      renderEndnotes: true,
      renderAltChunks: true,
      renderComments: false,
      renderChanges: false,
      useBase64URL: true,
      experimental: true,
    })
    loading.value = false
    highlighting.value = true
    await nextTick()
    applyRiskHighlights()
    attachDocxInteractions()
    activateRiskMark()
    scrollToCurrentHash()
    highlighting.value = false
  } catch (error) {
    console.error(error)
    errorMessage.value = '系统没有把原文件当纯文本读取，因此不会再显示 Word 内部结构或乱码。请确认原文件是有效 docx/pdf，或重新上传转换后的 docx。'
  } finally {
    loading.value = false
    highlighting.value = false
  }
}

function applyRiskHighlights() {
  const host = docxContainer.value
  if (!host) return

  for (const item of props.riskItems) {
    if (item.status !== 'pending' || item.riskLevel === 'normal') continue
    const target = normalizeText(item.originalText || item.currentText)
    if (!target) continue
    wrapTextMatch(host, target, item)
  }
  syncRiskMarks()
}

function syncRiskMarks() {
  const host = docxContainer.value
  if (!host) return
  const itemMap = new Map(props.riskItems.map((item) => [item.riskId, item]))
  host.querySelectorAll<HTMLElement>('.risk-highlight[data-risk-id]').forEach((mark) => {
    const item = itemMap.get(mark.dataset.riskId || '')
    if (!item) return
    const segmentIndex = Number(mark.dataset.segmentIndex || 0)
    mark.classList.toggle('applied', item.status === 'applied')
    mark.classList.toggle('ignored', item.status === 'ignored')
    mark.classList.remove('high', 'medium', 'low', 'normal')
    mark.classList.add(item.status === 'pending' ? item.riskLevel : 'normal')
    mark.textContent = item.status === 'applied'
      ? (segmentIndex === 0 ? (item.currentText || item.rewriteHint || item.originalText) : '')
      : (mark.dataset.original || '')
  })
  activateRiskMark()
}

function activateRiskMark() {
  const host = docxContainer.value
  if (!host) return
  host.querySelectorAll<HTMLElement>('.risk-highlight.active').forEach((mark) => {
    mark.classList.remove('active')
  })

  if (!props.activeRiskId) return
  const mark = host.querySelector<HTMLElement>(`.risk-highlight[data-risk-id="${cssEscape(props.activeRiskId)}"]`)
  if (!mark) return
  mark.classList.add('active')
  mark.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

function attachDocxInteractions() {
  const host = docxContainer.value
  if (!host) return
  host.querySelectorAll<HTMLAnchorElement>('a[href^="#"]').forEach((link) => {
    if (link.dataset.patafixAnchorBound === '1') return
    link.dataset.patafixAnchorBound = '1'
    link.addEventListener('click', (event) => {
      const hash = link.getAttribute('href') || ''
      if (!hash.startsWith('#')) return
      event.preventDefault()
      const targetId = decodeURIComponent(hash.slice(1))
      if (targetId) {
        history.replaceState(null, '', `${location.pathname}${location.search}#${targetId}`)
        scrollToDocxAnchor(targetId)
      }
    })
  })
}

function scrollToCurrentHash() {
  const targetId = decodeURIComponent(location.hash.replace(/^#/, ''))
  if (targetId) scrollToDocxAnchor(targetId, 'auto')
}

function scrollToSection(title: string, behavior: ScrollBehavior = 'smooth') {
  const host = docxContainer.value
  if (!host) return false

  const target = findElementByTitle(title)
  if (!target) return false
  const scrollRoot = host.closest<HTMLElement>('.preview-shell')
  if (scrollRoot) {
    const rootRect = scrollRoot.getBoundingClientRect()
    const targetRect = target.getBoundingClientRect()
    const top = scrollRoot.scrollTop + targetRect.top - rootRect.top - rootRect.height * 0.25
    scrollRoot.scrollTo({ top: Math.max(0, top), behavior })
  } else {
    target.scrollIntoView({ behavior, block: 'center', inline: 'nearest' })
  }
  return true
}

function scrollToDocxAnchor(targetId: string, behavior: ScrollBehavior = 'smooth') {
  const host = docxContainer.value
  if (!host) return
  const target = host.querySelector<HTMLElement>(`#${cssEscape(targetId)}`)
  const scrollRoot = host.closest<HTMLElement>('.preview-shell')
  if (!target || !scrollRoot) return
  const rootRect = scrollRoot.getBoundingClientRect()
  const targetRect = target.getBoundingClientRect()
  const top = scrollRoot.scrollTop + targetRect.top - rootRect.top - rootRect.height * 0.25
  scrollRoot.scrollTo({ top: Math.max(0, top), behavior })
}

function findAnchorIdByTitle(title: string) {
  const host = docxContainer.value
  if (!host) return ''
  const targetKey = sectionKey(title)
  if (!targetKey) return ''
  const links = Array.from(host.querySelectorAll<HTMLAnchorElement>('a[href^="#"]'))
  const exact = links.find((link) => {
    const text = sectionKey(link.textContent || '')
    return text === targetKey || text.includes(targetKey) || targetKey.includes(text)
  })
  const fuzzy = exact || links.find((link) => sectionWords(title).every((word) => (link.textContent || '').includes(word)))
  return fuzzy?.getAttribute('href')?.replace(/^#/, '') || ''
}

function findElementByTitle(title: string) {
  const host = docxContainer.value
  if (!host) return null
  const words = sectionWords(title)
  if (!words.length) return null
  const candidates = Array.from(host.querySelectorAll<HTMLElement>('p, h1, h2, h3, span, div'))
  // 从后往前找，优先匹配正文中的标题；跳过包含目录链接的元素
  for (let i = candidates.length - 1; i >= 0; i--) {
    const element = candidates[i]
    if (element.querySelector('a[href^="#"]')) continue
    const text = normalizeText(element.textContent || '')
    if (words.every((word) => text.includes(word))) {
      return element
    }
  }
  return null
}

function sectionWords(title: string) {
  const clean = normalizeText(title)
    .replace(/^第[一二三四五六七八九十\d]+章\s*/, '')
    .replace(/^\d+(?:\.\d+)*\s*/, '')
    .replace(/\s+\d+$/, '')
  return clean.match(/[\u4e00-\u9fa5A-Za-z0-9]+/g)?.filter((word) => word.length >= 2) || []
}

function sectionKey(title: string) {
  return sectionWords(title).join('').toLowerCase()
}

function wrapTextMatch(host: HTMLElement, target: string, item: RewriteRiskItem) {
  if (host.querySelector(`.risk-highlight[data-risk-id="${cssEscape(item.riskId)}"]`)) return

  const textNodes = collectTextNodes(host)
  const normalizedTarget = normalizeText(target)
  if (!normalizedTarget) return

  const normalizedIndex = buildSearchIndex(textNodes, false)
  let start = normalizedIndex.text.indexOf(normalizedTarget)
  if (start >= 0) {
    wrapTextRange(
      textNodes,
      normalizedIndex.offsets[start],
      normalizedIndex.offsets[start + normalizedTarget.length - 1] + 1,
      item
    )
    return
  }

  const compactTarget = normalizedTarget.replace(/\s+/g, '')
  if (!compactTarget) return
  const compactIndex = buildSearchIndex(textNodes, true)
  start = compactIndex.text.indexOf(compactTarget)
  if (start < 0) return
  wrapTextRange(
    textNodes,
    compactIndex.offsets[start],
    compactIndex.offsets[start + compactTarget.length - 1] + 1,
    item
  )
}

function collectTextNodes(host: HTMLElement) {
  const textNodes: Array<{ node: Text; start: number; end: number }> = []
  let offset = 0
  const walker = document.createTreeWalker(host, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      const parent = node.parentElement
      if (!parent) return NodeFilter.FILTER_REJECT
      if (parent.closest('.risk-highlight')) return NodeFilter.FILTER_REJECT
      if (['STYLE', 'SCRIPT'].includes(parent.tagName)) return NodeFilter.FILTER_REJECT
      return node.textContent ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP
    },
  })

  let node = walker.nextNode() as Text | null
  while (node) {
    const text = node.textContent || ''
    textNodes.push({ node, start: offset, end: offset + text.length })
    offset += text.length
    node = walker.nextNode() as Text | null
  }

  return textNodes
}

function wrapTextRange(
  textNodes: Array<{ node: Text; start: number; end: number }>,
  start: number,
  end: number,
  item: RewriteRiskItem
) {
  const touched = textNodes.filter((entry) => entry.end > start && entry.start < end)
  touched.forEach((entry, segmentIndex) => {
    const node = entry.node
    if (!node.parentNode) return
    const source = node.textContent || ''
    const segmentStart = Math.max(0, start - entry.start)
    const segmentEnd = Math.min(source.length, end - entry.start)
    const segment = source.slice(segmentStart, segmentEnd)
    if (!segment) return

    const before = source.slice(0, segmentStart)
    const after = source.slice(segmentEnd)
    const mark = document.createElement('mark')
    mark.className = `risk-highlight ${item.riskLevel}`
    mark.dataset.riskId = item.riskId
    mark.dataset.segmentIndex = String(segmentIndex)
    mark.dataset.original = segment
    mark.textContent = segment
    mark.addEventListener('click', (event) => {
      event.stopPropagation()
      emit('select-risk', item.riskId)
    })

    const parent = node.parentNode
    if (before) parent.insertBefore(document.createTextNode(before), node)
    parent.insertBefore(mark, node)
    if (after) parent.insertBefore(document.createTextNode(after), node)
    parent.removeChild(node)
  })
}

function normalizeText(text = '') {
  return text.replace(/\s+/g, ' ').trim()
}

function buildSearchIndex(
  textNodes: Array<{ node: Text; start: number; end: number }>,
  compact: boolean
) {
  let text = ''
  const offsets: number[] = []
  let lastWasSpace = true

  for (const entry of textNodes) {
    const source = entry.node.textContent || ''
    for (let index = 0; index < source.length; index += 1) {
      const char = source[index]
      if (/\s/.test(char)) {
        if (!compact && !lastWasSpace) {
          text += ' '
          offsets.push(entry.start + index)
          lastWasSpace = true
        }
        continue
      }
      text += char
      offsets.push(entry.start + index)
      lastWasSpace = false
    }
  }

  while (text.startsWith(' ')) {
    text = text.slice(1)
    offsets.shift()
  }
  while (text.endsWith(' ')) {
    text = text.slice(0, -1)
    offsets.pop()
  }

  return { text, offsets }
}

function cssEscape(value: string) {
  if (typeof CSS !== 'undefined' && CSS.escape) return CSS.escape(value)
  return value.replace(/"/g, '\\"')
}

function revokeObjectUrl() {
  if (!objectUrl.value) return
  URL.revokeObjectURL(objectUrl.value)
  objectUrl.value = ''
}
</script>

<style scoped>
.document-canvas {
  min-height: 0;
  overflow: hidden;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 14px;
}

.canvas-head {
  min-height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.canvas-head span {
  color: #0f8f4f;
  font-size: 12px;
  font-weight: 900;
}

.canvas-head h2 {
  margin: 4px 0 0;
  color: #111827;
  font-size: 21px;
  line-height: 1.25;
}

.legend {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #64748b;
  font-size: 12px;
  font-weight: 750;
  white-space: nowrap;
  flex-shrink: 0;
}

.legend i {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.legend .high {
  background: #ef4444;
}

.legend .medium {
  background: #f59e0b;
}

.legend .low {
  background: #8b5cf6;
}

.preview-shell {
  position: relative;
  min-height: 0;
  overflow: auto;
  border-radius: 18px;
  background: #eef1ee;
  border: 1px solid rgba(15, 23, 42, 0.06);
}

.preview-waiting {
  min-height: 720px;
  display: grid;
  place-items: center;
  padding: 86px 40px 44px;
}

.preview-waiting__notice {
  position: absolute;
  top: 42px;
  left: 50%;
  z-index: 2;
  width: min(640px, calc(100% - 48px));
  transform: translateX(-50%);
  padding: 16px 20px;
  border-radius: 14px;
  border: 1px solid #dfe6df;
  background: rgba(255, 255, 255, 0.96);
  color: #374151;
  font-size: 14px;
  line-height: 1.7;
  text-align: center;
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.06);
}

.preview-waiting__game {
  width: min(860px, 92%);
  height: min(520px, 58vh);
  min-height: 420px;
  border: 0;
  border-radius: 22px;
  background: #f8faf6;
  box-shadow: 0 28px 70px rgba(15, 23, 42, 0.14);
}

.docx-preview-host {
  min-height: 100%;
  padding: 24px 16px 36px;
}

.pdf-preview {
  width: 100%;
  height: 100%;
  min-height: 720px;
  border: 0;
  background: #fff;
}

.preview-state {
  width: min(640px, calc(100% - 48px));
  margin: 42px auto;
  padding: 18px 20px;
  border-radius: 14px;
  border: 1px solid #dfe6df;
  background: #fff;
  color: #374151;
  font-size: 14px;
  line-height: 1.7;
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.06);
}

.preview-state strong {
  display: block;
  margin-bottom: 6px;
  color: #b91c1c;
  font-size: 15px;
}

.preview-state p {
  margin: 0;
}

.preview-state.error {
  border-color: rgba(239, 68, 68, 0.22);
  background: #fff7f7;
}

.preview-state.sub {
  position: absolute;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  width: auto;
  margin: 0;
  padding: 8px 18px;
  border-radius: 999px;
  border: 1px solid #d1e7dd;
  background: #e8f5e9;
  color: #1b5e20;
  font-size: 13px;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(27, 94, 32, 0.1);
  animation: pulse-sub 1.6s ease-in-out infinite;
}

@keyframes pulse-sub {
  0%, 100% { opacity: 0.85; }
  50% { opacity: 1; }
}

:deep(.docx-wrapper) {
  background: transparent;
  padding: 0;
  align-items: flex-start;
  min-width: max-content;
}

:deep(.docx) {
  margin: 0 auto 24px;
  box-shadow: 0 22px 48px rgba(15, 23, 42, 0.08);
  border-radius: 4px;
  max-width: none;
  flex: 0 0 auto;
  font-family: 'Times New Roman', 'SimSun', 'Songti SC', 'STSong', serif;
  line-height: 1.6;
  overflow-wrap: break-word;
  overflow: visible !important;
}

:deep(.docx span) {
  display: inline !important;
  overflow: visible !important;
  text-overflow: clip !important;
}

:deep(section.docx > article) {
  width: 100%;
  flex: 0 0 auto;
}

:deep(.docx table) {
  max-width: none;
}

:deep(.docx img) {
  max-width: none;
}

:deep(.risk-highlight) {
  padding: 0;
  border-radius: 2px;
  color: inherit;
  cursor: pointer;
  box-decoration-break: clone;
  -webkit-box-decoration-break: clone;
}

:deep(.risk-highlight.high) {
  background: rgba(239, 68, 68, 0.22);
}

:deep(.risk-highlight.medium) {
  background: rgba(245, 158, 11, 0.2);
}

:deep(.risk-highlight.low) {
  background: rgba(139, 92, 246, 0.18);
}

:deep(.risk-highlight.normal) {
  background: transparent;
}

:deep(.risk-highlight.active) {
  outline: 2px solid rgba(15, 143, 79, 0.72);
  outline-offset: 2px;
}

:deep(.risk-highlight.applied) {
  background: rgba(15, 143, 79, 0.16);
}

:deep(.risk-highlight.ignored) {
  background: transparent;
  outline: 1px dashed rgba(100, 116, 139, 0.32);
}

@media (max-width: 1180px) {
  .docx-preview-host {
    padding: 16px 8px 28px;
  }

  :deep(.docx) {
    max-width: none;
  }
}
</style>
