<template>
  <section class="report-dashboard">
    <section class="report-hero-card">
      <div class="report-hero-main">
        <div class="report-hero-meta">
          <span class="report-eyebrow">
            {{ latestFeedback ? tx('已结合官方报告校准', 'Calibrated with official report') : tx('PataFix 风险总览', 'PataFix risk overview') }}
          </span>
          <span class="report-generated">
            {{ tx('生成于', 'Generated') }} {{ formatDate(report.generated_at) }}
          </span>
        </div>

        <div class="report-score-row">
          <div class="report-score-block">
            <div class="report-score-line">
              <strong>{{ cnkiBasedRiskScore }}</strong>
              <span>/ 100</span>
            </div>
            <h2>{{ heroHeadline }}</h2>
          </div>
          <span class="risk-pill" :class="riskPillClass(cnkiBasedRisk)">
            {{ riskText(cnkiBasedRisk) }}
          </span>
        </div>

        <p class="report-hero-copy">
          {{ localizedHeroCopy }}
        </p>

        <div v-if="heroNotice" class="report-inline-notice">
          <el-icon><Warning /></el-icon>
          <span>{{ heroNotice }}</span>
        </div>

        <div class="report-hero-actions">
          <el-button class="report-primary-btn" @click="openRewriteEditor">
            <el-icon><EditPen /></el-icon>
            {{ tx('进入在线改写', 'Open rewrite workspace') }}
          </el-button>
          <el-button class="report-secondary-btn" @click="openPrintReport">
            <el-icon><Download /></el-icon>
            {{ tx('导出 PDF 报告', 'Export PDF report') }}
          </el-button>
        </div>
      </div>

      <div class="report-metric-grid">
        <article v-for="metric in heroMetrics" :key="metric.key" class="metric-slab">
          <span class="metric-label">{{ metric.label }}</span>
          <strong class="metric-value">{{ metric.value }}</strong>
          <small class="metric-caption">{{ metric.caption }}</small>
        </article>
      </div>
    </section>

    <section class="report-chart-grid">
      <article class="report-card chart-card">
        <div class="card-heading">
          <div>
            <p class="section-kicker">{{ tx('整体风险分布', 'Overall risk distribution') }}</p>
            <h3>{{ tx('按片段划分的风险层级', 'Risk levels across document fragments') }}</h3>
          </div>
        </div>

        <div class="donut-layout">
          <div class="donut-shell">
            <div class="donut-chart" :style="riskDonutStyle">
              <div class="donut-center">
                <strong>{{ totalSegmentCount }}</strong>
                <span>{{ tx('总片段', 'Total fragments') }}</span>
              </div>
            </div>
          </div>

          <div class="donut-legend">
            <div v-for="item in riskDistributionItems" :key="item.key" class="legend-row">
              <div class="legend-label">
                <span class="legend-dot" :style="{ background: item.color }"></span>
                <span>{{ item.label }}</span>
              </div>
              <div class="legend-value">
                <strong>{{ item.count }}</strong>
                <small>{{ item.percentText }}</small>
              </div>
            </div>
          </div>
        </div>
      </article>

      <article class="report-card chart-card">
        <div class="card-heading">
          <div>
            <p class="section-kicker">{{ tx('优先修改区域 Top 3', 'Priority areas Top 3') }}</p>
            <h3>{{ tx('先改这些位置，收益最大', 'These areas are likely to move the score fastest') }}</h3>
          </div>
        </div>

        <div class="bar-stack">
          <button
            v-for="(item, index) in priorityAreaItems"
            :key="item.sectionIndex"
            type="button"
            class="priority-bar-card"
            @click="openRewriteAdvice(item.sectionIndex)"
          >
            <div class="priority-bar-head">
              <div class="priority-title-wrap">
                <span class="rank-chip">{{ index + 1 }}</span>
                <div>
                  <strong>{{ item.title }}</strong>
                  <small>{{ item.subtitle }}</small>
                </div>
              </div>
              <span class="priority-gain">{{ item.gainLabel }}</span>
            </div>
            <div class="priority-bar-track">
              <div
                class="priority-bar-fill"
                :class="`priority-bar-fill--${item.level}`"
                :style="{ width: `${item.width}%` }"
              ></div>
            </div>
          </button>
        </div>
      </article>

      <article class="report-card chart-card">
        <div class="card-heading">
          <div>
            <p class="section-kicker">{{ tx('风险成因分布', 'Risk reason distribution') }}</p>
            <h3>{{ tx('这份稿子最容易暴露的问题', 'What is most visibly driving the current risk') }}</h3>
          </div>
        </div>

        <div class="reason-stack">
          <div v-for="item in riskReasonItems" :key="item.key" class="reason-row">
            <div class="reason-text">
              <strong>{{ item.label }}</strong>
              <small>{{ item.hint }}</small>
            </div>
            <div class="reason-bar">
              <div class="reason-bar-track">
                <div class="reason-bar-fill" :style="{ width: `${item.value}%`, background: item.color }"></div>
              </div>
              <span>{{ item.value }}%</span>
            </div>
          </div>
        </div>
      </article>

      <article class="report-card chart-card">
        <div class="card-heading">
          <div>
            <p class="section-kicker">{{ tx('修改后 AIGC 下降趋势', 'Estimated AIGC reduction trend') }}</p>
            <h3>{{ tx('完成每一步后的预计下降幅度', 'Projected drop after each optimization step') }}</h3>
          </div>
        </div>

        <div class="trend-card-body">
          <svg viewBox="0 0 360 180" class="trend-chart" preserveAspectRatio="none" aria-hidden="true">
            <defs>
              <linearGradient id="trendAreaGradient" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="rgba(34, 197, 94, 0.28)" />
                <stop offset="100%" stop-color="rgba(34, 197, 94, 0.02)" />
              </linearGradient>
            </defs>
            <path :d="trendAreaPath" fill="url(#trendAreaGradient)"></path>
            <path :d="trendLinePath" class="trend-line"></path>
            <circle
              v-for="point in trendPoints"
              :key="point.label"
              :cx="point.x"
              :cy="point.y"
              r="5.5"
              class="trend-point"
            />
          </svg>

          <div class="trend-axis">
            <div v-for="point in trendPoints" :key="point.label" class="trend-axis-item">
              <strong>{{ point.value.toFixed(1) }}%</strong>
              <span>{{ point.label }}</span>
            </div>
          </div>
        </div>
      </article>
    </section>

    <section class="report-bottom-grid">
      <article class="report-card steps-card">
        <div class="card-heading">
          <div>
            <p class="section-kicker">{{ tx('三步优化计划', 'Three-step optimization plan') }}</p>
            <h3>{{ tx('先做最值钱的修改，再收尾', 'Sequence the edits so the biggest gains happen first') }}</h3>
          </div>
        </div>

        <div class="step-flow">
          <article
            v-for="step in optimizationSteps"
            :key="step.index"
            class="step-card"
            :class="`step-card--${step.tone}`"
          >
            <span class="step-index">{{ step.order }}</span>
            <strong>{{ step.title }}</strong>
            <p>{{ step.description }}</p>
            <span class="step-gain">{{ step.gainLabel }}</span>
          </article>
        </div>
      </article>

      <article class="report-card issues-card">
        <div class="card-heading">
          <div>
            <p class="section-kicker">{{ tx('重点问题定位 Top 3', 'Top 3 issue locations') }}</p>
            <h3>{{ tx('直接定位到最值得改的地方', 'The places most worth opening in rewrite next') }}</h3>
          </div>
        </div>

        <div class="issue-table-wrap">
          <table class="issue-table">
            <thead>
              <tr>
                <th>{{ tx('区域', 'Section') }}</th>
                <th>{{ tx('主要问题', 'Primary issue') }}</th>
                <th>{{ tx('风险等级', 'Risk') }}</th>
                <th>{{ tx('预计收益', 'Expected gain') }}</th>
                <th>{{ tx('操作', 'Action') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in topIssueRows" :key="row.sectionIndex">
                <td :data-label="tx('区域', 'Section')">
                  <strong>{{ row.title }}</strong>
                </td>
                <td :data-label="tx('主要问题', 'Primary issue')">
                  <span>{{ row.issue }}</span>
                </td>
                <td :data-label="tx('风险等级', 'Risk')">
                  <span class="risk-pill risk-pill--compact" :class="riskPillClass(row.level)">
                    {{ riskText(row.level) }}
                  </span>
                </td>
                <td :data-label="tx('预计收益', 'Expected gain')">
                  <span class="gain-text">↓ {{ row.gainLabel }}</span>
                </td>
                <td :data-label="tx('操作', 'Action')">
                  <button type="button" class="mini-action-btn" @click="openRewriteAdvice(row.sectionIndex)">
                    {{ tx('去修改', 'Revise') }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>
    </section>

    <section class="report-footnote">
      <el-icon><Warning /></el-icon>
      <span>
        {{ tx(
          '提示：以上结果由 PataFix AIGC 风险分析模型生成，仅供参考，建议结合人工判断。',
          'Note: These results are generated by the PataFix AIGC risk analysis model for reference only and should be reviewed with human judgment.'
        ) }}
      </span>
    </section>
  </section>

  <el-dialog
    v-model="rewriteDialogVisible"
    :title="`${tx('AI 改写建议', 'AI rewrite advice')} - ${currentRewriteSectionTitle}`"
    width="820px"
    destroy-on-close
    class="rewrite-dialog"
  >
    <div v-if="rewriteDialogLoading" class="rewrite-skeleton">
      <el-skeleton :rows="6" animated />
      <p class="skeleton-hint">
        {{ tx(
          '正在连接 AI 改写服务，请稍候。如果第三方服务繁忙，可能需要 30-90 秒。',
          'Connecting to the rewrite service. This may take 30-90 seconds if the provider is busy.'
        ) }}
      </p>
    </div>
    <div v-else-if="currentRewriteAdvice?.error" class="rewrite-error">
      <el-result
        icon="error"
        :title="tx('改写建议获取失败', 'Failed to load rewrite advice')"
        :sub-title="currentRewriteAdvice.error"
      >
        <template #extra>
          <el-button type="primary" @click="retryRewriteAdvice">{{ tx('重试', 'Retry') }}</el-button>
        </template>
      </el-result>
    </div>
    <div v-else class="rewrite-content">
      <el-alert
        v-if="currentRewriteAdvice?.diagnosis"
        :title="currentRewriteAdvice.diagnosis"
        type="info"
        :closable="false"
        show-icon
        class="diagnosis-alert"
      />

      <el-tag v-if="currentRewriteAdvice?.fallback" type="warning" effect="dark" class="fallback-tag">
        {{ tx(
          '当前展示的是离线兜底改写结果，可作为快速参考。',
          'The current result is an offline fallback rewrite and can be used as a quick reference.'
        ) }}
      </el-tag>

      <div v-if="currentRewriteAdvice?.sentences?.length" class="rewrite-block">
        <h4 class="block-title">
          <el-icon><EditPen /></el-icon>
          {{ tx('逐句改写对比', 'Sentence-by-sentence rewrite') }}
        </h4>

        <div v-for="(sentence, idx) in currentRewriteAdvice.sentences" :key="idx" class="sentence-card">
          <div class="sentence-header">
            <span class="risk-pill risk-pill--compact" :class="riskPillClass(sentence.risk)">
              {{ riskText(sentence.risk) }}
            </span>
            <span class="sentence-num">{{ locale === 'en' ? `Sentence ${idx + 1}` : `第 ${idx + 1} 句` }}</span>
          </div>

          <div class="sentence-body">
            <div class="sentence-row original-box">
              <label>{{ tx('原句', 'Original') }}</label>
              <p>{{ sentence.original }}</p>
            </div>

            <div class="arrow-divider">
              <el-icon><Bottom /></el-icon>
            </div>

            <div class="sentence-row rewritten-box">
              <label>{{ tx('改写后', 'Rewritten') }}</label>
              <p>{{ sentence.rewritten }}</p>
            </div>

            <div class="sentence-row explanation-box">
              <label>{{ tx('修改原因', 'Why this helps') }}</label>
              <p>{{ sentence.explanation }}</p>
            </div>
          </div>
        </div>
      </div>

      <div v-if="currentRewriteAdvice?.rewritten_paragraph" class="rewrite-block">
        <h4 class="block-title">
          <el-icon><DocumentCopy /></el-icon>
          {{ tx('整段改写参考', 'Full rewritten paragraph') }}
        </h4>

        <el-card shadow="never" class="paragraph-card">
          <p class="paragraph-text">{{ currentRewriteAdvice.rewritten_paragraph }}</p>
          <div class="paragraph-actions">
            <el-button
              type="primary"
              plain
              size="small"
              @click="copyText(currentRewriteAdvice.rewritten_paragraph, tx('已复制整段改写', 'Rewritten paragraph copied'))"
            >
              <el-icon><DocumentCopy /></el-icon>
              {{ tx('复制全文', 'Copy full paragraph') }}
            </el-button>
          </div>
        </el-card>
      </div>

      <div v-if="currentRewriteAdvice?.overall_advice" class="rewrite-block">
        <h4 class="block-title">
          <el-icon><Warning /></el-icon>
          {{ tx('整体修改策略', 'Overall strategy') }}
        </h4>
        <el-alert :title="currentRewriteAdvice.overall_advice" type="warning" :closable="false" show-icon />
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus/es/components/message/index'
import { Bottom, DocumentCopy, Download, EditPen, Warning } from '@element-plus/icons-vue'
import { getRewriteAdvice } from '../api'
import type {
  AnalysisRunStatusResponse,
  ModelStatusResponse,
  RewriteAdviceResponse,
  ScoreBand,
  SubScores,
  UnifiedReportResponse,
} from '../types'

const router = useRouter()

const props = defineProps<{
  report: UnifiedReportResponse
  runStatus: AnalysisRunStatusResponse | null
  modelStatus: ModelStatusResponse | null
}>()

type ReportLocale = 'zh' | 'en'
type RiskLevel = 'low' | 'medium' | 'high'

const locale = ref<ReportLocale>(
  (document.documentElement.dataset.lang as ReportLocale) ||
    (localStorage.getItem('patafix-language') as ReportLocale) ||
    'zh'
)

function syncLocale(next?: string) {
  locale.value = next === 'en' ? 'en' : 'zh'
}

function handleLanguageChange(event: Event) {
  syncLocale((event as CustomEvent<ReportLocale>).detail)
}

function tx(zh: string, en: string) {
  return locale.value === 'en' ? en : zh
}

onMounted(() => {
  syncLocale(document.documentElement.dataset.lang || localStorage.getItem('patafix-language') || 'zh')
  window.addEventListener('patafix:language-change', handleLanguageChange as EventListener)
})

onBeforeUnmount(() => {
  window.removeEventListener('patafix:language-change', handleLanguageChange as EventListener)
})

const rewriteDialogVisible = ref(false)
const rewriteDialogLoading = ref(false)
const currentRewriteAdvice = ref<RewriteAdviceResponse | null>(null)
const currentRewriteSectionTitle = ref('')
const currentRewriteSectionIndex = ref(0)

const latestFeedback = computed(() => props.report.feedback_timeline[0] || null)

const prioritizedSections = computed(() => {
  return props.report.priority_sections?.length ? props.report.priority_sections : props.report.top_risk_sections
})

const totalSegmentCount = computed(() => {
  return Math.max(props.report.local_metrics.segment_count, prioritizedSections.value.length, 1)
})

const cnkiBasedRisk = computed<RiskLevel>(() => {
  const latest = latestFeedback.value
  if (!latest) return props.report.summary.overall_risk
  const aigc = latest.cnki_aigc_percent ?? props.report.summary.predicted_cnki_aigc.center_percent
  const dup = latest.cnki_dup_percent ?? props.report.summary.predicted_cnki_dup.center_percent
  const maxScore = Math.max(aigc, dup)
  if (maxScore >= 30) return 'high'
  if (maxScore >= 15) return 'medium'
  return 'low'
})

const cnkiBasedRiskScore = computed(() => {
  const latest = latestFeedback.value
  if (!latest) return props.report.summary.risk_score
  const aigc = latest.cnki_aigc_percent ?? props.report.summary.predicted_cnki_aigc.center_percent
  const dup = latest.cnki_dup_percent ?? props.report.summary.predicted_cnki_dup.center_percent
  let score = 100 - dup * 0.42 - aigc * 0.38
  if (aigc >= 30) score -= 15
  if (dup >= 20) score -= 10
  return Math.max(10, Math.min(95, Math.round(score)))
})

const localizedHeroCopy = computed(() => {
  if (latestFeedback.value) {
    const aigc = latestFeedback.value.cnki_aigc_percent
    const dup = latestFeedback.value.cnki_dup_percent
    if (aigc != null && aigc >= 40) {
      return tx(
        `官方 AIGC 结果仍处于很高风险区间（${aigc.toFixed(1)}%），建议先完成高风险段落深改，再做一次整稿复检。`,
        `The official AIGC result is still in a very high-risk band (${aigc.toFixed(1)}%). Start with deep rewrites on the highest-risk passages, then recheck the full draft.`
      )
    }
    if (aigc != null && aigc >= 30) {
      return tx(
        `官方 AIGC 已超过安全线（${aigc.toFixed(1)}%），现在更适合用“先高风险、后结构、再细节”的顺序来压分。`,
        `The official AIGC result is above the safe range (${aigc.toFixed(1)}%), so the best path is high-risk passages first, then structure, then detail.`
      )
    }
    if (dup != null && dup >= 20) {
      return tx(
        `当前查重压力比 AIGC 更突出（${dup.toFixed(1)}%），建议先处理重复表达与证据引用，再收尾语言层面的优化。`,
        `Similarity is currently the more visible pressure point (${dup.toFixed(1)}%). Tackle repeated phrasing and evidence handling first, then polish the language.`
      )
    }
  }

  if (locale.value === 'zh') {
    return props.report.summary.one_line_judgement
  }

  if (cnkiBasedRisk.value === 'high') {
    return `This draft is still too risky for formal submission. Fix the most exposed passages first, then verify the whole paper again.`
  }
  if (cnkiBasedRisk.value === 'medium') {
    return `The draft is workable, but several passages still need targeted cleanup before a final check.`
  }
  return `The current draft looks relatively stable. A focused polish and one last verification should be enough.`
})

const heroHeadline = computed(() => {
  if (cnkiBasedRisk.value === 'high') {
    return tx('当前属于高风险稿件，需要优先压降暴露段落', 'High-risk draft that needs immediate exposure reduction')
  }
  if (cnkiBasedRisk.value === 'medium') {
    return tx('整体可控，但仍有关键段落需要处理', 'Overall manageable, with several key passages still exposed')
  }
  return tx('整体风险较低，适合做定稿前收尾', 'Low overall risk and suitable for final polishing')
})

const heroNotice = computed(() => {
  const warnings = props.report.warnings ?? []
  if (warnings.length > 0) return warnings[0]

  const latest = latestFeedback.value
  if (latest?.cnki_aigc_percent != null && latest.cnki_aigc_percent >= 30) {
    return tx(
      `当前官方 AIGC 为 ${latest.cnki_aigc_percent.toFixed(1)}%，下方建议已经按更严格标准收紧。`,
      `Official AIGC is currently ${latest.cnki_aigc_percent.toFixed(1)}%, so the suggestions below are already tightened to a stricter threshold.`
    )
  }

  return ''
})

const heroMetrics = computed(() => {
  const latest = latestFeedback.value
  return [
    {
      key: 'aigc',
      label: tx('预测 AIGC 区间', 'Estimated AIGC band'),
      value: latest?.cnki_aigc_percent != null ? optionalPercent(latest.cnki_aigc_percent) : bandText(props.report.summary.predicted_cnki_aigc),
      caption:
        latest?.cnki_aigc_percent != null
          ? tx('已以上传官方结果为准', 'Official report is taking precedence')
          : `${tx('中心值', 'Center')} ${props.report.summary.predicted_cnki_aigc.center_percent.toFixed(1)}%`,
    },
    {
      key: 'dup',
      label: tx('预测相似 / 查重区间', 'Estimated similarity band'),
      value: latest?.cnki_dup_percent != null ? optionalPercent(latest.cnki_dup_percent) : bandText(props.report.summary.predicted_cnki_dup),
      caption:
        latest?.cnki_dup_percent != null
          ? tx('已以上传官方结果为准', 'Official report is taking precedence')
          : `${tx('中心值', 'Center')} ${props.report.summary.predicted_cnki_dup.center_percent.toFixed(1)}%`,
    },
    {
      key: 'confidence',
      label: tx('模型置信度', 'Model confidence'),
      value: `${Math.round(props.report.summary.confidence * 100)}%`,
      caption: tx(
        `${props.report.local_metrics.segment_count} 个片段参与分析`,
        `${props.report.local_metrics.segment_count} fragments analyzed`
      ),
    },
    {
      key: 'priority',
      label: tx('优先建议修改段数', 'Priority passages'),
      value: `${prioritizedSections.value.length}`,
      caption: tx(
        `${prioritizedSections.value.filter(section => section.risk_level !== 'low').length} 段中高风险已排序`,
        `${prioritizedSections.value.filter(section => section.risk_level !== 'low').length} medium/high-risk passages ranked`
      ),
    },
  ]
})

const riskDistributionItems = computed(() => {
  const high = prioritizedSections.value.filter(item => item.risk_level === 'high').length
  const medium = prioritizedSections.value.filter(item => item.risk_level === 'medium').length
  const low = prioritizedSections.value.filter(item => item.risk_level === 'low').length
  const normal = Math.max(totalSegmentCount.value - high - medium - low, 0)

  const items = [
    { key: 'high', label: tx('高风险', 'High risk'), count: high, color: '#EF4444' },
    { key: 'medium', label: tx('中风险', 'Medium risk'), count: medium, color: '#F59E0B' },
    { key: 'low', label: tx('低风险', 'Low risk'), count: low, color: '#7C5CFF' },
    { key: 'normal', label: tx('正常', 'Normal'), count: normal, color: '#22C55E' },
  ]

  return items.map(item => ({
    ...item,
    percent: item.count / totalSegmentCount.value,
    percentText: `${Math.round((item.count / totalSegmentCount.value) * 100)}%`,
  }))
})

const riskDonutStyle = computed(() => {
  let cursor = 0
  const segments = riskDistributionItems.value
    .map(item => {
      const start = cursor
      const next = cursor + item.percent * 360
      cursor = next
      return `${item.color} ${start}deg ${next}deg`
    })
    .join(', ')

  return {
    background: `conic-gradient(${segments || '#22C55E 0deg 360deg'})`,
  }
})

const priorityAreaItems = computed(() => {
  const sections = prioritizedSections.value.slice(0, 3)
  const maxScore = Math.max(...sections.map(section => section.combined_score), 0.35)

  return sections.map(section => ({
    sectionIndex: section.section_index,
    title: section.title,
    subtitle: renderIssueSummary(section),
    level: section.risk_level,
    gainLabel: formatGainLabel(sectionExpectedDrop(section)),
    width: Math.max(32, Math.round((section.combined_score / maxScore) * 100)),
  }))
})

const riskReasonItems = computed(() => {
  const source = prioritizedSections.value.slice(0, 6).filter(item => item.sub_scores)
  if (!source.length) {
    return [
      { key: 'template', label: tx('模板化表达', 'Template-heavy phrasing'), value: 62, color: '#EF4444', hint: tx('重复套板较多', 'Repetitive wording patterns') },
      { key: 'repeat', label: tx('句式重复', 'Sentence repetition'), value: 55, color: '#F59E0B', hint: tx('结构变化偏少', 'Low sentence variation') },
      { key: 'empty', label: tx('套话空话', 'Empty filler language'), value: 48, color: '#7C5CFF', hint: tx('信息密度不足', 'Low information density') },
      { key: 'splice', label: tx('疑似拼接', 'Possible stitched phrasing'), value: 42, color: '#3B82F6', hint: tx('风格跳变明显', 'Style shifts between clauses') },
      { key: 'detail', label: tx('缺少细节', 'Lack of detail'), value: 38, color: '#22C55E', hint: tx('证据支撑不够', 'Weak supporting details') },
    ]
  }

  const average = (pick: (scores: SubScores) => number) =>
    Math.round(source.reduce((sum, item) => sum + pick(item.sub_scores as SubScores), 0) / source.length)

  return [
    {
      key: 'template',
      label: tx('模板化表达', 'Template-heavy phrasing'),
      value: average(scores => scores.template_score),
      color: '#EF4444',
      hint: tx('容易被看成统一话术', 'Likely to read as standardized phrasing'),
    },
    {
      key: 'repeat',
      label: tx('句式重复', 'Sentence repetition'),
      value: average(scores => scores.repetition_score),
      color: '#F59E0B',
      hint: tx('句子推进方式过于相似', 'The sentence rhythm repeats too often'),
    },
    {
      key: 'empty',
      label: tx('套话空话', 'Empty filler language'),
      value: average(scores => scores.semantic_empty_score),
      color: '#7C5CFF',
      hint: tx('表达泛、信息密度低', 'Broad wording with low information density'),
    },
    {
      key: 'splice',
      label: tx('疑似拼接', 'Possible stitched phrasing'),
      value: average(scores => (scores.ai_likelihood + scores.citation_risk) / 2),
      color: '#3B82F6',
      hint: tx('局部风格和来源感较强', 'The local style feels patched together'),
    },
    {
      key: 'detail',
      label: tx('缺少细节', 'Lack of detail'),
      value: average(scores => scores.semantic_empty_score * 0.7 + scores.ai_likelihood * 0.3),
      color: '#22C55E',
      hint: tx('例证和细节支撑不足', 'More evidence and specifics are needed'),
    },
  ]
})

const optimizationSteps = computed(() => {
  const defaults = [
    {
      index: 0,
      order: '01',
      title: tx('优先处理高风险段落', 'Handle the highest-risk passages first'),
      description: tx('先把最容易拉高结果的段落逐句改掉，优先清理模板化和高重复表达。', 'Rewrite the passages that are most visibly pushing the score up, especially templated and repetitive wording.'),
      tone: 'rose',
      gainLabel: tx('预计降低 12%+', 'Estimated drop 12%+'),
    },
    {
      index: 1,
      order: '02',
      title: tx('优化句式与结构', 'Vary sentence form and structure'),
      description: tx('拉开句子节奏，避免多段连续使用同一种说明方式。', 'Introduce more sentence variation so adjacent passages do not all move in the same pattern.'),
      tone: 'amber',
      gainLabel: tx('预计降低 10%+', 'Estimated drop 10%+'),
    },
    {
      index: 2,
      order: '03',
      title: tx('补充细节与证据', 'Add detail and supporting evidence'),
      description: tx('把空泛结论换成更具体的案例、过程、数据或判断依据。', 'Replace broad conclusions with concrete examples, process detail, data, or explicit reasoning.'),
      tone: 'violet',
      gainLabel: tx('预计降低 8%+', 'Estimated drop 8%+'),
    },
  ]

  if (!props.report.revision_plan.length) return defaults

  return defaults.map((fallback, index) => {
    const plan = props.report.revision_plan[index]
    if (!plan) return fallback
    return {
      ...fallback,
      title: plan.title,
      description: locale.value === 'en' ? plan.how_to_fix : plan.why,
      gainLabel: plan.expected_gain || fallback.gainLabel,
    }
  })
})

const topIssueRows = computed(() => {
  return prioritizedSections.value.slice(0, 3).map(section => ({
    sectionIndex: section.section_index,
    title: section.title,
    issue: renderIssueSummary(section),
    level: section.risk_level,
    gainLabel: formatGainLabel(sectionExpectedDrop(section)),
  }))
})

const trendValues = computed(() => {
  const current = latestFeedback.value?.cnki_aigc_percent ?? props.report.summary.predicted_cnki_aigc.center_percent
  const gains = optimizationSteps.value.map(step => extractGainNumber(step.gainLabel))
  const first = Math.max(current - gains[0], 6)
  const second = Math.max(first - gains[1] * 0.78, 5)
  const third = Math.max(second - gains[2] * 0.72, 4.5)
  const final = Math.max(third - 2.4, 4)

  return [current, first, second, third, final]
})

const trendLabels = computed(() => [
  tx('当前', 'Current'),
  tx('完成第 1 步', 'After step 1'),
  tx('完成第 2 步', 'After step 2'),
  tx('完成第 3 步', 'After step 3'),
  tx('最终预计', 'Final estimate'),
])

const trendPoints = computed(() => {
  const width = 360
  const height = 180
  const top = 16
  const bottom = 30
  const values = trendValues.value
  const max = Math.max(...values) + 4
  const min = Math.max(Math.min(...values) - 3, 0)

  return values.map((value, index) => {
    const x = 22 + (index * (width - 44)) / Math.max(values.length - 1, 1)
    const ratio = max === min ? 0.5 : (value - min) / (max - min)
    const y = height - bottom - ratio * (height - top - bottom)
    return {
      label: trendLabels.value[index],
      value,
      x,
      y,
    }
  })
})

const trendLinePath = computed(() => {
  return trendPoints.value.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ')
})

const trendAreaPath = computed(() => {
  const baseY = 150
  const line = trendLinePath.value
  const first = trendPoints.value[0]
  const last = trendPoints.value[trendPoints.value.length - 1]
  return `${line} L ${last.x} ${baseY} L ${first.x} ${baseY} Z`
})

async function openRewriteAdvice(sectionIndex: number) {
  const section = props.report.top_risk_sections.find(item => item.section_index === sectionIndex)
  currentRewriteSectionTitle.value = section?.title || (locale.value === 'en' ? `Paragraph ${sectionIndex + 1}` : `段落 ${sectionIndex + 1}`)
  currentRewriteSectionIndex.value = sectionIndex
  rewriteDialogLoading.value = true
  currentRewriteAdvice.value = null
  rewriteDialogVisible.value = true

  try {
    currentRewriteAdvice.value = await getRewriteAdvice(props.report.run_id, sectionIndex)
  } catch (error) {
    currentRewriteAdvice.value = {
      run_id: props.report.run_id,
      section_index: sectionIndex,
      diagnosis: '',
      sentences: [],
      rewritten_paragraph: '',
      overall_advice: '',
      error: error instanceof Error ? error.message : tx('获取改写建议失败', 'Failed to load rewrite advice'),
    }
  } finally {
    rewriteDialogLoading.value = false
  }
}

async function retryRewriteAdvice() {
  await openRewriteAdvice(currentRewriteSectionIndex.value)
}

function openPrintReport() {
  const url = router.resolve({
    name: 'report-print',
    params: { runId: props.report.run_id },
  }).href
  window.open(url, '_blank')
}

function openRewriteEditor() {
  router.push(`/app/rewrite/${props.report.run_id}`)
}

async function copyText(text: string, successMessage: string) {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.setAttribute('readonly', 'true')
      textarea.style.position = 'absolute'
      textarea.style.left = '-9999px'
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
    }
    ElMessage.success(successMessage)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : tx('复制失败', 'Copy failed'))
  }
}

