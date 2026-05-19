<template>
  <div class="landing">
    <section class="hero">
      <div class="hero-content">
        <span class="hero-badge">论文提交前的最后一道防线</span>
        <h1>PataFix论文检测</h1>
        <p class="hero-desc">
          在正式送检知网之前，用本地分析快速定位高风险段落，给出修改优先级。
          回填真实知网结果后系统持续校准，让预测越来越准。
        </p>
        <div class="hero-actions">
          <router-link to="/register" class="btn btn-primary btn-lg">免费注册，开始预检</router-link>
          <router-link to="/login" class="btn btn-outline btn-lg">已有账号，去登录</router-link>
        </div>
      </div>
    </section>

    <section class="quick-rewrite" id="quick-rewrite">
      <div class="quick-shell">
        <div class="quick-head">
          <span class="hero-badge">首页体验入口</span>
          <h2>短句风险优化</h2>
          <p>粘贴一段论文内容，快速查看 AIGC 疑似风险，并生成更自然的改写版本。</p>
        </div>

        <div class="quick-tool">
          <div class="quick-input-column">
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

            <label class="quick-label" for="quick-rewrite-input">
              输入论文段落
              <span>{{ quickInput.length }} 字</span>
            </label>
            <textarea
              id="quick-rewrite-input"
              v-model="quickInput"
              class="quick-textarea"
              rows="8"
              placeholder="请输入一段论文内容，建议 50～300 字"
            />

            <div class="quick-actions">
              <button
                type="button"
                class="btn btn-primary"
                :disabled="quickLoading || !quickInput.trim()"
                @click="handleQuickRewrite"
              >
                <Search class="button-icon" />
                {{ quickLoading ? '优化中...' : '检测并优化' }}
              </button>
              <button type="button" class="btn btn-outline" @click="fillExample">填入示例</button>
            </div>

            <p class="quick-limit">当前体验期不限次数、不限字数；建议先用 50～300 字短段查看标记和改写逻辑。</p>
            <div class="quick-input-tips">
              <strong>适合粘贴</strong>
              <p>摘要段落、绪论背景、研究意义、结论、系统介绍段落。</p>
              <p>建议输入 50-300 字，过短文本检测结果可能不稳定。</p>
            </div>
            <p v-if="quickError" class="quick-error">{{ quickError }}</p>
          </div>

          <div class="quick-output-column">
            <div v-if="!quickResult" class="quick-empty">
              <strong>检测结果会显示在这里</strong>
              <p>系统会标出风险短语、解释原因，并给出改写结果、修改对照和改写原理。</p>
            </div>

            <template v-else>
              <div class="risk-strip">
                <div>
                  <span>优化前风险指数</span>
                  <strong>{{ quickResult.beforeRisk.score }}</strong>
                </div>
                <div>
                  <span>优化后预估风险指数</span>
                  <strong>{{ afterRiskDisplay }}</strong>
                  <small>{{ afterRiskLevelLabel }}</small>
                </div>
              </div>
              <p class="quick-disclaimer">该结果为系统预估，不等同于知网检测结果。</p>
              <p class="quick-summary">{{ quickResult.summary }}</p>

              <div class="result-grid">
                <article class="result-panel">
                  <h3>原文风险标记</h3>
                  <p class="marked-text">
                    <template v-for="(seg, idx) in originalSegments" :key="`o-${idx}`">
                      <mark v-if="seg.mark" class="risk-mark" :title="seg.reason" :data-reason="seg.reason">{{ seg.text }}</mark>
                      <span v-else>{{ seg.text }}</span>
                    </template>
                  </p>
                  <ul class="reason-list-mini">
                    <li v-for="reason in riskReasons" :key="reason">{{ reason }}</li>
                  </ul>
                </article>

                <article class="result-panel">
                  <h3>改写结果</h3>
                  <p class="marked-text">
                    <template v-for="(seg, idx) in rewrittenSegments" :key="`r-${idx}`">
                      <mark v-if="seg.mark" class="improve-mark" :title="seg.reason" :data-reason="seg.reason">{{ seg.text }}</mark>
                      <span v-else>{{ seg.text }}</span>
                    </template>
                  </p>
                </article>

                <article class="result-panel">
                  <h3>修改对照</h3>
                  <div class="compare-list">
                    <div v-for="row in comparisonRows" :key="row.key" class="compare-card">
                      <div class="compare-phrase before">{{ row.before || '原句整体节奏' }}</div>
                      <div class="compare-arrow">→</div>
                      <div class="compare-phrase after">{{ row.after || '补充具体细节' }}</div>
                      <p>{{ row.reason }}</p>
                    </div>
                  </div>
                </article>

                <article class="result-panel">
                  <h3>改写原理</h3>
                  <ul class="principle-list">
                    <li v-for="item in quickResult.rewritePrinciples" :key="item">{{ item }}</li>
                  </ul>
                </article>
              </div>

              <div class="quick-result-actions">
                <button type="button" class="btn btn-primary" @click="copyRewritten">
                  <DocumentCopy class="button-icon" />
                  复制改写结果
                </button>
                <button type="button" class="btn btn-outline" :disabled="quickLoading" @click="handleQuickRewrite">
                  <Refresh class="button-icon" />
                  重新生成
                </button>
                <button type="button" class="btn btn-outline" @click="goUpload">
                  <Upload class="button-icon" />
                  上传全文检测
                </button>
              </div>
              <p class="quick-conversion">
                想定位整篇论文的高风险段落？上传全文后可查看完整风险分布、逐段改写建议和导出改写稿。
              </p>
            </template>
          </div>
        </div>
      </div>
    </section>

    <section class="features">
      <h2 class="section-title">为什么先预检再送检？</h2>
      <div class="feature-grid">
        <article class="feature-card">
          <div class="feature-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
          </div>
          <h3>详细分析报告</h3>
          <p>风险指数、章节热力图、逐段 AIGC 评分与重复检测，一次上传全部拿到。</p>
        </article>
        <article class="feature-card">
          <div class="feature-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
          </div>
          <h3>修改优先级排序</h3>
          <p>不是盲目全改，系统告诉你最该先改哪 3 个地方，省时省力。</p>
        </article>
        <article class="feature-card">
          <div class="feature-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
          </div>
          <h3>知网回填校准</h3>
          <p>拿到真实知网结果后回填进来，系统自动重训模型，预测精度持续提升。</p>
        </article>
        <article class="feature-card">
          <div class="feature-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
          </div>
          <h3>数据安全</h3>
          <p>论文内容只用于本次分析，不存储原文、不外传、不训练通用模型。</p>
        </article>
      </div>
    </section>

    <section class="how-it-works">
      <h2 class="section-title">三步完成预检</h2>
      <div class="steps">
        <div class="step">
          <span class="step-num">1</span>
          <h3>上传论文</h3>
          <p>支持 .docx、.pdf、.txt 等格式，最大 50MB</p>
        </div>
        <div class="step-arrow">→</div>
        <div class="step">
          <span class="step-num">2</span>
          <h3>等待分析</h3>
          <p>系统自动分段、评分、生成详细报告</p>
        </div>
        <div class="step-arrow">→</div>
        <div class="step">
          <span class="step-num">3</span>
          <h3>查看报告</h3>
          <p>风险指数 + 修改建议 + 导师沟通摘要</p>
        </div>
      </div>
    </section>

    <section class="cta-section">
      <h2>别等送检后才发现问题</h2>
      <p>提前预检，提前修改，省下一次正式送检的时间和费用。</p>
      <router-link to="/register" class="btn btn-primary btn-lg">立即开始</router-link>
    </section>

    <footer class="landing-footer">
      <p>PataFix论文检测 &copy; {{ new Date().getFullYear() }}</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus/es/components/message/index'
