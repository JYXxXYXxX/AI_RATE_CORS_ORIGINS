<template>
  <div class="rewrite-workspace-page">
    <RewriteTopNav
      :aigc-percent="metrics.currentAigcPercent"
      :export-loading="exportLoading"
      @download-report="openPrintReport"
      @export-document="exportDocument"
    />

    <RewriteStatsBar
      :metrics="metrics"
      :can-undo="history.length > 0"
      :can-redo="redoStack.length > 0"
      @back-report="goReport"
      @rewrite-all="rewriteAll"
      @undo="undo"
      @redo="redo"
      @save="save"
    />

    <div v-if="loading" class="state-card">正在整理文档结构和风险批注...</div>
    <div v-else-if="errorMessage" class="state-card error">{{ errorMessage }}</div>

    <RewriteMainLayout v-else>
      <ChapterSidebar
        :sections="sections"
        :active-section-id="activeSectionId"
        :warnings="warnings"
        @select-section="selectSection"
      />
      <DocumentCanvas
        ref="documentCanvasRef"
        :document-id="documentId"
        :title="workspaceTitle"
        :filename="filename"
        :source-format="sourceFormat"
        :risk-items="riskItems"
        :active-risk-id="activeRiskId"
        @select-risk="selectRisk"
      />
      <RewriteRiskPanel
        :active-tab="activeTab"
        :active-risk-id="activeRiskId"
        :active-item="activeRiskItem"
        :visible-items="visibleRiskItems"
        :counts="tabCounts"
        :suggestion="activeSuggestion"
        :suggestion-loading="adviceLoading"
        :has-previous="activeIndex > 0"
        :has-next="activeIndex >= 0 && activeIndex < orderedRiskItems.length - 1"
        @change-tab="changeTab"
        @select-risk="selectRisk"
        @previous="selectRelative(-1)"
        @next="selectRelative(1)"
        @apply="applyActive"
        @ignore="ignoreActive"
      />
    </RewriteMainLayout>

    <RewriteBottomActionBar
      v-if="!loading && !errorMessage"
      :export-loading="exportLoading"
      @reanalyze="save"
      @download-report="openPrintReport"
      @export-document="exportDocument"
 />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  createPatch,
  exportRun,
  getRunBlocks,
  getRewriteAdvice,
  getRunSections,
  getRewriteWorkspace,
} from '../api'
import type {
  DocumentBlock,
  RewriteAdviceResponse,
  RewriteWorkspaceResponse,
  RewriteWorkspaceRiskItem,
  RewriteWorkspaceSectionNode,
  RunSectionItem,
} from '../types'
import ChapterSidebar from '../components/rewrite/ChapterSidebar.vue'
import DocumentCanvas from '../components/rewrite/DocumentCanvas.vue'
import RewriteBottomActionBar from '../components/rewrite/RewriteBottomActionBar.vue'
import RewriteMainLayout from '../components/rewrite/RewriteMainLayout.vue'
import RewriteStatsBar from '../components/rewrite/RewriteStatsBar.vue'
import RewriteRiskPanel from '../components/rewrite/RewriteSuggestionPanel.vue'
import RewriteTopNav from '../components/rewrite/RewriteTopNav.vue'
import type {
  RewriteHistoryEntry,
  RewriteMetricsState,
  RewriteParagraph,
  RewriteRiskItem,
  RewriteSection,
  RiskLevel,
} from '../components/rewrite/types'

const props = defineProps<{
  runId: string
}>()

const router = useRouter()
const loading = ref(true)
const exportLoading = ref(false)
const errorMessage = ref('')
const workspaceTitle = ref('论文在线改写')
const filename = ref('paper.docx')
const sourceFormat = ref('docx')
const workspaceMode = ref<'estimate' | 'report'>('estimate')
const documentId = ref('')
const warnings = ref<string[]>([])
const baseMetrics = ref<RewriteMetricsState>(emptyMetrics())
const paragraphs = ref<RewriteParagraph[]>([])
const sections = ref<RewriteSection[]>([])
const riskItems = ref<RewriteRiskItem[]>([])
const adviceCache = ref<Record<string, RewriteAdviceResponse>>({})
const adviceLoading = ref(false)
const activeRiskId = ref('')
const activeParagraphId = ref('')
const activeSectionId = ref('')
const activeTab = ref<RiskLevel>('high')
const history = ref<RewriteHistoryEntry[]>([])
const redoStack = ref<RewriteHistoryEntry[]>([])
const documentCanvasRef = ref<{ scrollToSection: (title: string) => boolean } | null>(null)