function renderIssueSummary(section: UnifiedReportResponse['top_risk_sections'][number]) {
  if (section.reasons?.length) {
    return section.reasons.slice(0, 2).join(locale.value === 'en' ? ' / ' : '、')
  }
  if (section.sub_scores) {
    return dominantRiskLabel(section.sub_scores)
  }
  return tx('需要定向降重和降 AIGC 处理', 'Needs targeted similarity and AIGC reduction')
}

function dominantRiskLabel(subScores: SubScores) {
  const dimensions: [string, number][] = [
    [tx('模板化表达', 'Template-heavy phrasing'), subScores.template_score],
    [tx('句式重复', 'Sentence repetition'), subScores.repetition_score],
    [tx('套话空话', 'Empty filler language'), subScores.semantic_empty_score],
    [tx('疑似拼接', 'Possible stitched phrasing'), (subScores.ai_likelihood + subScores.citation_risk) / 2],
    [tx('缺少细节', 'Lack of detail'), subScores.semantic_empty_score * 0.7 + subScores.ai_likelihood * 0.3],
  ]
  dimensions.sort((a, b) => b[1] - a[1])
  return dimensions[0][0]
}

function sectionExpectedDrop(section: UnifiedReportResponse['top_risk_sections'][number]) {
  return Math.max(4, Math.min(18, Math.round(section.combined_score * 16 + section.aigc_score * 4)))
}