import { DocumentCopy, Refresh, Search, Upload } from '@element-plus/icons-vue'
import { getCurrentAccount, quickRewrite } from '../api'
import type { QuickRewriteMode, QuickRewritePhrase, QuickRewriteResult } from '../types'

const router = useRouter()

const quickInput = ref('')
const quickMode = ref<QuickRewriteMode>('auto')
const quickLoading = ref(false)
const quickError = ref('')
const quickResult = ref<QuickRewriteResult | null>(null)

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
  const before = quickResult.value.beforeRisk.score
  const low = Math.max(0, score - 6)
  const high = Math.min(Math.max(0, before - 1), score + 8)
  return `${Math.min(low, high)}-${Math.max(low, high)}`
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
const riskReasons = computed(() => {
  if (!quickResult.value) return []
  return [...new Set(quickResult.value.riskyPhrases.map((item) => item.reason))].slice(0, 4)
})
const comparisonRows = computed(() => {
  if (!quickResult.value) return []
  const count = Math.max(quickResult.value.riskyPhrases.length, quickResult.value.improvedPhrases.length)
  return Array.from({ length: count }).map((_, index) => ({
    key: `${index}-${quickResult.value?.riskyPhrases[index]?.text || 'risk'}-${quickResult.value?.improvedPhrases[index]?.text || 'improve'}`,
    before: quickResult.value?.riskyPhrases[index]?.text || '',
    after: quickResult.value?.improvedPhrases[index]?.text || '',
    reason: quickResult.value?.improvedPhrases[index]?.reason || quickResult.value?.riskyPhrases[index]?.reason || '保留原意，降低模板化表达。'
  }))
})

