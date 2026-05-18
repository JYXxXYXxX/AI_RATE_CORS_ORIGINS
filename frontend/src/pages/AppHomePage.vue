<template>
  <div class="home-page">
    <section class="home-hero">
      <div class="hero-copy">
        <p class="eyebrow">PataFix workspace</p>
        <h1>把论文修改变成一张清楚的工作台。</h1>
        <p>
          先上传论文生成报告，再进入在线改写。系统会保留原文档格式，只围绕风险段落给出可替换的句子。
        </p>
        <div class="hero-actions">
          <router-link to="/app/new" class="home-button primary">上传论文</router-link>
          <router-link to="/app/dashboard" class="home-button ghost">查看工作台</router-link>
        </div>
      </div>
      <div class="hero-board">
        <div class="mascot-stage" aria-hidden="true">
          <div class="scan-rail">
            <span />
            <span />
            <span />
          </div>
          <div class="pata-agent">
            <div class="agent-head">
              <span class="agent-eye left" />
              <span class="agent-eye right" />
              <span class="agent-smile" />
            </div>
            <div class="agent-body">
              <span class="agent-badge">P</span>
              <span class="agent-arm left" />
              <span class="agent-arm right" />
            </div>
            <div class="agent-shadow" />
          </div>
          <div class="document-orbit">
            <div class="orbit-paper paper-a">
              <span class="doc-title" />
              <span />
              <span class="risk-line red" />
              <span />
              <b>AIGC 82%</b>
            </div>
            <div class="orbit-paper paper-b">
              <span class="doc-title" />
              <span />
              <span class="risk-line amber" />
              <b>重复 46%</b>
            </div>
            <div class="orbit-paper paper-c clean">
              <span class="doc-title" />
              <span />
              <span />
              <b>已优化</b>
            </div>
          </div>
          <div class="rewrite-beam">
            <span class="beam-dot dot-one" />
            <span class="beam-dot dot-two" />
            <span class="beam-dot dot-three" />
          </div>
          <div class="word-chip chip-risk">模板句</div>
          <div class="word-chip chip-fix">证据细节</div>
          <div class="word-chip chip-safe">保格式替换</div>
        </div>
        <div class="side-ticket">
          <span>下一步</span>
          <strong>{{ latestRunId ? '继续改写最近论文' : '上传第一篇论文' }}</strong>
          <button type="button" @click="goPrimary">
            {{ latestRunId ? '进入改写' : '开始分析' }}
          </button>
        </div>
      </div>
    </section>

    <section class="case-carousel-section" aria-labelledby="case-carousel-title">
      <div class="section-head">
        <p class="eyebrow">rewrite scenes</p>
        <h2 id="case-carousel-title">修改案例场景</h2>
        <span>鼠标移到卡片上会暂停滚动，方便查看改写前后差异。</span>
      </div>
      <div class="case-carousel" aria-label="修改案例轮播">
        <div class="case-track">
          <article v-for="(item, index) in carouselCards" :key="`${item.title}-${index}`" class="case-card">
            <div class="case-card-top">
              <span class="case-tag">{{ item.tag }}</span>
              <strong>{{ item.beforeMetric }} → {{ item.afterMetric }}</strong>
            </div>
            <h3>{{ item.title }}</h3>
            <div class="case-text before">
              <span>原句</span>
              <p>{{ item.before }}</p>
            </div>
            <div class="case-text after">
              <span>优化后</span>
              <p>{{ item.after }}</p>
            </div>
          </article>
        </div>
      </div>
    </section>

    <section class="quick-rewrite-panel" aria-labelledby="quick-rewrite-title">
      <div class="quick-intro">
        <p class="eyebrow">try one sentence</p>
        <h2 id="quick-rewrite-title">短句风险优化</h2>
        <p>先粘贴一段论文内容，系统会标出高风险词组，并给出更像人工写作、可直接替换的版本。</p>
      </div>

      <div class="quick-tool">
        <div class="quick-input-card">
          <div class="mode-tabs" aria-label="改写模式">
            <button
              v-for="item in modeOptions"
              :key="item.value"
              type="button"
              class="mode-tab"
              :class="{ active: quickMode === item.value }"
              @click="quickMode = item.value"
            >
              {{ item.label }}
            </button>
          </div>

          <label class="quick-label" for="home-quick-rewrite-input">
            输入论文段落
            <span>{{ quickInput.length }} 字</span>
          </label>
          <textarea
            id="home-quick-rewrite-input"
            v-model="quickInput"
            class="quick-textarea"
            rows="8"
            placeholder="粘贴摘要、绪论、研究意义或系统介绍中的一小段"
          />

          <div class="quick-actions">
            <button type="button" class="home-button primary" :disabled="quickLoading || !quickInput.trim()" @click="handleQuickRewrite">
              {{ quickLoading ? '优化中...' : '检测并优化' }}
            </button>
            <button type="button" class="home-button ghost" :disabled="quickLoading" @click="loadSample">填入示例</button>
          </div>
          <p v-if="quickError" class="quick-error">{{ quickError }}</p>
        </div>

        <div class="quick-output-card">
          <div v-if="!quickResult" class="quick-empty">
            <strong>结果会在这里生成</strong>
            <p>红色标出原文风险词，绿色标出改写后发生变化、能降低风险的表达。</p>
          </div>

          <template v-else>
            <div class="risk-strip">
              <div>
                <span>优化前风险指数</span>
                <strong>{{ quickResult.beforeRisk.score }}</strong>
              </div>
              <div>
                <span>优化后预估区间</span>
                <strong>{{ afterRiskDisplay }}</strong>
                <small>{{ afterRiskLevelLabel }}</small>
              </div>
            </div>
            <p class="quick-summary">{{ quickResult.summary }}</p>

            <div class="rewrite-compare">
              <article class="result-panel">
                <h3>原文风险标记</h3>
                <p class="marked-text">
                  <template v-for="(seg, index) in originalSegments" :key="`origin-${index}`">
                    <mark v-if="seg.mark" class="risk-mark" :title="seg.reason">{{ seg.text }}</mark>
                    <span v-else>{{ seg.text }}</span>
                  </template>
                </p>
              </article>
              <article class="result-panel">
                <h3>改写结果</h3>
                <p class="marked-text">
                  <template v-for="(seg, index) in rewrittenSegments" :key="`rewrite-${index}`">
                    <mark v-if="seg.mark" class="improve-mark" :title="seg.reason">{{ seg.text }}</mark>
                    <span v-else>{{ seg.text }}</span>
                  </template>
                </p>
              </article>
            </div>

            <div class="principle-row">
              <span v-for="item in quickResult.rewritePrinciples.slice(0, 3)" :key="item">{{ item }}</span>
            </div>

            <div class="quick-actions">
              <button type="button" class="home-button primary" @click="copyRewritten">复制改写结果</button>
              <button type="button" class="home-button ghost" :disabled="quickLoading" @click="handleQuickRewrite">重新生成</button>
              <button type="button" class="home-button ghost" @click="router.push('/app/new')">上传全文检测</button>
            </div>
          </template>
        </div>
      </div>
    </section>

    <section class="home-grid">
      <article class="home-panel">
        <span class="panel-index">01</span>
        <h2>先检测</h2>
        <p>识别 AIGC、重复率和官方报告标记片段，不把正常段落堆给用户。</p>
      </article>
      <article class="home-panel">
        <span class="panel-index">02</span>
        <h2>再改写</h2>
        <p>按风险词、句式骨架、相似来源给出可落地替换句。</p>
      </article>
      <article class="home-panel">
        <span class="panel-index">03</span>
        <h2>保格式导出</h2>
        <p>改写稿基于原 DOCX 做文本替换，尽量不碰论文原来的版式。</p>
      </article>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus/es/components/message/index'
