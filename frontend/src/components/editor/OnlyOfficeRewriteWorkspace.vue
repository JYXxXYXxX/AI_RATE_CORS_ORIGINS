<template>
  <div class="workspace">
    <header class="workspace__topbar">
      <div class="workspace__title">
        <el-button text @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回报告
        </el-button>
        <div>
          <p class="workspace__eyebrow">PataFix 保格式在线改写</p>
          <h1>{{ workspace?.title || runMeta?.title || '论文在线改写' }}</h1>
          <p class="workspace__subtitle">{{ workspace?.filename || runMeta?.filename || '正在加载文档...' }}</p>
        </div>
      </div>

      <div class="workspace__metrics" v-if="workspace">
        <div class="metric-card">
          <span>当前 AIGC 疑似度</span>
          <strong>{{ formatPercent(workspace.metrics.currentAigcPercent) }}</strong>
        </div>
        <div class="metric-card">
          <span>优化后预计</span>
          <strong>{{ formatPercent(workspace.metrics.estimatedOptimizedPercent) }}</strong>
        </div>
        <div class="metric-card">
          <span>已改写数量</span>
          <strong>{{ workspace.metrics.rewrittenCount }}</strong>
        </div>
        <div class="metric-card metric-card--compact">
          <span>高 / 中 / 低</span>
          <strong>{{ workspace.metrics.highCount }} / {{ workspace.metrics.mediumCount }} / {{ workspace.metrics.lowCount }}</strong>
        </div>
      </div>

      <div class="workspace__actions">
        <el-button @click="downloadFile('original')">
          <el-icon><DocumentCopy /></el-icon>
          下载原文
        </el-button>
        <el-button type="primary" @click="downloadFile('edited')">
          <el-icon><Download /></el-icon>
          导出改写稿
        </el-button>
      </div>
    </header>

    <div class="workspace__body">
      <aside class="workspace__sidebar workspace__sidebar--left">
        <section class="panel">
          <div class="panel__header">
            <div>
              <p class="panel__eyebrow">风险目录</p>
              <h3>章节导航</h3>
            </div>
            <el-tag size="small" type="info">{{ workspace?.sections.length || 0 }} 节</el-tag>
          </div>

          <div v-if="workspace?.warnings.length" class="warning-stack">
            <div v-for="warning in workspace.warnings" :key="warning" class="warning-item">
              {{ warning }}
            </div>
          </div>

          <div v-if="workspace?.sections.length" class="section-list">
            <button
              v-for="section in workspace.sections"
              :key="section.sectionId"
              type="button"
              class="section-item"
              :class="{
                'is-active': section.sectionId === activeSectionId,
                [`is-${section.riskLevel}`]: true
              }"
              @click="selectSection(section.sectionId)"
            >
              <div class="section-item__head">
                <span class="risk-dot"></span>
                <span class="section-item__title">{{ section.title }}</span>
              </div>
              <p class="section-item__meta">
                高 {{ section.riskCounts.high || 0 }} / 中 {{ section.riskCounts.medium || 0 }} / 低 {{ section.riskCounts.low || 0 }}
              </p>
            </button>
          </div>

          <div v-else-if="!loading" class="empty-state">
            当前文档里暂时没有可处理的风险段落。
          </div>
        </section>
      </aside>

      <main class="workspace__main">
        <section v-if="activeRiskItem" class="panel preview-panel">
          <div class="panel__header">
            <div>
              <p class="panel__eyebrow">正文高亮预览</p>
              <h3>{{ activeRiskItem.sectionTitle || `正文第 ${activeRiskItem.sectionIndex + 1} 段` }}</h3>
            </div>
            <div class="preview-panel__meta">
              <span class="risk-pill" :class="`is-${activeRiskItem.riskLevel}`">{{ riskLevelLabel(activeRiskItem.riskLevel) }}</span>
              <span class="preview-panel__score">AIGC {{ formatPercent(activeRiskItem.aigcScore) }}</span>
            </div>
          </div>

          <div class="preview-panel__body">
            <div class="preview-panel__highlight" v-html="activeHighlightHtml"></div>
          </div>

          <div class="preview-panel__footer">
            <span>当前状态：{{ statusLabel(activeRiskItem.status) }}</span>
            <span>定位段落 #{{ activeRiskItem.displayOrder + 1 }}</span>
          </div>
        </section>

        <section v-if="loading" class="panel state-panel">
          <el-skeleton :rows="10" animated />
        </section>
        <section v-else-if="loadError" class="panel state-panel state-panel--error">
          <h3>加载失败</h3>
          <p>{{ loadError }}</p>
          <div class="state-panel__actions">
            <el-button type="primary" @click="refreshWorkspace">重新加载</el-button>
          </div>
        </section>
        <section v-else-if="!onlyOfficeConfig?.enabled || !onlyOfficeConfig?.supported" class="panel state-panel">
          <h3>ONLYOFFICE 当前不可用</h3>
          <p>{{ onlyOfficeConfig?.reason || '当前文档暂时不能进入保格式编辑模式。' }}</p>
          <div class="state-panel__actions">
            <el-button type="primary" @click="openFallback">切到兼容模式</el-button>
            <el-button @click="refreshWorkspace">重新加载</el-button>
          </div>
        </section>
        <section v-else class="panel editor-panel">
          <div class="editor-panel__toolbar">
            <div class="editor-panel__status">
              <span class="status-dot" :class="{ 'is-ready': editorReady }"></span>
              <span>{{ editorStatusText }}</span>
            </div>
            <div class="editor-panel__tools">
              <el-button text @click="refreshWorkspace">
                <el-icon><RefreshRight /></el-icon>
                刷新文档
              </el-button>
            </div>
          </div>
          <div :id="editorId" ref="editorHost" class="editor-host"></div>
        </section>
      </main>

      <aside class="workspace__sidebar workspace__sidebar--right">
        <section class="panel">
          <div class="panel__header">
            <div>
              <p class="panel__eyebrow">改写建议</p>
              <h3>{{ activeSectionTitle }}</h3>
            </div>
            <el-tag size="small" type="info">{{ visibleRiskItems.length }} 条</el-tag>
          </div>

          <div class="risk-card-list">
            <article
              v-for="item in visibleRiskItems"
              :key="item.riskId"
              class="risk-card"
              :class="{
                'is-active': item.riskId === activeRiskId,
                [`is-${item.riskLevel}`]: true,
                [`status-${item.status}`]: true
              }"
              @click="selectRisk(item.riskId)"
            >
              <div class="risk-card__head">
                <div class="risk-card__title">
                  <span class="risk-dot"></span>
                  <strong>{{ riskLevelLabel(item.riskLevel) }}</strong>
                </div>
                <div class="risk-card__badges">
                  <span class="score-badge">{{ formatPercent(item.aigcScore) }}</span>
                  <span class="status-badge">{{ statusLabel(item.status) }}</span>
                </div>
              </div>

              <div class="risk-card__block">
                <p class="risk-card__label">风险诊断</p>
                <p>{{ item.diagnosis }}</p>
              </div>

              <div class="risk-card__block">
                <p class="risk-card__label">原文</p>
                <p>{{ item.originalText }}</p>
              </div>

              <div class="risk-card__block">
                <p class="risk-card__label">改写建议</p>
                <p>{{ adviceParagraph(item) || item.rewriteHint }}</p>
              </div>

              <div class="risk-card__block">
                <p class="risk-card__label">改写原理</p>
                <p>{{ advicePrinciple(item) }}</p>
              </div>

              <div v-if="adviceFor(item)?.sentences?.length" class="sentence-list">
                <div v-for="(sentence, index) in adviceFor(item)?.sentences || []" :key="`${item.riskId}-${index}`" class="sentence-card">
                  <div class="sentence-card__head">
                    <span>{{ sentenceRiskLabel(sentence.risk) }}</span>
                    <el-button
                      size="small"
                      text
                      :loading="applyLoadingId === `${item.riskId}:sentence:${index}`"
                      @click.stop="applySentenceRewrite(item, sentence.original, sentence.rewritten, index)"
                    >
                      替换该句
                    </el-button>
                  </div>
                  <p class="sentence-card__original">{{ sentence.original }}</p>
                  <p class="sentence-card__rewritten">{{ sentence.rewritten }}</p>
                  <p class="sentence-card__explanation">{{ sentence.explanation }}</p>
                </div>
              </div>

              <div class="risk-card__actions">
                <el-button
                  size="small"
                  :loading="adviceLoadingId === item.riskId"
                  @click.stop="ensureAdvice(item, true)"
                >
                  {{ adviceFor(item) ? '刷新建议' : '生成建议' }}
                </el-button>
                <el-button
                  size="small"
                  type="primary"
                  :loading="applyLoadingId === item.riskId"
                  @click.stop="applyParagraphRewrite(item)"
                >
                  替换原文
                </el-button>
                <el-button
                  size="small"
                  :disabled="item.status === 'ignored'"
                  @click.stop="ignoreRisk(item)"
                >
                  忽略
                </el-button>
              </div>
            </article>
          </div>
        </section>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, DocumentCopy, Download, RefreshRight } from '@element-plus/icons-vue'