onMounted(() => {
  getCurrentAccount().then(() => {
    router.replace('/app')
  }).catch(() => {
    // 未登录，留在 landing page
  })
})

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

function fillExample() {
  quickInput.value = '随着人工智能技术的发展，旅游企业必须不断引入创新并结合有效营销策略以保持竞争力。创新带来的新技术和新理念可以帮助企业更好地提高服务内容与质量，具有重要意义，并能够为相关实践提供参考价值。'
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

function goUpload() {
  router.push('/app/new')
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
.landing {
  min-height: 100vh;
}

.hero {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 80vh;
  padding: 60px 28px;
  text-align: center;
}

.hero-content {
  max-width: 680px;
}

.hero-badge {
  display: inline-block;
  padding: 6px 16px;
  border-radius: 20px;
  background: rgba(47, 125, 103, 0.1);
  color: #2f7d67;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 24px;
}

.hero h1 {
  font-size: 48px;
  line-height: 1.15;
  color: #172033;
  margin: 0 0 20px;
}

.hero-desc {
  font-size: 17px;
  line-height: 1.75;
  color: #53606f;
  margin: 0 0 36px;
}

.hero-actions {
  display: flex;
  gap: 14px;
  justify-content: center;
  flex-wrap: wrap;
}

.quick-rewrite {
  padding: 0 28px 72px;
}

.quick-shell {
  max-width: 1160px;
  margin: 0 auto;
  padding: 30px;
  border: 1px solid rgba(31, 54, 73, 0.08);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 18px 48px rgba(29, 45, 61, 0.08);
}

.quick-head {
  max-width: 720px;
  margin-bottom: 24px;
}

.quick-head h2 {
  margin: 0 0 10px;
  color: #172033;
  font-size: 30px;
  line-height: 1.2;
}

.quick-head p,
.quick-limit,
.quick-summary,
.quick-disclaimer,
.quick-empty p {
  color: #53606f;
  line-height: 1.7;
}

.quick-tool {
  display: grid;
  grid-template-columns: minmax(280px, 0.92fr) minmax(0, 1.35fr);
  gap: 22px;
}

.quick-input-column,
.quick-output-column {
  min-width: 0;
}

.mode-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.mode-tab {
  border: 1px solid rgba(31, 54, 73, 0.12);
  border-radius: 8px;
  background: #fff;
  color: #344150;
  padding: 8px 12px;
  font: inherit;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.mode-tab.active {
  border-color: rgba(47, 125, 103, 0.55);
  background: rgba(47, 125, 103, 0.1);
  color: #236451;
}

.quick-label {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: #344150;
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 8px;
}

.quick-label span {
  color: #7c8794;
  font-weight: 600;
}

.quick-textarea {
  width: 100%;
  min-height: 210px;
  resize: vertical;
  border: 1px solid rgba(31, 54, 73, 0.14);
  border-radius: 8px;
  padding: 14px;
  font: inherit;
  line-height: 1.75;
  color: #172033;
  background: #fbfdfb;
  outline: none;
}

.quick-textarea:focus {
  border-color: #2f7d67;
  box-shadow: 0 0 0 3px rgba(47, 125, 103, 0.12);
}

.quick-actions,
.quick-result-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.button-icon {
  width: 16px;
  height: 16px;
  margin-right: 6px;
}

.quick-limit {
  margin-top: 12px;
  font-size: 13px;
}

.quick-input-tips {
  display: grid;
  gap: 4px;
  margin-top: 12px;
  padding: 12px 14px;
  border-radius: 8px;
  background: rgba(47, 125, 103, 0.08);
  color: #53606f;
  font-size: 13px;
  line-height: 1.65;
}

.quick-input-tips strong {
  color: #236451;
}

.quick-error {
  margin-top: 10px;
  color: #c94044;
  font-size: 14px;
}

.quick-empty {
  display: grid;
  align-content: center;
  min-height: 360px;
  padding: 24px;
  border: 1px dashed rgba(47, 125, 103, 0.28);
  border-radius: 8px;
  background: #f7faf8;
}

.quick-empty strong {
  margin-bottom: 8px;
  color: #203048;
  font-size: 18px;
}

.risk-strip {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 10px;
}

.risk-strip div {
  padding: 14px;
  border-radius: 8px;
  background: #f7faf8;
  border: 1px solid rgba(31, 54, 73, 0.06);
}

.risk-strip span {
  display: block;
  color: #5e6a78;
  font-size: 13px;
  margin-bottom: 6px;
}

.risk-strip strong {
  color: #203048;
  font-size: 28px;
  line-height: 1;
}

.risk-strip small {
  display: block;
  margin-top: 6px;
  color: #627083;
  font-size: 12px;
}

.quick-disclaimer {
  margin-bottom: 8px;
  font-size: 13px;
}

.quick-summary {
  margin-bottom: 14px;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.result-panel {
  min-width: 0;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid rgba(31, 54, 73, 0.08);
  background: #fff;
}

.result-panel h3 {
  margin: 0 0 10px;
  color: #172033;
  font-size: 16px;
}

.marked-text {
  color: #344150;
  line-height: 1.9;
  word-break: break-word;
}

.risk-mark,
.improve-mark {
  position: relative;
  border-radius: 4px;
  padding: 1px 3px;
  cursor: help;
}

.risk-mark {
  color: #9e2f38;
  background: rgba(200, 75, 82, 0.15);
}

.improve-mark {
  color: #236451;
  background: rgba(47, 125, 103, 0.16);
}

.risk-mark:hover::after,
.improve-mark:hover::after {
  position: absolute;
  z-index: 8;
  left: 0;
  bottom: calc(100% + 8px);
  width: max-content;
  max-width: 260px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #172033;
  color: #fff;
  content: attr(data-reason);
  font-size: 12px;
  line-height: 1.5;
  white-space: normal;
  box-shadow: 0 10px 24px rgba(23, 32, 51, 0.2);
}

.reason-list-mini,
.principle-list {
  margin: 12px 0 0;
  padding-left: 18px;
  color: #53606f;
  line-height: 1.7;
  font-size: 13px;
}

.compare-list {
  display: grid;
  gap: 10px;
}

.compare-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  padding: 10px;
  border-radius: 8px;
  background: #f9fbf9;
  border: 1px solid rgba(31, 54, 73, 0.06);
}

.compare-phrase {
  border-radius: 8px;
  padding: 9px 10px;
  line-height: 1.6;
  font-size: 13px;
  word-break: break-word;
}

.compare-card p {
  grid-column: 1 / -1;
  color: #627083;
  font-size: 12px;
  line-height: 1.6;
}

.compare-arrow {
  color: #8b95a2;
  font-weight: 700;
}

.compare-phrase.before {
  color: #9e2f38;
  background: rgba(200, 75, 82, 0.1);
}

.compare-phrase.after {
  color: #236451;
  background: rgba(47, 125, 103, 0.1);
}

.quick-conversion {
  margin-top: 14px;
  padding: 12px 14px;
  border-radius: 8px;
  background: rgba(32, 69, 90, 0.08);
  color: #344150;
  line-height: 1.7;
  font-size: 14px;
}

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10px 24px;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  text-decoration: none;
  border: 1.5px solid transparent;
  cursor: pointer;
  transition: all 0.18s ease;
}

.btn-lg {
  padding: 13px 32px;
  font-size: 16px;
  border-radius: 12px;
}

.btn-primary {
  background: linear-gradient(135deg, #2f7d67, #236451);
  color: #fff;
  border-color: transparent;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(47, 125, 103, 0.25);
}

.btn:disabled {
  cursor: not-allowed;
  opacity: 0.58;
  transform: none;
  box-shadow: none;
}

.btn-outline {
  background: transparent;
  color: #344150;
  border-color: rgba(31, 54, 73, 0.2);
}

.btn-outline:hover {
  border-color: #2f7d67;
  color: #2f7d67;
}

/* Features */
.features {
  padding: 80px 28px;
  max-width: 1100px;
  margin: 0 auto;
}

.section-title {
  text-align: center;
  font-size: 32px;
  color: #172033;
  margin: 0 0 48px;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.feature-card {
  padding: 28px 24px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(31, 54, 73, 0.06);
  box-shadow: 0 4px 20px rgba(29, 45, 61, 0.05);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.feature-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 32px rgba(29, 45, 61, 0.1);
}

.feature-icon {
  width: 52px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  background: rgba(47, 125, 103, 0.1);
  color: #2f7d67;
  margin-bottom: 18px;
}

.feature-card h3 {
  font-size: 18px;
  color: #172033;
  margin: 0 0 10px;
}

.feature-card p {
  font-size: 14px;
  line-height: 1.7;
  color: #53606f;
  margin: 0;
}

/* Steps */
.how-it-works {
  padding: 80px 28px;
  max-width: 900px;
  margin: 0 auto;
}

.steps {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 20px;
}

.step {
  flex: 1;
  text-align: center;
  padding: 24px;
}

.step-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: linear-gradient(135deg, #20455a, #2f7d67);
  color: #fff;
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 16px;
}

.step h3 {
  font-size: 18px;
  color: #172033;
  margin: 0 0 8px;
}

.step p {
  font-size: 14px;
  color: #53606f;
  line-height: 1.6;
  margin: 0;
}

.step-arrow {
  color: #b0bec5;
  font-size: 24px;
  margin-top: 36px;
}

/* CTA */
.cta-section {
  text-align: center;
  padding: 80px 28px;
  margin: 0 auto;
  max-width: 600px;
}

.cta-section h2 {
  font-size: 30px;
  color: #172033;
  margin: 0 0 14px;
}

.cta-section p {
  font-size: 16px;
  color: #53606f;
  line-height: 1.7;
  margin: 0 0 28px;
}

.landing-footer {
  text-align: center;
  padding: 28px;
  color: #8b95a2;
  font-size: 13px;
  border-top: 1px solid rgba(31, 54, 73, 0.06);
}

@media (max-width: 900px) {
  .quick-tool,
  .result-grid {
    grid-template-columns: 1fr;
  }

  .feature-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .hero h1 {
    font-size: 32px;
  }

  .quick-rewrite {
    padding: 0 16px 52px;
  }

  .quick-shell {
    padding: 18px;
  }

  .quick-head h2 {
    font-size: 24px;
  }

  .risk-strip,
  .compare-card {
    grid-template-columns: 1fr;
  }

  .compare-arrow {
    transform: rotate(90deg);
    justify-self: start;
  }

  .feature-grid {
    grid-template-columns: 1fr;
  }

  .steps {
    flex-direction: column;
    align-items: center;
  }

  .step-arrow {
    transform: rotate(90deg);
    margin: 0;
  }
}
</style>