import { quickRewrite } from '../api'
import { useAnalysisStore } from '../stores/analysis'
import type { QuickRewriteMode, QuickRewritePhrase, QuickRewriteResult } from '../types'

const router = useRouter()
const analysis = useAnalysisStore()

const latestRunId = computed(() => analysis.history.find(item => item.run_id)?.run_id || '')
const quickInput = ref('')
const quickMode = ref<QuickRewriteMode>('auto')
const quickLoading = ref(false)
const quickError = ref('')
const quickResult = ref<QuickRewriteResult | null>(null)

const caseCards = [
  {
    tag: '降AIGC',
    title: '摘要套话过重',
    beforeMetric: '82%',
    afterMetric: '28%',
    before: '随着人工智能技术的发展，相关系统在各领域中发挥着越来越重要的作用。',
    after: '本系统把账单识别、预算预警和月度复盘拆成三个流程，帮助用户更快发现异常支出。'
  },
  {
    tag: '降重复',
    title: '综述重复表达',
    beforeMetric: '46%',
    afterMetric: '17%',
    before: '国内外学者对该问题进行了大量研究，并取得了较为丰富的研究成果。',
    after: '现有研究主要集中在模型构建和指标筛选两类路径，本文进一步补充了场景化校验环节。'
  },
  {
    tag: '报告校准',
    title: '官方标红段落',
    beforeMetric: '高风险',
    afterMetric: '低风险',
    before: '平台可以提升用户体验，并为后续研究提供一定参考价值。',
    after: '平台将检测结果拆成风险句、替换词和导出记录，便于学生按学校报告逐条处理。'
  },
  {
    tag: '保格式',
    title: 'DOCX 原位替换',
    beforeMetric: '格式保留',
    afterMetric: '文本更新',
    before: '用户需要对论文内容进行修改，从而达到降低重复率的目的。',
    after: '用户只替换被标记的句子，标题、页眉、编号和表格样式继续沿用原文档。'
  },
  {
    tag: '学术润色',
    title: '研究意义空泛',
    beforeMetric: '泛化',
    afterMetric: '具体',
    before: '本研究具有重要的理论意义和现实意义，能够推动相关领域发展。',
    after: '本研究把检测、改写和回填校准放入同一流程，减少学生在多份报告之间反复比对的成本。'
  }
]