import type {
  AnalysisRunStatusResponse,
  OnlyOfficeConfigResponse,
  RewriteAdviceResponse,
  RewriteWorkspaceRiskItem,
  RewriteWorkspaceResponse,
} from '../../types'
import {
  applyOnlyOfficePatches,
  createPatch,
  getOnlyOfficeConfig,
  getOnlyOfficeDownloadUrl,
  getRewriteAdvice,
  getRewriteWorkspace,
  getRun,
} from '../../api'

declare global {
  interface Window {
    DocsAPI?: {
      DocEditor: new (id: string, config: Record<string, any>) => {
        destroyEditor?: () => void
      }
    }
    __patafixOnlyOfficeLoaders?: Record<string, Promise<void>>
  }
}

const props = defineProps<{
  runId: string
}>()

const router = useRouter()
const route = useRoute()

const loading = ref(true)
const loadError = ref('')
const editorReady = ref(false)
const editorStatusText = ref('正在准备文档...')
const adviceLoadingId = ref('')
const applyLoadingId = ref('')

const runMeta = ref<AnalysisRunStatusResponse | null>(null)
const workspace = ref<RewriteWorkspaceResponse | null>(null)
const onlyOfficeConfig = ref<OnlyOfficeConfigResponse | null>(null)
const activeSectionId = ref('')
const activeRiskId = ref('')
const adviceCache = ref<Record<string, RewriteAdviceResponse>>({})