const riskById = computed<Record<string, RewriteRiskItem>>(() =>
  Object.fromEntries(riskItems.value.map((item) => [item.riskId, item]))
)

const activeRiskItem = computed(() => riskById.value[activeRiskId.value] || null)
const activeSuggestion = computed(() => adviceCache.value[activeRiskId.value] || null)
const orderedRiskItems = computed(() =>
  [...riskItems.value].sort((a, b) => a.displayOrder - b.displayOrder)
)
const visibleRiskItems = computed(() =>
  orderedRiskItems.value.filter((item) => effectiveLevel(item) === activeTab.value)
)
const activeIndex = computed(() =>
  visibleRiskItems.value.findIndex((item) => item.riskId === activeRiskId.value)
)

const tabCounts = computed<Record<RiskLevel, number>>(() => {
  const counts: Record<RiskLevel, number> = { high: 0, medium: 0, low: 0, normal: 0 }
  for (const item of riskItems.value) counts[effectiveLevel(item)] += 1
  return counts
})

const metrics = computed<RewriteMetricsState>(() => {
  const rewrittenCount = riskItems.value.filter((item) => item.status === 'applied').length
  const ignoredCount = riskItems.value.filter((item) => item.status === 'ignored').length
  const pendingItems = riskItems.value.filter((item) => item.status === 'pending')
  const appliedScore = riskItems.value
    .filter((item) => item.status === 'applied')
    .reduce((sum, item) => sum + Math.max(4, item.aigcScore * 0.08), 0)
  const currentAigcPercent = clamp(baseMetrics.value.currentAigcPercent - appliedScore / Math.max(1, riskItems.value.length), 4, 99)
  const remainingEstimate = pendingItems.reduce((sum, item) => sum + Math.max(2, item.aigcScore * 0.035), 0) / Math.max(1, riskItems.value.length)
  const estimatedOptimizedPercent = Math.min(
    currentAigcPercent,
    clamp(currentAigcPercent - remainingEstimate, 3, 99)
  )

  return {
    ...baseMetrics.value,
    currentAigcPercent,
    estimatedOptimizedPercent,
    rewrittenCount,
    ignoredCount,
    totalRiskCount: riskItems.value.length,
    highCount: tabCounts.value.high,
    mediumCount: tabCounts.value.medium,
    lowCount: tabCounts.value.low,
    wordCount: paragraphs.value.reduce((sum, paragraph) => sum + paragraph.text.replace(/\s+/g, '').length, 0),
  }
})

onMounted(loadWorkspace)

watch(activeRiskItem, (item) => {
  if (!item || effectiveLevel(item) === 'normal') return
  void ensureAdvice(item)
})

async function loadWorkspace() {
  loading.value = true
  errorMessage.value = ''
  try {
    const workspace = await getRewriteWorkspace(props.runId)
    const [blocksResult, sectionResult] = await Promise.allSettled([
      getRunBlocks(props.runId),
      getRunSections(props.runId),
    ])

    const blocks = blocksResult.status === 'fulfilled' ? blocksResult.value.blocks : []
    const runSections = sectionResult.status === 'fulfilled' ? sectionResult.value : []
    applyWorkspace(workspace, blocks, runSections)
  } catch (error) {
    console.error(error)
    errorMessage.value = '在线改写数据加载失败，请先确认该论文已经完成分析。'
  } finally {
    loading.value = false
  }
}