function extractGainNumber(text: string) {
  const matched = text.match(/(\d+(?:\.\d+)?)/)
  return matched ? Number(matched[1]) : 8
}

function formatGainLabel(value: number) {
  return locale.value === 'en' ? `${value}%+` : `${value}%+`
}

function riskText(level: RiskLevel) {
  if (level === 'high') return tx('高风险', 'High risk')
  if (level === 'medium') return tx('中风险', 'Medium risk')
  return tx('低风险', 'Low risk')
}

function riskPillClass(level: RiskLevel | 'normal') {
  return `risk-pill--${level}`
}

function bandText(band: ScoreBand) {
  return `${band.low_percent.toFixed(1)}%-${band.high_percent.toFixed(1)}%`
}

function optionalPercent(value: number | null | undefined) {
  if (value == null) return '-'
  return `${value.toFixed(1)}%`
}

function formatDate(value: string) {
  return new Date(value).toLocaleString(locale.value === 'en' ? 'en-US' : 'zh-CN', { hour12: false })
}
</script>

<style scoped>
.report-dashboard {
  --report-bg-page: #f7f8f4;
  --report-bg-card: rgba(255, 255, 255, 0.94);
  --report-bg-card-soft: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(249, 251, 247, 0.98));
  --report-bg-elevated: rgba(255, 255, 255, 0.98);
  --report-bg-subtle: rgba(148, 163, 184, 0.10);
  --report-bg-track: rgba(148, 163, 184, 0.16);
  --report-text-main: #18202a;
  --report-text-secondary: #425066;
  --report-text-muted: #6b7280;
  --report-text-soft: #8a94a5;
  --report-brand: #0f8f4f;
  --report-brand-strong: #0f7a45;
  --report-brand-soft: rgba(15, 143, 79, 0.09);
  --report-risk-high: #ef4444;
  --report-risk-medium: #f59e0b;
  --report-risk-low: #7c5cff;
  --report-risk-normal: #22c55e;
  --report-risk-blue: #3b82f6;
  --report-border: rgba(148, 163, 184, 0.16);
  --report-shadow: 0 20px 48px rgba(15, 23, 42, 0.08);
  --report-shadow-soft: 0 12px 28px rgba(15, 23, 42, 0.05);
  display: grid;
  gap: 24px;
  color: var(--report-text-main);
}

