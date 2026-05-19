<template>
  <div class="rewrite-workspace">
    <RewriteTopBar
      :title="workspace?.title || runMeta?.title || '论文在线改写'"
      :filename="workspace?.filename || runMeta?.filename || '正在加载文档...'"
      :metrics="topMetrics"
      :can-undo="undoStack.length > 0"
      :can-redo="redoStack.length > 0"
      :save-loading="saving"
      :export-loading="exporting"
      :rewrite-all-loading="rewriteAllLoading"
      @back="goBack"
      @rewrite-all="applyAllVisible"
      @undo="undoLastAction"
      @redo="redoLastAction"
      @save="saveSession"
      @export="exportDocument"
    />

    <div v-if="loading" class="workspace-state">
      <el-skeleton :rows="14" animated />
    </div>

    <div v-else-if="loadError" class="workspace-state workspace-state--error">
      <h3>改写页加载失败</h3>
      <p>{{ loadError }}</p>
      <el-button type="primary" @click="loadWorkspace">重新加载</el-button>
    </div>

    <div v-else class="rewrite-workspace__body">
      <div class="workspace-panel workspace-panel--left">
        <RewriteOutlineNav
          :items="outlineItems"
          :active-id="activeOutlineId"
          :warnings="workspace?.warnings || []"
          @select="selectOutline"
        />
      </div>

      <div class="workspace-panel workspace-panel--center">
        <RewriteDocumentPane
          :blocks="renderBlocks"
          :risk-item-by-block-id="riskItemByBlockId"
          :status-by-risk-id="statusByRiskId"
          :active-block-id="activeBlockId"
          @select-block="selectBlock"
        />
      </div>

      <div class="workspace-panel workspace-panel--right">
        <RewriteSuggestionPanel
          :active-tab="activeTab"
          :active-risk-id="activeRiskId"
          :active-item="activeRiskItem"
          :active-status="activeRiskStatus"
          :visible-items="visibleRiskItems"
          :suggestion="activeSuggestion"
          :has-previous="activeIndex > 0"
          :has-next="activeIndex >= 0 && activeIndex < visibleRiskItems.length - 1"
          :apply-loading="applyLoading"
          :status-by-risk-id="statusByRiskId"
          @change-tab="changeTab"
          @select-risk="selectRisk"
          @previous="selectRelative(-1)"
          @next="selectRelative(1)"
          @apply="applyActiveSuggestion"
          @ignore="ignoreActiveRisk"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import RewriteDocumentPane, { type RenderBlock } from './RewriteDocumentPane.vue'
import RewriteOutlineNav, { type OutlineItem } from './RewriteOutlineNav.vue'
import RewriteSuggestionPanel from './RewriteSuggestionPanel.vue'
import RewriteTopBar from './RewriteTopBar.vue'
import type {
  AnalysisRunStatusResponse,
  DocumentBlock,
  RewriteAdviceResponse,
  RewriteWorkspaceRiskItem,
  RewriteWorkspaceResponse,
  UnifiedReportResponse,
} from '../../types'
import {
  applyOnlyOfficePatches,
  createPatch,
  exportRun,
  getOnlyOfficeDownloadUrl,
  getRewriteAdvice,
  getRewriteWorkspace,
  getRun,
  getRunBlocks,
  getUnifiedReport,
} from '../../api'

type RiskTab = 'high' | 'medium' | 'low' | 'normal'
type RiskStatus = RewriteWorkspaceRiskItem['status']

interface RiskState {
  status: RiskStatus
  currentText: string
}

interface HistoryEntry {
  riskId: string
  previous: RiskState
  next: RiskState
}

const props = defineProps<{
  runId: string
}>()

const router = useRouter()

const loading = ref(true)
const loadError = ref('')
const saving = ref(false)
const exporting = ref(false)
const applyLoading = ref(false)
const rewriteAllLoading = ref(false)

const runMeta = ref<AnalysisRunStatusResponse | null>(null)
const workspace = ref<RewriteWorkspaceResponse | null>(null)
const report = ref<UnifiedReportResponse | null>(null)
const blocks = ref<DocumentBlock[]>([])

const activeTab = ref<RiskTab>('high')
const activeRiskId = ref('')
const activeOutlineId = ref('')