function applyWorkspace(workspace: RewriteWorkspaceResponse, blocks: DocumentBlock[], runSections: RunSectionItem[]) {
  workspaceTitle.value = workspace.title || '论文在线改写'
  filename.value = workspace.filename || 'paper.docx'
  sourceFormat.value = workspace.sourceFormat || 'docx'
  workspaceMode.value = workspace.mode || 'estimate'
  documentId.value = workspace.documentId || ''
  warnings.value = normalizeWarnings(workspace.warnings || [], workspace.sourceFormat)
  baseMetrics.value = {
    ...workspace.metrics,
    duplicatePercent: inferDuplicatePercent(blocks, runSections),
    wordCount: 0,
  }

  const normalizedRisks = normalizeRiskItems(workspace.riskItems)
  const normalizedParagraphs = buildParagraphs(blocks, runSections, normalizedRisks)
  const paragraphRiskMap = bindRisksToParagraphs(normalizedParagraphs, normalizedRisks)

  paragraphs.value = normalizedParagraphs.map((paragraph) => ({
    ...paragraph,
    riskId: paragraphRiskMap.get(paragraph.paragraphId),
  }))
  riskItems.value = normalizedRisks.map((item) => {
    const paragraph = paragraphs.value.find((entry) => entry.riskId === item.riskId)
    return {
      ...item,
      blockId: paragraph?.blockId || item.blockId,
      sectionId: paragraph?.sectionId || item.sectionId,
      sectionTitle: paragraph?.sectionTitle || item.sectionTitle,
      currentText: paragraph?.text || item.currentText || item.originalText,
    }
  })
  sections.value = buildSections(workspace.sections, paragraphs.value, riskItems.value)

  const firstPending = orderedRiskItems.value.find((item) => item.status === 'pending') || orderedRiskItems.value[0]
  if (firstPending) selectRisk(firstPending.riskId)
  else if (paragraphs.value[0]) {
    activeParagraphId.value = paragraphs.value[0].paragraphId
    activeSectionId.value = paragraphs.value[0].sectionId
  }
}

function normalizeRiskItems(items: RewriteWorkspaceRiskItem[]): RewriteRiskItem[] {
  return items
    .filter((item) => isReadableText(item.originalText || item.currentText))
    .map((item, index) => ({
      ...item,
      riskId: item.riskId || `risk-${index}`,
      blockId: item.blockId || '',
      sectionId: item.sectionId || 'sec_fallback',
      displayOrder: item.displayOrder ?? index,
      originalText: cleanText(item.originalText || item.currentText),
      currentText: cleanText(item.currentText || item.originalText),
      rewriteHint: cleanText(item.rewriteHint || makeRewriteHint(item.originalText || item.currentText)),
      diagnosis: cleanText(item.diagnosis || ''),
      principle: cleanText(item.principle || ''),
      riskLevel: normalizeRiskLevel(item.riskLevel, item.aigcScore),
      status: item.status || 'pending',
      highlights: item.highlights || [],
    }))
}

function buildParagraphs(
  blocks: DocumentBlock[],
  runSections: RunSectionItem[],
  normalizedRisks: RewriteRiskItem[]
): RewriteParagraph[] {
  const readableBlocks = blocks.filter((block) => isReadableText(block.text || block.effectiveText || ''))
  if (readableBlocks.length) {
    let currentSectionId = 'sec_intro'
    let currentSectionTitle = '摘要'
    return readableBlocks.map((block, index) => {
      const text = cleanText(block.effectiveText || block.text)
      if (block.type === 'title' || block.type === 'heading') {
        currentSectionTitle = text
        currentSectionId = sectionIdFromTitle(text)
      }
      const sectionTitle = block.sectionTitle || currentSectionTitle
      const sectionId = block.sectionTitle ? sectionIdFromTitle(block.sectionTitle) : currentSectionId
      return {
        paragraphId: block.blockId || `p_${index}`,
        blockId: block.blockId || `block_${index}`,
        sectionId,
        sectionTitle,
        type: block.type || 'paragraph',
        text,
        html: block.html,
        displayOrder: block.displayOrder ?? index,
        charCount: block.charCount || text.length,
        sourceMap: block.sourceMap,
      }
    })
  }

  if (runSections.length) {
    return runSections
      .filter((section) => isReadableText(section.content))
      .map((section, index) => ({
        paragraphId: `section_${section.section_index}_${index}`,
        blockId: `section_${section.section_index}_${index}`,
        sectionId: sectionIdFromTitle(section.section_title || `段落 ${index + 1}`, index),
        sectionTitle: section.section_title || fallbackSectionTitle(index),
        type: section.section_type === 'heading' ? 'heading' : 'paragraph',
        text: cleanText(section.content),
        displayOrder: index,
        charCount: section.char_count || section.content.length,
      }))
  }

  return normalizedRisks.map((item, index) => ({
    paragraphId: item.blockId || `risk_paragraph_${index}`,
    blockId: item.blockId || `risk_block_${index}`,
    sectionId: item.sectionId || sectionIdFromTitle(item.sectionTitle || fallbackSectionTitle(index), index),
    sectionTitle: item.sectionTitle || fallbackSectionTitle(index),
    type: index === 0 ? 'heading' : 'paragraph',
    text: item.currentText || item.originalText,
    displayOrder: index,
    charCount: (item.currentText || item.originalText).length,
  }))
}

