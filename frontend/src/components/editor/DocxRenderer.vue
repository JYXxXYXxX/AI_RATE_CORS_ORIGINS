<template>
  <div ref="containerRef" class="docx-renderer">
    <div v-if="loading" class="renderer-loading">
      <el-skeleton :rows="12" animated />
    </div>
    <div v-else-if="error" class="renderer-error" style="display:none;">
      <!-- 错误由父组件处理 -->
    </div>
    <div v-else class="mammoth-doc" v-html="htmlContent" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import mammoth from 'mammoth'

const props = defineProps<{
  arrayBuffer: ArrayBuffer | null
  fileType: string
}>()

const emit = defineEmits<{
  (e: 'rendered', container: HTMLElement): void
  (e: 'error', message: string): void
}>()

const containerRef = ref<HTMLDivElement | null>(null)
const htmlContent = ref('')
const loading = ref(false)
const error = ref('')

async function renderDocx(buffer: ArrayBuffer) {
  loading.value = true
  error.value = ''
  try {
    const result = await mammoth.convertToHtml(
      { arrayBuffer: buffer },
      {
        styleMap: [
          "p[style-name='Heading 1'] => h1.chapter-title:fresh",
          "p[style-name='Heading 2'] => h2.section-title:fresh",
          "p[style-name='Heading 3'] => h3.subsection-title:fresh",
          "p => p.doc-paragraph:fresh",
          "table => table.doc-table:fresh",
          "r[style-name='Strong'] => strong",
          "r[style-name='Emphasis'] => em",
        ],
        convertImage: mammoth.images.imgElement((image) => {
          return image.read('base64').then((base64) => ({
            src: `data:${image.contentType};base64,${base64}`,
            class: 'doc-image',
          }))
        }),
      }
    )
    htmlContent.value = result.value
  } catch (err) {
    const msg = err instanceof Error ? err.message : '文档渲染失败'
    error.value = msg
    emit('error', msg)
  } finally {
    loading.value = false
  }
}

watch(
  () => props.arrayBuffer,
  (buf) => {
    if (buf) renderDocx(buf)
  },
  { immediate: true }
)

watch(htmlContent, async () => {
  await new Promise((r) => setTimeout(r, 50))
  if (containerRef.value) {
    emit('rendered', containerRef.value)
  }
})
</script>

<style>
.mammoth-doc {
  font-family: 'Times New Roman', 'SimSun', serif;
  font-size: 12pt;
  line-height: 1.8;
  color: #1a1a1a;
}

.mammoth-doc h1.chapter-title,
.mammoth-doc h2.section-title,
.mammoth-doc h3.subsection-title {
  font-family: 'SimHei', '黑体', sans-serif;
  text-align: center;
  font-weight: bold;
  margin: 18pt 0 12pt;
}

.mammoth-doc h1.chapter-title {
  font-size: 16pt;
}

.mammoth-doc h2.section-title {
  font-size: 14pt;
}

.mammoth-doc h3.subsection-title {
  font-size: 13pt;
}

.mammoth-doc p.doc-paragraph {
  text-indent: 2em;
  margin: 0 0 6pt 0;
  cursor: pointer;
  border-left: 3px solid transparent;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.12s ease;
}

.mammoth-doc p.doc-paragraph:hover {
  filter: brightness(0.97);
}

.mammoth-doc p.doc-paragraph.is-active {
  outline: 2px solid #2E7D5A;
  outline-offset: -2px;
}

/* 风险着色 */
.mammoth-doc p.doc-paragraph.risk-high {
  background: rgba(229, 57, 53, 0.18) !important;
  border-left-color: #E53935;
}

.mammoth-doc p.doc-paragraph.risk-medium {
  background: rgba(251, 140, 0, 0.18) !important;
  border-left-color: #FB8C00;
}

.mammoth-doc p.doc-paragraph.risk-low {
  background: rgba(142, 36, 170, 0.15) !important;
  border-left-color: #8E24AA;
}

.mammoth-doc p.doc-paragraph.risk-normal {
  border-left-color: transparent;
}

.mammoth-doc p.doc-paragraph.risk-gray {
  color: #9e9e9e;
  background: rgba(189, 189, 189, 0.08) !important;
  border-left-color: #bdbdbd;
}

.mammoth-doc p.doc-paragraph.is-rewritten {
  border-left-color: #2E7D5A !important;
  border-left-width: 4px;
}

.mammoth-doc table.doc-table {
  border-collapse: collapse;
  margin: 12pt auto;
  width: 100%;
}

.mammoth-doc table.doc-table td,
.mammoth-doc table.doc-table th {
  border: 1px solid #ccc;
  padding: 6px 10px;
  font-size: 11pt;
}

.mammoth-doc img.doc-image {
  max-width: 100%;
  display: block;
  margin: 12pt auto;
}

.mammoth-doc ul,
.mammoth-doc ol {
  margin: 6pt 0;
  padding-left: 2em;
}

.mammoth-doc li {
  margin-bottom: 3pt;
}

.renderer-loading {
  padding: 40px;
}

.renderer-error {
  padding: 20px;
}
</style>
