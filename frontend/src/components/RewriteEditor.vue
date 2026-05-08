<template>
  <div class="rewrite-editor">
    <!-- 顶部工具栏 -->
    <div class="score-bar">
      <div class="score-group">
        <div class="score-item">
          <span class="score-label">AIGC 总体疑似度</span>
          <span class="score-value" :class="aigcColor">
            {{ animatedAigc.toFixed(2) }}%
          </span>
          <span v-if="aigcDelta !== 0" class="score-delta" :class="aigcDelta < 0 ? 'down' : 'up'">
            {{ aigcDelta > 0 ? '+' : '' }}{{ aigcDelta.toFixed(2) }}%
          </span>
        </div>
        <div class="score-item">
          <span class="score-label">查重率</span>
          <span class="score-value" :class="dupColor">
            {{ animatedDup.toFixed(2) }}%
          </span>
          <span v-if="dupDelta !== 0" class="score-delta" :class="dupDelta < 0 ? 'down' : 'up'">
            {{ dupDelta > 0 ? '+' : '' }}{{ dupDelta.toFixed(2) }}%
          </span>
        </div>
        <div class="score-item">
          <span class="score-label">已改写</span>
          <span class="score-value accent">{{ rewrittenCount }} / {{ sections.length }}</span>
        </div>
      </div>

      <div class="score-actions">
        <el-button
          type="warning"
          size="small"
          :loading="batchLoading"
          :disabled="!highRiskSections.length"
          @click="fetchBatchAdvice"
        >
          {{ batchLoading ? `批量建议 ${batchProgress}/${highRiskSections.length}` : '批量获取建议' }}
        </el-button>
        <el-button
          type="success"
          size="small"
          :disabled="!batchAdviceMap.size"
          @click="applyAllBatch"
        >
          一键应用 ({{ batchAdviceReadyCount }})
        </el-button>
        <el-button
          type="primary"
          size="small"
          :loading="isReanalyzing"
          :disabled="!rewrittenCount"
          @click="doReanalyze"
        >
          {{ isReanalyzing ? '重算中...' : '真实重算分数' }}
        </el-button>
        <el-dropdown size="small" trigger="click" :disabled="!rewrittenCount">
          <el-button size="small" :disabled="!rewrittenCount">
            导出改写稿 <el-icon class="el-icon--right"><arrow-down /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="doExport('docx')">导出 .docx</el-dropdown-item>
              <el-dropdown-item @click="doExport('txt')">导出 .txt</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button size="small" plain :disabled="!canUndo" @click="undo">
          <el-icon><arrow-left /></el-icon> 撤销
        </el-button>
        <el-button size="small" plain :disabled="!canRedo" @click="redo">
          <el-icon><arrow-right /></el-icon> 重做
        </el-button>
        <el-button size="small" plain @click="emit('close')">关闭</el-button>
      </div>
    </div>

    <!-- 主体三栏布局 -->
    <div class="editor-body">
      <!-- 左侧迷你导航条 -->
      <div class="minimap" title="点击跳转到对应段落">
        <div
          v-for="sec in sections"
          :key="sec.section_index"
          class="minimap-segment"
          :class="['minimap-' + aigcColorClass(sec), sec.section_index === activeSectionIndex ? 'active' : '']"
          :style="{ height: Math.max(3, (sec.char_count / totalChars) * 100) + '%' }"
          @click="scrollToSection(sec.section_index)"
        />
      </div>

      <!-- 中间论文正文 -->
      <div ref="docRef" class="document-view">
        <div
          v-for="sec in sections"
          :key="sec.section_index"
          :id="'sec-' + sec.section_index"
          class="doc-section"
          :class="[
            'doc-' + aigcColorClass(sec),
            { 'is-rewritten': rewrittenMap.has(sec.section_index), 'has-advice': batchAdviceMap.has(sec.section_index) }
          ]"
          @click="selectSection(sec)"
        >
          <div v-if="sec.section_title" class="doc-section-title">
            {{ sec.section_title }}
          </div>
          <div class="doc-section-content">{{ displayContent(sec) }}</div>
          <div class="doc-section-meta">
            <span
              v-if="sec.section_type === 'references' || sec.section_type === 'acknowledgement'"
              class="doc-tag doc-tag-gray"
            >灰色 · 不参与检测</span>
            <span v-else-if="effectiveAigc(sec) >= 0.70" class="doc-tag doc-tag-red">
              红色 · AIGC {{ (effectiveAigc(sec) * 100).toFixed(1) }}%
            </span>
            <span v-else-if="effectiveAigc(sec) >= 0.60" class="doc-tag doc-tag-orange">
              橙色 · AIGC {{ (effectiveAigc(sec) * 100).toFixed(1) }}%
            </span>
            <span v-else-if="effectiveAigc(sec) >= 0.50" class="doc-tag doc-tag-purple">
              紫色 · AIGC {{ (effectiveAigc(sec) * 100).toFixed(1) }}%
            </span>
            <span v-else class="doc-tag doc-tag-normal">
              正常 · AIGC {{ (effectiveAigc(sec) * 100).toFixed(1) }}%
            </span>
            <span v-if="effectiveDup(sec) > 0" class="doc-tag doc-tag-dup">
              查重 {{ (effectiveDup(sec) * 100).toFixed(1) }}%
            </span>
            <span v-if="rewrittenMap.has(sec.section_index)" class="doc-tag doc-tag-rewritten">已改写</span>
            <span v-else-if="batchAdviceMap.has(sec.section_index)" class="doc-tag doc-tag-advice">建议就绪</span>
          </div>
        </div>
      </div>

      <!-- 右侧边栏 -->
      <div class="right-sidebar">
        <!-- 颜色图例 -->
        <div class="legend-box">
          <h4>片段的不同颜色表示不同的疑似度范围</h4>
          <div class="legend-item">
            <span class="legend-dot legend-red" />
            <span class="legend-text">红色 · AIGC生成疑似度在70%以上（高度疑似）</span>
          </div>
          <div class="legend-item">
            <span class="legend-dot legend-orange" />
            <span class="legend-text">橙色 · AIGC生成疑似度在60%~70%（中度疑似）</span>
          </div>
          <div class="legend-item">
            <span class="legend-dot legend-purple" />
            <span class="legend-text">紫色 · AIGC生成疑似度在50%~60%（轻度疑似）</span>
          </div>
          <div class="legend-item">
            <span class="legend-dot legend-normal" />
            <span class="legend-text">正常 · AIGC生成疑似度在50%以下</span>
          </div>
          <div class="legend-item">
            <span class="legend-dot legend-gray" />
            <span class="legend-text">灰色 · 过短片段、标题和英文等不予检测</span>
          </div>
          <p class="legend-hint">如果要查看片段详细识别结果，请点击有颜色标识的部分。</p>
        </div>

        <!-- 改写建议面板 -->
        <div v-if="panelVisible" class="rewrite-panel">
          <div class="panel-header">
            <strong>段落改写建议</strong>
            <button class="close-btn" @click="panelVisible = false">✕</button>
          </div>

          <div v-if="panelLoading" class="panel-loading">
            <el-skeleton :rows="4" animated />
          </div>

          <div v-else-if="panelError" class="panel-error">
            <el-alert :title="panelError" type="warning" :closable="false" show-icon />
          </div>

          <div v-else-if="rewriteAdvice" class="panel-body">
            <div class="diagnosis-box" v-if="rewriteAdvice.diagnosis">
              <strong>风险诊断</strong>
              <p>{{ rewriteAdvice.diagnosis }}</p>
            </div>

            <div v-if="rewriteAdvice.sentences.length" class="sentences-list">
              <div
                v-for="(sent, idx) in rewriteAdvice.sentences"
                :key="idx"
                class="sentence-item"
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
                <el-button
                  size="small"
                  type="success"
                  plain
                  @click.stop="applySentenceRewrite(idx)"
                >
                  应用此句
                </el-button>
              </div>
            </div>

            <div v-if="rewriteAdvice.rewritten_paragraph" class="full-rewrite">
              <strong>全文改写</strong>
              <div class="rewrite-text">{{ rewriteAdvice.rewritten_paragraph }}</div>
              <el-button size="small" type="primary" @click.stop="applyFullRewrite">
                应用全文改写
              </el-button>
            </div>

            <div v-if="rewriteAdvice.overall_advice" class="overall-advice">
              <strong>整体建议</strong>
              <p>{{ rewriteAdvice.overall_advice }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowLeft, ArrowRight, ArrowDown } from '@element-plus/icons-vue'
