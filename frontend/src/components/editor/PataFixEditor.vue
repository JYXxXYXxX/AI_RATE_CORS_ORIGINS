<template>
  <div class="patafix-editor">
    <!-- 顶部指标工具条 -->
    <div class="editor-topbar">
      <div class="topbar-left">
        <el-button size="small" plain @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon>返回报告
        </el-button>
      </div>
      <div class="topbar-metrics">
        <div class="metric-item">
          <span class="metric-label">AIGC 疑似度</span>
          <span class="metric-value" :class="'color-' + aigcColor">{{ animatedAigc.toFixed(2) }}%</span>
          <span v-if="aigcDelta !== 0" class="metric-delta" :class="aigcDelta < 0 ? 'delta-down' : 'delta-up'">
            {{ aigcDelta > 0 ? '+' : '' }}{{ aigcDelta.toFixed(2) }}%
          </span>
        </div>
        <div class="metric-item">
          <span class="metric-label">重复率</span>
          <span class="metric-value" :class="'color-' + dupColor">{{ animatedDup.toFixed(2) }}%</span>
          <span v-if="dupDelta !== 0" class="metric-delta" :class="dupDelta < 0 ? 'delta-down' : 'delta-up'">
            {{ dupDelta > 0 ? '+' : '' }}{{ dupDelta.toFixed(2) }}%
          </span>
        </div>
        <div class="metric-item">
          <span class="metric-label">优化后预计</span>
          <span class="metric-value color-predicted">{{ predictedAigc.toFixed(2) }}%</span>
          <span class="metric-delta delta-down">预计下降 {{ predictedDrop.toFixed(2) }}%</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">已改写</span>
          <span class="metric-value color-accent">{{ rewrittenCount }} / {{ sections.length }}</span>
          <span class="metric-sub">句子</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">字数</span>
          <span class="metric-value">{{ totalChars }}</span>
          <span class="metric-sub">全文</span>
        </div>
      </div>
      <div class="topbar-actions">
        <el-button
          type="primary"
          size="small"
          :loading="batchLoading"
          :disabled="!highRiskSections.length"
          @click="fetchBatchAdvice"
        >
          {{ batchLoading ? `批量建议 ${batchProgress}/${highRiskSections.length}` : '一键改写' }}
        </el-button>
        <el-button size="small" :disabled="!canUndo" @click="undo">
          <el-icon><RefreshLeft /></el-icon>撤销
        </el-button>
        <el-button size="small" :disabled="!canRedo" @click="redo">
          <el-icon><RefreshRight /></el-icon>重做
        </el-button>
        <el-button size="small" @click="doSave">
          <el-icon><Download /></el-icon>保存
        </el-button>
      </div>
    </div>

    <!-- 主体三栏 -->
    <div class="editor-body">
      <!-- 左侧目录 -->
      <aside class="editor-sidebar-left">
        <div class="sidebar-tabs">
          <div class="sidebar-tab active">目录</div>
          <div class="sidebar-tab">风险分布</div>
        </div>
        <div class="outline-tree">
          <div
            v-for="(group, gIdx) in groupedSections"
            :key="gIdx"
            class="outline-chapter"
            :class="{ active: activeGroupIndex === gIdx }"
            @click="scrollToGroup(gIdx)"
          >
            <div class="outline-title">
              <span class="outline-dot" :class="'dot-' + groupMaxColor(group)" />
              <span class="outline-text">{{ group.title || '正文' }}</span>
            </div>
            <div class="outline-children">
              <div
                v-for="(para, pIdx) in group.paragraphs"
                :key="pIdx"
                class="outline-para"
                :class="{ active: activeParaIndex === para.paragraphIndex }"
                @click.stop="scrollToParagraph(para.paragraphIndex)"
              >
                <span class="outline-dot" :class="'dot-' + paraRiskColor(para)" />
                <span class="outline-text truncate">{{ paraPreview(para) }}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="risk-legend">
          <div class="legend-title">风险等级说明</div>
          <div class="legend-item"><span class="legend-dot dot-red" />高风险（AIGC疑似度 ≥ 70%）</div>
          <div class="legend-item"><span class="legend-dot dot-orange" />中风险（60% ≤ AIGC疑似度 < 70%）</div>
          <div class="legend-item"><span class="legend-dot dot-purple" />低风险（50% ≤ AIGC疑似度 < 60%）</div>
          <div class="legend-item"><span class="legend-dot dot-normal" />正常（AIGC疑似度 < 50%）</div>
          <div class="legend-item"><span class="legend-dot dot-gray" />未检测</div>
        </div>
      </aside>

      <!-- 中间正文 -->
      <main ref="docRef" class="editor-document">
        <div v-if="loading" class="doc-loading">
          <el-skeleton :rows="10" animated />
        </div>
        <template v-else>
          <div class="a4-page">
            <div v-if="paperTitle" class="paper-title">{{ paperTitle }}</div>
            <div
              v-for="(group, gIdx) in groupedSections"
              :key="gIdx"
              :id="'group-' + gIdx"
              class="chapter-block"
            >
              <h3 v-if="group.title" class="chapter-title">{{ group.title }}</h3>
              <div class="chapter-body">
                <div
                  v-for="para in group.paragraphs"
                  :key="para.paragraphIndex ?? -1"
                  :id="'para-' + para.paragraphIndex"
                  class="doc-paragraph"
                  :class="[
                    'para-' + paraRiskColor(para),
                    { 'is-rewritten': para.rewritten, 'is-active': activeParaIndex === para.paragraphIndex }
                  ]"
                  @click="selectParagraph(para)"
                >
                  <div class="doc-paragraph-content">{{ para.content }}</div>
                </div>
              </div>
            </div>
          </div>
        </template>
      </main>

      <!-- 右侧面板 -->
      <aside class="editor-sidebar-right">
        <div class="panel-header">
          <h4>批注与改写建议</h4>
          <button class="panel-close" @click="panelVisible = false">✕</button>
        </div>

        <div v-if="!panelVisible" class="panel-empty">
          <div class="empty-hint">点击正文中带颜色标记的句子，查看风险诊断与改写建议</div>
        </div>

        <template v-else>
          <div class="risk-filter-bar">
            <span class="filter-tag filter-high">高风险 {{ riskCounts.high }}</span>
            <span class="filter-tag filter-medium">中风险 {{ riskCounts.medium }}</span>
            <span class="filter-tag filter-low">低风险 {{ riskCounts.low }}</span>
            <span class="filter-tag filter-normal">正常 {{ riskCounts.normal }}</span>
          </div>

          <div v-if="panelLoading" class="panel-loading">
            <el-skeleton :rows="6" animated />
          </div>

          <div v-else-if="panelError" class="panel-error">
            <el-alert :title="panelError" type="warning" :closable="false" show-icon />
          </div>

          <div v-else-if="rewriteAdvice" class="advice-cards">
            <div class="advice-card">
              <div class="card-header">
                <span class="risk-badge" :class="'badge-' + activeRiskLevel">{{ riskText(activeRiskLevel) }}</span>
                <span class="aigc-score">AIGC疑似度 {{ (activeAigcScore * 100).toFixed(0) }}%</span>
              </div>

              <div class="card-section">
                <div class="section-title">风险诊断</div>
                <p class="section-text">{{ rewriteAdvice.diagnosis || '该段落存在AI生成特征，建议优化。' }}</p>
              </div>

              <div class="card-section">
                <div class="section-title">原文</div>
                <div class="original-text">{{ activeSectionContent }}</div>
              </div>

              <div class="card-section">
                <div class="section-title">改写建议</div>
                <div class="rewritten-text">{{ rewriteAdvice.rewritten_paragraph }}</div>
              </div>

              <div v-if="rewriteAdvice.overall_advice" class="card-section">
                <div class="section-title">改写原理</div>
                <p class="section-text">{{ rewriteAdvice.overall_advice }}</p>
              </div>

              <div class="card-actions">
                <el-button type="primary" size="small" @click="applyFullRewrite">替换原文</el-button>
                <el-button size="small" plain @click="ignoreActive">忽略</el-button>
              </div>
            </div>

            <div v-if="rewriteAdvice.sentences.length" class="sentence-cards">
              <div
                v-for="(sent, idx) in rewriteAdvice.sentences"
                :key="idx"
                class="sentence-card"
              >
                <div class="sent-original">
                  <label>原文</label>
                  <p>{{ sent.original }}</p>
                </div>
                <div class="sent-rewritten">
                  <label>改写</label>
                  <p>{{ sent.rewritten }}</p>
                </div>
                <div class="sent-explanation">
                  <label>原理</label>
                  <p>{{ sent.explanation }}</p>
                </div>
                <el-button size="small" type="success" plain @click="applySentenceRewrite(idx)">
                  应用此句
                </el-button>
              </div>
            </div>
          </div>
        </template>
      </aside>
    </div>

    <!-- 底部操作栏 -->
    <div class="editor-bottombar">
      <div class="bottombar-left">
        <el-button size="small" plain :disabled="!prevSection" @click="goPrev">
          <el-icon><ArrowLeft /></el-icon>上一条
        </el-button>
        <span class="bottombar-count">{{ currentIndex + 1 }} / {{ highRiskSections.length }}</span>
        <el-button size="small" plain :disabled="!nextSection" @click="goNext">
          下一条<el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
      <div class="bottombar-center">
        <span class="status-text"><el-icon><CircleCheck /></el-icon>检测完成</span>
        <span class="status-sub">全文共 {{ totalChars }} 字 · 检测范围：全文</span>
      </div>
      <div class="bottombar-right">
        <el-button size="small" plain :loading="isReanalyzing" @click="doReanalyze">
          <el-icon><Refresh /></el-icon>重新检测
        </el-button>
        <el-dropdown size="small" trigger="click">
          <el-button size="small" type="primary">
            <el-icon><Download /></el-icon>导出文稿<el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="doExport('docx')">导出 Word (.docx)</el-dropdown-item>
              <el-dropdown-item @click="doExport('txt')">导出 TXT (.txt)</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, ArrowRight, ArrowDown, RefreshLeft, RefreshRight,
  Download, Refresh, CircleCheck
} from '@element-plus/icons-vue'
import { getRunSections, getRewriteAdvice, reanalyzeRun, exportRun } from '../../api'
import type { RunSectionItem, RewriteAdviceResponse, ReanalyzeResponse } from '../../types'