function bindRisksToParagraphs(paragraphList: RewriteParagraph[], itemList: RewriteRiskItem[]) {
  const map = new Map<string, string>()
  const used = new Set<string>()
  for (const item of itemList) {
    let paragraph = paragraphList.find((entry) => entry.blockId === item.blockId && !used.has(entry.paragraphId))
    if (!paragraph) {
      const target = item.currentText || item.originalText
      paragraph = paragraphList.find((entry) => entry.text.includes(target.slice(0, Math.min(32, target.length))) && !used.has(entry.paragraphId))
    }
    if (!paragraph) {
      paragraph = paragraphList.find((entry) => entry.sectionId === item.sectionId && !used.has(entry.paragraphId))
    }
    if (paragraph) {
      map.set(paragraph.paragraphId, item.riskId)
      used.add(paragraph.paragraphId)
    }
  }
  return map
}

function buildSections(
  workspaceSections: RewriteWorkspaceSectionNode[],
  paragraphList: RewriteParagraph[],
  itemList: RewriteRiskItem[]
): RewriteSection[] {
  const sectionMap = new Map<string, RewriteSection>()

  for (const section of workspaceSections) {
    const title = cleanTitle(section.title)
    if (!title || isGenericTitle(title)) continue
    const stableId = sectionIdFromTitle(title)
    if (sectionMap.has(stableId)) continue
    sectionMap.set(stableId, {
      ...section,
      sectionId: stableId,
      title,
      level: inferLevel(title),
      paragraphIds: [],
      riskCounts: { high: 0, medium: 0, low: 0, normal: 0 },
      riskLevel: 'normal',
    })
  }

  for (const paragraph of paragraphList) {
    if (!sectionMap.has(paragraph.sectionId)) {
      sectionMap.set(paragraph.sectionId, {
        sectionId: paragraph.sectionId,
        sectionIndex: sectionMap.size,
        paragraphIndex: null,
        title: cleanTitle(paragraph.sectionTitle) || fallbackSectionTitle(sectionMap.size),
        level: inferLevel(paragraph.sectionTitle),
        itemIds: [],
        itemCount: 0,
        paragraphIds: [],
        riskCounts: { high: 0, medium: 0, low: 0, normal: 0 },
        riskLevel: 'normal',
      })
    }
    sectionMap.get(paragraph.sectionId)?.paragraphIds.push(paragraph.paragraphId)
  }

  if (sectionMap.size <= 1 && paragraphList.length > 4) {
    return buildFallbackSections(paragraphList, itemList)
  }

  for (const item of itemList) {
    const section = sectionMap.get(item.sectionId)
    if (!section) continue
    const level = effectiveLevel(item)
    section.riskCounts[level] += 1
    section.itemIds.push(item.riskId)
    section.itemCount = section.itemIds.length
    section.riskLevel = worseRisk(section.riskLevel, level)
  }

  const result = [...sectionMap.values()].sort((a, b) => a.sectionIndex - b.sectionIndex)
  if (result.length > 80) {
    return buildReadableOutlineFromHeadings(paragraphList, itemList)
  }
  return result
}