:global(:root[data-theme='dark']) .report-dashboard {
  --report-bg-page: #09121a;
  --report-bg-card: #101922;
  --report-bg-card-soft: linear-gradient(180deg, #101a23 0%, #0c151d 100%);
  --report-bg-elevated: #13202a;
  --report-bg-subtle: rgba(110, 128, 149, 0.16);
  --report-bg-track: rgba(94, 112, 132, 0.26);
  --report-text-main: #f2f6fb;
  --report-text-secondary: #d6deea;
  --report-text-muted: #a4b0bf;
  --report-text-soft: #738196;
  --report-brand: #22c55e;
  --report-brand-strong: #17a34a;
  --report-brand-soft: rgba(34, 197, 94, 0.16);
  --report-border: rgba(118, 136, 158, 0.22);
  --report-shadow: 0 18px 42px rgba(0, 0, 0, 0.26);
  --report-shadow-soft: 0 10px 24px rgba(0, 0, 0, 0.18);
}

:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard {
  --report-bg-page: #0b1220 !important;
  --report-bg-card: #121c2f !important;
  --report-bg-card-soft: linear-gradient(180deg, #121c2f 0%, #101a2d 100%) !important;
  --report-bg-elevated: #162235 !important;
  --report-bg-subtle: rgba(255, 255, 255, 0.045) !important;
  --report-bg-track: rgba(255, 255, 255, 0.08) !important;
  --report-text-main: #f5f7fa !important;
  --report-text-secondary: #edf2f8 !important;
  --report-text-muted: #c8d1dd !important;
  --report-text-soft: #a1adbd !important;
  --report-brand: #1fa45b !important;
  --report-brand-strong: #168a4b !important;
  --report-brand-soft: rgba(31, 164, 91, 0.16) !important;
  --report-border: rgba(255, 255, 255, 0.08) !important;
  --report-shadow: 0 10px 28px rgba(0, 0, 0, 0.22) !important;
  --report-shadow-soft: 0 8px 18px rgba(0, 0, 0, 0.16) !important;
}

.report-hero-card,
.report-card {
  background: var(--report-bg-card-soft);
  border: 1px solid var(--report-border);
  border-radius: 24px;
  box-shadow: var(--report-shadow);
}

:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .report-hero-card,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .report-card {
  background: var(--report-bg-card-soft) !important;
  border-color: var(--report-border) !important;
  box-shadow: var(--report-shadow) !important;
}

.report-hero-card {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(360px, 0.95fr);
  gap: 22px;
  padding: 28px;
  position: relative;
}

.report-hero-main {
  display: grid;
  gap: 18px;
  min-width: 0;
}

.report-hero-meta,
.report-score-row,
.report-hero-actions,
.card-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.report-eyebrow,
.section-kicker {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--report-brand);
}

.report-generated {
  color: var(--report-text-soft);
  font-size: 13px;
}

.report-score-row {
  align-items: flex-start;
}

.report-score-line {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.report-score-line strong {
  font-size: clamp(52px, 8vw, 76px);
  line-height: 0.95;
  letter-spacing: -0.03em;
  font-weight: 800;
}

.report-score-line span {
  font-size: 22px;
  color: var(--report-text-soft);
}

.report-score-block h2 {
  margin: 10px 0 0;
  font-size: clamp(26px, 3vw, 34px);
  line-height: 1.15;
  color: var(--report-text-main);
}

.report-hero-copy {
  margin: 0;
  max-width: 56ch;
  font-size: 15px;
  line-height: 1.8;
  color: var(--report-text-muted);
}

.report-inline-notice {
  display: inline-flex;
  align-items: flex-start;
  gap: 10px;
  width: fit-content;
  max-width: 100%;
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(255, 244, 226, 0.84);
  border: 1px solid rgba(245, 158, 11, 0.18);
  color: #9a5d00;
  font-size: 13px;
  line-height: 1.65;
}

:global(:root[data-theme='dark']) .report-inline-notice {
  background: rgba(72, 54, 18, 0.32);
  border-color: rgba(240, 177, 69, 0.18);
  color: #f7d18d;
}

.report-hero-actions {
  justify-content: flex-start;
  flex-wrap: wrap;
}

.report-primary-btn,
.report-secondary-btn {
  height: 46px;
  border-radius: 12px;
  padding: 0 18px;
  font-weight: 700;
  transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease, border-color 0.18s ease;
}

.report-primary-btn {
  background: linear-gradient(135deg, var(--report-brand), var(--report-brand-strong));
  color: #ffffff;
  border: none;
  box-shadow: 0 16px 30px rgba(15, 143, 79, 0.22);
}

.report-primary-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 20px 34px rgba(15, 143, 79, 0.3);
}

.report-primary-btn:active {
  transform: scale(0.985);
}

.report-secondary-btn {
  background: rgba(255, 255, 255, 0.84);
  color: var(--report-brand-strong);
  border: 1px solid rgba(15, 143, 79, 0.26);
}

.report-secondary-btn:hover {
  transform: translateY(-1px);
  background: rgba(232, 246, 238, 0.96);
}

:global(:root[data-theme='dark']) .report-primary-btn {
  box-shadow: 0 16px 32px rgba(34, 197, 94, 0.24);
}

:global(:root[data-theme='dark']) .report-secondary-btn {
  background: #121d26;
  border-color: rgba(63, 213, 111, 0.24);
  color: #dff7e6;
}

:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .report-primary-btn {
  background: linear-gradient(135deg, #1fa45b, #168a4b) !important;
  color: #ffffff !important;
  box-shadow: 0 12px 24px rgba(31, 164, 91, 0.18) !important;
}

:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .report-secondary-btn {
  background: rgba(31, 164, 91, 0.06) !important;
  border-color: rgba(31, 164, 91, 0.34) !important;
  color: #d8f6e3 !important;
}

.report-metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.metric-slab {
  display: grid;
  gap: 8px;
  padding: 18px;
  border-radius: 18px;
  background: var(--report-bg-elevated);
  border: 1px solid var(--report-border);
  box-shadow: var(--report-shadow-soft);
  min-height: 128px;
}

:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .metric-slab,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .priority-bar-card,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .issue-table tbody tr,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .sentence-card,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .paragraph-card {
  background: var(--report-bg-elevated) !important;
  border-color: var(--report-border) !important;
  box-shadow: var(--report-shadow-soft) !important;
}

.metric-label {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--report-text-soft);
}

.metric-value {
  font-size: 30px;
  line-height: 1.05;
  color: var(--report-text-main);
}

.metric-caption {
  color: var(--report-text-muted);
  font-size: 13px;
  line-height: 1.55;
}

:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .report-generated,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .metric-label,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .section-kicker,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .metric-caption,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .priority-title-wrap small,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .reason-text small,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .trend-axis-item span,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .issue-table thead th,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .sentence-num {
  color: var(--report-text-muted) !important;
}

:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard h2,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard h3,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard strong,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .metric-value,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .report-score-line strong,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .priority-title-wrap strong,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .reason-text strong,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .donut-center strong,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .trend-axis-item strong {
  color: var(--report-text-main) !important;
}

:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .report-hero-copy,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .legend-label,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .legend-value small,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .reason-bar span,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .step-card p,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .issue-table tbody td span,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .donut-center span {
  color: var(--report-text-secondary) !important;
}

:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .report-hero-copy,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .metric-caption,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .priority-title-wrap small,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .reason-text small,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .trend-axis-item span,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .step-card p,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .issue-table tbody td,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .legend-label,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .legend-value small {
  font-weight: 500 !important;
}

:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .report-score-block h2,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .metric-value,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .donut-center strong,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .issue-table tbody td strong {
  font-weight: 800 !important;
}

.report-chart-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 20px;
}