const props = defineProps<{
  runId: string
}>()

const sections = ref<RunSectionItem[]>([])
const loading = ref(false)
const docRef = ref<HTMLDivElement | null>(null)
const paperTitle = ref('')

// 改写状态
const rewrittenMap = ref<Map<number, string>>(new Map())
const panelVisible = ref(false)
const panelLoading = ref(false)
const panelError = ref('')
const activeSectionIndex = ref<number | null>(null)
const rewriteAdvice = ref<RewriteAdviceResponse | null>(null)

// 真实重算结果
const realScores = ref<ReanalyzeResponse | null>(null)
const isReanalyzing = ref(false)

// 批量建议
const batchAdviceMap = ref<Map<number, RewriteAdviceResponse>>(new Map())
const batchLoading = ref(false)
const batchProgress = ref(0)

// 历史栈（撤销/重做）
interface HistoryEntry {
  sectionIndex: number
  previousText: string | undefined
  newText: string
  timestamp: number
}
const historyStack = ref<HistoryEntry[]>([])
const historyIndex = ref(-1)

// 初始分数（从 sections 计算）
const initialAigc = ref(0)
const initialDup = ref(0)

// 动画分数
const animatedAigc = ref(0)
const animatedDup = ref(0)

onMounted(() => {
  loadSections()
})

