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
        <div class="mascot-stage product-showcase" aria-hidden="true">
          <div class="repair-prism">
            <span class="prism-mark">P</span>
            <i class="prism-ring ring-one" />
            <i class="prism-ring ring-two" />
          </div>
          <div class="risk-shards">
            <span />
            <span />
            <span />
          </div>
          <div class="delivery-trails">
            <span />
            <span />
            <span />
          </div>
          <div class="delivery-seal">
            <span>{{ copy.sealEyebrow }}</span>
            <strong>{{ copy.sealTitle }}</strong>
            <i />
          </div>
          <div class="sentence-conveyor">
            <span class="conveyor-risk">{{ copy.conveyorRisk }}</span>
            <b />
            <span class="conveyor-ready">{{ copy.conveyorReady }}</span>
          </div>
          <div class="editor-window">
            <div class="editor-topbar">
              <span />
              <span />
              <span />
              <strong>PataFix Live Editor</strong>
            </div>
            <div class="editor-body">
              <aside class="paper-outline">
                <b>01</b>
                <span class="active" />
                <span />
                <span />
                <b>02</b>
                <span />
                <span />
              </aside>
              <main class="paper-sheet">
                <div class="paper-title" />
                <p>
                  <span />
                  <mark class="risk-word" />
                  <span class="short" />
                </p>
                <p>
                  <span class="wide" />
                  <mark class="risk-line" />
                </p>
                <p>
                  <span />
                  <mark class="fix-word" />
                  <span class="medium" />
                </p>
                <p>
                  <span class="wide" />
                  <span class="short" />
                </p>
                <div class="rewrite-arrow" />
                <div class="clean-paragraph">
                  <span />
                  <mark />
                  <span class="medium" />
                </div>
              </main>
              <aside class="rewrite-inspector">
                <div class="score-card danger">
                  <span>AIGC</span>
                  <strong>32% → 9%</strong>
                </div>
                <div class="score-card safe">
                  <span>{{ copy.similarityMetric }}</span>
                  <strong>18% → 6%</strong>
                </div>
                <div class="suggestion-card">
                  <b>{{ copy.templateTag }}</b>
                  <span class="danger-chip" />
                  <span />
                  <span class="safe-chip" />
                </div>
              </aside>
            </div>
          </div>
          <div class="floating-proof proof-one">
            <span />
            <strong>{{ copy.templateTag }}</strong>
          </div>
          <div class="floating-proof proof-two">
            <span />
            <strong>{{ copy.formatTag }}</strong>
          </div>
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
    sealEyebrow: 'PataFix 校准',
    sealTitle: '定稿',
    conveyorRisk: '风险句',
    conveyorReady: '可交付句',
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
    sealEyebrow: 'PataFix calibrated',
    sealTitle: 'READY',
    conveyorRisk: 'Risk text',
    conveyorReady: 'Ready line',
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
  display: flex;
  flex-direction: column;
  justify-content: center;
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
  min-height: 560px;
  border-radius: 26px;
  overflow: hidden;
  background:
    radial-gradient(circle at 72% 16%, rgba(255, 138, 89, 0.22), transparent 30%),
    radial-gradient(circle at 20% 72%, rgba(126, 213, 203, 0.14), transparent 30%),
    linear-gradient(rgba(255, 255, 255, 0.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.035) 1px, transparent 1px),
    linear-gradient(145deg, #1b1d22 0%, #111318 52%, #090a0d 100%);
  background-size: 100% 100%, 100% 100%, 36px 36px, 36px 36px, 100% 100%;
}

.hero-board::before,
.hero-board::after {
  content: "";
  position: absolute;
  pointer-events: none;
}

.hero-board::before {
  z-index: 0;
  width: 260px;
  height: 260px;
  right: -118px;
  top: -98px;
  border-radius: 50%;
  background: rgba(255, 138, 89, 0.16);
  filter: blur(4px);
}

.hero-board::after {
  z-index: 0;
  width: 240px;
  height: 150px;
  left: -88px;
  bottom: 60px;
  border-radius: 50%;
  background: rgba(117, 205, 218, 0.12);
  filter: blur(2px);
}

.mascot-stage {
  position: absolute;
  z-index: 1;
  inset: 18px 20px 92px;
  border-radius: 30px;
  overflow: hidden;
  background: transparent;
  filter: drop-shadow(0 28px 42px rgba(0, 0, 0, 0.32));
}

.mascot-stage::before {
  content: none;
}

.mascot-stage::after {
  content: none;
}

.hero-scene-image {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
  object-position: center;
  transform: rotate(-1.8deg) scale(0.98);
  transition:
    transform 0.9s cubic-bezier(0.2, 0.82, 0.2, 1),
    filter 0.9s ease;
}

.hero-board:hover .hero-scene-image {
  transform: rotate(-0.8deg) scale(1.01);
  filter: saturate(1.06) contrast(1.02);
}

