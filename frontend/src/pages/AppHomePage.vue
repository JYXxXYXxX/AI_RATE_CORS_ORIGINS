<template>
  <div class="home-page">
    <section class="home-hero">
      <div class="hero-copy">
        <p class="eyebrow">{{ copy.heroEyebrow }}</p>
        <h1>
          {{ copy.heroTitleLead }}
          <span class="hero-crayon">{{ copy.heroTitleMark }}</span>
          {{ copy.heroTitleTail }}
        </h1>
        <p>
          {{ copy.heroDesc }}
        </p>
        <div class="hero-actions">
          <router-link to="/app/new" class="home-button primary">{{ copy.upload }}</router-link>
          <router-link to="/app/dashboard" class="home-button ghost">{{ copy.dashboard }}</router-link>
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
            <span class="agent-antenna" />
            <div class="agent-head">
              <span class="agent-eye left" />
              <span class="agent-eye right" />
              <span class="agent-cheek left" />
              <span class="agent-cheek right" />
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
              <b>{{ copy.aigcMetric }}</b>
            </div>
            <div class="orbit-paper paper-b">
              <span class="doc-title" />
              <span />
              <span class="risk-line amber" />
              <b>{{ copy.similarityMetric }}</b>
            </div>
            <div class="orbit-paper paper-c clean">
              <span class="doc-title" />
              <span />
              <span />
              <b>{{ copy.optimizedTag }}</b>
            </div>
          </div>
          <div class="rewrite-beam">
            <span class="beam-dot dot-one" />
            <span class="beam-dot dot-two" />
            <span class="beam-dot dot-three" />
          </div>
          <div class="word-chip chip-risk">{{ copy.templateTag }}</div>
          <div class="word-chip chip-fix">{{ copy.evidenceTag }}</div>
          <div class="word-chip chip-safe">{{ copy.formatTag }}</div>
        </div>
        <div class="side-ticket">
          <span>{{ copy.next }}</span>
          <strong>{{ latestRunId ? copy.continueLatest : copy.uploadFirst }}</strong>
          <button type="button" @click="goPrimary">
            {{ latestRunId ? copy.enterRewrite : copy.startAnalysis }}
          </button>
        </div>
      </div>
    </section>

    <section class="case-carousel-section reveal-on-scroll" aria-labelledby="case-carousel-title">
      <div class="section-head">
        <p class="eyebrow">{{ copy.caseEyebrow }}</p>
        <h2 id="case-carousel-title">{{ copy.caseTitle }}</h2>
        <span>{{ copy.caseDesc }}</span>
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
              <span>{{ copy.before }}</span>
              <p>{{ item.before }}</p>
            </div>
            <div class="case-text after">
              <span>{{ copy.after }}</span>
              <p>{{ item.after }}</p>
            </div>
          </article>
        </div>
      </div>
    </section>

    <section class="quick-rewrite-panel reveal-on-scroll" aria-labelledby="quick-rewrite-title">
      <div class="quick-intro">
        <p class="eyebrow">{{ copy.quickEyebrow }}</p>
        <h2 id="quick-rewrite-title">{{ copy.quickTitle }}</h2>
        <p>{{ copy.quickDesc }}</p>
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
            {{ copy.inputLabel }}
            <span>{{ quickInput.length }} {{ copy.words }}</span>
          </label>
          <textarea
            id="home-quick-rewrite-input"
            v-model="quickInput"
            class="quick-textarea"
            rows="8"
            :placeholder="copy.placeholder"
          />

          <div class="quick-actions">
            <button type="button" class="home-button primary" :disabled="quickLoading || !quickInput.trim()" @click="handleQuickRewrite">
              {{ quickLoading ? copy.optimizing : copy.optimize }}
            </button>
            <button type="button" class="home-button ghost" :disabled="quickLoading" @click="loadSample">{{ copy.sample }}</button>
          </div>
          <p v-if="quickError" class="quick-error">{{ quickError }}</p>
        </div>

        <div class="quick-output-card">
          <div v-if="!quickResult" class="quick-empty">
            <strong>{{ copy.emptyTitle }}</strong>
            <p>{{ copy.emptyDesc }}</p>
          </div>

          <template v-else>
            <div class="risk-strip">
              <div>
                <span>{{ copy.beforeRisk }}</span>
                <strong>{{ quickResult.beforeRisk.score }}</strong>
              </div>
              <div>
                <span>{{ copy.afterRisk }}</span>
                <strong>{{ afterRiskDisplay }}</strong>
                <small>{{ afterRiskLevelLabel }}</small>
              </div>
            </div>
            <p class="quick-summary">{{ quickResult.summary }}</p>

            <div class="rewrite-compare">
              <article class="result-panel">
                <h3>{{ copy.originalMarked }}</h3>
                <p class="marked-text">
                  <template v-for="(seg, index) in originalSegments" :key="`origin-${index}`">
                    <mark v-if="seg.mark" class="risk-mark" :title="seg.reason">{{ seg.text }}</mark>
                    <span v-else>{{ seg.text }}</span>
                  </template>
                </p>
              </article>
              <article class="result-panel">
                <h3>{{ copy.rewriteResult }}</h3>
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
              <button type="button" class="home-button primary" @click="copyRewritten">{{ copy.copyResult }}</button>
              <button type="button" class="home-button ghost" :disabled="quickLoading" @click="handleQuickRewrite">{{ copy.regenerate }}</button>
              <button type="button" class="home-button ghost" @click="router.push('/app/new')">{{ copy.uploadFull }}</button>
            </div>
          </template>
        </div>
      </div>
    </section>

    <section class="home-grid reveal-on-scroll">
      <article v-for="(panel, index) in copy.panels" :key="panel.title" class="home-panel">
        <span class="panel-index">{{ String(index + 1).padStart(2, '0') }}</span>
        <h2>{{ panel.title }}</h2>
        <p>{{ panel.desc }}</p>
      </article>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
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
type HomeLocale = 'zh' | 'en'
const locale = ref<HomeLocale>((localStorage.getItem('patafix-language') as HomeLocale) || 'zh')