const carouselCards = computed(() => [...caseCards, ...caseCards])

const modeOptions: Array<{ value: QuickRewriteMode; label: string }> = [
  { value: 'auto', label: '智能推荐' },
  { value: 'aigc', label: '降AIGC' },
  { value: 'similarity', label: '降重复' },
  { value: 'polish', label: '学术润色' }
]

const originalSegments = computed(() =>
  quickResult.value ? buildMarkedSegments(quickResult.value.originalText, quickResult.value.riskyPhrases) : []
)
const rewrittenSegments = computed(() =>
  quickResult.value ? buildMarkedSegments(quickResult.value.rewrittenText, quickResult.value.improvedPhrases) : []
)
const afterRiskDisplay = computed(() => {
  if (!quickResult.value) return '--'
  const score = quickResult.value.afterRisk.score
  return `${Math.max(0, score - 6)}-${Math.min(100, score + 8)}`
})
const afterRiskLevelLabel = computed(() => {
  if (!quickResult.value) return ''
  const map = {
    high: '仍需重点优化',
    medium: '中等风险',
    low: '低风险',
    normal: '低风险'
  }
  return map[quickResult.value.afterRisk.level]
})

onMounted(() => {
  analysis.refreshHistory()
})

function goPrimary() {
  if (latestRunId.value) {
    router.push(`/app/rewrite/${latestRunId.value}`)
  } else {
    router.push('/app/new')
  }
}

async function handleQuickRewrite() {
  const text = quickInput.value.trim()
  if (!text) {
    ElMessage.warning('请先输入一段论文内容')
    return
  }
  quickLoading.value = true
  quickError.value = ''
  try {
    quickResult.value = await quickRewrite({ text, mode: quickMode.value })
  } catch (error) {
    quickError.value = error instanceof Error ? error.message : '检测失败，请稍后再试'
    ElMessage.error(quickError.value)
  } finally {
    quickLoading.value = false
  }
}

function loadSample() {
  quickInput.value = '随着人工智能技术的发展，个人财务管理系统在日常生活中发挥着越来越重要的作用。该系统能够帮助用户提高财务管理效率，具有较强的现实意义，并为相关研究提供一定参考价值。'
}