const adviceCache = ref<Record<string, RewriteAdviceResponse>>({})
const riskStateMap = ref<Record<string, RiskState>>({})
const initialStateMap = ref<Record<string, RiskState>>({})
const undoStack = ref<HistoryEntry[]>([])
const redoStack = ref<HistoryEntry[]>([])

const riskItems = computed(() => workspace.value?.riskItems || [])

const statusByRiskId = computed<Record<string, RiskStatus>>(() => {
  const result: Record<string, RiskStatus> = {}
  for (const item of riskItems.value) {
    result[item.riskId] = riskStateMap.value[item.riskId]?.status || item.status
  }
  return result
})

const renderBlocks = computed<RenderBlock[]>(() => {
  return (blocks.value || []).map((block) => {
    const linkedRisk = riskItems.value.find((item) => item.blockId === block.blockId)
    const currentText = linkedRisk
      ? (riskStateMap.value[linkedRisk.riskId]?.currentText || linkedRisk.currentText || linkedRisk.originalText)
      : block.text
    return {
      ...block,
      currentText,
    }
  })
})

const riskItemByBlockId = computed<Record<string, RewriteWorkspaceRiskItem | undefined>>(() => {
  const map: Record<string, RewriteWorkspaceRiskItem | undefined> = {}
  for (const item of riskItems.value) {
    map[item.blockId] = item
  }
  return map
})

const activeRiskItem = computed(() =>
  riskItems.value.find((item) => item.riskId === activeRiskId.value) || null
)

const activeRiskStatus = computed<RiskStatus>(() =>
  activeRiskItem.value ? (riskStateMap.value[activeRiskItem.value.riskId]?.status || activeRiskItem.value.status) : 'pending'
)

const activeBlockId = computed(() => activeRiskItem.value?.blockId || activeOutlineId.value || '')

const currentDupPercent = computed(() => {
  const value = report.value?.summary?.predicted_cnki_dup?.center_percent
  return typeof value === 'number' ? `${Math.round(value)}%` : '--'
})

const wordCount = computed(() =>
  renderBlocks.value.reduce((sum, block) => sum + (block.currentText?.replace(/\s+/g, '').length || 0), 0)
)

function effectiveLevel(item: RewriteWorkspaceRiskItem): RiskTab {
  const status = statusByRiskId.value[item.riskId]
  if (status === 'applied' || status === 'ignored') return 'normal'
  return item.riskLevel
}

const visibleRiskItems = computed(() => {
  const filtered = riskItems.value.filter((item) => effectiveLevel(item) === activeTab.value)
  return filtered.sort((a, b) => a.displayOrder - b.displayOrder)
})

const activeIndex = computed(() => visibleRiskItems.value.findIndex((item) => item.riskId === activeRiskId.value))

const activeSuggestion = computed(() => (activeRiskItem.value ? adviceCache.value[activeRiskItem.value.riskId] || null : null))

const rewrittenCount = computed(() =>
  riskItems.value.filter((item) => statusByRiskId.value[item.riskId] === 'applied').length
)

const estimatedOptimizedPercent = computed(() => {
  const base = workspace.value?.metrics.currentAigcPercent || 0
  let reduction = 0
  for (const item of riskItems.value) {
    if (statusByRiskId.value[item.riskId] !== 'applied') continue
    if (item.riskLevel === 'high') reduction += 7
    else if (item.riskLevel === 'medium') reduction += 4
    else if (item.riskLevel === 'low') reduction += 2
  }
  return `${Math.max(0, Math.round(base - reduction))}%`
})

const topMetrics = computed(() => [
  { label: 'AIGC 疑似度', value: `${Math.round(workspace.value?.metrics.currentAigcPercent || 0)}%` },
  { label: '重复率', value: currentDupPercent.value },
  { label: '优化后预计', value: estimatedOptimizedPercent.value },
  { label: '已改写', value: `${rewrittenCount.value} / ${riskItems.value.length}` },
  { label: '字数', value: String(wordCount.value) },
  { label: '文档格式', value: (workspace.value?.sourceFormat || 'docx').toUpperCase() },
])