const copies = {
  zh: {
    heroEyebrow: 'PataFix workspace',
    heroTitleLead: '把论文红区，划成',
    heroTitleMark: '可直接替换',
    heroTitleTail: '的修改稿。',
    heroDesc: '先上传论文生成报告，再进入在线改写。系统会保留原文档格式，只围绕风险段落给出可替换的句子。',
    upload: '上传论文',
    dashboard: '查看工作台',
    next: '下一步',
    continueLatest: '继续改写最近论文',
    uploadFirst: '上传第一篇论文',
    enterRewrite: '进入改写',
    startAnalysis: '开始分析',
    aigcMetric: 'AIGC 82%',
    similarityMetric: '重复 46%',
    optimizedTag: '已优化',
    templateTag: '模板句',
    evidenceTag: '证据细节',
    formatTag: '保格式替换',
    caseEyebrow: 'rewrite scenes',
    caseTitle: '修改案例场景',
    caseDesc: '鼠标移到卡片上会暂停滚动，方便查看改写前后差异。',
    before: '原句',
    after: '优化后',
    quickEyebrow: 'try one sentence',
    quickTitle: '短句风险优化',
    quickDesc: '先粘贴一段论文内容，系统会标出高风险词组，并给出更像人工写作、可直接替换的版本。',
    inputLabel: '输入论文段落',
    words: '字',
    placeholder: '粘贴摘要、绪论、研究意义或系统介绍中的一小段',
    optimizing: '优化中...',
    optimize: '检测并优化',
    sample: '填入示例',
    emptyTitle: '结果会在这里生成',
    emptyDesc: '红色标出原文风险词，绿色标出改写后发生变化、能降低风险的表达。',
    beforeRisk: '优化前风险指数',
    afterRisk: '优化后预估区间',
    originalMarked: '原文风险标记',
    rewriteResult: '改写结果',
    copyResult: '复制改写结果',
    regenerate: '重新生成',
    uploadFull: '上传全文检测',
    panels: [
      { title: '先检测', desc: '识别 AIGC、重复率和官方报告标记片段，不把正常段落堆给用户。' },
      { title: '再改写', desc: '按风险词、句式骨架、相似来源给出可落地替换句。' },
      { title: '保格式导出', desc: '改写稿基于原 DOCX 做文本替换，尽量不碰论文原来的版式。' }
    ]
  },
  en: {
    heroEyebrow: 'PataFix workspace',
    heroTitleLead: 'Turn thesis red flags into a ',
    heroTitleMark: 'ready-to-replace',
    heroTitleTail: ' rewrite draft.',
    heroDesc: 'Upload a paper, generate a report, then rewrite only the risky passages while keeping the original document format intact.',
    upload: 'Upload paper',
    dashboard: 'Workspace',
    next: 'Next',
    continueLatest: 'Continue latest rewrite',
    uploadFirst: 'Upload first paper',
    enterRewrite: 'Open rewrite',
    startAnalysis: 'Start scan',
    aigcMetric: 'AIGC 82%',
    similarityMetric: 'Similarity 46%',
    optimizedTag: 'Optimized',
    templateTag: 'Template',
    evidenceTag: 'Evidence details',
    formatTag: 'Keep formatting',
    caseEyebrow: 'rewrite scenes',
    caseTitle: 'Rewrite case studies',
    caseDesc: 'Hover over the cards to pause the carousel and compare before and after.',
    before: 'Before',
    after: 'After',
    quickEyebrow: 'try one sentence',
    quickTitle: 'Short passage optimizer',
    quickDesc: 'Paste a thesis paragraph to see risky phrases and generate a more natural replacement.',
    inputLabel: 'Paper paragraph',
    words: 'chars',
    placeholder: 'Paste a short abstract, introduction, significance, or system-description paragraph',
    optimizing: 'Optimizing...',
    optimize: 'Scan and optimize',
    sample: 'Use sample',
    emptyTitle: 'Results will appear here',
    emptyDesc: 'Risky phrases are marked in red, while meaningful rewrite changes are marked in green.',
    beforeRisk: 'Before risk index',
    afterRisk: 'Estimated after range',
    originalMarked: 'Original risk marks',
    rewriteResult: 'Rewrite result',
    copyResult: 'Copy rewrite',
    regenerate: 'Regenerate',
    uploadFull: 'Upload full paper',
    panels: [
      { title: 'Scan first', desc: 'Find AIGC, similarity, and official-report risk marks without flooding users with normal sections.' },
      { title: 'Rewrite next', desc: 'Suggest usable replacements based on risk words, sentence skeletons, and similarity sources.' },
      { title: 'Export safely', desc: 'Patch text inside the original DOCX while preserving titles, tables, and document style as much as possible.' }
    ]
  }
}