async function copyRewritten() {
  if (!quickResult.value) return
  try {
    await navigator.clipboard.writeText(quickResult.value.rewrittenText)
    ElMessage.success('改写结果已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

function buildMarkedSegments(text: string, phrases: QuickRewritePhrase[]) {
  const ranges = locateRanges(text, phrases)
  const segments: Array<{ text: string; mark: boolean; reason?: string }> = []
  let cursor = 0
  for (const range of ranges) {
    if (range.start > cursor) {
      segments.push({ text: text.slice(cursor, range.start), mark: false })
    }
    segments.push({
      text: text.slice(range.start, range.end),
      mark: true,
      reason: range.reason
    })
    cursor = range.end
  }
  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor), mark: false })
  }
  return segments
}

function locateRanges(text: string, phrases: QuickRewritePhrase[]) {
  const ranges: Array<{ start: number; end: number; reason: string }> = []
  for (const phrase of phrases) {
    let start = typeof phrase.start === 'number' ? phrase.start : -1
    let end = typeof phrase.end === 'number' ? phrase.end : -1
    if (start < 0 || end <= start || text.slice(start, end) !== phrase.text) {
      start = text.indexOf(phrase.text)
      end = start >= 0 ? start + phrase.text.length : -1
    }
    if (start < 0 || end <= start) continue
    if (ranges.some((range) => !(end <= range.start || start >= range.end))) continue
    ranges.push({ start, end, reason: phrase.reason })
  }
  return ranges.sort((a, b) => a.start - b.start)
}
</script>

<style scoped>
.home-page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 34px 28px 48px;
}

.home-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 28px;
  align-items: stretch;
}

.hero-copy,
.hero-board,
.home-panel {
  border: 1px solid rgba(58, 67, 61, 0.1);
  background: rgba(255, 253, 247, 0.92);
  box-shadow: 0 18px 50px rgba(46, 56, 48, 0.08);
}

.hero-copy {
  padding: 44px;
  border-radius: 26px;
}

.eyebrow {
  color: #6f7e4d;
  letter-spacing: 0.12em;
}

.hero-copy h1 {
  max-width: 680px;
  margin: 10px 0 14px;
  color: #20251f;
  font-size: 42px;
  line-height: 1.12;
  letter-spacing: 0;
}

.hero-copy p {
  max-width: 620px;
  color: #62695f;
  line-height: 1.8;
}

.hero-actions {
  display: flex;
  gap: 12px;
  margin-top: 28px;
}

.home-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 42px;
  padding: 0 18px;
  border-radius: 10px;
  text-decoration: none;
  font-weight: 700;
  border: 0;
  font: inherit;
  cursor: pointer;
}

.home-button.primary {
  color: #fff;
  background: #2f6f53;
}

.home-button.ghost {
  color: #2f3b34;
  background: #f0eadf;
}

.home-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.hero-board {
  position: relative;
  min-height: 360px;
  border-radius: 26px;
  overflow: hidden;
  background:
    radial-gradient(circle at 72% 18%, rgba(216, 173, 95, 0.34), transparent 30%),
    radial-gradient(circle at 14% 22%, rgba(67, 112, 89, 0.24), transparent 28%),
    linear-gradient(135deg, rgba(255, 253, 247, 0.96), rgba(232, 239, 225, 0.9));
}

