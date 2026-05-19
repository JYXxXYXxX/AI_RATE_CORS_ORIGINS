<template>
  <div class="rewrite-workspace">
    <RewriteTopBar
      :title="workspace?.title || runMeta?.title || '论文在线改写'"
      :filename="workspace?.filename || runMeta?.filename || '正在加载文档...'"
      :progress="Math.round(workspace?.metrics.currentAigcPercent || 0)"
      :progress-label="currentAigcLabel"
      :export-loading="exporting"
      @download-report="goBack"
      @export="exportDocument"
    />

    <RewriteWorkspaceStatsBar
      :metrics="statsMetrics"
      :can-undo="undoStack.length > 0"
      :can-redo="redoStack.length > 0"
      :save-loading="saving"
      :rewrite-all-loading="rewriteAllLoading"
      @back="goBack"
      @rewrite-all="applyAllVisible"
      @undo="undoLastAction"
      @redo="redoLastAction"
      @save="saveSession"
    />

    <div v-if="loading" class="workspace-state">
      <el-skeleton :rows="14" animated />
    </div>

    <div v-else-if="loadError" class="workspace-state workspace-state--error">
      <h3>改写页面加载失败</h3>
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
          :title="workspace?.title || '论文正文'"
          :blocks="renderBlocks"
          :word-count="wordCount"
          :source-format="(workspace?.sourceFormat || 'docx').toLowerCase()"
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
          :tab-counts="tabCounts"
          @change-tab="changeTab"
          @select-risk="selectRisk"
          @previous="selectRelative(-1)"
          @next="selectRelative(1)"
          @apply="applyActiveSuggestion"
          @ignore="ignoreActiveRisk"
        />
      </div>
    </div>

    <RewriteBottomActionBar
      :export-loading="exporting"
      @download-original="downloadOriginal"
      @download-report="goBack"
      @export="exportDocument"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import RewriteBottomActionBar from './RewriteBottomActionBar.vue'
import RewriteDocumentPane, { type RenderBlock } from './RewriteDocumentPane.vue'
import RewriteOutlineNav, { type OutlineItem } from './RewriteOutlineNav.vue'
import RewriteWorkspaceStatsBar from './RewriteWorkspaceStatsBar.vue'
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
  getOriginalDocumentUrl,
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

