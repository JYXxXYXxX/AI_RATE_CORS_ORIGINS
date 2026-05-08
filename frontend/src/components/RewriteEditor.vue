<template>
  <div class="rewrite-editor">
    <!-- 顶部分数栏 -->
    <div class="score-bar">
      <div class="score-group">
        <div class="score-item">
          <span class="score-label">本地 AIGC</span>
          <span class="score-value" :class="aigcColor">
            {{ animatedAigc.toFixed(1) }}%
          </span>
          <span v-if="aigcDelta !== 0" class="score-delta" :class="aigcDelta < 0 ? 'down' : 'up'">
            {{ aigcDelta > 0 ? '+' : '' }}{{ aigcDelta.toFixed(1) }}%
          </span>
        </div>
        <div class="score-item">
          <span class="score-label">查重率</span>
          <span class="score-value" :class="dupColor">
            {{ animatedDup.toFixed(1) }}%
          </span>
          <span v-if="dupDelta !== 0" class="score-delta" :class="dupDelta < 0 ? 'down' : 'up'">
            {{ dupDelta > 0 ? '+' : '' }}{{ dupDelta.toFixed(1) }}%
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

    <!-- 正文区域 -->
    <div class="editor-body">
      <div class="paragraphs">
        <div
          v-for="sec in sections"
          :key="sec.section_index"
          class="para-block"
          :class="{
            'risk-high': effectiveRisk(sec) === 'high',
            'risk-medium': effectiveRisk(sec) === 'medium',
            'risk-low': effectiveRisk(sec) === 'low',
            'rewritten': rewrittenMap.has(sec.section_index),
            'has-batch-advice': batchAdviceMap.has(sec.section_index)
          }"
          @click="selectSection(sec)"
        >
          <div class="para-title" v-if="sec.section_title">
            {{ sec.section_title }}
          </div>
          <div class="para-content">
            {{ displayContent(sec) }}
          </div>
          <div class="para-meta">
            <span class="risk-tag" :class="'tag-' + effectiveRisk(sec)">
              {{ riskText(effectiveRisk(sec)) }}
            </span>
            <span v-if="effectiveAigc(sec) > 0" class="score-tag">
              AIGC {{ (effectiveAigc(sec) * 100).toFixed(1) }}%
            </span>
            <span v-if="effectiveDup(sec) > 0" class="score-tag">
              查重 {{ (effectiveDup(sec) * 100).toFixed(1) }}%
            </span>
            <span v-if="batchAdviceMap.has(sec.section_index)" class="advice-tag">
              建议已就绪
            </span>
          </div>
        </div>
      </div>

      <!-- 侧边改写面板 -->
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
          <!-- 诊断 -->
          <div class="diagnosis-box" v-if="rewriteAdvice.diagnosis">
            <strong>风险诊断</strong>
            <p>{{ rewriteAdvice.diagnosis }}</p>
          </div>

          <!-- 逐句改写 -->
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

          <!-- 全文改写 -->
          <div v-if="rewriteAdvice.rewritten_paragraph" class="full-rewrite">
            <strong>全文改写</strong>
            <div class="rewrite-text">{{ rewriteAdvice.rewritten_paragraph }}</div>
            <el-button size="small" type="primary" @click.stop="applyFullRewrite">
              应用全文改写
            </el-button>
          </div>

          <!-- 整体建议 -->
          <div v-if="rewriteAdvice.overall_advice" class="overall-advice">
            <strong>整体建议</strong>
            <p>{{ rewriteAdvice.overall_advice }}</p>
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

async function selectSection(sec: RunSectionItem) {
  activeSectionIndex.value = sec.section_index
  panelVisible.value = true
  panelLoading.value = true
  panelError.value = ''
  rewriteAdvice.value = null

  // 优先使用缓存的批量建议
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
  // 如果当前不在栈顶，截断后面的历史
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

.score-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 20px;
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

.editor-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.paragraphs {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.para-block {
  padding: 16px 18px;
  margin-bottom: 12px;
  border-radius: 10px;
  border: 1.5px solid transparent;
  background: #fafbfc;
  cursor: pointer;
  transition: all 0.15s ease;
}

.para-block:hover {
  border-color: rgba(47, 125, 103, 0.2);
  box-shadow: 0 2px 8px rgba(29, 45, 61, 0.04);
}

.para-block.risk-high {
  border-color: rgba(196, 30, 58, 0.25);
  background: #fff5f5;
}

.para-block.risk-medium {
  border-color: rgba(230, 162, 60, 0.25);
  background: #fffbf0;
}

.para-block.risk-low {
  border-color: rgba(47, 125, 103, 0.15);
  background: #f6ffed;
}

.para-block.rewritten {
  border-left: 4px solid #2f7d67;
}

.para-block.has-batch-advice {
  border-style: dashed;
}

.para-title {
  font-weight: 600;
  font-size: 14px;
  color: #172033;
  margin-bottom: 6px;
}

.para-content {
  font-size: 14px;
  line-height: 1.8;
  color: #344150;
  white-space: pre-wrap;
}

.para-meta {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.risk-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}

.tag-high {
  color: #c41e3a;
  background: #fde2e2;
}

.tag-medium {
  color: #b45309;
  background: #fef3c7;
}

.tag-low {
  color: #2f7d67;
  background: #d1fae5;
}

.score-tag {
  font-size: 11px;
  color: #666;
  padding: 2px 8px;
  background: #f0f0f0;
  border-radius: 4px;
}

.advice-tag {
  font-size: 11px;
  color: #2f7d67;
  padding: 2px 8px;
  background: #e8f5e9;
  border-radius: 4px;
}

.rewrite-panel {
  width: 420px;
  border-left: 1px solid #e8e8e8;
  background: #fff;
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

@media (max-width: 768px) {
  .rewrite-panel {
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
}
</style>