const localizedCaseCards = {
  zh: [
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
  ],
  en: [
    {
      tag: 'AIGC',
      title: 'Template abstract',
      beforeMetric: '82%',
      afterMetric: '28%',
      before: 'With the development of artificial intelligence, related systems play an increasingly important role in many fields.',
      after: 'The system separates bill recognition, budget alerts, and monthly review so users can spot abnormal spending faster.'
    },
    {
      tag: 'Similarity',
      title: 'Generic literature review',
      beforeMetric: '46%',
      afterMetric: '17%',
      before: 'Scholars at home and abroad have conducted extensive research and achieved rich results.',
      after: 'Existing studies focus on model construction and indicator selection, while this work adds scenario-based verification.'
    },
    {
      tag: 'Report mode',
      title: 'Official red marks',
      beforeMetric: 'High',
      afterMetric: 'Low',
      before: 'The platform can improve user experience and provide certain reference value for future research.',
      after: 'The platform splits results into risk sentences, replacement terms, and export records for report-by-report revision.'
    },
    {
      tag: 'DOCX',
      title: 'In-place replacement',
      beforeMetric: 'Keep style',
      afterMetric: 'Patch text',
      before: 'Users need to modify paper content to reduce the similarity rate.',
      after: 'Users replace only marked sentences while headings, headers, numbering, and table styles remain from the original file.'
    },
    {
      tag: 'Polish',
      title: 'Vague significance',
      beforeMetric: 'Generic',
      afterMetric: 'Specific',
      before: 'This research has important theoretical and practical significance and can promote the development of related fields.',
      after: 'This study places detection, rewriting, and feedback calibration in one workflow, reducing repeated report comparison.'
    }
  ]
}