.report-card {
  padding: 22px;
}

.chart-card {
  display: grid;
  gap: 18px;
  min-height: 100%;
}

.card-heading {
  align-items: flex-start;
}

.card-heading h3 {
  margin: 6px 0 0;
  font-size: 18px;
  line-height: 1.35;
  color: var(--report-text-main);
}

.donut-layout {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 18px;
  align-items: center;
}

.donut-shell {
  display: grid;
  place-items: center;
}

.donut-chart {
  width: 168px;
  height: 168px;
  border-radius: 50%;
  position: relative;
}

.donut-chart::after {
  content: '';
  position: absolute;
  inset: 18px;
  border-radius: 50%;
  background: var(--report-bg-card);
  border: 1px solid var(--report-border);
}

:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .donut-chart::after {
  background: #101a2d !important;
  border-color: rgba(255, 255, 255, 0.08) !important;
}

.donut-center {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: grid;
  place-items: center;
  align-content: center;
  text-align: center;
}

.donut-center strong {
  font-size: 34px;
  line-height: 1;
}

.donut-center span {
  margin-top: 6px;
  font-size: 12px;
  color: var(--report-text-muted);
}

.donut-legend,
.bar-stack,
.reason-stack,
.trend-card-body,
.step-flow {
  display: grid;
  gap: 12px;
}