const editorHost = ref<HTMLElement | null>(null)
const editorInstance = ref<{ destroyEditor?: () => void } | null>(null)
const editorId = `patafix-onlyoffice-${props.runId}`

const visibleRiskItems = computed(() => {
  if (!workspace.value) return []
  if (!activeSectionId.value) return workspace.value.riskItems
  return workspace.value.riskItems.filter(item => item.sectionId === activeSectionId.value)
})

const activeRiskItem = computed(() =>
  workspace.value?.riskItems.find(item => item.riskId === activeRiskId.value) || visibleRiskItems.value[0] || null
)

const activeSectionTitle = computed(() => {
  if (!workspace.value) return '风险卡片'
  const section = workspace.value.sections.find(item => item.sectionId === activeSectionId.value)
  return section?.title || '风险卡片'
})

function adviceFor(item: RewriteWorkspaceRiskItem): RewriteAdviceResponse | null {
  return adviceCache.value[item.riskId] || null
}

function riskLevelLabel(level: 'high' | 'medium' | 'low' | 'normal'): string {
  if (level === 'high') return '高风险'
  if (level === 'medium') return '中风险'
  if (level === 'low') return '低风险'
  return '正常'
}

function sentenceRiskLabel(level: 'high' | 'medium' | 'low'): string {
  if (level === 'high') return '高风险句'
  if (level === 'medium') return '中风险句'
  return '低风险句'
}

function statusLabel(status: 'pending' | 'applied' | 'ignored'): string {
  if (status === 'applied') return '已处理'
  if (status === 'ignored') return '已忽略'
  return '待处理'
}