function buildReadableOutlineFromHeadings(paragraphList: RewriteParagraph[], itemList: RewriteRiskItem[]): RewriteSection[] {
  const headingParagraphs = paragraphList.filter((paragraph) =>
    (paragraph.type === 'heading' || paragraph.type === 'title') &&
    !isGenericTitle(paragraph.text) &&
    paragraph.text.length <= 80
  )
  if (headingParagraphs.length < 2 || headingParagraphs.length > 80) {
    return buildFallbackSections(paragraphList, itemList)
  }

  const result: RewriteSection[] = []
  for (const heading of headingParagraphs) {
    const sectionId = sectionIdFromTitle(heading.text)
    if (result.some((section) => section.sectionId === sectionId)) continue
    result.push({
      sectionId,
      sectionIndex: result.length,
      paragraphIndex: null,
      title: heading.text,
      level: inferLevel(heading.text),
      itemIds: [],
      itemCount: 0,
      paragraphIds: [],
      riskCounts: { high: 0, medium: 0, low: 0, normal: 0 },
      riskLevel: 'normal',
    })
  }

  if (!result.length) return buildFallbackSections(paragraphList, itemList)

  let currentSection = result[0]
  for (const paragraph of paragraphList) {
    const matched = result.find((section) => section.title === paragraph.text)
    if (matched) currentSection = matched
    paragraph.sectionId = currentSection.sectionId
    paragraph.sectionTitle = currentSection.title
    currentSection.paragraphIds.push(paragraph.paragraphId)
  }

  for (const item of itemList) {
    const paragraph = paragraphList.find((entry) => entry.riskId === item.riskId)
    const section = paragraph ? result.find((entry) => entry.sectionId === paragraph.sectionId) : null
    if (!section) continue
    item.sectionId = section.sectionId
    item.sectionTitle = section.title
    const level = effectiveLevel(item)
    section.riskCounts[level] += 1
    section.itemIds.push(item.riskId)
    section.itemCount = section.itemIds.length
    section.riskLevel = worseRisk(section.riskLevel, level)
  }

  return result
}

function buildFallbackSections(paragraphList: RewriteParagraph[], itemList: RewriteRiskItem[]): RewriteSection[] {
  const titles = ['摘要', '第1章 绪论', '1.1 研究背景', '1.2 研究意义', '1.3 国内外研究现状', '第2章 系统分析', '2.1 需求分析', '2.2 可行性分析', '2.3 业务流程分析', '第3章 系统设计', '第4章 系统实现', '第5章 总结与展望']
  const groupSize = Math.max(1, Math.ceil(paragraphList.length / titles.length))
  return titles.map((title, index) => {
    const assigned = paragraphList.slice(index * groupSize, (index + 1) * groupSize)
    for (const paragraph of assigned) {
      paragraph.sectionId = sectionIdFromTitle(title, index)
      paragraph.sectionTitle = title
    }
    const sectionItems = itemList.filter((item) => assigned.some((paragraph) => paragraph.riskId === item.riskId))
    const counts = countRiskLevels(sectionItems)
    return {
      sectionId: sectionIdFromTitle(title, index),
      sectionIndex: index,
      paragraphIndex: null,
      title,
      level: inferLevel(title),
      itemIds: sectionItems.map((item) => item.riskId),
      itemCount: sectionItems.length,
      paragraphIds: assigned.map((paragraph) => paragraph.paragraphId),
      riskCounts: counts,
      riskLevel: highestFromCounts(counts),
    }
  }).filter((section) => section.paragraphIds.length || section.itemCount)
}

function selectRisk(riskId: string) {
  const item = riskById.value[riskId]
  if (!item) return
  activeRiskId.value = riskId
  activeTab.value = effectiveLevel(item)
  const paragraph = paragraphs.value.find((entry) => entry.riskId === riskId || entry.blockId === item.blockId)
  if (paragraph) {
    activeParagraphId.value = paragraph.paragraphId
    activeSectionId.value = paragraph.sectionId
  }
}