.legend-row,
.reason-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.legend-label {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: var(--report-text-muted);
  line-height: 1.5;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  flex-shrink: 0;
}

.legend-value {
  text-align: right;
}

.legend-value strong {
  display: block;
  font-size: 16px;
}

.legend-value small {
  color: var(--report-text-muted);
}

.priority-bar-card {
  width: 100%;
  border: 1px solid var(--report-border);
  border-radius: 18px;
  padding: 14px 16px;
  background: var(--report-bg-elevated);
  color: inherit;
  cursor: pointer;
  text-align: left;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.priority-bar-card:hover {
  transform: translateY(-1px);
  box-shadow: var(--report-shadow-soft);
  border-color: rgba(15, 143, 79, 0.24);
}

.priority-bar-head,
.priority-title-wrap,
.reason-bar,
.trend-axis,
.issue-table-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
}

.priority-bar-head {
  justify-content: space-between;
  margin-bottom: 10px;
}

.priority-title-wrap strong {
  display: block;
  font-size: 15px;
  line-height: 1.4;
  color: var(--report-text-main);
}

.priority-title-wrap small {
  display: block;
  margin-top: 2px;
  color: var(--report-text-muted);
  font-size: 12px;
  line-height: 1.6;
}

.rank-chip {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  font-size: 13px;
  font-weight: 700;
  background: var(--report-brand-soft);
  color: var(--report-brand);
  flex-shrink: 0;
}