function formatPercent(value: number): string {
  return `${Math.round(value)}%`
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function sentenceFallback(text: string, level: RewriteWorkspaceRiskItem['riskLevel']) {
  const parts = text.match(/[^。！？!?；;]+[。！？!?；;]?|[^\s]+/g) || [text]
  return parts
    .map(part => ({ text: part, riskLevel: level }))
    .filter(part => part.text.trim())
}

function buildHighlightHtml(text: string, item: RewriteWorkspaceRiskItem): string {
  const advice = adviceFor(item)
  const previewText = item.status === 'applied' ? item.currentText : text
  const highlights = item.status === 'applied'
    ? sentenceFallback(previewText, item.riskLevel)
    : (advice?.sentences?.length
        ? advice.sentences.map(sentence => ({ text: sentence.original, riskLevel: sentence.risk }))
        : (item.highlights.length ? item.highlights : sentenceFallback(previewText, item.riskLevel)))

  let cursor = 0
  let html = ''
  for (const highlight of highlights) {
    const fragment = highlight.text.trim()
    if (!fragment) continue
    const index = previewText.indexOf(fragment, cursor)
    if (index === -1) continue
    if (index > cursor) {
      html += escapeHtml(previewText.slice(cursor, index))
    }
    html += `<mark class="highlight highlight--${highlight.riskLevel}">${escapeHtml(fragment)}</mark>`
    cursor = index + fragment.length
  }
  if (cursor < previewText.length) {
    html += escapeHtml(previewText.slice(cursor))
  }
  return html || escapeHtml(previewText)
}

const activeHighlightHtml = computed(() => {
  if (!activeRiskItem.value) return ''
  const baseText = activeRiskItem.value.status === 'applied'
    ? activeRiskItem.value.currentText
    : activeRiskItem.value.originalText
  return buildHighlightHtml(baseText, activeRiskItem.value)
})

function adviceParagraph(item: RewriteWorkspaceRiskItem): string {
  return adviceFor(item)?.rewritten_paragraph || ''
}

function advicePrinciple(item: RewriteWorkspaceRiskItem): string {
  const advice = adviceFor(item)
  const sentenceExplanations = advice?.sentences?.map(sentence => sentence.explanation).filter(Boolean) || []
  return sentenceExplanations[0] || advice?.overall_advice || item.principle
}

function ensureSelection() {
  if (!workspace.value) return
  if (!activeSectionId.value || !workspace.value.sections.some(item => item.sectionId === activeSectionId.value)) {
    activeSectionId.value = workspace.value.sections[0]?.sectionId || ''
  }
  if (!activeRiskId.value || !visibleRiskItems.value.some(item => item.riskId === activeRiskId.value)) {
    activeRiskId.value = visibleRiskItems.value[0]?.riskId || workspace.value.riskItems[0]?.riskId || ''
  }
}

async function loadWorkspace() {
  loading.value = true
  loadError.value = ''
  editorStatusText.value = '正在准备文档...'
  try {
    const [run, nextWorkspace, ooConfig] = await Promise.all([
      getRun(props.runId),
      getRewriteWorkspace(props.runId),
      getOnlyOfficeConfig(props.runId),
    ])
    runMeta.value = run
    workspace.value = nextWorkspace
    onlyOfficeConfig.value = ooConfig
    ensureSelection()
    if (ooConfig.enabled && ooConfig.supported) {
      await mountOnlyOffice()
    } else {
      destroyOnlyOffice()
    }
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '加载在线改写工作区失败'
    destroyOnlyOffice()
  } finally {
    loading.value = false
  }
}

async function ensureAdvice(item: RewriteWorkspaceRiskItem, force = false) {
  if (!force && adviceCache.value[item.riskId]) return
  adviceLoadingId.value = item.riskId
  try {
    const advice = await getRewriteAdvice(props.runId, item.sectionIndex)
    adviceCache.value = {
      ...adviceCache.value,
      [item.riskId]: advice,
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '生成改写建议失败')
  } finally {
    adviceLoadingId.value = ''
  }
}

async function loadOnlyOfficeScript(url: string) {
  if (window.DocsAPI) return
  window.__patafixOnlyOfficeLoaders ||= {}
  if (!window.__patafixOnlyOfficeLoaders[url]) {
    window.__patafixOnlyOfficeLoaders[url] = new Promise<void>((resolve, reject) => {
      const script = document.createElement('script')
      script.src = url
      script.async = true
      script.onload = () => resolve()
      script.onerror = () => reject(new Error('ONLYOFFICE 脚本加载失败'))
      document.head.appendChild(script)
    })
  }
  await window.__patafixOnlyOfficeLoaders[url]
  if (!window.DocsAPI) {
    const response = await fetch(url, { credentials: 'include' })
    if (!response.ok) {
      throw new Error('ONLYOFFICE 脚本请求失败')
    }
    const source = await response.text()
    const inlineScript = document.createElement('script')
    inlineScript.text = source
    document.head.appendChild(inlineScript)
  }
}

function destroyOnlyOffice() {
  editorReady.value = false
  editorInstance.value?.destroyEditor?.()
  editorInstance.value = null
  if (editorHost.value) {
    editorHost.value.innerHTML = ''
  }
}

async function mountOnlyOffice() {
  if (!onlyOfficeConfig.value?.editorConfig || !onlyOfficeConfig.value.scriptUrl) return
  editorStatusText.value = '正在连接 ONLYOFFICE...'
  editorReady.value = false
  await loadOnlyOfficeScript(onlyOfficeConfig.value.scriptUrl)
  await nextTick()
  if (!window.DocsAPI) {
    throw new Error('ONLYOFFICE 初始化失败')
  }

  destroyOnlyOffice()
  const config = JSON.parse(JSON.stringify(onlyOfficeConfig.value.editorConfig || {}))
  const slowTimer = window.setTimeout(() => {
    if (!editorReady.value) {
      editorStatusText.value = '文档服务连接较慢，正在继续等待...'
    }
  }, 12000)

  config.events = {
    ...(config.events || {}),
    onDocumentReady: () => {
      window.clearTimeout(slowTimer)
      editorReady.value = true
      editorStatusText.value = '文档已连接，可直接保留原格式编辑'
    },
    onError: (event: any) => {
      window.clearTimeout(slowTimer)
      editorReady.value = false
      const code = event?.data?.errorCode
      editorStatusText.value = code ? `ONLYOFFICE 加载失败（${code}）` : 'ONLYOFFICE 加载失败'
      ElMessage.error(editorStatusText.value)
    },
  }
  editorInstance.value = new window.DocsAPI.DocEditor(editorId, config)
}

async function persistRiskRewrite(
  item: RewriteWorkspaceRiskItem,
  nextText: string,
  action: 'replace' | 'ignored',
  applyKey: string,
) {
  const target = nextText.trim()
  if (!target) {
    ElMessage.warning('改写内容不能为空')
    return
  }
  if (action === 'replace' && target === item.currentText.trim()) {
    ElMessage.info('这段内容已经是最新版本')
    return
  }

  applyLoadingId.value = applyKey
  try {
    await createPatch(props.runId, {
      block_id: item.blockId,
      old_text: item.currentText,
      new_text: action === 'ignored' ? item.currentText : target,
      source_map: {
        ...(item.sourceMap || {}),
        action,
        riskId: item.riskId,
        sectionId: item.sectionId,
        paragraphIndex: item.paragraphIndex ?? undefined,
      },
    })

    if (action === 'replace') {
      const result = await applyOnlyOfficePatches(props.runId, { blockId: item.blockId })
      if (result.config) {
        onlyOfficeConfig.value = result.config
      }
      ElMessage.success(`已写入文档，成功替换 ${result.patchStats.applied}/${result.patchStats.requested} 处`)
    } else {
      ElMessage.success('该条风险已标记为忽略')
    }

    await loadWorkspace()
    await nextTick()
    activeSectionId.value = item.sectionId
    activeRiskId.value = item.riskId
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '写入文档失败')
  } finally {
    applyLoadingId.value = ''
  }
}