const outlineItems = computed<OutlineItem[]>(() => {
  const items: OutlineItem[] = []
  const seen = new Set<string>()

  const firstBlock = renderBlocks.value[0]
  if (firstBlock && firstBlock.text.trim()) {
    items.push({
      id: firstBlock.blockId,
      title: firstBlock.text.trim(),
      riskLevel: 'normal',
      counts: { high: 0, medium: 0, low: 0, normal: 0 },
    })
  }

  for (const block of renderBlocks.value) {
    const title = normalizeSectionTitle(block.sectionTitle)
    if (!title || seen.has(title)) continue
    seen.add(title)
    const linked = riskItems.value.filter((item) => normalizeSectionTitle(item.sectionTitle) === title)
    items.push({
      id: block.blockId,
      title,
      riskLevel: aggregateRiskLevel(linked),
      counts: aggregateCounts(linked),
    })
  }

  if (items.length > 1) {
    return items
  }

  return (workspace.value?.sections || []).map((section) => ({
    id: section.sectionId,
    title: section.title,
    riskLevel: aggregateRiskLevel(
      riskItems.value.filter((item) => item.sectionId === section.sectionId)
    ),
    counts: aggregateCounts(riskItems.value.filter((item) => item.sectionId === section.sectionId)),
  }))
})

function aggregateCounts(items: RewriteWorkspaceRiskItem[]) {
  const counts = { high: 0, medium: 0, low: 0, normal: 0 }
  for (const item of items) {
    counts[effectiveLevel(item)] += 1
  }
  return counts
}

function aggregateRiskLevel(items: RewriteWorkspaceRiskItem[]): RiskTab {
  const counts = aggregateCounts(items)
  if (counts.high) return 'high'
  if (counts.medium) return 'medium'
  if (counts.low) return 'low'
  return 'normal'
}