const riskItemsBySection = computed(() => {
  const map = new Map<string, RewriteWorkspaceRiskItem[]>()
  for (const item of riskItems.value) {
    const key = item.sectionId || normalizeTitle(item.sectionTitle)
    const list = map.get(key) || []
    list.push(item)
    map.set(key, list)
  }
  return map
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

const currentAigcLabel = computed(() => `${Math.round(workspace.value?.metrics.currentAigcPercent || 0)}%`)

const wordCount = computed(() =>
  renderBlocks.value.reduce((sum, block) => sum + (block.currentText?.replace(/\s+/g, '').length || 0), 0)
)

function effectiveLevel(item: RewriteWorkspaceRiskItem): RiskTab {
  const status = statusByRiskId.value[item.riskId]
  if (status === 'applied' || status === 'ignored') return 'normal'
  return item.riskLevel
}

const tabCounts = computed<Record<RiskTab, number>>(() => ({
  high: riskItems.value.filter((item) => effectiveLevel(item) === 'high').length,
  medium: riskItems.value.filter((item) => effectiveLevel(item) === 'medium').length,
  low: riskItems.value.filter((item) => effectiveLevel(item) === 'low').length,
  normal: riskItems.value.filter((item) => effectiveLevel(item) === 'normal').length,
}))

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

const statsMetrics = computed(() => [
  { label: 'AIGC 疑似度', value: currentAigcLabel.value, helper: '当前检测', tone: 'high' as const },
  { label: '重复率', value: currentDupPercent.value, helper: '预测区间', tone: 'medium' as const },
  { label: '优化后预计', value: estimatedOptimizedPercent.value, helper: '改写同步更新', tone: 'brand' as const },
  { label: '已改写', value: `${rewrittenCount.value} / ${riskItems.value.length}`, helper: '风险句数量', tone: 'low' as const },
  { label: '字数', value: String(wordCount.value), helper: (workspace.value?.sourceFormat || 'docx').toUpperCase() },
])

const outlineItems = computed<OutlineItem[]>(() => {
  const sourceSections = workspace.value?.sections || []
  const result: OutlineItem[] = []

  for (const section of sourceSections) {
    const sectionRisks = riskItemsBySection.value.get(section.sectionId) || []
    const sectionTitle = normalizeTitle(section.title) || fallbackSectionTitle(section.sectionIndex)
    const anchorBlock = findAnchorBlock(section.sectionId, section.title)

    result.push({
      id: anchorBlock?.blockId || section.sectionId,
      title: sectionTitle,
      depth: sectionDepth(sectionTitle),
      riskLevel: sectionRisks.length ? aggregateRiskLevel(sectionRisks) : section.riskLevel,
      counts: sectionRisks.length ? aggregateCounts(sectionRisks) : section.riskCounts,
    })
  }

  if (result.length) return dedupeOutlineItems(result)

  return buildOutlineFromBlocks()
})

function dedupeOutlineItems(items: OutlineItem[]) {
  const seen = new Set<string>()
  return items.filter((item) => {
    const key = `${item.title}-${item.id}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function buildOutlineFromBlocks(): OutlineItem[] {
  const items: OutlineItem[] = []
  const seenTitles = new Set<string>()
  for (const block of renderBlocks.value) {
    const title = normalizeTitle(block.sectionTitle || (block.type === 'heading' || block.type === 'title' ? block.text : ''))
    if (!title || seenTitles.has(title)) continue
    seenTitles.add(title)
    const linked = riskItems.value.filter((item) => normalizeTitle(item.sectionTitle) === title)
    items.push({
      id: block.blockId,
      title,
      depth: sectionDepth(title),
      riskLevel: aggregateRiskLevel(linked),
      counts: aggregateCounts(linked),
    })
  }
  return items
}

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

function normalizeTitle(value: string | null | undefined) {
  return String(value || '')
    .replace(/\[\d+\]/g, '')
    .replace(/\s+\d+$/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function fallbackSectionTitle(index: number) {
  return `第 ${index + 1} 部分`
}

function sectionDepth(title: string) {
  if (/^\d+\.\d+\.\d+/.test(title)) return 3
  if (/^\d+\.\d+/.test(title)) return 2
  if (/^第.+章/.test(title) || /^\d+/.test(title) || /^(摘要|结论|参考文献|致谢|附录|Abstract)$/i.test(title)) {
    return 1
  }
  return 1
}

function findAnchorBlock(sectionId: string, sectionTitle?: string | null) {
  const normalized = normalizeTitle(sectionTitle)
  return renderBlocks.value.find((block) => {
    const matchesTitle = normalized && normalizeTitle(block.sectionTitle) === normalized
    const matchesRisk = riskItems.value.some((item) => item.sectionId === sectionId && item.blockId === block.blockId)
    const matchesHeading = normalizeTitle(block.text) === normalized && (block.type === 'heading' || block.type === 'title')
    return Boolean(matchesTitle || matchesRisk || matchesHeading)
  })
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
  if (!active) {
    activeOutlineId.value = outlineItems.value[0]?.id || ''
    return
  }

  const bySection = outlineItems.value.find((item) =>
    normalizeTitle(item.title) === normalizeTitle(active.sectionTitle)
  )
  activeOutlineId.value = bySection?.id || active.blockId
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

function downloadOriginal() {
  const documentId = workspace.value?.documentId || runMeta.value?.document_id
  if (!documentId) return
  window.open(getOriginalDocumentUrl(documentId), '_blank')
}

function changeTab(value: RiskTab) {
  activeTab.value = value
  syncSelection()
}

function selectRisk(riskId: string) {
  activeRiskId.value = riskId
  const item = riskItems.value.find((entry) => entry.riskId === riskId)
  if (!item) return
  const outline = outlineItems.value.find((entry) => normalizeTitle(entry.title) === normalizeTitle(item.sectionTitle))
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
  const directRisk = riskItems.value.find((item) => item.blockId === outlineId)
  if (directRisk) {
    selectRisk(directRisk.riskId)
    return
  }

  const outline = outlineItems.value.find((entry) => entry.id === outlineId)
  if (!outline) return
  const byHeading = riskItems.value.find((item) => normalizeTitle(item.sectionTitle) === normalizeTitle(outline.title))
  if (byHeading) {
    selectRisk(byHeading.riskId)
  }
}

async function ensureAdvice(item: RewriteWorkspaceRiskItem) {
  if (adviceCache.value[item.riskId]) return adviceCache.value[item.riskId]
  const advice = await getRewriteAdvice(props.runId, adviceTargetIndex(item))
  adviceCache.value = {
    ...adviceCache.value,
    [item.riskId]: advice,
  }
  return advice
}

function adviceTargetIndex(item: RewriteWorkspaceRiskItem) {
  if (workspace.value?.mode === 'report') {
    return item.paragraphIndex ?? item.displayOrder ?? item.sectionIndex
  }
  return item.sectionIndex
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
    .filter((block) => block.type === 'paragraph' || block.type === 'heading' || block.type === 'title')
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
      ElMessage.success('正在导出保留原格式的修改稿')
      return
    }

    const { blob } = await exportRun(props.runId, buildExportSections(), 'docx')
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'PataFix_修改稿.docx'
    anchor.click()
    URL.revokeObjectURL(url)
    await loadWorkspace()
    ElMessage.success('已导出修改稿')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '导出失败')
  } finally {
    exporting.value = false
  }
}

watch([visibleRiskItems, activeTab, outlineItems], () => {
  syncSelection()
})

watch(activeRiskItem, async (item) => {
  if (!item) return
  if (!adviceCache.value[item.riskId] && effectiveLevel(item) !== 'normal') {
    try {
      const advice = await getRewriteAdvice(props.runId, adviceTargetIndex(item))
      adviceCache.value = {
        ...adviceCache.value,
        [item.riskId]: advice,
      }
    } catch {
      // Keep panel usable even if advice loading fails.
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
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  background:
    radial-gradient(circle at top left, rgba(15, 143, 79, 0.08), transparent 28%),
    linear-gradient(180deg, #f6f7f1 0%, #f0f3f6 100%);
}

.rewrite-workspace__body {
  min-height: 0;
  display: grid;
  grid-template-columns: 276px minmax(0, 1fr) 392px;
  gap: 18px;
  padding: 18px 24px;
}

.workspace-panel {
  min-height: 0;
  border-radius: 24px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.07);
  padding: 18px;
}

.workspace-panel--center {
  background: linear-gradient(180deg, rgba(243, 245, 242, 0.96) 0%, rgba(236, 240, 245, 0.96) 100%);
}

.workspace-state {
  margin: 18px 24px;
  border-radius: 24px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.07);
  padding: 24px;
}

.workspace-state--error {
  display: grid;
  gap: 12px;
}

.workspace-state--error h3 {
  margin: 0;
  font-size: 22px;
  color: #111827;
}

.workspace-state--error p {
  margin: 0;
  color: #4b5563;
  line-height: 1.8;
}

@media (max-width: 1500px) {
  .rewrite-workspace__body {
    grid-template-columns: 248px minmax(0, 1fr) 352px;
  }
}

@media (max-width: 1220px) {
  .rewrite-workspace__body {
    grid-template-columns: 1fr;
  }
}
</style>