async function applyParagraphRewrite(item: RewriteWorkspaceRiskItem) {
  await ensureAdvice(item)
  const advice = adviceFor(item)
  const rewritten = advice?.rewritten_paragraph?.trim()
  if (!rewritten) {
    ElMessage.warning('当前还没有生成整段改写建议')
    return
  }
  await persistRiskRewrite(item, rewritten, 'replace', item.riskId)
}

async function applySentenceRewrite(
  item: RewriteWorkspaceRiskItem,
  original: string,
  rewritten: string,
  index: number,
) {
  const current = item.currentText
  if (!current.includes(original)) {
    ElMessage.warning('当前段落里没有找到这句原文，请先确认文档当前版本。')
    return
  }
  const nextText = current.replace(original, rewritten)
  await persistRiskRewrite(item, nextText, 'replace', `${item.riskId}:sentence:${index}`)
}

async function ignoreRisk(item: RewriteWorkspaceRiskItem) {
  await persistRiskRewrite(item, item.currentText, 'ignored', `${item.riskId}:ignored`)
}

function downloadFile(variant: 'original' | 'edited') {
  window.open(getOnlyOfficeDownloadUrl(props.runId, variant), '_blank')
}

function goBack() {
  router.push({ name: 'report', params: { runId: props.runId } })
}