.product-showcase {
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(circle at 18% 14%, rgba(255, 209, 102, 0.18), transparent 30%),
    radial-gradient(circle at 82% 78%, rgba(110, 197, 181, 0.2), transparent 32%),
    linear-gradient(rgba(255, 255, 255, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.045) 1px, transparent 1px),
    linear-gradient(145deg, rgba(24, 27, 31, 0.92), rgba(9, 11, 14, 0.96));
  background-size: 100% 100%, 100% 100%, 26px 26px, 26px 26px, 100% 100%;
}

.product-showcase::before {
  content: "";
  position: absolute;
  left: 34px;
  right: 34px;
  top: 44%;
  height: 2px;
  border-radius: 999px;
  background: linear-gradient(90deg, transparent, rgba(255, 107, 91, 0.78), rgba(255, 209, 102, 0.6), rgba(83, 209, 184, 0.8), transparent);
  box-shadow:
    0 0 18px rgba(255, 209, 102, 0.28),
    0 0 28px rgba(83, 209, 184, 0.18);
  animation: repairScan 3.8s ease-in-out infinite;
}

.product-showcase::after {
  content: "";
  position: absolute;
  inset: 28px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 24px;
  pointer-events: none;
}

.repair-prism {
  position: absolute;
  z-index: 1;
  left: 50%;
  top: 46%;
  width: 150px;
  height: 150px;
  border-radius: 38% 62% 48% 52%;
  background:
    radial-gradient(circle at 32% 24%, rgba(255, 255, 255, 0.74), transparent 18%),
    conic-gradient(from 210deg, rgba(255, 117, 104, 0.72), rgba(255, 209, 102, 0.6), rgba(83, 209, 184, 0.72), rgba(122, 167, 255, 0.58), rgba(255, 117, 104, 0.72));
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.18),
    0 0 34px rgba(83, 209, 184, 0.28),
    0 0 62px rgba(255, 117, 104, 0.2);
  opacity: 0.72;
  transform: translate(-50%, -50%) rotate(-14deg);
  animation: prismPulse 5.8s ease-in-out infinite;
}

.prism-mark {
  position: absolute;
  inset: 24px;
  display: grid;
  place-items: center;
  border-radius: 34% 66% 44% 56%;
  color: rgba(12, 16, 18, 0.78);
  background: rgba(255, 253, 247, 0.9);
  font-size: 52px;
  font-weight: 950;
  line-height: 1;
}

.prism-ring {
  position: absolute;
  inset: -18px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 44% 56% 47% 53%;
  transform: rotate(18deg);
}

.ring-two {
  inset: -34px;
  border-color: rgba(83, 209, 184, 0.18);
  transform: rotate(-22deg);
}

.risk-shards,
.delivery-trails {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
}

.risk-shards span,
.delivery-trails span {
  position: absolute;
  display: block;
  border-radius: 999px;
}

