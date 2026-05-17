<template>
  <div ref="containerRef" class="pdf-renderer">
    <div v-if="loading" class="renderer-loading">
      <el-skeleton :rows="12" animated />
    </div>
    <div v-else-if="error" class="renderer-error" style="display: none;">
      <!-- 错误由父组件处理 -->
    </div>
    <div v-else class="pdf-pages">
      <div
        v-for="(page, idx) in pages"
        :key="idx"
        ref="pageWrapperRefs"
        class="pdf-page-wrapper"
      >
        <canvas :ref="el => { if (el) canvasRefs[idx] = el as HTMLCanvasElement }" class="pdf-canvas" />
        <div
          :ref="el => { if (el) textLayerRefs[idx] = el as HTMLDivElement }"
          class="text-layer"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
import { TextLayer } from 'pdfjs-dist'
import type { DocumentBlock } from '../../types'
import { getRiskStyle } from './riskStyle'

pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs'

const props = defineProps<{
  arrayBuffer: ArrayBuffer | null
  blocks?: DocumentBlock[]
}>()

const emit = defineEmits<{
  (e: 'rendered', container: HTMLElement): void
  (e: 'error', message: string): void
  (e: 'select-block', blockId: string): void
  (e: 'page-count', count: number): void
}>()

const containerRef = ref<HTMLDivElement | null>(null)
const loading = ref(false)
const error = ref('')
const pages = ref<number[]>([])
const canvasRefs = ref<HTMLCanvasElement[]>([])
const textLayerRefs = ref<HTMLDivElement[]>([])
const pageWrapperRefs = ref<HTMLDivElement[]>([])

function findBlockByText(text: string): DocumentBlock | undefined {
  if (!props.blocks || !text.trim()) return undefined
  const trimmed = text.trim()
  // 优先精确匹配
  let block = props.blocks.find(b => b.text.trim() === trimmed)
  if (block) return block
  // 次优先：block 文本包含这段文本
  block = props.blocks.find(b => b.text.trim().includes(trimmed))
  if (block) return block
  // 再次优先：这段文本包含 block 文本
  block = props.blocks.find(b => trimmed.includes(b.text.trim()))
  return block
}

function applyHighlightsToTextLayer(pageIndex: number) {
  const textLayerDiv = textLayerRefs.value[pageIndex]
  if (!textLayerDiv || !props.blocks) return

  const spans = textLayerDiv.querySelectorAll('span')
  spans.forEach((span) => {
    const text = span.textContent || ''
    const block = findBlockByText(text)
    if (!block) return

    const style = getRiskStyle(block.riskScore ?? 0)
    const el = span as HTMLElement

    // 添加风险背景色
    el.style.backgroundColor = style.bg
    el.style.borderLeft = `3px solid ${style.border}`
    el.style.cursor = 'pointer'
    el.style.borderRadius = '2px'

    // 点击事件
    el.addEventListener('click', (e) => {
      e.stopPropagation()
      emit('select-block', block.blockId)
    })
  })
}

onMounted(async () => {
  if (!props.arrayBuffer) return
  loading.value = true
  error.value = ''
  try {
    const pdf = await pdfjsLib.getDocument({ data: props.arrayBuffer }).promise
    const pageCount = pdf.numPages
    emit('page-count', pageCount)
    pages.value = Array.from({ length: pageCount }, (_, i) => i + 1)

    // 等待 DOM 更新
    await new Promise(r => setTimeout(r, 50))

    for (let i = 1; i <= pageCount; i++) {
      const page = await pdf.getPage(i)
      const scale = 1.8
      const viewport = page.getViewport({ scale })
      const canvas = canvasRefs.value[i - 1]
      const textLayerDiv = textLayerRefs.value[i - 1]
      const wrapper = pageWrapperRefs.value[i - 1]
      if (!canvas || !textLayerDiv || !wrapper) continue

      const ctx = canvas.getContext('2d')
      if (!ctx) continue

      canvas.width = viewport.width
      canvas.height = viewport.height
      canvas.style.width = '100%'
      canvas.style.height = 'auto'

      // 设置 wrapper 尺寸，让 textLayer 能绝对定位覆盖 canvas
      wrapper.style.position = 'relative'
      wrapper.style.width = canvas.style.width
      wrapper.style.height = 'auto'

      textLayerDiv.style.position = 'absolute'
      textLayerDiv.style.top = '0'
      textLayerDiv.style.left = '0'
      textLayerDiv.style.width = `${viewport.width}px`
      textLayerDiv.style.height = `${viewport.height}px`
      textLayerDiv.style.zIndex = '10'

      // 渲染 canvas
      await page.render({ canvasContext: ctx, viewport, canvas }).promise

      // 渲染 text layer
      const textContent = await page.getTextContent()
      const textLayer = new TextLayer({
        textContentSource: textContent,
        container: textLayerDiv,
        viewport,
      })
      await textLayer.render()

      // 应用高亮和点击事件
      applyHighlightsToTextLayer(i - 1)
    }

    if (containerRef.value) {
      emit('rendered', containerRef.value)
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'PDF 渲染失败'
    error.value = msg
    emit('error', msg)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.pdf-renderer {
  background: #fff;
}

.pdf-pages {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px;
}

.pdf-page-wrapper {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  background: #fff;
}

.pdf-canvas {
  display: block;
  width: 100%;
  height: auto;
}

.text-layer {
  pointer-events: auto;
  opacity: 1;
}

.text-layer ::v-deep(span) {
  position: absolute;
  white-space: pre;
  transform-origin: 0% 0%;
  cursor: text;
}

.renderer-loading {
  padding: 40px;
}
</style>