.priority-gain,
.step-gain,
.gain-text {
  color: var(--report-brand);
  font-size: 13px;
  font-weight: 700;
}

.priority-bar-track,
.reason-bar-track {
  width: 100%;
  height: 10px;
  border-radius: 999px;
  background: var(--report-bg-track);
  overflow: hidden;
}

:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .trend-chart {
  background: transparent !important;
}

:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .trend-line {
  stroke: #1fa45b !important;
}

:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .trend-point {
  fill: #162235 !important;
  stroke: #1fa45b !important;
}

.priority-bar-fill,
.reason-bar-fill {
  height: 100%;
  border-radius: inherit;
}

.priority-bar-fill--high {
  background: linear-gradient(90deg, #f87171, #ef4444);
}

.priority-bar-fill--medium {
  background: linear-gradient(90deg, #fbbf24, #f59e0b);
}

.priority-bar-fill--low {
  background: linear-gradient(90deg, #9b8cff, #7c5cff);
}

.reason-text {
  min-width: 0;
}

.reason-text strong {
  display: block;
  font-size: 14px;
  color: var(--report-text-secondary);
}

.reason-text small {
  color: var(--report-text-muted);
  font-size: 12px;
  line-height: 1.55;
}

.reason-bar {
  flex: 1;
  justify-content: flex-end;
}

.reason-bar span {
  min-width: 42px;
  text-align: right;
  font-size: 13px;
  color: var(--report-text-muted);
}

.trend-chart {
  width: 100%;
  height: 180px;
}

.trend-line {
  fill: none;
  stroke: var(--report-brand);
  stroke-width: 4;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.trend-point {
  fill: #ffffff;
  stroke: var(--report-brand);
  stroke-width: 3;
}

:global(:root[data-theme='dark']) .trend-point {
  fill: #101922;
}

.trend-axis {
  justify-content: space-between;
  align-items: stretch;
}

.trend-axis-item {
  display: grid;
  gap: 4px;
  text-align: center;
  flex: 1;
}

.trend-axis-item strong {
  font-size: 15px;
}

.trend-axis-item span {
  color: var(--report-text-muted);
  font-size: 12px;
  line-height: 1.5;
}

.report-bottom-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(0, 0.92fr);
  gap: 20px;
}

.steps-card,
.issues-card {
  min-height: 100%;
}

.step-flow {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.step-card {
  position: relative;
  display: grid;
  gap: 14px;
  min-height: 220px;
  padding: 20px 18px;
  border-radius: 20px;
  border: 1px solid transparent;
}

.step-card::after {
  content: '→';
  position: absolute;
  right: -14px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 24px;
  color: var(--report-text-soft);
}

.step-card:last-child::after {
  display: none;
}

.step-card--rose {
  background: rgba(254, 242, 242, 0.92);
  border-color: rgba(239, 68, 68, 0.16);
}

.step-card--amber {
  background: rgba(255, 247, 237, 0.92);
  border-color: rgba(245, 158, 11, 0.16);
}

.step-card--violet {
  background: rgba(245, 243, 255, 0.94);
  border-color: rgba(124, 92, 255, 0.16);
}

:global(:root[data-theme='dark']) .step-card--rose {
  background: linear-gradient(180deg, rgba(72, 27, 35, 0.78), rgba(54, 22, 29, 0.84));
  border-color: rgba(239, 68, 68, 0.16);
}

:global(:root[data-theme='dark']) .step-card--amber {
  background: linear-gradient(180deg, rgba(73, 52, 22, 0.76), rgba(53, 37, 16, 0.84));
  border-color: rgba(245, 158, 11, 0.16);
}

:global(:root[data-theme='dark']) .step-card--violet {
  background: linear-gradient(180deg, rgba(48, 39, 82, 0.78), rgba(37, 31, 61, 0.84));
  border-color: rgba(124, 92, 255, 0.16);
}

.step-index {
  font-size: 30px;
  font-weight: 800;
  line-height: 1;
  color: var(--report-text-soft);
}

.step-card strong {
  font-size: 17px;
  line-height: 1.35;
}

.step-card p {
  margin: 0;
  color: var(--report-text-muted);
  font-size: 14px;
  line-height: 1.72;
}

.issue-table-wrap {
  display: block;
  overflow-x: auto;
}

.issue-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0 10px;
  min-width: 620px;
}

.issue-table thead th {
  padding: 0 14px 8px;
  text-align: left;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--report-text-soft);
}

.issue-table tbody tr {
  background: var(--report-bg-elevated);
  box-shadow: var(--report-shadow-soft);
}

.issue-table tbody td {
  padding: 16px 14px;
  font-size: 14px;
  vertical-align: middle;
  border-top: 1px solid var(--report-border);
  border-bottom: 1px solid var(--report-border);
  color: var(--report-text-secondary);
}

.issue-table tbody td:first-child {
  border-left: 1px solid var(--report-border);
  border-radius: 14px 0 0 14px;
}

.issue-table tbody td:last-child {
  border-right: 1px solid var(--report-border);
  border-radius: 0 14px 14px 0;
}

.mini-action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 36px;
  min-width: 88px;
  padding: 0 14px;
  border-radius: 8px;
  border: 1px solid rgba(15, 143, 79, 0.26);
  background: transparent;
  color: var(--report-brand);
  font-weight: 700;
  font-size: 13px;
  line-height: 1;
  white-space: nowrap;
  word-break: keep-all;
  cursor: pointer;
  transition: all 0.16s ease;
}

.mini-action-btn:hover {
  background: var(--report-brand);
  color: #ffffff;
}

.report-footnote {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(232, 246, 238, 0.92);
  border: 1px solid rgba(15, 143, 79, 0.14);
  color: #275a3c;
  font-size: 13px;
  line-height: 1.6;
}

:global(:root[data-theme='dark']) .report-footnote {
  background: rgba(17, 45, 35, 0.56);
  border-color: rgba(34, 197, 94, 0.14);
  color: #d4f5de;
}

:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .report-footnote {
  background: rgba(20, 53, 40, 0.42) !important;
  border-color: rgba(31, 164, 91, 0.16) !important;
  color: #d4f5de !important;
}

.risk-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  border: 1px solid transparent;
  white-space: nowrap;
}