import { getRunSections, getRewriteAdvice, reanalyzeRun, exportRun } from '../api'
import type { RunSectionItem, RewriteAdviceResponse, ReanalyzeResponse } from '../types'

const props = defineProps<{
  runId: string
  initialAigc: number
  initialDup: number
}>()

const emit = defineEmits<{
  close: []
}>()

const sections = ref<RunSectionItem[]>([])
const loading = ref(false)
const docRef = ref<HTMLDivElement | null>(null)

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

// 动画分数
const animatedAigc = ref(props.initialAigc * 100)
const animatedDup = ref(props.initialDup * 100)

onMounted(() => {
  loadSections()
})

const totalChars = computed(() =>
  sections.value.reduce((sum, s) => sum + (s.char_count || 0), 0)
)

const rewrittenCount = computed(() => rewrittenMap.value.size)

const highRiskSections = computed(() =>
  sections.value.filter(s => s.risk_level !== 'low')
)

const batchAdviceReadyCount = computed(() => {
  let count = 0
  for (const sec of highRiskSections.value) {
    if (batchAdviceMap.value.has(sec.section_index) && !rewrittenMap.value.has(sec.section_index)) {
      count++
    }
  }
  return count
})

const currentAigc = computed(() =>
  realScores.value ? realScores.value.ai_like_percent : props.initialAigc * 100
)
const currentDup = computed(() =>
  realScores.value ? realScores.value.duplication_percent : props.initialDup * 100
)