const copy = computed(() => copies[locale.value])
const carouselCards = computed(() => [...localizedCaseCards[locale.value], ...localizedCaseCards[locale.value]])

const modeOptions = computed<Array<{ value: QuickRewriteMode; label: string }>>(() => {
  if (locale.value === 'en') {
    return [
      { value: 'auto', label: 'Auto' },
      { value: 'aigc', label: 'Lower AIGC' },
      { value: 'similarity', label: 'Lower similarity' },
      { value: 'polish', label: 'Academic polish' }
    ]
  }
  return [
    { value: 'auto', label: '智能推荐' },
    { value: 'aigc', label: '降AIGC' },
    { value: 'similarity', label: '降重复' },
    { value: 'polish', label: '学术润色' }
  ]
})

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
  const map = locale.value === 'en'
    ? {
        high: 'Still needs work',
        medium: 'Medium risk',
        low: 'Low risk',
        normal: 'Low risk'
      }
    : {
        high: '仍需重点优化',
        medium: '中等风险',
        low: '低风险',
        normal: '低风险'
      }
  return map[quickResult.value.afterRisk.level]
})

onMounted(() => {
  analysis.refreshHistory()
  setupRevealAnimations()
  window.addEventListener('patafix:language-change', handleLanguageChange)
})

onBeforeUnmount(() => {
  window.removeEventListener('patafix:language-change', handleLanguageChange)
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
  quickInput.value = locale.value === 'en'
    ? 'With the development of artificial intelligence, personal finance management systems play an increasingly important role in daily life. The system can help users improve financial management efficiency and has strong practical significance.'
    : '随着人工智能技术的发展，个人财务管理系统在日常生活中发挥着越来越重要的作用。该系统能够帮助用户提高财务管理效率，具有较强的现实意义，并为相关研究提供一定参考价值。'
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

function handleLanguageChange(event: Event) {
  locale.value = (event as CustomEvent<HomeLocale>).detail || 'zh'
}

function setupRevealAnimations() {
  const elements = Array.from(document.querySelectorAll<HTMLElement>('.reveal-on-scroll'))
  if (!('IntersectionObserver' in window)) {
    elements.forEach((element) => element.classList.add('is-visible'))
    return
  }
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue
      entry.target.classList.add('is-visible')
      observer.unobserve(entry.target)
    }
  }, { threshold: 0.18, rootMargin: '0px 0px -8% 0px' })
  elements.forEach((element) => observer.observe(element))
}
</script>

<style scoped>
.home-page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 34px 28px 48px;
}

.reveal-on-scroll {
  opacity: 0;
  transform: translateY(26px);
  transition:
    opacity 0.72s ease,
    transform 0.72s cubic-bezier(0.2, 0.82, 0.2, 1);
  will-change: opacity, transform;
}