.risk-pill--compact {
  padding: 6px 10px;
  font-size: 12px;
}

.risk-pill--high {
  color: var(--report-risk-high);
  background: rgba(239, 68, 68, 0.12);
  border-color: rgba(239, 68, 68, 0.18);
}

.risk-pill--medium {
  color: var(--report-risk-medium);
  background: rgba(245, 158, 11, 0.14);
  border-color: rgba(245, 158, 11, 0.18);
}

.risk-pill--low {
  color: var(--report-risk-low);
  background: rgba(124, 92, 255, 0.12);
  border-color: rgba(124, 92, 255, 0.18);
}

.risk-pill--normal {
  color: var(--report-risk-normal);
  background: rgba(34, 197, 94, 0.12);
  border-color: rgba(34, 197, 94, 0.18);
}

.rewrite-skeleton {
  padding: 20px;
}

.skeleton-hint {
  margin-top: 12px;
  font-size: 13px;
  color: var(--report-text-muted);
  text-align: center;
}

.rewrite-content {
  max-height: 65vh;
  overflow-y: auto;
  padding-right: 4px;
}

.rewrite-block {
  margin-bottom: 24px;
}

.block-title {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 12px;
  font-size: 15px;
  font-weight: 700;
  color: var(--report-text-main);
}

.diagnosis-alert {
  margin-bottom: 16px;
}

.fallback-tag {
  margin-bottom: 16px;
}

.sentence-card {
  border: 1px solid var(--report-border);
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 16px;
  background: var(--report-bg-elevated);
}

.sentence-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.sentence-num {
  font-size: 13px;
  color: var(--report-text-muted);
}

.sentence-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.sentence-row {
  border-radius: 12px;
  padding: 12px;
}

.sentence-row label {
  display: block;
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.sentence-row p,
.paragraph-text {
  margin: 0;
  line-height: 1.8;
  font-size: 14px;
  color: var(--report-text-main);
  white-space: pre-wrap;
}

.original-box {
  background: var(--report-bg-subtle);
  border-left: 3px solid rgba(148, 163, 184, 0.78);
}

.original-box label {
  color: var(--report-text-muted);
}

.rewritten-box {
  background: rgba(34, 197, 94, 0.1);
  border-left: 3px solid var(--report-brand);
}

.rewritten-box label {
  color: var(--report-brand);
}

.explanation-box {
  background: rgba(245, 158, 11, 0.08);
  border-left: 3px solid var(--report-risk-medium);
}

.explanation-box label {
  color: #b26a00;
}

:global(:root[data-theme='dark']) .explanation-box label {
  color: #ffd38a;
}

.arrow-divider {
  display: flex;
  justify-content: center;
  color: var(--report-brand);
  font-size: 18px;
}

.paragraph-card {
  background: var(--report-bg-subtle);
  border-radius: 16px;
  border: 1px solid var(--report-border);
}

:global(:root[data-theme='dark']) .report-page .report-dashboard .report-hero-card,
:global(:root[data-theme='dark']) .report-page .report-dashboard .report-card,
:global(:root[data-theme='dark']) .report-page .report-dashboard .metric-slab,
:global(:root[data-theme='dark']) .report-page .report-dashboard .priority-bar-card,
:global(:root[data-theme='dark']) .report-page .report-dashboard .issue-table tbody tr,
:global(:root[data-theme='dark']) .report-page .report-dashboard .sentence-card,
:global(:root[data-theme='dark']) .report-page .report-dashboard .paragraph-card {
  backdrop-filter: none;
}

:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .report-hero-card,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .report-card,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .metric-slab,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .priority-bar-card,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .step-card,
:global(html[data-theme='dark'][data-report-page='true']) .report-page .report-dashboard .report-footnote {
  backdrop-filter: none !important;
}

.paragraph-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.rewrite-error {
  padding: 20px 0;
}

@media (max-width: 1280px) {
  .report-chart-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .report-bottom-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1080px) {
  .report-hero-card {
    grid-template-columns: 1fr;
  }

  .report-metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .step-flow {
    grid-template-columns: 1fr;
  }

  .step-card::after {
    display: none;
  }
}

@media (max-width: 768px) {
  .report-dashboard {
    gap: 18px;
  }

  .report-hero-card,
  .report-card {
    padding: 18px;
    border-radius: 20px;
  }

  .report-metric-grid,
  .report-chart-grid,
  .donut-layout {
    grid-template-columns: 1fr;
  }

  .trend-axis {
    flex-wrap: wrap;
  }

  .report-hero-meta,
  .report-score-row,
  .report-hero-actions,
  .card-heading,
  .priority-bar-head,
  .legend-row,
  .reason-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .report-primary-btn,
  .report-secondary-btn {
    width: 100%;
  }

  .issue-table {
    min-width: 0;
    border-spacing: 0;
  }

  .issue-table thead {
    display: none;
  }

  .issue-table tbody,
  .issue-table tr,
  .issue-table td {
    display: block;
    width: 100%;
  }

  .issue-table tbody tr {
    margin-bottom: 12px;
    border: 1px solid var(--report-border);
    border-radius: 16px;
    overflow: hidden;
  }

  .issue-table tbody td {
    border: none;
    border-bottom: 1px solid var(--report-border);
    border-radius: 0 !important;
    padding: 12px 14px;
  }

  .issue-table tbody td:last-child {
    border-bottom: none;
  }

  .issue-table tbody td::before {
    content: attr(data-label);
    display: block;
    margin-bottom: 6px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--report-text-soft);
  }
}
</style>