function openFallback() {
  const filename = (workspace.value?.filename || runMeta.value?.filename || '').toLowerCase()
  if (filename.endsWith('.doc')) {
    ElMessage.warning('当前这份 DOC 文档切到兼容模式后容易出现乱码，请继续使用 ONLYOFFICE；如需兼容模式，请先另存为 .docx 后重新上传。')
    return
  }
  router.replace({
    name: 'rewrite',
    params: { runId: props.runId },
    query: { ...route.query, fallback: '1' },
  })
}

function selectSection(sectionId: string) {
  activeSectionId.value = sectionId
  activeRiskId.value = visibleRiskItems.value[0]?.riskId || ''
}

function selectRisk(riskId: string) {
  activeRiskId.value = riskId
  const item = workspace.value?.riskItems.find(entry => entry.riskId === riskId)
  if (item) {
    activeSectionId.value = item.sectionId
  }
}

async function refreshWorkspace() {
  await loadWorkspace()
  if (activeRiskItem.value) {
    await ensureAdvice(activeRiskItem.value)
  }
}

watch(activeRiskItem, (item) => {
  if (item) {
    void ensureAdvice(item)
  }
}, { immediate: false })

watch(activeSectionId, () => {
  if (!visibleRiskItems.value.some(item => item.riskId === activeRiskId.value)) {
    activeRiskId.value = visibleRiskItems.value[0]?.riskId || ''
  }
})

onMounted(async () => {
  await loadWorkspace()
  if (activeRiskItem.value) {
    await ensureAdvice(activeRiskItem.value)
  }
})

onBeforeUnmount(() => {
  destroyOnlyOffice()
})
</script>

<style scoped>
.workspace {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f6f6f8;
  color: #1f2937;
}

.workspace__topbar {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(420px, 1fr) auto;
  gap: 16px;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e5e7eb;
  background: #fff;
}

.workspace__title {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.workspace__eyebrow,
.panel__eyebrow {
  margin: 0 0 4px;
  font-size: 12px;
  color: #6b7280;
}

.workspace__title h1,
.panel h3 {
  margin: 0;
  font-size: 20px;
  line-height: 1.2;
}

.workspace__subtitle {
  margin: 4px 0 0;
  font-size: 13px;
  color: #6b7280;
}

.workspace__metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.metric-card {
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fafafa;
}

.metric-card span {
  display: block;
  font-size: 12px;
  color: #6b7280;
}

.metric-card strong {
  display: block;
  margin-top: 6px;
  font-size: 22px;
  line-height: 1.2;
}

.metric-card--compact strong {
  font-size: 18px;
}

.workspace__actions {
  display: flex;
  gap: 10px;
}

.workspace__body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 380px;
  gap: 16px;
  padding: 16px;
}

.workspace__sidebar,
.workspace__main {
  min-height: 0;
}

.workspace__main {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 16px;
}

.panel {
  height: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
}

.panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid #f0f1f3;
}

.warning-stack {
  padding: 12px 16px 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.warning-item {
  padding: 10px 12px;
  border: 1px solid #fed7aa;
  border-radius: 8px;
  background: #fff7ed;
  color: #9a3412;
  font-size: 13px;
  line-height: 1.6;
}

.section-list,
.risk-card-list {
  height: calc(100% - 73px);
  overflow: auto;
  padding: 16px;
}

.section-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-item {
  width: 100%;
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.section-item:hover,
.section-item.is-active {
  border-color: #cbd5e1;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
}

.section-item__head,
.risk-card__head,
.sentence-card__head,
.editor-panel__toolbar,
.editor-panel__status,
.preview-panel__footer {
  display: flex;
  align-items: center;
  gap: 10px;
}

.section-item__title {
  font-weight: 600;
}

.section-item__meta {
  margin: 8px 0 0;
  font-size: 12px;
  color: #6b7280;
}

.risk-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #9ca3af;
  flex: 0 0 auto;
}

.is-high .risk-dot {
  background: #dc2626;
}

.is-medium .risk-dot {
  background: #ea580c;
}

.is-low .risk-dot {
  background: #7c3aed;
}

.preview-panel {
  display: flex;
  flex-direction: column;
}

.preview-panel__meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.risk-pill,
.score-badge,
.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  line-height: 1.6;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  color: #374151;
}