.reveal-on-scroll.is-visible {
  opacity: 1;
  transform: translateY(0);
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

.hero-crayon {
  position: relative;
  display: inline-block;
  color: #255f48;
  isolation: isolate;
  white-space: nowrap;
}

.hero-crayon::before {
  content: "";
  position: absolute;
  left: -0.3em;
  bottom: 0.01em;
  z-index: -1;
  width: 0.42em;
  height: 0.42em;
  border-radius: 58% 42% 46% 54%;
  background:
    radial-gradient(circle at 36% 42%, rgba(255, 255, 255, 0.52), transparent 0.09em),
    linear-gradient(135deg, #f8d474, #e7a932 58%, #c98625);
  box-shadow:
    -0.08em 0.08em 0 rgba(37, 95, 72, 0.08),
    0 0 0 0.08em rgba(247, 226, 145, 0.24);
  opacity: 0;
  transform: rotate(-15deg) scale(0.82);
  animation: crayonTip 1.18s 0.34s cubic-bezier(0.2, 0.9, 0.2, 1) forwards;
}

.hero-crayon::after {
  content: "";
  position: absolute;
  left: -0.12em;
  right: -0.13em;
  bottom: -0.03em;
  height: 0.34em;
  z-index: -1;
  border-radius: 42% 58% 48% 52% / 54% 44% 56% 46%;
  background:
    radial-gradient(circle at 11% 52%, rgba(255, 255, 255, 0.28) 0 0.08em, transparent 0.085em),
    radial-gradient(circle at 34% 38%, rgba(255, 246, 209, 0.36) 0 0.06em, transparent 0.065em),
    radial-gradient(circle at 62% 64%, rgba(161, 96, 18, 0.18) 0 0.055em, transparent 0.06em),
    repeating-linear-gradient(-8deg, rgba(255, 250, 223, 0.2) 0 0.1em, rgba(255, 255, 255, 0) 0.1em 0.22em),
    linear-gradient(90deg, rgba(255, 210, 97, 0.15), rgba(255, 200, 69, 0.96) 42%, rgba(255, 145, 105, 0.62));
  box-shadow:
    0 0.08em 0 rgba(47, 111, 83, 0.08),
    0 0.18em 0.28em rgba(232, 185, 82, 0.18);
  clip-path: polygon(0 48%, 5% 36%, 12% 47%, 20% 31%, 29% 45%, 37% 32%, 47% 46%, 57% 35%, 66% 48%, 76% 36%, 86% 45%, 100% 38%, 100% 78%, 91% 67%, 82% 82%, 72% 67%, 62% 81%, 52% 68%, 42% 82%, 31% 67%, 22% 82%, 12% 68%, 0 79%);
  transform: scaleX(0) rotate(-1.6deg);
  transform-origin: left center;
  animation: crayonDraw 1.18s 0.34s cubic-bezier(0.2, 0.9, 0.2, 1) forwards;
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
    radial-gradient(circle at 76% 18%, rgba(232, 194, 116, 0.38), transparent 31%),
    radial-gradient(circle at 14% 18%, rgba(128, 171, 148, 0.26), transparent 30%),
    radial-gradient(circle at 50% 88%, rgba(246, 218, 195, 0.34), transparent 30%),
    linear-gradient(135deg, #fffdf6 0%, #eef6e9 54%, #fbf0d8 100%);
}

.mascot-stage {
  position: absolute;
  inset: 18px 18px 88px;
  border-radius: 22px;
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 48%, rgba(255, 255, 255, 0.66), transparent 42%),
    linear-gradient(rgba(47, 67, 58, 0.07) 1px, transparent 1px),
    linear-gradient(90deg, rgba(47, 67, 58, 0.07) 1px, transparent 1px);
  background-size: 100% 100%, 28px 28px, 28px 28px;
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
  left: 34px;
  right: 34px;
  top: 44%;
  display: flex;
  justify-content: space-between;
  opacity: 0.65;
  transform: rotate(-5deg);
}

.scan-rail span {
  width: 30%;
  height: 3px;
  border-radius: 99px;
  background: linear-gradient(90deg, transparent, #94bca6, transparent);
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
  top: 53%;
  width: 150px;
  height: 178px;
  transform: translate(-50%, -50%);
  animation: agentFloat 4.2s ease-in-out infinite;
}

.agent-antenna {
  position: absolute;
  left: 50%;
  top: -12px;
  width: 44px;
  height: 34px;
  border-top: 4px solid #26382f;
  border-radius: 999px 999px 0 0;
  transform: translateX(-50%);
}

.agent-antenna::before,
.agent-antenna::after {
  content: "";
  position: absolute;
  top: -7px;
  width: 13px;
  height: 13px;
  border: 3px solid #26382f;
  border-radius: 50%;
  background: #e5b95e;
  box-shadow: 0 0 0 5px rgba(229, 185, 94, 0.16);
}

.agent-antenna::before {
  left: -5px;
}

.agent-antenna::after {
  right: -5px;
}

.agent-head {
  position: absolute;
  left: 8px;
  right: 8px;
  top: 0;
  height: 104px;
  border: 4px solid #26382f;
  border-radius: 44px 44px 38px 38px;
  background:
    radial-gradient(circle at 28% 24%, rgba(255, 255, 255, 0.94), transparent 22%),
    linear-gradient(145deg, #fffdf3, #e9f4e5);
  box-shadow: inset 0 -9px 0 rgba(47, 111, 83, 0.08), 0 18px 30px rgba(46, 56, 48, 0.13);
}

.agent-head::before {
  content: "";
  position: absolute;
  left: 31px;
  right: 31px;
  top: 25px;
  height: 35px;
  border-radius: 999px;
  background: linear-gradient(90deg, #2a3a32, #20332b);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
}

.agent-eye {
  position: absolute;
  z-index: 1;
  top: 37px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #efc96f;
  box-shadow: 0 0 14px rgba(239, 201, 111, 0.8);
  animation: eyeBlink 5s ease-in-out infinite;
}

.agent-eye.left {
  left: 54px;
}

.agent-eye.right {
  right: 54px;
}

.agent-cheek {
  position: absolute;
  z-index: 1;
  top: 66px;
  width: 18px;
  height: 9px;
  border-radius: 999px;
  background: rgba(232, 151, 132, 0.34);
}

.agent-cheek.left {
  left: 34px;
}

.agent-cheek.right {
  right: 34px;
}

.agent-smile {
  position: absolute;
  left: 50%;
  bottom: 23px;
  width: 40px;
  height: 17px;
  border-bottom: 3px solid #2f6f53;
  border-radius: 0 0 999px 999px;
  transform: translateX(-50%);
}

.agent-body {
  position: absolute;
  left: 31px;
  right: 31px;
  top: 95px;
  height: 76px;
  border-radius: 36px 36px 42px 42px;
  background:
    radial-gradient(circle at 70% 18%, rgba(255, 255, 255, 0.18), transparent 24%),
    linear-gradient(145deg, #2f7659, #243b31);
  box-shadow: 0 18px 30px rgba(46, 56, 48, 0.22);
}

.agent-badge {
  position: absolute;
  left: 50%;
  top: 18px;
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #2c342e;
  background: #e5b95e;
  font-weight: 900;
  box-shadow: inset -5px -5px 0 rgba(133, 91, 26, 0.12);
  transform: translateX(-50%);
}

.agent-arm {
  position: absolute;
  top: 21px;
  width: 55px;
  height: 16px;
  border-radius: 99px;
  background: #26382f;
  transform-origin: center;
}

.agent-arm.left {
  left: -45px;
  transform: rotate(-20deg);
}

.agent-arm.right {
  right: -45px;
  transform: rotate(20deg);
}

.agent-shadow {
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: -6px;
  height: 20px;
  border-radius: 50%;
  background: rgba(31, 42, 36, 0.16);
  filter: blur(3px);
  animation: shadowPulse 4.2s ease-in-out infinite;
}

.document-orbit {
  position: absolute;
  inset: 0;
}

.orbit-paper {
  position: absolute;
  width: 132px;
  min-height: 126px;
  padding: 16px;
  border: 1px solid rgba(47, 67, 58, 0.08);
  border-radius: 18px;
  background: rgba(255, 254, 250, 0.96);
  box-shadow: 0 16px 30px rgba(46, 56, 48, 0.12);
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
  background: #526553;
}

.orbit-paper b {
  width: fit-content;
  margin-top: 3px;
  padding: 6px 9px;
  border-radius: 999px;
  color: #26382f;
  background: #f1e3c4;
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
  left: 19px;
  top: 83px;
  transform: rotate(-10deg);
  animation: paperFloatA 5s ease-in-out infinite;
}

.paper-b {
  right: 16px;
  top: 72px;
  transform: rotate(8deg);
  animation: paperFloatB 5.6s ease-in-out infinite;
}

.paper-c {
  right: 58px;
  bottom: 20px;
  transform: rotate(-3deg);
  animation: paperFloatC 6s ease-in-out infinite;
}

.paper-c b {
  color: #fff;
  background: #2f6f53;
}

.rewrite-beam {
  position: absolute;
  left: 68px;
  right: 70px;
  top: 48%;
  height: 74px;
  border-top: 2px dashed rgba(47, 111, 83, 0.28);
  border-bottom: 2px dashed rgba(229, 185, 94, 0.3);
  transform: rotate(-5deg);
}

.beam-dot {
  position: absolute;
  top: 50%;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #e5b95e;
  box-shadow: 0 0 16px rgba(229, 185, 94, 0.78);
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
  padding: 8px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  border: 1px solid rgba(47, 67, 58, 0.05);
  box-shadow: 0 12px 24px rgba(46, 56, 48, 0.11);
  animation: chipFloat 4.8s ease-in-out infinite;
}

.chip-risk {
  left: 40px;
  top: 82px;
  color: #8f332f;
  background: #f4d9d1;
}

.chip-fix {
  left: 150px;
  top: 38px;
  color: #5b3f13;
  background: #f4e3bf;
  animation-delay: 0.4s;
}

.chip-safe {
  right: 24px;
  top: 28px;
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
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease;
}

.home-panel:hover {
  transform: translateY(-3px);
  box-shadow: 0 22px 54px rgba(46, 56, 48, 0.12);
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

@keyframes crayonDraw {
  0% {
    opacity: 0;
    transform: scaleX(0) rotate(-1.6deg) translateY(0.03em);
  }
  14% {
    opacity: 1;
  }
  58% {
    transform: scaleX(0.72) rotate(-1.6deg) translateY(-0.02em);
  }
  100% {
    opacity: 1;
    transform: scaleX(1) rotate(-1.6deg) translateY(0);
  }
}

@keyframes crayonTip {
  0% {
    left: -0.3em;
    opacity: 0;
    transform: rotate(-18deg) scale(0.78);
  }
  12% {
    opacity: 1;
  }
  70% {
    left: calc(100% - 0.12em);
    opacity: 1;
    transform: rotate(-10deg) scale(1);
  }
  100% {
    left: calc(100% + 0.02em);
    opacity: 0;
    transform: rotate(-8deg) scale(0.9);
  }
}

:global(html[data-theme='dark']) .hero-copy,
:global(html[data-theme='dark']) .hero-board,
:global(html[data-theme='dark']) .home-panel,
:global(html[data-theme='dark']) .case-carousel-section,
:global(html[data-theme='dark']) .quick-rewrite-panel {
  border-color: rgba(232, 235, 245, 0.11);
  background:
    radial-gradient(circle at 16% 0%, rgba(138, 180, 255, 0.08), transparent 28%),
    linear-gradient(180deg, rgba(14, 15, 20, 0.96), rgba(4, 5, 7, 0.98));
  box-shadow: 0 22px 62px rgba(0, 0, 0, 0.34);
}

:global(html[data-theme='dark']) .hero-copy h1,
:global(html[data-theme='dark']) .section-head h2,
:global(html[data-theme='dark']) .quick-intro h2,
:global(html[data-theme='dark']) .home-panel h2,
:global(html[data-theme='dark']) .result-panel h3,
:global(html[data-theme='dark']) .quick-empty strong,
:global(html[data-theme='dark']) .case-card h3 {
  color: #f4f1eb;
}

:global(html[data-theme='dark']) .hero-copy p,
:global(html[data-theme='dark']) .section-head span,
:global(html[data-theme='dark']) .quick-intro p,
:global(html[data-theme='dark']) .home-panel p,
:global(html[data-theme='dark']) .quick-empty p,
:global(html[data-theme='dark']) .quick-summary,
:global(html[data-theme='dark']) .marked-text,
:global(html[data-theme='dark']) .case-text p {
  color: #c9ced8;
}

:global(html[data-theme='dark']) .eyebrow,
:global(html[data-theme='dark']) .panel-index,
:global(html[data-theme='dark']) .case-card-top strong {
  color: #ffd166;
}

:global(html[data-theme='dark']) .hero-crayon {
  color: #a9c8ff;
}

:global(html[data-theme='dark']) .hero-crayon::after {
  background:
    radial-gradient(circle at 11% 52%, rgba(255, 255, 255, 0.22) 0 0.08em, transparent 0.085em),
    radial-gradient(circle at 34% 38%, rgba(255, 246, 209, 0.28) 0 0.06em, transparent 0.065em),
    radial-gradient(circle at 62% 64%, rgba(28, 44, 94, 0.22) 0 0.055em, transparent 0.06em),
    repeating-linear-gradient(-8deg, rgba(255, 255, 255, 0.13) 0 0.1em, rgba(255, 255, 255, 0) 0.1em 0.22em),
    linear-gradient(90deg, rgba(138, 180, 255, 0.18), rgba(138, 180, 255, 0.94) 42%, rgba(255, 209, 102, 0.52));
  box-shadow:
    0 0.08em 0 rgba(138, 180, 255, 0.08),
    0 0.18em 0.32em rgba(138, 180, 255, 0.18);
}

:global(html[data-theme='dark']) .hero-crayon::before {
  background:
    radial-gradient(circle at 36% 42%, rgba(255, 255, 255, 0.48), transparent 0.09em),
    linear-gradient(135deg, #dce8ff, #8ab4ff 58%, #5f7fe4);
  box-shadow:
    -0.08em 0.08em 0 rgba(0, 0, 0, 0.18),
    0 0 0 0.08em rgba(138, 180, 255, 0.18);
}

:global(html[data-theme='dark']) .home-button.ghost,
:global(html[data-theme='dark']) .mode-tab,
:global(html[data-theme='dark']) .quick-input-card,
:global(html[data-theme='dark']) .quick-output-card,
:global(html[data-theme='dark']) .result-panel,
:global(html[data-theme='dark']) .case-card {
  border-color: rgba(232, 235, 245, 0.12);
  background: rgba(255, 255, 255, 0.065);
  color: #f4f1eb;
}

:global(html[data-theme='dark']) .mode-tab.active,
:global(html[data-theme='dark']) .case-tag {
  border-color: rgba(138, 180, 255, 0.38);
  background: rgba(138, 180, 255, 0.14);
  color: #9fc2ff;
}

:global(html[data-theme='dark']) .quick-textarea {
  border-color: rgba(232, 235, 245, 0.13);
  background: rgba(6, 7, 10, 0.68);
  color: #f4f1eb;
}

:global(html[data-theme='dark']) .hero-board {
  background:
    radial-gradient(circle at 76% 18%, rgba(255, 209, 102, 0.16), transparent 31%),
    radial-gradient(circle at 20% 16%, rgba(138, 180, 255, 0.18), transparent 30%),
    radial-gradient(circle at 50% 88%, rgba(255, 122, 112, 0.1), transparent 34%),
    linear-gradient(135deg, #090a0d 0%, #11131a 56%, #030405 100%);
}

:global(html[data-theme='dark']) .mascot-stage {
  background:
    radial-gradient(circle at 50% 48%, rgba(138, 180, 255, 0.08), transparent 42%),
    linear-gradient(rgba(232, 235, 245, 0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(232, 235, 245, 0.055) 1px, transparent 1px);
  background-size: 100% 100%, 28px 28px, 28px 28px;
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
    width: 126px;
    height: 154px;
  }

  .agent-antenna {
    top: -10px;
    width: 36px;
    height: 28px;
    border-top-width: 3px;
  }

  .agent-antenna::before,
  .agent-antenna::after {
    width: 10px;
    height: 10px;
    border-width: 2px;
  }

  .agent-head {
    left: 8px;
    right: 8px;
    height: 88px;
    border-width: 3px;
  }

  .agent-head::before {
    left: 26px;
    right: 26px;
    top: 22px;
    height: 29px;
  }

  .agent-eye {
    top: 31px;
  }

  .agent-eye.left {
    left: 43px;
  }

  .agent-eye.right {
    right: 43px;
  }

  .agent-cheek {
    top: 56px;
    width: 15px;
  }

  .agent-cheek.left {
    left: 28px;
  }

  .agent-cheek.right {
    right: 28px;
  }

  .agent-body {
    left: 24px;
    right: 24px;
    top: 80px;
    height: 62px;
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
    top: 114px;
  }

  .side-ticket {
    left: 16px;
    right: 16px;
    gap: 10px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .reveal-on-scroll {
    opacity: 1;
    transform: none;
    transition: none;
  }

  .hero-crayon::after {
    animation: none;
    opacity: 1;
    transform: scaleX(1) rotate(-1.5deg);
  }

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