.mascot-stage {
  position: absolute;
  inset: 18px 18px 88px;
  border-radius: 22px;
  overflow: hidden;
  background:
    linear-gradient(rgba(47, 67, 58, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(47, 67, 58, 0.08) 1px, transparent 1px);
  background-size: 28px 28px;
}

.mascot-stage::before {
  content: "";
  position: absolute;
  inset: 38px 42px;
  border: 1px solid rgba(47, 67, 58, 0.08);
  border-radius: 50%;
  transform: rotate(-8deg);
}

.scan-rail {
  position: absolute;
  left: 26px;
  right: 26px;
  top: 28px;
  display: flex;
  justify-content: space-between;
  opacity: 0.8;
}

.scan-rail span {
  width: 28%;
  height: 3px;
  border-radius: 99px;
  background: linear-gradient(90deg, transparent, #2f6f53, transparent);
  animation: railPulse 2.6s ease-in-out infinite;
}

.scan-rail span:nth-child(2) {
  animation-delay: 0.32s;
}

.scan-rail span:nth-child(3) {
  animation-delay: 0.64s;
}

.pata-agent {
  position: absolute;
  left: 50%;
  top: 54%;
  width: 136px;
  height: 170px;
  transform: translate(-50%, -50%);
  animation: agentFloat 4.2s ease-in-out infinite;
}

.agent-head {
  position: absolute;
  left: 18px;
  right: 18px;
  top: 0;
  height: 92px;
  border: 3px solid #26382f;
  border-radius: 34px 34px 28px 28px;
  background: linear-gradient(145deg, #fffaf1, #e6f0df);
  box-shadow: inset 0 -10px 0 rgba(47, 111, 83, 0.1), 0 18px 32px rgba(46, 56, 48, 0.14);
}

.agent-head::before {
  content: "";
  position: absolute;
  left: 22px;
  right: 22px;
  top: 20px;
  height: 28px;
  border-radius: 999px;
  background: #24362e;
}

.agent-eye {
  position: absolute;
  z-index: 1;
  top: 29px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #d8ad5f;
  box-shadow: 0 0 12px rgba(216, 173, 95, 0.76);
  animation: eyeBlink 5s ease-in-out infinite;
}

.agent-eye.left {
  left: 42px;
}

.agent-eye.right {
  right: 42px;
}

.agent-smile {
  position: absolute;
  left: 50%;
  bottom: 22px;
  width: 34px;
  height: 13px;
  border-bottom: 3px solid #2f6f53;
  border-radius: 0 0 999px 999px;
  transform: translateX(-50%);
}

.agent-body {
  position: absolute;
  left: 30px;
  right: 30px;
  top: 82px;
  height: 72px;
  border-radius: 28px 28px 34px 34px;
  background: linear-gradient(145deg, #2f6f53, #253a31);
  box-shadow: 0 18px 30px rgba(46, 56, 48, 0.2);
}

.agent-badge {
  position: absolute;
  left: 50%;
  top: 18px;
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #2c342e;
  background: #d8ad5f;
  font-weight: 900;
  transform: translateX(-50%);
}

.agent-arm {
  position: absolute;
  top: 18px;
  width: 42px;
  height: 12px;
  border-radius: 99px;
  background: #253a31;
}

.agent-arm.left {
  left: -34px;
  transform: rotate(-18deg);
}

.agent-arm.right {
  right: -34px;
  transform: rotate(18deg);
}

.agent-shadow {
  position: absolute;
  left: 20px;
  right: 20px;
  bottom: 0;
  height: 18px;
  border-radius: 50%;
  background: rgba(31, 42, 36, 0.18);
  filter: blur(3px);
  animation: shadowPulse 4.2s ease-in-out infinite;
}

.document-orbit {
  position: absolute;
  inset: 0;
}

.orbit-paper {
  position: absolute;
  width: 128px;
  min-height: 126px;
  padding: 16px;
  border: 1px solid rgba(47, 67, 58, 0.1);
  border-radius: 14px;
  background: rgba(255, 254, 250, 0.96);
  box-shadow: 0 14px 30px rgba(46, 56, 48, 0.12);
  display: grid;
  align-content: start;
  gap: 9px;
}

.orbit-paper span {
  display: block;
  height: 7px;
  border-radius: 99px;
  background: #d9d4c8;
}

.orbit-paper .doc-title {
  width: 68%;
  height: 11px;
  background: #56644f;
}

.orbit-paper b {
  width: fit-content;
  margin-top: 3px;
  padding: 5px 8px;
  border-radius: 8px;
  color: #26382f;
  background: #efe7d5;
  font-size: 12px;
}

.risk-line.red {
  background: #d76052;
  box-shadow: 0 0 0 4px rgba(215, 96, 82, 0.14);
}

.risk-line.amber {
  background: #d8ad5f;
  box-shadow: 0 0 0 4px rgba(216, 173, 95, 0.16);
}

.paper-a {
  left: 22px;
  top: 72px;
  transform: rotate(-10deg);
  animation: paperFloatA 5s ease-in-out infinite;
}

.paper-b {
  right: 22px;
  top: 54px;
  transform: rotate(8deg);
  animation: paperFloatB 5.6s ease-in-out infinite;
}

.paper-c {
  right: 62px;
  bottom: 18px;
  transform: rotate(-3deg);
  animation: paperFloatC 6s ease-in-out infinite;
}

.paper-c b {
  color: #fff;
  background: #2f6f53;
}

.rewrite-beam {
  position: absolute;
  left: 72px;
  right: 78px;
  top: 48%;
  height: 70px;
  border-top: 2px dashed rgba(47, 111, 83, 0.36);
  border-bottom: 2px dashed rgba(216, 173, 95, 0.32);
  transform: rotate(-5deg);
}

.beam-dot {
  position: absolute;
  top: 50%;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #d8ad5f;
  box-shadow: 0 0 16px rgba(216, 173, 95, 0.78);
  animation: beamMove 3.4s linear infinite;
}

.dot-one {
  animation-delay: 0s;
}

.dot-two {
  animation-delay: 1.1s;
}

.dot-three {
  animation-delay: 2.2s;
}

.word-chip {
  position: absolute;
  padding: 7px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  box-shadow: 0 10px 24px rgba(46, 56, 48, 0.1);
  animation: chipFloat 4.8s ease-in-out infinite;
}

.chip-risk {
  left: 30px;
  bottom: 32px;
  color: #8f332f;
  background: #f4d9d1;
}

.chip-fix {
  left: 158px;
  top: 38px;
  color: #5b3f13;
  background: #f4e3bf;
  animation-delay: 0.4s;
}

.chip-safe {
  right: 28px;
  bottom: 154px;
  color: #245642;
  background: #dce9dd;
  animation-delay: 0.8s;
}

.side-ticket {
  position: absolute;
  left: 28px;
  right: 28px;
  bottom: 24px;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px;
  border-radius: 16px;
  background: rgba(40, 48, 42, 0.9);
  color: #fff;
}

.side-ticket span {
  color: rgba(255, 255, 255, 0.62);
  font-size: 12px;
}

.side-ticket strong {
  flex: 1;
}

.side-ticket button {
  border: 0;
  border-radius: 9px;
  padding: 8px 12px;
  background: #d8ad5f;
  color: #20251f;
  font-weight: 800;
  cursor: pointer;
}

.case-carousel-section,
.quick-rewrite-panel {
  margin-top: 20px;
  border: 1px solid rgba(58, 67, 61, 0.1);
  border-radius: 8px;
  background: rgba(255, 253, 247, 0.9);
  box-shadow: 0 18px 50px rgba(46, 56, 48, 0.07);
}

.case-carousel-section {
  padding: 24px 0 24px 24px;
  overflow: hidden;
}

.section-head,
.quick-intro {
  max-width: 760px;
  padding-right: 24px;
}

.section-head h2,
.quick-intro h2 {
  margin: 8px 0 8px;
  color: #20251f;
  font-size: 28px;
  line-height: 1.2;
}

.section-head span,
.quick-intro p {
  color: #62695f;
  line-height: 1.7;
}

.case-carousel {
  position: relative;
  margin-top: 18px;
  overflow: hidden;
}

.case-carousel::before,
.case-carousel::after {
  content: "";
  position: absolute;
  top: 0;
  z-index: 2;
  width: 72px;
  height: 100%;
  pointer-events: none;
}

.case-carousel::before {
  left: 0;
  background: linear-gradient(90deg, rgba(255, 253, 247, 0.95), transparent);
}

.case-carousel::after {
  right: 0;
  background: linear-gradient(270deg, rgba(255, 253, 247, 0.95), transparent);
}

.case-track {
  display: flex;
  gap: 14px;
  width: max-content;
  animation: caseScroll 38s linear infinite;
}

.case-carousel:hover .case-track {
  animation-play-state: paused;
}

.case-card {
  width: 318px;
  min-height: 286px;
  display: grid;
  gap: 12px;
  align-content: start;
  padding: 18px;
  border: 1px solid rgba(58, 67, 61, 0.11);
  border-radius: 8px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(248, 244, 235, 0.88)),
    #fff;
  box-shadow: 0 12px 28px rgba(46, 56, 48, 0.08);
}

.case-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.case-tag {
  width: fit-content;
  padding: 5px 9px;
  border-radius: 999px;
  color: #2f6f53;
  background: rgba(47, 111, 83, 0.1);
  font-size: 12px;
  font-weight: 900;
}

.case-card-top strong {
  color: #9b7750;
  font-size: 13px;
}

.case-card h3 {
  margin: 0;
  color: #20251f;
  font-size: 18px;
}

.case-text {
  padding: 12px;
  border-radius: 8px;
  line-height: 1.7;
}

.case-text span {
  display: block;
  margin-bottom: 5px;
  font-size: 12px;
  font-weight: 900;
}

.case-text p {
  margin: 0;
  color: #3f4741;
  font-size: 14px;
}

.case-text.before {
  background: rgba(215, 96, 82, 0.1);
}

.case-text.before span {
  color: #9b332f;
}

.case-text.after {
  background: rgba(47, 111, 83, 0.1);
}

.case-text.after span {
  color: #2f6f53;
}

.quick-rewrite-panel {
  padding: 28px;
}

.quick-tool {
  display: grid;
  grid-template-columns: minmax(280px, 0.82fr) minmax(0, 1.18fr);
  gap: 18px;
  margin-top: 22px;
}

.quick-input-card,
.quick-output-card {
  min-width: 0;
  padding: 18px;
  border: 1px solid rgba(58, 67, 61, 0.1);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.72);
}

.mode-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}

.mode-tab {
  border: 1px solid rgba(58, 67, 61, 0.14);
  border-radius: 8px;
  background: #fffdf7;
  color: #3f4741;
  padding: 8px 11px;
  font: inherit;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.mode-tab.active {
  border-color: rgba(47, 111, 83, 0.55);
  background: rgba(47, 111, 83, 0.1);
  color: #245642;
}

.quick-label {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  color: #2f3b34;
  font-size: 14px;
  font-weight: 900;
}

.quick-label span {
  color: #7d857b;
  font-weight: 700;
}

.quick-textarea {
  width: 100%;
  min-height: 218px;
  resize: vertical;
  border: 1px solid rgba(58, 67, 61, 0.14);
  border-radius: 8px;
  padding: 14px;
  background: #fffefa;
  color: #20251f;
  font: inherit;
  line-height: 1.75;
  outline: none;
}

.quick-textarea:focus {
  border-color: #2f6f53;
  box-shadow: 0 0 0 3px rgba(47, 111, 83, 0.12);
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.quick-error {
  margin: 12px 0 0;
  color: #b23a34;
  font-size: 14px;
}

.quick-empty {
  min-height: 318px;
  display: grid;
  align-content: center;
  gap: 8px;
  padding: 24px;
  border: 1px dashed rgba(47, 111, 83, 0.28);
  border-radius: 8px;
  background: rgba(237, 244, 236, 0.7);
}

.quick-empty strong {
  color: #20251f;
  font-size: 18px;
}

.quick-empty p,
.quick-summary {
  color: #62695f;
  line-height: 1.7;
}

.risk-strip {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.risk-strip div {
  padding: 14px;
  border-radius: 8px;
  border: 1px solid rgba(58, 67, 61, 0.08);
  background: #f7f4ec;
}

.risk-strip span,
.risk-strip small {
  display: block;
  color: #667064;
  font-size: 12px;
}

.risk-strip strong {
  display: block;
  margin: 7px 0 4px;
  color: #20251f;
  font-size: 28px;
  line-height: 1;
}

.rewrite-compare {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.result-panel {
  min-width: 0;
  padding: 15px;
  border: 1px solid rgba(58, 67, 61, 0.09);
  border-radius: 8px;
  background: #fffefa;
}

.result-panel h3 {
  margin: 0 0 10px;
  color: #20251f;
  font-size: 16px;
}

.marked-text {
  margin: 0;
  color: #3f4741;
  line-height: 1.9;
  word-break: break-word;
}

.risk-mark,
.improve-mark {
  border-radius: 4px;
  padding: 1px 3px;
}

.risk-mark {
  color: #9b332f;
  background: rgba(215, 96, 82, 0.17);
}

.improve-mark {
  color: #245642;
  background: rgba(47, 111, 83, 0.17);
}

.principle-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.principle-row span {
  max-width: 100%;
  padding: 7px 9px;
  border-radius: 8px;
  color: #5b3f13;
  background: rgba(216, 173, 95, 0.16);
  font-size: 12px;
  font-weight: 800;
}

.home-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-top: 18px;
}

.home-panel {
  border-radius: 18px;
  padding: 22px;
}

.panel-index {
  color: #9b7750;
  font-weight: 900;
}

.home-panel h2 {
  margin: 10px 0 8px;
  color: #20251f;
  font-size: 20px;
}

.home-panel p {
  color: #62695f;
  line-height: 1.7;
}

@keyframes agentFloat {
  0%, 100% {
    transform: translate(-50%, -50%);
  }
  50% {
    transform: translate(-50%, calc(-50% - 12px));
  }
}

@keyframes shadowPulse {
  0%, 100% {
    transform: scaleX(1);
    opacity: 0.9;
  }
  50% {
    transform: scaleX(0.76);
    opacity: 0.48;
  }
}

@keyframes eyeBlink {
  0%, 92%, 100% {
    transform: scaleY(1);
  }
  95% {
    transform: scaleY(0.18);
  }
}

@keyframes railPulse {
  0%, 100% {
    opacity: 0.18;
    transform: translateX(-8px);
  }
  50% {
    opacity: 0.9;
    transform: translateX(8px);
  }
}

@keyframes paperFloatA {
  0%, 100% {
    transform: rotate(-10deg) translateY(0);
  }
  50% {
    transform: rotate(-7deg) translateY(-10px);
  }
}

@keyframes paperFloatB {
  0%, 100% {
    transform: rotate(8deg) translateY(0);
  }
  50% {
    transform: rotate(5deg) translateY(12px);
  }
}

@keyframes paperFloatC {
  0%, 100% {
    transform: rotate(-3deg) translateY(0);
  }
  50% {
    transform: rotate(-1deg) translateY(-8px);
  }
}

@keyframes beamMove {
  from {
    left: 0;
    opacity: 0;
  }
  12%, 86% {
    opacity: 1;
  }
  to {
    left: 100%;
    opacity: 0;
  }
}

@keyframes chipFloat {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-7px);
  }
}

@keyframes caseScroll {
  from {
    transform: translateX(0);
  }
  to {
    transform: translateX(calc(-50% - 7px));
  }
}

@media (max-width: 980px) {
  .home-hero,
  .home-grid,
  .quick-tool,
  .rewrite-compare {
    grid-template-columns: 1fr;
  }

  .hero-board {
    min-height: 320px;
  }
}

@media (max-width: 560px) {
  .home-page {
    padding: 22px 16px 36px;
  }

  .hero-copy {
    padding: 28px;
  }

  .hero-copy h1 {
    font-size: 32px;
  }

  .hero-actions {
    flex-direction: column;
  }

  .case-carousel-section,
  .quick-rewrite-panel {
    margin-top: 16px;
  }

  .case-carousel-section {
    padding: 20px 0 20px 16px;
  }

  .section-head,
  .quick-intro {
    padding-right: 16px;
  }

  .section-head h2,
  .quick-intro h2 {
    font-size: 24px;
  }

  .case-card {
    width: 282px;
  }

  .quick-rewrite-panel {
    padding: 18px;
  }

  .risk-strip {
    grid-template-columns: 1fr;
  }

  .hero-board {
    min-height: 340px;
  }

  .mascot-stage {
    inset: 14px 14px 92px;
  }

  .pata-agent {
    width: 116px;
    height: 150px;
  }

  .agent-head {
    left: 14px;
    right: 14px;
    height: 82px;
  }

  .agent-body {
    left: 24px;
    right: 24px;
    top: 74px;
    height: 64px;
  }

  .orbit-paper {
    width: 104px;
    min-height: 108px;
    padding: 12px;
  }

  .paper-a {
    left: 10px;
    top: 64px;
  }

  .paper-b {
    right: 8px;
    top: 48px;
  }

  .paper-c {
    right: 36px;
    bottom: 12px;
  }

  .chip-safe {
    right: 18px;
    bottom: 132px;
  }

  .side-ticket {
    left: 16px;
    right: 16px;
    gap: 10px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .case-track,
  .pata-agent,
  .scan-rail span,
  .agent-eye,
  .agent-shadow,
  .paper-a,
  .paper-b,
  .paper-c,
  .beam-dot,
  .word-chip {
    animation: none;
  }
}
</style>
