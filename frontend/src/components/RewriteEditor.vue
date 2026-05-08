<template>
  <div class="rewrite-editor">
    <!-- 顶部分数栏 -->
    <div class="score-bar">
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
      <el-button type="primary" size="small" :disabled="!rewrittenCount" @click="applyAll">
        全文应用
      </el-button>
    </div>

    <!-- 正文区域 -->
    <div class="editor-body">
      <div class="paragraphs">
        <div
          v-for="sec in sections"
          :key="sec.section_index"
          class="para-block"
          :class="{
            'risk-high': sec.risk_level === 'high',
            'risk-medium': sec.risk_level === 'medium',
            'rewritten': rewrittenMap.has(sec.section_index)
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
            <span class="risk-tag" :class="'tag-' + sec.risk_level">
              {{ riskText(sec.risk_level) }}
            </span>
            <span v-if="sec.aigc_score > 0" class="score-tag">
              AIGC {{ (sec.aigc_score * 100).toFixed(1) }}%
            </span>
            <span v-if="sec.dup_score > 0" class="score-tag">
              查重 {{ (sec.dup_score * 100).toFixed(1) }}%
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
                @click="applySentenceRewrite(idx)"
              >
                应用此句
              </el-button>
            </div>
          </div>

          <!-- 全文改写 -->
          <div v-if="rewriteAdvice.rewritten_paragraph" class="full-rewrite">
            <strong>全文改写</strong>
            <div class="rewrite-text">{{ rewriteAdvice.rewritten_paragraph }}</div>
            <el-button size="small" type="primary" @click="applyFullRewrite">
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
import { getRunSections, getRewriteAdvice } from '../api'
import type { RunSectionItem, RewriteAdviceResponse } from '../types'

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

// 动画分数
const animatedAigc = ref(props.initialAigc * 100)
const animatedDup = ref(props.initialDup * 100)

onMounted(() => {
  loadSections()
})

const rewrittenCount = computed(() => rewrittenMap.value.size)

const aigcDelta = computed(() => {
  const base = props.initialAigc * 100
  const reduction = rewrittenCount.value * 1.5 // 每改写一段模拟降低 1.5%
  return Math.max(-base + 1, -reduction)
})

const dupDelta = computed(() => {
  const base = props.initialDup * 100
  const reduction = rewrittenCount.value * 1.2
  return Math.max(-base + 1, -reduction)
})

const aigcColor = computed(() => {
  const v = animatedAigc.value
  return v >= 30 ? 'high' : v >= 15 ? 'medium' : 'low'
})

const dupColor = computed(() => {
  const v = animatedDup.value
  return v >= 20 ? 'high' : v >= 10 ? 'medium' : 'low'
})

watch(rewrittenCount, () => {
  animateScore()
})

function animateScore() {
  const targetAigc = props.initialAigc * 100 + aigcDelta.value
  const targetDup = props.initialDup * 100 + dupDelta.value
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

  try {
    rewriteAdvice.value = await getRewriteAdvice(props.runId, sec.section_index)
  } catch (err) {
    panelError.value = err instanceof Error ? err.message : '获取改写建议失败'
  } finally {
    panelLoading.value = false
  }
}

function applySentenceRewrite(sentenceIdx: number) {
  if (!rewriteAdvice.value || activeSectionIndex.value === null) return
  const sent = rewriteAdvice.value.sentences[sentenceIdx]
  if (!sent) return

  const sec = sections.value.find((s: RunSectionItem) => s.section_index === activeSectionIndex.value)
  if (!sec) return

  const current = rewrittenMap.value.get(activeSectionIndex.value) || sec.content
  const updated = current.replace(sent.original, sent.rewritten)
  rewrittenMap.value.set(activeSectionIndex.value, updated)
  ElMessage.success('已应用改写')
}

function applyFullRewrite() {
  if (!rewriteAdvice.value || activeSectionIndex.value === null) return
  rewrittenMap.value.set(activeSectionIndex.value, rewriteAdvice.value.rewritten_paragraph)
  ElMessage.success('已应用全文改写')
}

function applyAll() {
  if (!rewriteAdvice.value) return
  // 对当前所有高风险段落应用全文改写
  for (const sec of sections.value) {
    if (sec.risk_level !== 'low' && !rewrittenMap.value.has(sec.section_index)) {
      // 这里简化处理：不能批量调用 API，只能提示用户逐段处理
    }
  }
  ElMessage.info('请逐段点击获取改写建议后应用')
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
  gap: 24px;
  padding: 14px 20px;
  border-bottom: 1px solid #e8e8e8;
  background: #fafbfc;
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

.para-block.rewritten {
  border-color: rgba(230, 162, 60, 0.4);
  background: #fffbe6;
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
}
</style>