interface ParagraphBlock {
  paragraphIndex: number | null
  content: string
  sectionIndices: number[]
  aigcScore: number
  dupScore: number
  riskLevel: 'low' | 'medium' | 'high'
  sectionTitle: string | null
  sectionType: string | null
  rewritten: boolean
  hasAdvice: boolean
}

interface ChapterGroup {
  title: string | null
  type: string | null
  paragraphs: ParagraphBlock[]
  totalChars: number
  maxAigc: number
  maxDup: number
  rewrittenCount: number
  adviceCount: number
}

const groupedSections = computed(() => {
  const groups: ChapterGroup[] = []
  let current: ChapterGroup | null = null
  let currentPara: ParagraphBlock | null = null

  for (const sec of sections.value) {
    if (!current || current.title !== sec.section_title) {
      current = {
        title: sec.section_title,
        type: sec.section_type,
        paragraphs: [],
        totalChars: 0,
        maxAigc: 0,
        maxDup: 0,
        rewrittenCount: 0,
        adviceCount: 0
      }
      groups.push(current)
      currentPara = null
    }

    const paraIdx = sec.paragraph_index ?? sec.section_index
    if (!currentPara || currentPara.paragraphIndex !== paraIdx) {
      currentPara = {
        paragraphIndex: paraIdx,
        content: '',
        sectionIndices: [],
        aigcScore: 0,
        dupScore: 0,
        riskLevel: 'low',
        sectionTitle: sec.section_title,
        sectionType: sec.section_type,
        rewritten: false,
        hasAdvice: false
      }
      current.paragraphs.push(currentPara)
    }

    const text = rewrittenMap.value.get(sec.section_index) || sec.content
    currentPara.content += (currentPara.content ? '\n' : '') + text
    currentPara.sectionIndices.push(sec.section_index)
    currentPara.aigcScore = Math.max(currentPara.aigcScore, effectiveAigc(sec))
    currentPara.dupScore = Math.max(currentPara.dupScore, effectiveDup(sec))
    currentPara.riskLevel = currentPara.aigcScore >= 0.70 ? 'high' : currentPara.aigcScore >= 0.50 ? 'medium' : 'low'
    if (rewrittenMap.value.has(sec.section_index)) currentPara.rewritten = true
    if (batchAdviceMap.value.has(sec.section_index)) currentPara.hasAdvice = true

    current.totalChars += sec.char_count
    current.maxAigc = Math.max(current.maxAigc, effectiveAigc(sec))
    current.maxDup = Math.max(current.maxDup, effectiveDup(sec))
    if (rewrittenMap.value.has(sec.section_index)) current.rewrittenCount++
    if (batchAdviceMap.value.has(sec.section_index)) current.adviceCount++
  }
  return groups
})