function selectParagraph(paragraphId: string) {
  const paragraph = paragraphs.value.find((entry) => entry.paragraphId === paragraphId)
  if (!paragraph) return
  activeParagraphId.value = paragraphId
  activeSectionId.value = paragraph.sectionId
  if (paragraph.riskId) selectRisk(paragraph.riskId)
}

function selectSection(sectionId: string) {
  const section = sections.value.find((entry) => entry.sectionId === sectionId)
  if (!section) return
  activeSectionId.value = sectionId
  documentCanvasRef.value?.scrollToSection(section.title)
  const paragraph = paragraphs.value.find((entry) => section.paragraphIds.includes(entry.paragraphId))
  if (paragraph) selectParagraph(paragraph.paragraphId)
}

function changeTab(level: RiskLevel) {
  activeTab.value = level
  const first = visibleRiskItems.value[0] || orderedRiskItems.value.find((item) => effectiveLevel(item) === level)
  if (first) selectRisk(first.riskId)
}

function selectRelative(direction: -1 | 1) {
  const next = visibleRiskItems.value[activeIndex.value + direction]
  if (next) selectRisk(next.riskId)
}

async function ensureAdvice(item: RewriteRiskItem) {
  const cached = adviceCache.value[item.riskId]
  if (cached) return cached

  const shouldShowLoading = activeRiskId.value === item.riskId
  if (shouldShowLoading) adviceLoading.value = true
  try {
    const advice = await getRewriteAdvice(props.runId, adviceTargetIndex(item))
    adviceCache.value = {
      ...adviceCache.value,
      [item.riskId]: advice,
    }
    return advice
  } finally {
    if (shouldShowLoading) adviceLoading.value = false
  }
}

function adviceTargetIndex(item: RewriteRiskItem) {
  if (workspaceMode.value === 'report') {
    return item.paragraphIndex ?? item.displayOrder ?? item.sectionIndex
  }
  return item.sectionIndex
}

function resolveRewriteText(item: RewriteRiskItem, advice?: RewriteAdviceResponse | null) {
  const rewrittenParagraph = advice?.rewritten_paragraph?.trim()
  if (rewrittenParagraph) return cleanText(rewrittenParagraph)

  const rebuilt = advice?.sentences
    ?.map((sentence) => sentence.rewritten?.trim())
    .filter((sentence): sentence is string => Boolean(sentence))
    .join(' ')
  if (rebuilt) return cleanText(rebuilt)

  return cleanText(item.rewriteHint || item.currentText || item.originalText)
}

async function applyActive() {
  const item = activeRiskItem.value
  if (!item || item.status !== 'pending') return
  const paragraph = paragraphs.value.find((entry) => entry.riskId === item.riskId)
  if (!paragraph) return
  const advice = await ensureAdvice(item)
  const nextText = resolveRewriteText(item, advice)
  const entry: RewriteHistoryEntry = {
    riskId: item.riskId,
    paragraphId: paragraph.paragraphId,
    beforeText: paragraph.text,
    afterText: nextText,
    beforeStatus: item.status,
    afterStatus: 'applied',
  }
  applyHistoryEntry(entry)
  history.value.push(entry)
  redoStack.value = []

  try {
    await createPatch(props.runId, {
      block_id: paragraph.blockId,
      old_text: item.currentText || item.originalText,
      new_text: nextText,
      source_map: paragraph.sourceMap || item.sourceMap,
    })
  } catch (error) {
    console.warn(error)
    ElMessage.warning('页面已替换，后端格式补丁稍后可重试保存。')
  }
}

function ignoreActive() {
  const item = activeRiskItem.value
  if (!item || item.status !== 'pending') return
  const paragraph = paragraphs.value.find((entry) => entry.riskId === item.riskId)
  const entry: RewriteHistoryEntry = {
    riskId: item.riskId,
    paragraphId: paragraph?.paragraphId || '',
    beforeText: paragraph?.text || item.currentText,
    afterText: paragraph?.text || item.currentText,
    beforeStatus: item.status,
    afterStatus: 'ignored',
  }
  applyHistoryEntry(entry)
  history.value.push(entry)
  redoStack.value = []
}