.risk-shards span {
  height: 9px;
  background: linear-gradient(90deg, #ff7568, #ffb36b);
  box-shadow: 0 0 18px rgba(255, 117, 104, 0.28);
  animation: shardIn 4.4s ease-in-out infinite;
}

.risk-shards span:nth-child(1) {
  left: 28px;
  top: 106px;
  width: 94px;
  --r: -15deg;
  transform: rotate(var(--r));
}

.risk-shards span:nth-child(2) {
  left: 40px;
  top: 174px;
  width: 66px;
  animation-delay: 0.35s;
}

.risk-shards span:nth-child(3) {
  left: 76px;
  bottom: 116px;
  width: 86px;
  --r: 12deg;
  transform: rotate(var(--r));
  animation-delay: 0.7s;
}

.delivery-trails span {
  right: 30px;
  height: 8px;
  background: linear-gradient(90deg, #53d1b8, #a7d8ff);
  box-shadow: 0 0 18px rgba(83, 209, 184, 0.3);
  animation: trailOut 4.4s ease-in-out infinite;
}

.delivery-trails span:nth-child(1) {
  top: 112px;
  width: 104px;
}

.delivery-trails span:nth-child(2) {
  top: 204px;
  width: 72px;
  animation-delay: 0.4s;
}

.delivery-trails span:nth-child(3) {
  bottom: 126px;
  width: 96px;
  animation-delay: 0.8s;
}

.delivery-seal {
  position: absolute;
  z-index: 5;
  right: 22px;
  top: 24px;
  width: 96px;
  height: 96px;
  display: grid;
  place-items: center;
  padding: 18px;
  border: 2px solid rgba(255, 209, 102, 0.74);
  border-radius: 50%;
  color: #fff5d7;
  background:
    radial-gradient(circle at 50% 50%, rgba(255, 209, 102, 0.18), transparent 56%),
    rgba(12, 15, 17, 0.58);
  box-shadow:
    inset 0 0 0 7px rgba(255, 209, 102, 0.08),
    0 0 0 1px rgba(255, 255, 255, 0.12),
    0 18px 34px rgba(0, 0, 0, 0.28),
    0 0 30px rgba(255, 209, 102, 0.22);
  text-align: center;
  transform: rotate(10deg);
  animation: sealLand 4.8s cubic-bezier(0.2, 0.82, 0.2, 1) infinite;
}

.delivery-seal span {
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.delivery-seal strong {
  color: #fff9e8;
  font-size: 25px;
  line-height: 1;
  letter-spacing: 0;
}

.delivery-seal i {
  width: 54px;
  height: 10px;
  border-radius: 999px;
  background: linear-gradient(90deg, #ff7568, #ffd166, #53d1b8);
}

.sentence-conveyor {
  position: absolute;
  z-index: 4;
  left: 34px;
  right: 34px;
  bottom: 62px;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid rgba(255, 255, 255, 0.13);
  border-radius: 999px;
  color: #fffaf0;
  background: rgba(9, 11, 14, 0.64);
  backdrop-filter: blur(14px);
  box-shadow: 0 18px 34px rgba(0, 0, 0, 0.24);
}

.sentence-conveyor span {
  padding: 6px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 900;
  white-space: nowrap;
}

.conveyor-risk {
  color: #ffe8e4;
  background: rgba(255, 117, 104, 0.28);
}

.conveyor-ready {
  color: #e8fff9;
  background: rgba(83, 209, 184, 0.24);
}

.sentence-conveyor b {
  position: relative;
  height: 4px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
}

.sentence-conveyor b::before {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(90deg, #ff7568, #ffd166, #53d1b8);
  transform: translateX(-72%);
  animation: conveyorFlow 3.2s ease-in-out infinite;
}

.editor-window {
  position: relative;
  z-index: 3;
  width: min(100%, 355px);
  min-height: 345px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 22px;
  overflow: hidden;
  background: rgba(252, 250, 244, 0.96);
  box-shadow:
    0 28px 60px rgba(0, 0, 0, 0.32),
    0 0 0 10px rgba(255, 255, 255, 0.035);
  transform: rotate(-2.2deg) translateY(4px);
  transition:
    transform 0.5s ease,
    box-shadow 0.5s ease;
}

.hero-board:hover .editor-window {
  transform: rotate(-1deg) translateY(-4px);
  box-shadow:
    0 34px 70px rgba(0, 0, 0, 0.38),
    0 0 0 10px rgba(255, 255, 255, 0.052);
}

.editor-topbar {
  height: 42px;
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 0 15px;
  color: rgba(255, 255, 255, 0.74);
  background: linear-gradient(90deg, #23262d, #15181d);
  font-size: 12px;
}

.editor-topbar span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ff6b5b;
}

.editor-topbar span:nth-child(2) {
  background: #ffd166;
}

.editor-topbar span:nth-child(3) {
  background: #53d1b8;
}

.editor-topbar strong {
  margin-left: 5px;
  font-weight: 800;
  letter-spacing: 0;
}

.editor-body {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr) 92px;
  gap: 12px;
  padding: 14px;
}

.paper-outline,
.rewrite-inspector {
  min-width: 0;
}

.paper-outline {
  display: grid;
  align-content: start;
  gap: 8px;
  padding-top: 4px;
}

.paper-outline b {
  color: #a17a3d;
  font-size: 11px;
  font-weight: 900;
}

.paper-outline span {
  height: 8px;
  border-radius: 999px;
  background: #ded8ca;
}

.paper-outline span.active {
  background: #ff806f;
  box-shadow: 0 0 0 4px rgba(255, 128, 111, 0.12);
}

.paper-sheet {
  position: relative;
  min-height: 270px;
  padding: 18px 16px 20px;
  border: 1px solid rgba(35, 43, 38, 0.1);
  border-radius: 14px;
  background:
    linear-gradient(90deg, rgba(47, 111, 83, 0.05) 1px, transparent 1px),
    linear-gradient(#fffefa, #faf6eb);
  background-size: 16px 100%, 100% 100%;
  box-shadow: inset 0 -12px 24px rgba(47, 67, 58, 0.035);
}

.paper-title {
  width: 68%;
  height: 13px;
  margin-bottom: 18px;
  border-radius: 999px;
  background: #2d3831;
}

.paper-sheet p,
.clean-paragraph {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0 0 12px;
}

.paper-sheet p span,
.clean-paragraph span,
.suggestion-card > span {
  height: 8px;
  border-radius: 999px;
  background: #d8d2c4;
}

.paper-sheet p span {
  width: 54px;
}

.paper-sheet p span.short {
  width: 32px;
}

.paper-sheet p span.medium {
  width: 48px;
}

.paper-sheet p span.wide {
  width: 96px;
}

.paper-sheet mark,
.clean-paragraph mark {
  height: 8px;
  border-radius: 999px;
}

.risk-word {
  width: 58px;
  background: #ff7568;
  box-shadow: 0 0 0 5px rgba(255, 117, 104, 0.16);
}

.risk-line {
  width: 112px;
  background: linear-gradient(90deg, #ff7568, #ffb36b);
  box-shadow: 0 0 0 5px rgba(255, 117, 104, 0.14);
}

.fix-word {
  width: 74px;
  background: #53b98d;
  box-shadow: 0 0 0 5px rgba(83, 185, 141, 0.14);
}

.rewrite-arrow {
  width: 112px;
  height: 28px;
  margin: 16px auto 12px;
  border-radius: 999px;
  background:
    radial-gradient(circle at 84% 50%, #fffefa 0 4px, transparent 5px),
    linear-gradient(90deg, rgba(255, 117, 104, 0.1), rgba(83, 209, 184, 0.34));
  position: relative;
}

.rewrite-arrow::before,
.rewrite-arrow::after {
  content: "";
  position: absolute;
  top: 50%;
  background: #2f6f53;
  transform: translateY(-50%);
}

.rewrite-arrow::before {
  left: 22px;
  width: 58px;
  height: 3px;
  border-radius: 999px;
}

.rewrite-arrow::after {
  right: 24px;
  width: 11px;
  height: 11px;
  clip-path: polygon(0 0, 100% 50%, 0 100%);
}

.clean-paragraph {
  padding: 12px;
  border-radius: 12px;
  background: rgba(83, 209, 184, 0.1);
}

.clean-paragraph span {
  width: 58px;
  background: rgba(47, 111, 83, 0.26);
}

.clean-paragraph span.medium {
  width: 76px;
}

.clean-paragraph mark {
  width: 68px;
  background: #53b98d;
}

.rewrite-inspector {
  display: grid;
  align-content: start;
  gap: 10px;
}

.score-card,
.suggestion-card {
  border-radius: 12px;
  border: 1px solid rgba(44, 53, 48, 0.08);
  background: #fffdf7;
  box-shadow: 0 10px 20px rgba(46, 56, 48, 0.08);
}

.score-card {
  display: grid;
  gap: 3px;
  padding: 11px;
}

.score-card span {
  color: #4f5a53;
  font-size: 11px;
  font-weight: 900;
}

.score-card strong {
  color: #17221c;
  font-size: 13px;
  letter-spacing: 0;
}

.score-card.danger {
  background: #fff0ec;
  box-shadow: inset 4px 0 0 rgba(255, 117, 104, 0.72), 0 10px 20px rgba(46, 56, 48, 0.08);
}

.score-card.safe {
  background: #e8f8f2;
  box-shadow: inset 4px 0 0 rgba(83, 185, 141, 0.72), 0 10px 20px rgba(46, 56, 48, 0.08);
}

.suggestion-card {
  display: grid;
  gap: 8px;
  padding: 12px;
}

.suggestion-card b {
  color: #2d3831;
  font-size: 12px;
}

.suggestion-card > span {
  width: 100%;
}

.suggestion-card .danger-chip {
  background: #ff7568;
}

.suggestion-card .safe-chip {
  background: #53b98d;
}

.floating-proof {
  position: absolute;
  z-index: 3;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 999px;
  color: #fffaf0;
  background: rgba(14, 17, 20, 0.62);
  backdrop-filter: blur(14px);
  box-shadow: 0 16px 28px rgba(0, 0, 0, 0.22);
  font-size: 12px;
  font-weight: 900;
  animation: proofFloat 4.6s ease-in-out infinite;
}

.floating-proof span {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.proof-one {
  left: 18px;
  top: 26px;
}

.proof-one span {
  background: #ff7568;
}

.proof-two {
  right: 18px;
  bottom: 34px;
  animation-delay: 0.55s;
}

.proof-two span {
  background: #53d1b8;
}

.scene-glow {
  position: absolute;
  z-index: 2;
  left: 16px;
  bottom: 18px;
  width: 48%;
  height: 38%;
  border-radius: 50%;
  background: rgba(255, 196, 113, 0.22);
  filter: blur(34px);
  pointer-events: none;
}

.scene-metric,
.scene-pill {
  position: absolute;
  z-index: 3;
  border: 1px solid rgba(255, 255, 255, 0.28);
  color: #fffaf0;
  backdrop-filter: blur(16px);
  box-shadow: 0 18px 36px rgba(6, 10, 15, 0.24);
}

.scene-metric {
  display: grid;
  gap: 3px;
  min-width: 118px;
  padding: 11px 13px;
  border-radius: 16px;
  background: rgba(19, 24, 27, 0.58);
}

.scene-metric span,
.scene-pill span {
  color: rgba(255, 250, 240, 0.72);
  font-size: 12px;
  font-weight: 800;
}

.scene-metric strong {
  font-size: 17px;
  letter-spacing: 0;
}

.scene-metric.risk {
  left: 18px;
  top: 18px;
}

.scene-metric.risk strong {
  color: #ffb1a5;
}

.scene-metric.clean {
  right: 18px;
  bottom: 18px;
}

.scene-metric.clean strong {
  color: #a9e3d1;
}

.scene-pill {
  left: 18px;
  bottom: 18px;
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: 190px;
  padding: 9px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.13);
}

.scene-pill b {
  color: #ffd166;
  font-size: 12px;
  white-space: nowrap;
}

.paper-sparks span,
.scribble-line span {
  position: absolute;
  display: block;
}

.spark {
  width: 15px;
  height: 15px;
  background: #ffd166;
  clip-path: polygon(50% 0, 62% 34%, 100% 50%, 62% 64%, 50% 100%, 36% 64%, 0 50%, 36% 34%);
  filter: drop-shadow(0 6px 8px rgba(180, 116, 54, 0.18));
  animation: sparkTwinkle 3.4s ease-in-out infinite;
}

.spark-one {
  left: 56px;
  top: 38px;
}

.spark-two {
  right: 78px;
  top: 34px;
  width: 12px;
  height: 12px;
  background: #ff8b78;
  animation-delay: 0.35s;
}

.spark-three {
  left: 78px;
  bottom: 72px;
  width: 11px;
  height: 11px;
  background: #69b6d9;
  animation-delay: 0.7s;
}

.scribble-line {
  position: absolute;
  inset: 0;
}

.scribble-line span {
  height: 9px;
  border-radius: 999px;
  opacity: 0.74;
  transform-origin: left center;
}

.scribble-line span:nth-child(1) {
  left: 36px;
  top: 72px;
  width: 118px;
  background: #ff8b78;
  clip-path: polygon(0 34%, 10% 20%, 18% 48%, 30% 28%, 44% 53%, 56% 28%, 72% 48%, 84% 26%, 100% 42%, 100% 86%, 86% 72%, 74% 91%, 60% 72%, 44% 92%, 30% 70%, 18% 88%, 0 70%);
  transform: rotate(-8deg);
  animation: scribbleDraw 4.6s ease-in-out infinite;
}

.scribble-line span:nth-child(2) {
  right: 44px;
  top: 94px;
  width: 92px;
  background: #76c6e8;
  transform: rotate(9deg);
  animation: scribbleDraw 4.8s 0.4s ease-in-out infinite;
}

.scribble-line span:nth-child(3) {
  right: 74px;
  bottom: 66px;
  width: 116px;
  background: #ffd166;
  transform: rotate(-5deg);
  animation: scribbleDraw 5s 0.8s ease-in-out infinite;
}

.sticky-note {
  position: absolute;
  z-index: 2;
  width: 126px;
  padding: 14px 13px 12px;
  border: 2px solid rgba(38, 56, 47, 0.08);
  border-radius: 16px 18px 14px 18px;
  box-shadow: 0 18px 30px rgba(46, 56, 48, 0.11);
  display: grid;
  gap: 8px;
}

.sticky-note strong {
  color: #2d352f;
  font-size: 13px;
}

.note-pin {
  position: absolute;
  top: -8px;
  left: 50%;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #ff8b78;
  box-shadow: inset -3px -3px 0 rgba(98, 48, 35, 0.12);
  transform: translateX(-50%);
}

.note-row {
  height: 7px;
  border-radius: 999px;
  background: rgba(63, 71, 65, 0.17);
}

.note-row.long {
  width: 100%;
}

.note-row.medium {
  width: 78%;
}

.note-row.short {
  width: 58%;
}

.note-row.danger {
  width: 84%;
  background: #d95b51;
  box-shadow: 0 0 0 4px rgba(217, 91, 81, 0.12);
}

.note-row.safe {
  width: 88%;
  background: #3b8f6b;
  box-shadow: 0 0 0 4px rgba(59, 143, 107, 0.12);
}

.note-risk {
  left: 18px;
  top: 78px;
  background: #fff0dc;
  transform: rotate(-8deg);
  animation: noteFloatA 5.4s ease-in-out infinite;
}

.note-clean {
  right: 18px;
  top: 74px;
  background: #e8f8f4;
  transform: rotate(7deg);
  animation: noteFloatB 5.8s ease-in-out infinite;
}

.pata-buddy {
  position: absolute;
  z-index: 4;
  left: 50%;
  top: 54%;
  width: 174px;
  height: 206px;
  --buddy-scale: 1;
  transform: translate(-50%, -50%);
  animation: buddyFloat 4.4s ease-in-out infinite;
}

.buddy-tail {
  position: absolute;
  right: -10px;
  bottom: 38px;
  width: 52px;
  height: 74px;
  border: 4px solid #26382f;
  border-left: 0;
  border-radius: 20px 46px 46px 20px;
  background:
    radial-gradient(circle at 68% 28%, #fff6e8 0 16px, transparent 17px),
    linear-gradient(145deg, #ffa07e, #f06f63);
  transform: rotate(18deg);
}

.buddy-ear {
  position: absolute;
  z-index: 2;
  top: 3px;
  width: 48px;
  height: 54px;
  border: 4px solid #26382f;
  border-radius: 16px 16px 10px 28px;
  background: #ffa07e;
}

.buddy-ear::after {
  content: "";
  position: absolute;
  inset: 12px 12px 10px;
  border-radius: inherit;
  background: #ffe1d6;
}

.buddy-ear.left {
  left: 24px;
  transform: rotate(-22deg);
}

.buddy-ear.right {
  right: 24px;
  border-radius: 16px 16px 28px 10px;
  transform: rotate(22deg);
}

.buddy-face {
  position: absolute;
  z-index: 3;
  left: 15px;
  right: 15px;
  top: 26px;
  height: 112px;
  border: 4px solid #26382f;
  border-radius: 56px 56px 48px 48px;
  background:
    radial-gradient(circle at 50% 70%, #fff9ed 0 32%, transparent 33%),
    radial-gradient(circle at 30% 28%, rgba(255, 255, 255, 0.76), transparent 18%),
    linear-gradient(145deg, #ffb08d, #ff806f);
  box-shadow: inset 0 -8px 0 rgba(114, 54, 44, 0.08), 0 18px 30px rgba(46, 56, 48, 0.14);
}

.buddy-eye {
  position: absolute;
  top: 43px;
  width: 12px;
  height: 15px;
  border-radius: 50%;
  background: #26382f;
  animation: eyeBlink 5.4s ease-in-out infinite;
}

.buddy-eye.left {
  left: 45px;
}

.buddy-eye.right {
  right: 45px;
}

.buddy-cheek {
  position: absolute;
  top: 68px;
  width: 22px;
  height: 10px;
  border-radius: 999px;
  background: rgba(255, 114, 116, 0.28);
}

.buddy-cheek.left {
  left: 26px;
}

.buddy-cheek.right {
  right: 26px;
}

.buddy-nose {
  position: absolute;
  left: 50%;
  top: 58px;
  width: 13px;
  height: 10px;
  border-radius: 50% 50% 58% 58%;
  background: #26382f;
  transform: translateX(-50%);
}

.buddy-mouth {
  position: absolute;
  left: 50%;
  top: 70px;
  width: 34px;
  height: 15px;
  border-bottom: 3px solid #26382f;
  border-radius: 0 0 999px 999px;
  transform: translateX(-50%);
}

.buddy-body {
  position: absolute;
  z-index: 2;
  left: 35px;
  right: 35px;
  top: 122px;
  height: 70px;
  border: 4px solid #26382f;
  border-radius: 34px 34px 42px 42px;
  background: linear-gradient(145deg, #fff6e8, #f0fbf8);
  box-shadow: 0 18px 28px rgba(46, 56, 48, 0.13);
}

.buddy-scarf {
  position: absolute;
  left: 18px;
  right: 18px;
  top: -8px;
  height: 18px;
  border-radius: 999px;
  background: #76c6e8;
  box-shadow: inset -10px -4px 0 rgba(35, 83, 118, 0.12);
}

.hugged-paper {
  position: absolute;
  left: 19px;
  top: 12px;
  width: 72px;
  height: 88px;
  padding: 12px 10px;
  border: 3px solid #26382f;
  border-radius: 10px 14px 12px 10px;
  background: #fffefa;
  display: grid;
  align-content: start;
  gap: 6px;
  transform: rotate(-4deg);
  box-shadow: 0 12px 18px rgba(46, 56, 48, 0.12);
}

.paper-badge {
  position: absolute;
  right: -12px;
  top: -14px;
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border: 3px solid #26382f;
  border-radius: 50%;
  background: #ffd166;
  color: #26382f;
  font-weight: 900;
}

.paper-line {
  height: 6px;
  border-radius: 999px;
  background: #d8d4ca;
}

.paper-line.title {
  width: 80%;
  height: 9px;
  background: #3f4741;
}

.paper-line.risk {
  width: 88%;
  background: #d95b51;
}

.paper-line.safe {
  width: 70%;
  background: #3b8f6b;
}

.buddy-arm {
  position: absolute;
  z-index: 3;
  top: 18px;
  width: 48px;
  height: 17px;
  border: 4px solid #26382f;
  border-radius: 999px;
  background: #ff9c7c;
}

.buddy-arm.left {
  left: -33px;
  transform: rotate(25deg);
}

.buddy-arm.right {
  right: -36px;
  transform: rotate(-22deg);
}

.pencil-wand {
  position: absolute;
  z-index: 5;
  right: -46px;
  top: -2px;
  width: 78px;
  height: 13px;
  border: 3px solid #26382f;
  border-radius: 999px;
  background: linear-gradient(90deg, #ffd166 0 68%, #fff6e8 68% 82%, #ff806f 82%);
  transform: rotate(-28deg);
  transform-origin: 14px 50%;
  animation: pencilWiggle 3.6s ease-in-out infinite;
}

.pencil-wand i {
  position: absolute;
  right: -13px;
  top: -3px;
  width: 16px;
  height: 16px;
  background: #26382f;
  clip-path: polygon(0 0, 100% 50%, 0 100%);
}

.buddy-shadow {
  position: absolute;
  left: 16px;
  right: 16px;
  bottom: 0;
  height: 23px;
  border-radius: 50%;
  background: rgba(31, 42, 36, 0.16);
  filter: blur(4px);
  animation: shadowPulse 4.4s ease-in-out infinite;
}

.rewrite-ribbon {
  position: absolute;
  z-index: 1;
  left: 58px;
  right: 54px;
  bottom: 55px;
  height: 18px;
  border-radius: 999px;
  background:
    repeating-linear-gradient(-8deg, rgba(255, 255, 255, 0.28) 0 10px, transparent 10px 20px),
    linear-gradient(90deg, #ff8b78, #ffd166 48%, #76c6e8);
  clip-path: polygon(0 45%, 10% 22%, 22% 52%, 34% 26%, 48% 54%, 61% 28%, 76% 52%, 88% 25%, 100% 45%, 100% 79%, 88% 65%, 76% 86%, 61% 66%, 48% 84%, 34% 66%, 22% 86%, 10% 66%, 0 80%);
  box-shadow: 0 12px 18px rgba(94, 72, 42, 0.12);
  animation: ribbonGlow 3.8s ease-in-out infinite;
}

.word-chip {
  position: absolute;
  z-index: 5;
  padding: 8px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  border: 1px solid rgba(47, 67, 58, 0.05);
  box-shadow: 0 12px 24px rgba(46, 56, 48, 0.11);
  animation: chipFloat 4.8s ease-in-out infinite;
}

.chip-risk {
  left: 34px;
  top: 32px;
  color: #8f332f;
  background: #f4d9d1;
}

.chip-fix {
  left: 145px;
  top: 24px;
  color: #5b3f13;
  background: #f4e3bf;
  animation-delay: 0.4s;
}

.chip-safe {
  right: 28px;
  bottom: 28px;
  color: #245642;
  background: #dce9dd;
  animation-delay: 0.8s;
}

.side-ticket {
  position: absolute;
  z-index: 2;
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

@keyframes buddyFloat {
  0%, 100% {
    transform: translate(-50%, -50%) scale(var(--buddy-scale, 1));
  }
  50% {
    transform: translate(-50%, calc(-50% - 12px)) scale(var(--buddy-scale, 1));
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

@keyframes sparkTwinkle {
  0%, 100% {
    opacity: 0.58;
    transform: scale(0.9) rotate(0deg);
  }
  50% {
    opacity: 1;
    transform: scale(1.18) rotate(18deg);
  }
}

@keyframes scribbleDraw {
  0%, 100% {
    opacity: 0.42;
    clip-path: inset(0 100% 0 0 round 999px);
  }
  50% {
    opacity: 0.86;
    clip-path: inset(0 0 0 0 round 999px);
  }
}

@keyframes noteFloatA {
  0%, 100% {
    transform: rotate(-8deg) translateY(0);
  }
  50% {
    transform: rotate(-5deg) translateY(-9px);
  }
}

@keyframes noteFloatB {
  0%, 100% {
    transform: rotate(7deg) translateY(0);
  }
  50% {
    transform: rotate(4deg) translateY(10px);
  }
}

@keyframes pencilWiggle {
  0%, 100% {
    transform: rotate(-28deg);
  }
  50% {
    transform: rotate(-20deg) translateX(3px);
  }
}

@keyframes ribbonGlow {
  0%, 100% {
    filter: saturate(0.92);
    transform: translateY(0);
  }
  50% {
    filter: saturate(1.16);
    transform: translateY(-3px);
  }
}

@keyframes repairScan {
  0%, 100% {
    opacity: 0.46;
    transform: translateY(-78px) scaleX(0.72);
  }
  50% {
    opacity: 1;
    transform: translateY(78px) scaleX(1);
  }
}

@keyframes proofFloat {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-7px);
  }
}

@keyframes prismPulse {
  0%, 100% {
    opacity: 0.62;
    transform: translate(-50%, -50%) rotate(-14deg) scale(0.96);
  }
  50% {
    opacity: 0.86;
    transform: translate(-50%, -50%) rotate(-8deg) scale(1.04);
  }
}

@keyframes shardIn {
  0%, 100% {
    opacity: 0.26;
    transform: translateX(-10px) rotate(var(--r, 0deg));
  }
  50% {
    opacity: 0.88;
    transform: translateX(18px) rotate(var(--r, 0deg));
  }
}

@keyframes trailOut {
  0%, 100% {
    opacity: 0.24;
    transform: translateX(10px);
  }
  50% {
    opacity: 0.9;
    transform: translateX(-18px);
  }
}

@keyframes sealLand {
  0%, 100% {
    opacity: 0.88;
    transform: rotate(10deg) scale(0.98);
  }
  42% {
    opacity: 1;
    transform: rotate(6deg) scale(1.06);
  }
  52% {
    transform: rotate(8deg) scale(0.96);
    box-shadow:
      inset 0 0 0 7px rgba(255, 209, 102, 0.08),
      0 0 0 1px rgba(255, 255, 255, 0.12),
      0 14px 26px rgba(0, 0, 0, 0.22),
      0 0 42px rgba(255, 209, 102, 0.36);
  }
}

@keyframes conveyorFlow {
  0%, 100% {
    transform: translateX(-74%);
  }
  50% {
    transform: translateX(74%);
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
    radial-gradient(circle at 51% 47%, rgba(138, 180, 255, 0.13), transparent 42%),
    radial-gradient(circle at 50% 92%, rgba(255, 209, 102, 0.13), transparent 34%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.055), rgba(255, 255, 255, 0.02));
}

:global(html[data-theme='dark']) .product-showcase {
  background:
    radial-gradient(circle at 18% 14%, rgba(255, 209, 102, 0.16), transparent 30%),
    radial-gradient(circle at 82% 78%, rgba(110, 197, 181, 0.18), transparent 32%),
    linear-gradient(rgba(255, 255, 255, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.045) 1px, transparent 1px),
    linear-gradient(145deg, rgba(24, 27, 31, 0.92), rgba(9, 11, 14, 0.96));
  background-size: 100% 100%, 100% 100%, 26px 26px, 26px 26px, 100% 100%;
}

:global(html[data-theme='dark']) .editor-window {
  background: rgba(250, 247, 238, 0.98);
  box-shadow:
    0 32px 78px rgba(0, 0, 0, 0.52),
    0 0 0 10px rgba(255, 255, 255, 0.045);
}

:global(html[data-theme='dark']) .paper-sheet {
  background:
    linear-gradient(90deg, rgba(47, 111, 83, 0.06) 1px, transparent 1px),
    linear-gradient(#fffefa, #fbf6ec);
  color: #1b221d;
}

:global(html[data-theme='dark']) .score-card span,
:global(html[data-theme='dark']) .suggestion-card b {
  color: #334139;
}

:global(html[data-theme='dark']) .score-card strong {
  color: #101812;
}

:global(html[data-theme='dark']) .score-card.danger {
  background: #fff0ec;
}

:global(html[data-theme='dark']) .score-card.safe {
  background: #e8f8f2;
}

:global(html[data-theme='dark']) .floating-proof,
:global(html[data-theme='dark']) .side-ticket {
  background: rgba(17, 22, 22, 0.88);
  color: #fffaf0;
}

:global(html[data-theme='dark']) .mascot-stage::after {
  border-color: rgba(232, 235, 245, 0.1);
}

:global(html[data-theme='dark']) .sticky-note {
  border-color: rgba(232, 235, 245, 0.13);
  box-shadow: 0 18px 34px rgba(0, 0, 0, 0.3);
}

:global(html[data-theme='dark']) .sticky-note strong {
  color: #f4f1eb;
}

:global(html[data-theme='dark']) .note-risk {
  background: rgba(96, 45, 42, 0.82);
}

:global(html[data-theme='dark']) .note-clean {
  background: rgba(32, 74, 78, 0.82);
}

:global(html[data-theme='dark']) .note-row {
  background: rgba(244, 241, 235, 0.22);
}

:global(html[data-theme='dark']) .buddy-face,
:global(html[data-theme='dark']) .buddy-body,
:global(html[data-theme='dark']) .hugged-paper,
:global(html[data-theme='dark']) .paper-badge,
:global(html[data-theme='dark']) .buddy-ear,
:global(html[data-theme='dark']) .buddy-tail,
:global(html[data-theme='dark']) .buddy-arm,
:global(html[data-theme='dark']) .pencil-wand {
  border-color: #11131a;
}

:global(html[data-theme='dark']) .buddy-body {
  background: linear-gradient(145deg, #f8efe3, #dff7fb);
}

:global(html[data-theme='dark']) .word-chip {
  border-color: rgba(232, 235, 245, 0.12);
  box-shadow: 0 14px 30px rgba(0, 0, 0, 0.28);
}

@media (max-width: 980px) {
  .home-hero,
  .home-grid,
  .quick-tool,
  .rewrite-compare {
    grid-template-columns: 1fr;
  }

  .hero-board {
    min-height: 540px;
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
    min-height: 520px;
  }

  .mascot-stage {
    inset: 14px 14px 92px;
  }

  .product-showcase {
    padding: 18px;
  }

  .editor-window {
    width: min(100%, 330px);
  }

  .editor-body {
    grid-template-columns: 42px minmax(0, 1fr) 76px;
    gap: 9px;
    padding: 11px;
  }

  .paper-sheet {
    padding: 14px 12px 16px;
  }

  .floating-proof {
    padding: 8px 10px;
    font-size: 11px;
  }

  .pata-buddy {
    top: 56%;
    --buddy-scale: 0.82;
  }

  .sticky-note {
    width: 104px;
    padding: 12px 11px 10px;
  }

  .note-risk {
    left: 8px;
    top: 82px;
  }

  .note-clean {
    right: 8px;
    top: 68px;
  }

  .rewrite-ribbon {
    left: 34px;
    right: 34px;
    bottom: 48px;
  }

  .chip-risk {
    left: 18px;
    top: 26px;
  }

  .chip-fix {
    left: 108px;
    top: 20px;
  }

  .chip-safe {
    right: 16px;
    bottom: 24px;
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
  .pata-buddy,
  .buddy-eye,
  .buddy-shadow,
  .spark,
  .scribble-line span,
  .sticky-note,
  .pencil-wand,
  .rewrite-ribbon,
  .product-showcase::before,
  .repair-prism,
  .risk-shards span,
  .delivery-trails span,
  .floating-proof,
  .word-chip {
    animation: none;
  }
}
</style>