.risk-pill.is-high,
.risk-card.is-high .score-badge {
  border-color: #fecaca;
  background: #fef2f2;
  color: #b91c1c;
}

.risk-pill.is-medium,
.risk-card.is-medium .score-badge {
  border-color: #fed7aa;
  background: #fff7ed;
  color: #c2410c;
}

.risk-pill.is-low,
.risk-card.is-low .score-badge {
  border-color: #ddd6fe;
  background: #f5f3ff;
  color: #6d28d9;
}

.preview-panel__score {
  font-size: 13px;
  color: #6b7280;
}

.preview-panel__body {
  padding: 0 16px 16px;
}

.preview-panel__highlight {
  padding: 14px;
  border-radius: 8px;
  background: #f9fafb;
  line-height: 1.9;
  white-space: pre-wrap;
  word-break: break-word;
}

:deep(.highlight) {
  padding: 0 2px;
  border-radius: 4px;
}

:deep(.highlight--high) {
  background: rgba(239, 68, 68, 0.16);
}

:deep(.highlight--medium) {
  background: rgba(249, 115, 22, 0.16);
}

:deep(.highlight--low) {
  background: rgba(124, 58, 237, 0.16);
}

.preview-panel__footer {
  justify-content: space-between;
  padding: 12px 16px 16px;
  border-top: 1px solid #f0f1f3;
  font-size: 12px;
  color: #6b7280;
}

.editor-panel {
  display: flex;
  flex-direction: column;
}

.editor-panel__toolbar {
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #f0f1f3;
}

.editor-panel__status {
  font-size: 13px;
  color: #4b5563;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: #f59e0b;
}

.status-dot.is-ready {
  background: #16a34a;
}

.editor-host {
  flex: 1;
  min-height: 0;
}

.state-panel,
.empty-state {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.state-panel {
  padding: 28px;
}

.state-panel--error {
  border-color: #fecaca;
}

.state-panel__actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}

.risk-card-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.risk-card {
  padding: 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.18s ease, box-shadow 0.18s ease, opacity 0.18s ease;
}

.risk-card:hover,
.risk-card.is-active {
  border-color: #cbd5e1;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
}

.risk-card.status-ignored {
  opacity: 0.72;
}

.risk-card__head {
  justify-content: space-between;
}

.risk-card__title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.risk-card__badges {
  display: flex;
  align-items: center;
  gap: 8px;
}

.risk-card__block {
  margin-top: 12px;
}

.risk-card__block p,
.sentence-card p,
.state-panel p {
  margin: 6px 0 0;
  line-height: 1.75;
  word-break: break-word;
}

.risk-card__label {
  margin: 0;
  font-size: 12px;
  font-weight: 700;
  color: #6b7280;
}

.risk-card__actions {
  display: flex;
  gap: 8px;
  margin-top: 14px;
}

.sentence-list {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sentence-card {
  padding: 12px;
  border-radius: 8px;
  background: #f9fafb;
}

.sentence-card__head {
  justify-content: space-between;
  font-size: 12px;
  color: #6b7280;
}

.sentence-card__original {
  color: #991b1b;
}

.sentence-card__rewritten {
  color: #166534;
  font-weight: 600;
}

.sentence-card__explanation {
  color: #6b7280;
  font-size: 13px;
}

.empty-state {
  padding: 24px 16px;
  color: #6b7280;
  font-size: 13px;
  line-height: 1.7;
}

@media (max-width: 1440px) {
  .workspace__topbar {
    grid-template-columns: 1fr;
  }

  .workspace__metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .workspace__actions {
    justify-content: flex-start;
  }
}

@media (max-width: 1200px) {
  .workspace__body {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto;
  }

  .workspace__main {
    order: -1;
  }
}
</style>