function undo() {
  const entry = history.value.pop()
  if (!entry) return
  reverseHistoryEntry(entry)
  redoStack.value.push(entry)
}

function redo() {
  const entry = redoStack.value.pop()
  if (!entry) return
  applyHistoryEntry(entry)
  history.value.push(entry)
}

function rewriteAll() {
  void rewriteAllAsync()
}

async function rewriteAllAsync() {
  for (const item of orderedRiskItems.value.filter((risk) => risk.status === 'pending')) {
    activeRiskId.value = item.riskId
    const paragraph = paragraphs.value.find((entry) => entry.riskId === item.riskId)
    if (!paragraph) continue
    const advice = await ensureAdvice(item)
    const entry: RewriteHistoryEntry = {
      riskId: item.riskId,
      paragraphId: paragraph.paragraphId,
      beforeText: paragraph.text,
      afterText: resolveRewriteText(item, advice),
      beforeStatus: item.status,
      afterStatus: 'applied',
    }
    applyHistoryEntry(entry)
    history.value.push(entry)
  }
  redoStack.value = []
  ElMessage.success('已按建议批量替换页面正文')
}

function save() {
  ElMessage.success('当前改写状态已保存在页面中，导出时会带上替换内容。')
}

function applyHistoryEntry(entry: RewriteHistoryEntry) {
  const paragraph = paragraphs.value.find((item) => item.paragraphId === entry.paragraphId)
  if (paragraph) paragraph.text = entry.afterText
  const item = riskItems.value.find((risk) => risk.riskId === entry.riskId)
  if (item) {
    item.status = entry.afterStatus
    item.currentText = entry.afterText
  }
}

function reverseHistoryEntry(entry: RewriteHistoryEntry) {
  const paragraph = paragraphs.value.find((item) => item.paragraphId === entry.paragraphId)
  if (paragraph) paragraph.text = entry.beforeText
  const item = riskItems.value.find((risk) => risk.riskId === entry.riskId)
  if (item) {
    item.status = entry.beforeStatus
    item.currentText = entry.beforeText
  }
}

async function exportDocument() {
  exportLoading.value = true
  try {
    const sectionsPayload = paragraphs.value.map((paragraph, index) => ({
      section_index: index,
      content: paragraph.text,
      risk_level: paragraph.riskId ? riskById.value[paragraph.riskId]?.riskLevel : 'normal',
    }))
    console.log('[Export] sections count:', sectionsPayload.length)
    const { blob } = await exportRun(props.runId, sectionsPayload, 'docx')
    console.log('[Export] blob size:', blob.size, 'type:', blob.type)
    if (!blob.size) {
      ElMessage.warning('导出文件为空，请稍后重试')
      return
    }
    downloadBlob(blob, `${stripExtension(filename.value)}-PataFix改写稿.docx`)
  } catch (error) {
    console.error('[Export] error:', error)
    ElMessage.error(error instanceof Error ? error.message : '导出失败')
  } finally {
    exportLoading.value = false
  }
}

function goReport() {
  router.push(`/app/report/${props.runId}`)
}

function openPrintReport() {
  const url = router.resolve({
    name: 'report-print',
    params: { runId: props.runId },
  }).href
  window.open(url, '_blank')
}

function effectiveLevel(item: RewriteRiskItem): RiskLevel {
  if (item.status === 'applied' || item.status === 'ignored') return 'normal'
  return item.riskLevel
}

function countRiskLevels(items: RewriteRiskItem[]) {
  const counts: Record<RiskLevel, number> = { high: 0, medium: 0, low: 0, normal: 0 }
  for (const item of items) counts[effectiveLevel(item)] += 1
  return counts
}

function highestFromCounts(counts: Record<RiskLevel, number>): RiskLevel {
  if (counts.high) return 'high'
  if (counts.medium) return 'medium'
  if (counts.low) return 'low'
  return 'normal'
}

function worseRisk(left: RiskLevel, right: RiskLevel): RiskLevel {
  const order: Record<RiskLevel, number> = { normal: 0, low: 1, medium: 2, high: 3 }
  return order[right] > order[left] ? right : left
}