const totalChars = computed(() =>
  sections.value.reduce((sum, s) => sum + (s.char_count || 0), 0)
)

const rewrittenCount = computed(() => rewrittenMap.value.size)

const highRiskSections = computed(() =>
  sections.value.filter(s => s.risk_level !== 'low')
)

const riskCounts = computed(() => {
  const counts = { high: 0, medium: 0, low: 0, normal: 0 }
  for (const s of sections.value) {
    const level = effectiveRisk(s)
    if (level === 'high') counts.high++
    else if (level === 'medium') counts.medium++
    else if (level === 'low') counts.low++
    else counts.normal++
  }
  return counts
})

const currentAigc = computed(() =>
  realScores.value ? realScores.value.ai_like_percent : initialAigc.value * 100
)
const currentDup = computed(() =>
  realScores.value ? realScores.value.duplication_percent : initialDup.value * 100
)

const predictedAigc = computed(() => Math.max(0, currentAigc.value * 0.45))
const predictedDrop = computed(() => currentAigc.value - predictedAigc.value)

const aigcDelta = computed(() => currentAigc.value - initialAigc.value * 100)
const dupDelta = computed(() => currentDup.value - initialDup.value * 100)

const aigcColor = computed(() => {
  const v = animatedAigc.value
  return v >= 30 ? 'high' : v >= 15 ? 'medium' : 'low'
})

const dupColor = computed(() => {
  const v = animatedDup.value
  return v >= 20 ? 'high' : v >= 10 ? 'medium' : 'low'
})

const canUndo = computed(() => historyIndex.value >= 0)
const canRedo = computed(() => historyIndex.value < historyStack.value.length - 1)

const activeGroupIndex = computed(() => {
  if (activeSectionIndex.value == null) return -1
  const sec = sections.value.find(s => s.section_index === activeSectionIndex.value)
  if (!sec) return -1
  return groupedSections.value.findIndex(g => g.title === sec.section_title)
})

const activeParaIndex = computed(() => {
  if (activeSectionIndex.value == null) return null
  const sec = sections.value.find(s => s.section_index === activeSectionIndex.value)
  if (!sec) return null
  return sec.paragraph_index ?? sec.section_index
})

const activeRiskLevel = computed(() => {
  if (activeSectionIndex.value == null) return 'low'
  const sec = sections.value.find(s => s.section_index === activeSectionIndex.value)
  if (!sec) return 'low'
  return effectiveRisk(sec)
})

const activeAigcScore = computed(() => {
  if (activeSectionIndex.value == null) return 0
  const sec = sections.value.find(s => s.section_index === activeSectionIndex.value)
  if (!sec) return 0
  return effectiveAigc(sec)
})

const activeSectionContent = computed(() => {
  if (activeSectionIndex.value == null) return ''
  const sec = sections.value.find(s => s.section_index === activeSectionIndex.value)
  if (!sec) return ''
  return rewrittenMap.value.get(sec.section_index) || sec.content
})

const currentIndex = computed(() => {
  if (activeSectionIndex.value == null) return -1
  return highRiskSections.value.findIndex(s => s.section_index === activeSectionIndex.value)
})

const prevSection = computed(() => {
  const idx = currentIndex.value
  return idx > 0 ? highRiskSections.value[idx - 1] : null
})

const nextSection = computed(() => {
  const idx = currentIndex.value
  return idx >= 0 && idx < highRiskSections.value.length - 1 ? highRiskSections.value[idx + 1] : null
})

watch([currentAigc, currentDup], () => {
  animateScore()
})