function normalizeSectionTitle(value: string | null | undefined) {
  return String(value || '')
    .replace(/\[\d+\]/g, '')
    .replace(/\s+\d+$/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function syncInitialState(nextWorkspace: RewriteWorkspaceResponse) {
  const nextRiskState: Record<string, RiskState> = {}
  const nextInitialState: Record<string, RiskState> = {}

  for (const item of nextWorkspace.riskItems) {
    const state = {
      status: item.status,
      currentText: item.currentText || item.originalText,
    }
    nextRiskState[item.riskId] = state
    nextInitialState[item.riskId] = { ...state }
  }

  riskStateMap.value = nextRiskState
  initialStateMap.value = nextInitialState
  undoStack.value = []
  redoStack.value = []
}

function syncSelection() {
  const preferredItems = visibleRiskItems.value.length ? visibleRiskItems.value : riskItems.value
  if (!preferredItems.some((item) => item.riskId === activeRiskId.value)) {
    activeRiskId.value = preferredItems[0]?.riskId || ''
  }

  const active = activeRiskItem.value
  if (!active) return
  if (active.sectionTitle) {
    const outline = outlineItems.value.find((item) => item.title.trim() === active.sectionTitle?.trim())
    activeOutlineId.value = outline?.id || active.blockId
  } else {
    activeOutlineId.value = active.blockId
  }
}

async function loadWorkspace() {
  loading.value = true
  loadError.value = ''
  try {
    const [nextRun, nextWorkspace, nextBlocks] = await Promise.all([
      getRun(props.runId),
      getRewriteWorkspace(props.runId),
      getRunBlocks(props.runId),
    ])
    runMeta.value = nextRun
    workspace.value = nextWorkspace
    blocks.value = nextBlocks.blocks.sort((a, b) => a.displayOrder - b.displayOrder)
    syncInitialState(nextWorkspace)
    activeTab.value = nextWorkspace.metrics.highCount > 0 ? 'high' : nextWorkspace.metrics.mediumCount > 0 ? 'medium' : nextWorkspace.metrics.lowCount > 0 ? 'low' : 'normal'
    try {
      report.value = await getUnifiedReport(props.runId)
    } catch {
      report.value = null
    }
    syncSelection()
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '改写工作区加载失败'
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.push(`/app/report/${props.runId}`)
}

function changeTab(value: RiskTab) {
  activeTab.value = value
  syncSelection()
}

function selectRisk(riskId: string) {
  activeRiskId.value = riskId
  const item = riskItems.value.find((entry) => entry.riskId === riskId)
  if (!item) return
  const outline = outlineItems.value.find((entry) => normalizeSectionTitle(entry.title) === normalizeSectionTitle(item.sectionTitle))
  activeOutlineId.value = outline?.id || item.blockId
}

function selectRelative(offset: number) {
  if (activeIndex.value < 0) return
  const next = visibleRiskItems.value[activeIndex.value + offset]
  if (next) selectRisk(next.riskId)
}

function selectBlock(blockId: string) {
  const item = riskItems.value.find((entry) => entry.blockId === blockId)
  if (item) {
    selectRisk(item.riskId)
  }
}

function selectOutline(outlineId: string) {
  activeOutlineId.value = outlineId
  const outlineTitle = normalizeSectionTitle(outlineItems.value.find((entry) => entry.id === outlineId)?.title)
  const byHeading = riskItems.value.find((item) => normalizeSectionTitle(item.sectionTitle) === outlineTitle)
  if (byHeading) {
    selectRisk(byHeading.riskId)
    return
  }
  const bySectionId = riskItems.value.find((item) => item.sectionId === outlineId)
  if (bySectionId) {
    selectRisk(bySectionId.riskId)
  }
}

async function ensureAdvice(item: RewriteWorkspaceRiskItem) {
  if (adviceCache.value[item.riskId]) return adviceCache.value[item.riskId]
  const advice = await getRewriteAdvice(props.runId, item.sectionIndex)
  adviceCache.value = {
    ...adviceCache.value,
    [item.riskId]: advice,
  }
  return advice
}

function pushHistory(entry: HistoryEntry) {
  undoStack.value = [...undoStack.value, entry]
  redoStack.value = []
}

function applyStateChange(riskId: string, next: RiskState, previous?: RiskState, push = true) {
  const current = previous || riskStateMap.value[riskId]
  if (!current) return
  riskStateMap.value = {
    ...riskStateMap.value,
    [riskId]: { ...next },
  }
  if (push) {
    pushHistory({
      riskId,
      previous: { ...current },
      next: { ...next },
    })
  }
}

async function applyActiveSuggestion() {
  const item = activeRiskItem.value
  if (!item) return
  applyLoading.value = true
  try {
    const advice = await ensureAdvice(item)
    const rewrittenText = advice.rewritten_paragraph?.trim() || item.rewriteHint || item.currentText || item.originalText
    applyStateChange(
      item.riskId,
      {
        status: 'applied',
        currentText: rewrittenText,
      }
    )
    ElMessage.success('已替换到正文预览中')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '改写建议生成失败')
  } finally {
    applyLoading.value = false
  }
}

function ignoreActiveRisk() {
  const item = activeRiskItem.value
  if (!item) return
  applyStateChange(
    item.riskId,
    {
      status: 'ignored',
      currentText: item.originalText,
    }
  )
  ElMessage.success('该条风险已忽略')
}

async function applyAllVisible() {
  const candidates = visibleRiskItems.value.filter((item) => statusByRiskId.value[item.riskId] === 'pending')
  if (!candidates.length) {
    ElMessage.info('当前筛选下没有待改写内容')
    return
  }

  rewriteAllLoading.value = true
  try {
    for (const item of candidates) {
      const advice = await ensureAdvice(item)
      const rewrittenText = advice.rewritten_paragraph?.trim() || item.rewriteHint || item.currentText || item.originalText
      applyStateChange(
        item.riskId,
        {
          status: 'applied',
          currentText: rewrittenText,
        }
      )
    }
    ElMessage.success(`已批量改写 ${candidates.length} 条风险内容`)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '批量改写失败')
  } finally {
    rewriteAllLoading.value = false
  }
}

function undoLastAction() {
  const entry = undoStack.value[undoStack.value.length - 1]
  if (!entry) return
  undoStack.value = undoStack.value.slice(0, -1)
  redoStack.value = [...redoStack.value, entry]
  riskStateMap.value = {
    ...riskStateMap.value,
    [entry.riskId]: { ...entry.previous },
  }
}

function redoLastAction() {
  const entry = redoStack.value[redoStack.value.length - 1]
  if (!entry) return
  redoStack.value = redoStack.value.slice(0, -1)
  undoStack.value = [...undoStack.value, entry]
  riskStateMap.value = {
    ...riskStateMap.value,
    [entry.riskId]: { ...entry.next },
  }
}

function buildDirtyItems() {
  return riskItems.value.filter((item) => {
    const current = riskStateMap.value[item.riskId]
    const initial = initialStateMap.value[item.riskId]
    if (!current || !initial) return false
    return current.status !== initial.status || current.currentText !== initial.currentText
  })
}

async function persistSession() {
  const dirtyItems = buildDirtyItems()
  if (!dirtyItems.length) return 0

  for (const item of dirtyItems) {
    const current = riskStateMap.value[item.riskId]
    if (!current) continue
    await createPatch(props.runId, {
      block_id: item.blockId,
      old_text: item.originalText,
      new_text: current.status === 'ignored' ? item.originalText : current.currentText,
      source_map: {
        action: current.status === 'ignored' ? 'ignored' : 'rewrite',
        risk_id: item.riskId,
        section_id: item.sectionId,
      },
    })
  }
  return dirtyItems.length
}

function buildExportSections() {
  return renderBlocks.value
    .filter((block) => block.type === 'paragraph' || block.type === 'heading')
    .map((block, index) => ({
      section_index: index,
      content: block.currentText,
      risk_level: riskItemByBlockId.value[block.blockId]?.riskLevel || 'normal',
    }))
}

async function saveSession() {
  saving.value = true
  try {
    const persisted = await persistSession()
    if (persisted) {
      await loadWorkspace()
      ElMessage.success(`已保存 ${persisted} 条改写结果`)
    } else {
      ElMessage.info('当前没有需要保存的改动')
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function exportDocument() {
  exporting.value = true
  try {
    await persistSession()
    const sourceFormat = (workspace.value?.sourceFormat || '').toLowerCase()

    if (sourceFormat === 'docx') {
      await applyOnlyOfficePatches(props.runId)
      window.open(getOnlyOfficeDownloadUrl(props.runId, 'edited'), '_blank')
      await loadWorkspace()
      ElMessage.success('正在导出保留原格式的改写稿')
      return
    }

    const { blob } = await exportRun(props.runId, buildExportSections(), 'docx')
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'PataFix_改写稿.docx'
    anchor.click()
    URL.revokeObjectURL(url)
    await loadWorkspace()
    ElMessage.success('已导出改写稿')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '导出失败')
  } finally {
    exporting.value = false
  }
}

watch([visibleRiskItems, activeTab], () => {
  syncSelection()
})

watch(activeRiskItem, async (item) => {
  if (!item) return
  if (!adviceCache.value[item.riskId] && effectiveLevel(item) !== 'normal') {
    try {
      const advice = await getRewriteAdvice(props.runId, item.sectionIndex)
      adviceCache.value = {
        ...adviceCache.value,
        [item.riskId]: advice,
      }
    } catch {
      // keep panel usable even if advice loading fails
    }
  }
})

onMounted(() => {
  loadWorkspace()
})
</script>

<style scoped>
.rewrite-workspace {
  min-height: 100vh;
  background:
    linear-gradient(180deg, #f7f6f2 0%, #f3f4f6 100%);
  display: flex;
  flex-direction: column;
}

.rewrite-workspace__body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr) 420px;
  gap: 18px;
  padding: 18px;
}

.workspace-panel {
  min-height: 0;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 22px;
  box-shadow: 0 20px 44px rgba(15, 23, 42, 0.07);
  padding: 18px;
}

.workspace-panel--center {
  background: linear-gradient(180deg, #f4f4f5 0%, #eceff3 100%);
}

.workspace-state {
  margin: 18px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 22px;
  box-shadow: 0 20px 44px rgba(15, 23, 42, 0.07);
  padding: 24px;
}

.workspace-state--error {
  display: grid;
  gap: 12px;
}

.workspace-state--error h3 {
  margin: 0;
  color: #111827;
}

.workspace-state--error p {
  margin: 0;
  color: #4b5563;
  line-height: 1.7;
}

@media (max-width: 1500px) {
  .rewrite-workspace__body {
    grid-template-columns: 240px minmax(0, 1fr) 360px;
  }
}

@media (max-width: 1200px) {
  .rewrite-workspace__body {
    grid-template-columns: 1fr;
  }
}
</style>