function inferDuplicatePercent(blocks: DocumentBlock[], runSections: RunSectionItem[]) {
  const values = [
    ...blocks.map((block) => block.reportRisk?.similarity).filter((value): value is number => typeof value === 'number'),
    ...runSections.map((section) => section.dup_score).filter((value): value is number => typeof value === 'number'),
  ]
  if (!values.length) return 0
  return values.reduce((sum, value) => sum + value, 0) / values.length
}

function normalizeRiskLevel(level: string, score: number): RiskLevel {
  if (level === 'high' || score >= 70) return 'high'
  if (level === 'medium' || score >= 60) return 'medium'
  if (level === 'low' || score >= 30) return 'low'
  return 'normal'
}

function inferLevel(title = '') {
  if (/^\d+\.\d+\.\d+/.test(title)) return 3
  if (/^\d+\.\d+/.test(title)) return 2
  if (/^第?\d+章/.test(title) || /^第[一二三四五六七八九十]+章/.test(title)) return 1
  return title === '摘要' ? 1 : 1
}

function fallbackSectionTitle(index: number) {
  const titles = ['摘要', '第1章 绪论', '1.1 研究背景', '1.2 研究意义', '第2章 系统分析', '第3章 系统设计', '第4章 系统实现', '第5章 总结与展望']
  return titles[index] || `段落 ${index + 1}`
}

function sectionIdFromTitle(title: string, index = 0) {
  const key = title.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 36)
  return key ? `sec_${key}` : `sec_${index}_section`
}

function isGenericTitle(title: string) {
  return /^正文\s*\d*$/.test(title) || /^正文段落/.test(title) || /^段落\s*\d+$/.test(title)
}

function cleanTitle(title = '') {
  const clean = cleanText(title)
  return isReadableText(clean) ? clean : ''
}

function cleanText(text = '') {
  return text.replace(/\u0000/g, '').replace(/\s+/g, ' ').trim()
}

function isReadableText(text = '') {
  const clean = cleanText(text)
  if (clean.length < 2) return false
  if (/PK\u0003\u0004|word\/document\.xml|Content_Types|w:document|xml version/i.test(clean)) return false
  const controlChars = clean.match(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g)?.length || 0
  return controlChars / Math.max(1, clean.length) < 0.02
}

function makeRewriteHint(text = '') {
  return cleanText(text)
}

function normalizeWarnings(rawWarnings: string[], format?: string | null) {
  const result = rawWarnings.filter(Boolean).map(cleanText)
  if (format === 'pdf') {
    result.push('PDF 当前以固定版式预览和文本映射为主，导出可编辑稿建议转换为 docx。')
  }
  if (format === 'doc') {
    result.push('doc 文件会优先走服务端转换链路，页面不会直接读取原始二进制内容。')
  }
  return [...new Set(result)]
}

function emptyMetrics(): RewriteMetricsState {
  return {
    currentAigcPercent: 0,
    estimatedOptimizedPercent: 0,
    rewrittenCount: 0,
    ignoredCount: 0,
    totalRiskCount: 0,
    highCount: 0,
    mediumCount: 0,
    lowCount: 0,
    duplicatePercent: 0,
    wordCount: 0,
  }
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value || 0))
}

function stripExtension(name: string) {
  return name.replace(/\.[^.]+$/, '') || 'paper'
}

function downloadBlob(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.style.display = 'none'
  link.href = url
  link.download = name
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}
</script>

<style scoped>
.rewrite-workspace-page {
  min-height: 100vh;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f7f8f4;
  color: #111827;
  overflow: hidden;
}

.state-card {
  margin: 32px auto;
  width: min(720px, calc(100% - 48px));
  padding: 22px 24px;
  border-radius: 16px;
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #374151;
  font-size: 15px;
  font-weight: 750;
  box-shadow: 0 18px 34px rgba(15, 23, 42, 0.06);
}

.state-card.error {
  border-color: rgba(239, 68, 68, 0.2);
  background: #fff7f7;
  color: #b91c1c;
}

@media (max-width: 1020px) {
  .rewrite-workspace-page {
    height: auto;
    overflow: auto;
  }
}
</style>