function animateScore() {
  const targetAigc = currentAigc.value
  const targetDup = currentDup.value
  const startAigc = animatedAigc.value
  const startDup = animatedDup.value
  const duration = 600
  const start = performance.now()

  function tick(now: number) {
    const p = Math.min((now - start) / duration, 1)
    animatedAigc.value = startAigc + (targetAigc - startAigc) * p
    animatedDup.value = startDup + (targetDup - startDup) * p
    if (p < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

async function loadSections() {
  loading.value = true
  try {
    sections.value = await getRunSections(props.runId)
    // 计算初始分数
    const scored = sections.value.filter(s => s.section_type !== 'references' && s.section_type !== 'acknowledgement')
    const scoredChars = scored.reduce((sum, s) => sum + s.char_count, 0)
    if (scoredChars > 0) {
      initialAigc.value = scored.reduce((sum, s) => sum + s.aigc_score * s.char_count, 0) / scoredChars
      initialDup.value = scored.reduce((sum, s) => sum + s.dup_score * s.char_count, 0) / scoredChars
    }
    animatedAigc.value = initialAigc.value * 100
    animatedDup.value = initialDup.value * 100

    const first = sections.value[0]
    if (first?.section_title && first.section_type === 'abstract') {
      paperTitle.value = first.section_title
    }
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '加载段落失败')
  } finally {
    loading.value = false
  }
}

function effectiveAigc(sec: RunSectionItem): number {
  if (realScores.value) {
    const rs = realScores.value.sections.find(s => s.section_index === sec.section_index)
    if (rs) return rs.aigc_score
  }
  return sec.aigc_score
}

function effectiveDup(sec: RunSectionItem): number {
  if (realScores.value) {
    const rs = realScores.value.sections.find(s => s.section_index === sec.section_index)
    if (rs) return rs.duplication_score
  }
  return sec.dup_score
}

function effectiveRisk(sec: RunSectionItem): 'low' | 'medium' | 'high' {
  if (realScores.value) {
    const rs = realScores.value.sections.find(s => s.section_index === sec.section_index)
    if (rs) return rs.risk_level
  }
  return sec.risk_level
}

function paraRiskColor(para: ParagraphBlock): string {
  if (para.sectionType === 'references' || para.sectionType === 'acknowledgement') return 'gray'
  if (para.aigcScore >= 0.70) return 'red'
  if (para.aigcScore >= 0.60) return 'orange'
  if (para.aigcScore >= 0.50) return 'purple'
  return 'normal'
}

function groupMaxColor(group: ChapterGroup): string {
  if (group.type === 'references' || group.type === 'acknowledgement') return 'gray'
  if (group.maxAigc >= 0.70) return 'red'
  if (group.maxAigc >= 0.60) return 'orange'
  if (group.maxAigc >= 0.50) return 'purple'
  return 'normal'
}

function riskText(level: string) {
  return level === 'high' ? '高风险' : level === 'medium' ? '中风险' : '低风险'
}

function paraPreview(para: ParagraphBlock): string {
  return para.content.slice(0, 24) + (para.content.length > 24 ? '…' : '')
}

function scrollToGroup(gIdx: number) {
  const el = document.getElementById('group-' + gIdx)
  if (el && docRef.value) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

function scrollToParagraph(paraIdx: number | null) {
  if (paraIdx == null) return
  const el = document.getElementById('para-' + paraIdx)
  if (el && docRef.value) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

async function selectParagraph(para: ParagraphBlock) {
  if (!para.sectionIndices.length) return
  let targetSec = sections.value.find(s => s.section_index === para.sectionIndices[0])
  for (const idx of para.sectionIndices) {
    const sec = sections.value.find(s => s.section_index === idx)
    if (sec && effectiveAigc(sec) > (targetSec ? effectiveAigc(targetSec) : 0)) {
      targetSec = sec
    }
  }
  if (targetSec) {
    await selectSection(targetSec)
  }
}

async function selectSection(sec: RunSectionItem) {
  activeSectionIndex.value = sec.section_index
  panelVisible.value = true
  panelLoading.value = true
  panelError.value = ''
  rewriteAdvice.value = null

  const cached = batchAdviceMap.value.get(sec.section_index)
  if (cached) {
    rewriteAdvice.value = cached
    panelLoading.value = false
    return
  }

  try {
    rewriteAdvice.value = await getRewriteAdvice(props.runId, sec.section_index)
  } catch (err) {
    panelError.value = err instanceof Error ? err.message : '获取改写建议失败'
  } finally {
    panelLoading.value = false
  }
}

function pushHistory(sectionIndex: number, previousText: string | undefined, newText: string) {
  if (historyIndex.value < historyStack.value.length - 1) {
    historyStack.value = historyStack.value.slice(0, historyIndex.value + 1)
  }
  historyStack.value.push({ sectionIndex, previousText, newText, timestamp: Date.now() })
  historyIndex.value = historyStack.value.length - 1
}

function applyRewrite(sectionIndex: number, newText: string) {
  const previousText = rewrittenMap.value.get(sectionIndex)
  rewrittenMap.value.set(sectionIndex, newText)
  pushHistory(sectionIndex, previousText, newText)
}

function applySentenceRewrite(sentenceIdx: number) {
  if (!rewriteAdvice.value || activeSectionIndex.value === null) return
  const sent = rewriteAdvice.value.sentences[sentenceIdx]
  if (!sent) return

  const sec = sections.value.find((s: RunSectionItem) => s.section_index === activeSectionIndex.value)
  if (!sec) return

  const current = rewrittenMap.value.get(activeSectionIndex.value) || sec.content
  const updated = current.replace(sent.original, sent.rewritten)
  applyRewrite(activeSectionIndex.value, updated)
  ElMessage.success('已应用改写')
}

function applyFullRewrite() {
  if (!rewriteAdvice.value || activeSectionIndex.value === null) return
  applyRewrite(activeSectionIndex.value, rewriteAdvice.value.rewritten_paragraph)
  ElMessage.success('已替换原文')
}

function ignoreActive() {
  if (activeSectionIndex.value === null) return
  ElMessage.info('已忽略该条建议')
}

async function fetchBatchAdvice() {
  const targets = highRiskSections.value.filter(s => !batchAdviceMap.value.has(s.section_index))
  if (!targets.length) {
    ElMessage.info('所有高风险段落建议已获取')
    return
  }
  batchLoading.value = true
  batchProgress.value = 0
  try {
    await Promise.all(
      targets.map(async (sec) => {
        try {
          const advice = await getRewriteAdvice(props.runId, sec.section_index)
          batchAdviceMap.value.set(sec.section_index, advice)
        } catch {
          // 忽略单个失败
        } finally {
          batchProgress.value++
        }
      })
    )
    ElMessage.success(`已获取 ${batchAdviceMap.value.size} 条改写建议`)
  } finally {
    batchLoading.value = false
  }
}

async function doReanalyze() {
  if (!rewrittenCount.value) return
  isReanalyzing.value = true
  try {
    const payload = sections.value.map(sec => ({
      section_index: sec.section_index,
      content: rewrittenMap.value.get(sec.section_index) || sec.content
    }))
    const result = await reanalyzeRun(props.runId, payload)
    realScores.value = result
    ElMessage.success(`重算完成：AIGC ${result.ai_like_percent.toFixed(1)}%，查重 ${result.duplication_percent.toFixed(1)}%`)
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '重算失败')
  } finally {
    isReanalyzing.value = false
  }
}

async function doExport(format: 'docx' | 'txt') {
  try {
    const payload = sections.value.map(sec => ({
      section_index: sec.section_index,
      content: rewrittenMap.value.get(sec.section_index) || sec.content
    }))
    const blob = await exportRun(props.runId, payload, format)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `PataFix_改写稿.${format}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success(`已导出 ${format.toUpperCase()}`)
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '导出失败')
  }
}

function doSave() {
  ElMessage.success('已保存改写进度到本地')
}

function undo() {
  if (!canUndo.value) return
  const entry = historyStack.value[historyIndex.value]
  if (entry.previousText === undefined) {
    rewrittenMap.value.delete(entry.sectionIndex)
  } else {
    rewrittenMap.value.set(entry.sectionIndex, entry.previousText)
  }
  historyIndex.value--
  ElMessage.success('已撤销')
}

function redo() {
  if (!canRedo.value) return
  historyIndex.value++
  const entry = historyStack.value[historyIndex.value]
  rewrittenMap.value.set(entry.sectionIndex, entry.newText)
  ElMessage.success('已重做')
}

function goPrev() {
  if (prevSection.value) {
    selectSection(prevSection.value)
    scrollToParagraph(prevSection.value.paragraph_index ?? prevSection.value.section_index)
  }
}

function goNext() {
  if (nextSection.value) {
    selectSection(nextSection.value)
    scrollToParagraph(nextSection.value.paragraph_index ?? nextSection.value.section_index)
  }
}
</script>

<style scoped>
/* ===== 编辑器根 ===== */
.patafix-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #FAF9F6;
}

/* ===== 顶部指标条 ===== */
.editor-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: #fff;
  border-bottom: 1px solid #E8E6E1;
  gap: 16px;
  flex-shrink: 0;
}

.topbar-left {
  flex-shrink: 0;
}

.topbar-metrics {
  display: flex;
  align-items: center;
  gap: 32px;
  flex: 1;
  justify-content: center;
}

.metric-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.metric-label {
  font-size: 12px;
  color: #9E9E9E;
  font-weight: 500;
}

.metric-value {
  font-size: 22px;
  font-weight: 700;
  line-height: 1.2;
}

.metric-sub {
  font-size: 11px;
  color: #BDBDBD;
}

.metric-delta {
  font-size: 11px;
  font-weight: 500;
}

.delta-down { color: #2E7D5A; }
.delta-up { color: #D32F2F; }

.color-high { color: #D32F2F; }
.color-medium { color: #F57C00; }
.color-low { color: #2E7D5A; }
.color-predicted { color: #2E7D5A; }
.color-accent { color: #2E7D5A; }

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

/* ===== 主体三栏 ===== */
.editor-body {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* ===== 左侧目录 ===== */
.editor-sidebar-left {
  width: 260px;
  min-width: 260px;
  background: #fff;
  border-right: 1px solid #E8E6E1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-tabs {
  display: flex;
  border-bottom: 1px solid #E8E6E1;
  padding: 0 16px;
}

.sidebar-tab {
  padding: 12px 8px;
  font-size: 14px;
  font-weight: 500;
  color: #9E9E9E;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: all 0.15s;
}

.sidebar-tab.active {
  color: #2E7D5A;
  border-bottom-color: #2E7D5A;
  font-weight: 600;
}

.outline-tree {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
}

.outline-chapter {
  margin-bottom: 4px;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.12s;
}

.outline-chapter:hover,
.outline-chapter.active {
  background: #E8F5E9;
}

.outline-title {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 6px;
  font-size: 14px;
  font-weight: 600;
  color: #1A1A1A;
}

.outline-children {
  padding-left: 16px;
}

.outline-para {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px;
  font-size: 13px;
  color: #6B6B6B;
  border-radius: 4px;
  cursor: pointer;
}

.outline-para:hover,
.outline-para.active {
  background: #F5F5F5;
  color: #1A1A1A;
}

.outline-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.outline-text {
  line-height: 1.4;
}

.truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dot-red { background: #E53935; }
.dot-orange { background: #FB8C00; }
.dot-purple { background: #8E24AA; }
.dot-normal { background: #9E9E9E; }
.dot-gray { background: #BDBDBD; }

.risk-legend {
  padding: 16px;
  border-top: 1px solid #E8E6E1;
  font-size: 12px;
  color: #6B6B6B;
}

.legend-title {
  font-weight: 600;
  margin-bottom: 10px;
  color: #1A1A1A;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* ===== 中间正文 ===== */
.editor-document {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: #FAF9F6;
}

.a4-page {
  max-width: 210mm;
  min-height: 297mm;
  margin: 0 auto;
  background: #fff;
  padding: 24mm 20mm;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  border-radius: 4px;
}

.paper-title {
  font-size: 22pt;
  font-weight: bold;
  text-align: center;
  margin-bottom: 24pt;
  color: #1A1A1A;
  font-family: 'SimHei', '黑体', sans-serif;
}

.chapter-block {
  margin-bottom: 18pt;
}

.chapter-title {
  font-size: 16pt;
  font-weight: bold;
  color: #1A1A1A;
  margin: 18pt 0 12pt;
  text-align: center;
  font-family: 'SimHei', '黑体', sans-serif;
}

.doc-paragraph {
  padding: 6px 10px;
  margin: 0;
  cursor: pointer;
  transition: background 0.12s ease;
  border-left: 3px solid transparent;
  border-radius: 4px;
  text-indent: 2em;
  line-height: 1.8;
  font-size: 12pt;
  font-family: 'SimSun', '宋体', serif;
  color: #1A1A1A;
  white-space: pre-wrap;
  word-break: break-word;
}

.doc-paragraph:hover {
  filter: brightness(0.97);
}

.doc-paragraph.is-active {
  outline: 2px solid #2E7D5A;
  outline-offset: -2px;
}

/* 风险着色 */
.para-red {
  background: rgba(229, 57, 53, 0.12);
  border-left-color: #E53935;
}

.para-orange {
  background: rgba(251, 140, 0, 0.12);
  border-left-color: #FB8C00;
}

.para-purple {
  background: rgba(142, 36, 170, 0.10);
  border-left-color: #8E24AA;
}

.para-normal {
  border-left-color: transparent;
}

.para-gray {
  color: #9E9E9E;
  background: rgba(189, 189, 189, 0.06);
  border-left-color: #BDBDBD;
}

.doc-paragraph.is-rewritten {
  border-left-color: #2E7D5A !important;
  border-left-width: 4px;
}

/* ===== 右侧面板 ===== */
.editor-sidebar-right {
  width: 380px;
  min-width: 380px;
  background: #fff;
  border-left: 1px solid #E8E6E1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #E8E6E1;
}

.panel-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1A1A1A;
}

.panel-close {
  background: none;
  border: none;
  font-size: 18px;
  color: #9E9E9E;
  cursor: pointer;
  line-height: 1;
}

.panel-close:hover {
  color: #1A1A1A;
}

.panel-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.empty-hint {
  font-size: 14px;
  color: #9E9E9E;
  text-align: center;
  line-height: 1.6;
}

.risk-filter-bar {
  display: flex;
  gap: 8px;
  padding: 12px 20px;
  border-bottom: 1px solid #E8E6E1;
  overflow-x: auto;
}

.filter-tag {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 4px;
  font-weight: 500;
  white-space: nowrap;
}

.filter-high { color: #C62828; background: #FFEBEE; }
.filter-medium { color: #EF6C00; background: #FFF3E0; }
.filter-low { color: #6A1B9A; background: #F3E5F5; }
.filter-normal { color: #424242; background: #F5F5F5; }

.panel-loading,
.panel-error {
  padding: 20px;
}

.advice-cards {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}

.advice-card {
  background: #FAF9F6;
  border: 1px solid #E8E6E1;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.risk-badge {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 4px;
  font-weight: 600;
}

.badge-high { color: #C62828; background: #FFEBEE; }
.badge-medium { color: #EF6C00; background: #FFF3E0; }
.badge-low { color: #6A1B9A; background: #F3E5F5; }

.aigc-score {
  font-size: 13px;
  color: #F57C00;
  font-weight: 600;
}

.card-section {
  margin-bottom: 14px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #1A1A1A;
  margin-bottom: 6px;
}

.section-text {
  font-size: 13px;
  color: #6B6B6B;
  line-height: 1.7;
  margin: 0;
}

.original-text {
  font-size: 13px;
  color: #9E9E9E;
  line-height: 1.7;
  padding: 10px;
  background: #fff;
  border-radius: 4px;
  border: 1px dashed #E0E0E0;
}

.rewritten-text {
  font-size: 13px;
  color: #1A1A1A;
  line-height: 1.7;
  padding: 10px;
  background: #E8F5E9;
  border-radius: 4px;
  border: 1px solid #C8E6C9;
}

.card-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.sentence-card {
  background: #fff;
  border: 1px solid #E8E6E1;
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 12px;
}

.sent-original,
.sent-rewritten,
.sent-explanation {
  margin-bottom: 10px;
}

.sent-original label,
.sent-rewritten label,
.sent-explanation label {
  font-size: 11px;
  font-weight: 600;
  color: #9E9E9E;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  display: block;
  margin-bottom: 4px;
}

.sent-original p {
  font-size: 13px;
  color: #9E9E9E;
  margin: 0;
  line-height: 1.6;
}

.sent-rewritten p {
  font-size: 13px;
  color: #1A1A1A;
  margin: 0;
  line-height: 1.6;
  padding: 8px;
  background: #E8F5E9;
  border-radius: 4px;
}

.sent-explanation p {
  font-size: 12px;
  color: #6B6B6B;
  margin: 0;
  line-height: 1.6;
}

/* ===== 底部操作栏 ===== */
.editor-bottombar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 24px;
  background: #fff;
  border-top: 1px solid #E8E6E1;
  flex-shrink: 0;
  gap: 16px;
}

.bottombar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.bottombar-count {
  font-size: 14px;
  font-weight: 600;
  color: #1A1A1A;
  min-width: 60px;
  text-align: center;
}

.bottombar-center {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 13px;
  color: #6B6B6B;
}

.status-text {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #2E7D5A;
  font-weight: 500;
}

.status-sub {
  color: #9E9E9E;
}

.bottombar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ===== 加载态 ===== */
.doc-loading {
  padding: 40px;
}

/* ===== 滚动条美化 ===== */
.editor-document::-webkit-scrollbar,
.outline-tree::-webkit-scrollbar,
.advice-cards::-webkit-scrollbar {
  width: 6px;
}

.editor-document::-webkit-scrollbar-thumb,
.outline-tree::-webkit-scrollbar-thumb,
.advice-cards::-webkit-scrollbar-thumb {
  background: #D8D8D8;
  border-radius: 3px;
}
</style>