const aigcDelta = computed(() => currentAigc.value - props.initialAigc * 100)
const dupDelta = computed(() => currentDup.value - props.initialDup * 100)

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
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '加载段落失败')
  } finally {
    loading.value = false
  }
}

function aigcColorClass(sec: RunSectionItem): string {
  if (sec.section_type === 'references' || sec.section_type === 'acknowledgement') return 'gray'
  const score = effectiveAigc(sec)
  if (score >= 0.70) return 'red'
  if (score >= 0.60) return 'orange'
  if (score >= 0.50) return 'purple'
  return 'normal'
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

function displayContent(sec: RunSectionItem): string {
  return rewrittenMap.value.get(sec.section_index) || sec.content
}

function riskText(level: string) {
  return level === 'high' ? '高风险' : level === 'medium' ? '中风险' : '低风险'
}

function scrollToSection(index: number) {
  const el = document.getElementById('sec-' + index)
  if (el && docRef.value) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    activeSectionIndex.value = index
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
  historyStack.value.push({
    sectionIndex,
    previousText,
    newText,
    timestamp: Date.now()
  })
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
  ElMessage.success('已应用全文改写')
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

function applyAllBatch() {
  let applied = 0
  for (const sec of highRiskSections.value) {
    const advice = batchAdviceMap.value.get(sec.section_index)
    if (advice?.rewritten_paragraph && !rewrittenMap.value.has(sec.section_index)) {
      applyRewrite(sec.section_index, advice.rewritten_paragraph)
      applied++
    }
  }
  if (applied) {
    ElMessage.success(`已一键应用 ${applied} 段改写`)
  } else {
    ElMessage.info('没有可应用的改写建议')
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
    a.download = `改写稿.${format}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success(`已导出 ${format.toUpperCase()}`)
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '导出失败')
  }
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
</script>

<style scoped>
.rewrite-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
}

/* ===== 顶部工具栏 ===== */
.score-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 20px;
  border-bottom: 1px solid #e8e8e8;
  background: #fafbfc;
  flex-wrap: wrap;
}

.score-group {
  display: flex;
  align-items: center;
  gap: 24px;
}

.score-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.score-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.score-label {
  font-size: 13px;
  color: #666;
}

.score-value {
  font-size: 20px;
  font-weight: 700;
}

.score-value.high { color: #c41e3a; }
.score-value.medium { color: #e6a23c; }
.score-value.low { color: #2f7d67; }
.score-value.accent { color: #2f7d67; }

.score-delta {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
}

.score-delta.down {
  color: #2f7d67;
  background: #e8f5e9;
}

.score-delta.up {
  color: #c41e3a;
  background: #ffebee;
}

/* ===== 主体三栏布局 ===== */
.editor-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ===== 左侧迷你导航条 ===== */
.minimap {
  width: 20px;
  min-width: 20px;
  background: #f5f5f5;
  border-right: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  cursor: pointer;
}

.minimap-segment {
  width: 100%;
  min-height: 2px;
  transition: opacity 0.15s ease;
  border-bottom: 1px solid rgba(255, 255, 255, 0.3);
}

.minimap-segment:hover {
  opacity: 0.7;
}

.minimap-segment.active {
  box-shadow: inset 0 0 0 2px #2f7d67;
}

.minimap-red { background: #e53935; }
.minimap-orange { background: #fb8c00; }
.minimap-purple { background: #8e24aa; }
.minimap-normal { background: #424242; }
.minimap-gray { background: #bdbdbd; }

/* ===== 中间论文正文 ===== */
.document-view {
  flex: 1;
  overflow-y: auto;
  padding: 24px 40px;
  background: #fff;
  line-height: 1.8;
  font-size: 15px;
  color: #333;
}

.doc-section {
  padding: 12px 16px;
  margin-bottom: 2px;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s ease;
  border-left: 3px solid transparent;
}

.doc-section:hover {
  background: #f5f5f5;
}

/* 风险着色 */
.doc-red {
  background: #ffebee;
  border-left-color: #e53935;
}
.doc-red:hover {
  background: #ffcdd2;
}

.doc-orange {
  background: #fff3e0;
  border-left-color: #fb8c00;
}
.doc-orange:hover {
  background: #ffe0b2;
}

.doc-purple {
  background: #f3e5f5;
  border-left-color: #8e24aa;
}
.doc-purple:hover {
  background: #e1bee7;
}

.doc-normal {
  border-left-color: #9e9e9e;
}

.doc-gray {
  color: #9e9e9e;
  border-left-color: #bdbdbd;
}

.doc-section.is-rewritten {
  border-left-width: 4px;
  border-left-color: #2f7d67 !important;
}

.doc-section.has-advice {
  outline: 1px dashed #fb8c00;
  outline-offset: -1px;
}

.doc-section-title {
  font-weight: 600;
  font-size: 16px;
  color: #1a1a1a;
  margin-bottom: 6px;
}

.doc-section-content {
  white-space: pre-wrap;
  word-break: break-word;
}

.doc-section-meta {
  display: flex;
  gap: 8px;
  margin-top: 6px;
  flex-wrap: wrap;
}

.doc-tag {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 500;
}

.doc-tag-red {
  color: #c62828;
  background: #ffcdd2;
}

.doc-tag-orange {
  color: #ef6c00;
  background: #ffe0b2;
}

.doc-tag-purple {
  color: #6a1b9a;
  background: #e1bee7;
}

.doc-tag-normal {
  color: #424242;
  background: #eeeeee;
}

.doc-tag-gray {
  color: #757575;
  background: #e0e0e0;
}

.doc-tag-dup {
  color: #1565c0;
  background: #bbdefb;
}

.doc-tag-rewritten {
  color: #1b5e20;
  background: #c8e6c9;
}

.doc-tag-advice {
  color: #e65100;
  background: #ffe0b2;
}

/* ===== 右侧边栏 ===== */
.right-sidebar {
  width: 340px;
  min-width: 340px;
  border-left: 1px solid #e8e8e8;
  background: #fff;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 图例 */
.legend-box {
  padding: 16px;
  border-bottom: 1px solid #e8e8e8;
  flex-shrink: 0;
}

.legend-box h4 {
  margin: 0 0 12px;
  font-size: 14px;
  color: #333;
  font-weight: 600;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 12px;
  color: #555;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-red { background: #e53935; }
.legend-orange { background: #fb8c00; }
.legend-purple { background: #8e24aa; }
.legend-normal { background: #424242; }
.legend-gray { background: #bdbdbd; }

.legend-hint {
  margin: 12px 0 0;
  font-size: 12px;
  color: #888;
  line-height: 1.5;
}

/* 改写面板 */
.rewrite-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid #e8e8e8;
  background: #fafbfc;
}

.close-btn {
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  color: #999;
}

.panel-loading,
.panel-error,
.panel-body {
  padding: 16px;
  overflow-y: auto;
  flex: 1;
}

.diagnosis-box {
  background: #fff5f5;
  border: 1px solid #fde2e2;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 16px;
}

.diagnosis-box strong {
  color: #c41e3a;
  font-size: 13px;
}

.diagnosis-box p {
  margin: 4px 0 0;
  font-size: 13px;
  color: #555;
}

.sentences-list {
  display: grid;
  gap: 14px;
}

.sentence-item {
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 12px;
}

.sentence-item label {
  font-size: 11px;
  font-weight: 600;
  color: #888;
  text-transform: uppercase;
}

.sentence-item p {
  margin: 4px 0 10px;
  font-size: 13px;
  line-height: 1.6;
}

.sent-original p {
  color: #555;
}

.sent-rewritten p {
  color: #2f7d67;
  font-weight: 500;
}

.sent-explanation p {
  color: #888;
  font-size: 12px;
}

.full-rewrite {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed #ddd;
}

.rewrite-text {
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  border-radius: 6px;
  padding: 10px;
  font-size: 13px;
  line-height: 1.6;
  margin: 8px 0;
}

.overall-advice {
  margin-top: 16px;
  padding: 12px;
  background: #f0f9ff;
  border-radius: 6px;
  font-size: 13px;
}

/* ===== 响应式 ===== */
@media (max-width: 1024px) {
  .right-sidebar {
    width: 280px;
    min-width: 280px;
  }
}

@media (max-width: 768px) {
  .minimap {
    display: none;
  }

  .right-sidebar {
    position: fixed;
    right: 0;
    top: 0;
    bottom: 0;
    width: 100%;
    z-index: 100;
  }

  .score-bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .score-actions {
    width: 100%;
  }

  .document-view {
    padding: 16px;
  }
}
</style>
