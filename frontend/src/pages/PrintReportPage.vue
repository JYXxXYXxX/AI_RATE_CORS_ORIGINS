<template>
  <div class="print-report" v-if="report">
    <!-- 报告头部 -->
    <header class="report-header">
      <img class="report-logo" src="/logo-icon.png?v=3" alt="PataFix" />
      <h1>论文风险预检报告</h1>
      <div class="report-meta">
        <span>报告编号：{{ report.run_id }}</span>
        <span>生成时间：{{ formatDate(report.generated_at) }}</span>
      </div>
    </header>

    <!-- 论文信息 -->
    <section class="info-section">
      <table class="info-table">
        <tbody>
          <tr>
            <td class="label">论文标题</td>
            <td class="value">{{ report.title || '未命名' }}</td>
            <td class="label">学科</td>
            <td class="value">{{ report.subject || '—' }}</td>
          </tr>
          <tr>
            <td class="label">层级</td>
            <td class="value">{{ report.degree_level || '—' }}</td>
            <td class="label">分析片段数</td>
            <td class="value">{{ report.local_metrics.segment_count }} 个</td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- 检测结果总览 -->
    <section class="result-section">
      <h2>一、检测结果总览</h2>
      <table class="result-table">
        <thead>
          <tr>
            <th>检测项目</th>
            <th>预测区间</th>
            <th>中心值</th>
            <th>风险等级</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>知网 AIGC 疑似率</td>
            <td>{{ bandText(report.summary.predicted_cnki_aigc) }}</td>
            <td>{{ report.summary.predicted_cnki_aigc.center_percent.toFixed(1) }}%</td>
            <td :class="aigcRiskClass">{{ aigcRiskText }}</td>
          </tr>
          <tr>
            <td>知网查重率</td>
            <td>{{ bandText(report.summary.predicted_cnki_dup) }}</td>
            <td>{{ report.summary.predicted_cnki_dup.center_percent.toFixed(1) }}%</td>
            <td :class="dupRiskClass">{{ dupRiskText }}</td>
          </tr>
        </tbody>
      </table>

      <div class="summary-box" :class="overallRiskClass">
        <strong>综合评定：{{ riskText(report.summary.overall_risk) }}</strong>
        <p>{{ report.summary.one_line_judgement }}</p>
      </div>
    </section>

    <!-- 章节风险分布 -->
    <section class="heatmap-section">
      <h2>二、章节风险分布</h2>
      <table class="heatmap-table">
        <thead>
          <tr>
            <th>章节</th>
            <th>片段数</th>
            <th>AIGC 均分</th>
            <th>查重均分</th>
            <th>综合评分</th>
            <th>风险等级</th>
            <th>修改建议</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in report.chapter_heatmap" :key="item.chapter_title">
            <td>{{ item.chapter_title }}</td>
            <td>{{ item.section_count }}</td>
            <td>{{ (item.avg_aigc_score * 100).toFixed(1) }}%</td>
            <td>{{ (item.avg_duplication_score * 100).toFixed(1) }}%</td>
            <td>{{ (item.combined_score * 100).toFixed(1) }}%</td>
            <td :class="riskClass(item.risk_level)">{{ riskText(item.risk_level) }}</td>
            <td>{{ item.advice }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- 高风险片段明细 -->
    <section class="sections-section" v-if="highRiskSections.length">
      <h2>三、高风险片段明细</h2>
      <div
        v-for="(item, idx) in highRiskSections"
        :key="idx"
        class="section-item"
      >
        <div class="section-header">
          <strong>{{ item.title || item.section_title || `片段 ${item.section_index}` }}</strong>
          <span class="section-risk" :class="riskClass(item.risk_level)">
            AIGC {{ (item.aigc_score * 100).toFixed(1) }}% / 查重 {{ (item.duplication_score * 100).toFixed(1) }}%
          </span>
        </div>
        <p class="section-preview">{{ item.text_preview }}</p>
        <div class="section-reasons" v-if="item.reasons.length">
          <span class="reason-tag" v-for="(r, i) in item.reasons" :key="i">{{ r }}</span>
        </div>
      </div>
    </section>

    <!-- 修改行动计划 -->
    <section class="plan-section" v-if="report.revision_plan.length">
      <h2>四、修改行动计划</h2>
      <div
        v-for="item in report.revision_plan"
        :key="item.priority"
        class="plan-item"
      >
        <div class="plan-title">
          <span class="plan-priority">P{{ item.priority }}</span>
          <strong>{{ item.title }}</strong>
        </div>
        <p><strong>原因：</strong>{{ item.why }}</p>
        <p><strong>修改方法：</strong>{{ item.how_to_fix }}</p>
        <p><strong>预期收益：</strong>{{ item.expected_gain }}</p>
      </div>
    </section>

    <!-- 导师沟通摘要 -->
    <section class="mentor-section">
      <h2>五、导师沟通摘要</h2>
      <div class="mentor-box">
        <p><strong>{{ report.mentor_brief.headline }}</strong></p>
        <p>{{ report.mentor_brief.summary }}</p>
        <div class="mentor-message">
          <strong>建议沟通话术：</strong>
          <p>{{ report.mentor_brief.suggested_message }}</p>
        </div>
      </div>
    </section>

    <!-- 送检前检查清单 -->
    <section class="checklist-section" v-if="report.submission_checklist.length">
      <h2>六、送检前检查清单</h2>
      <ul class="checklist">
        <li
          v-for="item in report.submission_checklist"
          :key="item.label"
          :class="{ checked: item.done }"
        >
          {{ item.done ? '☑' : '☐' }} {{ item.label }}
        </li>
      </ul>
    </section>

    <!-- 免责声明 -->
    <footer class="report-footer">
      <p><strong>免责声明：</strong>{{ report.disclaimer }}</p>
      <p><strong>数据保留政策：</strong>{{ report.retained_content_policy }}</p>
      <p class="report-note">本报告由 AI Rate Detector 自动生成，仅供参考，不构成正式学术鉴定结论。</p>
    </footer>
  </div>

  <div v-else class="print-loading">
    <p>报告加载中...</p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getUnifiedReport } from '../api'
import type { UnifiedReportResponse } from '../types'

const route = useRoute()
const report = ref<UnifiedReportResponse | null>(null)

onMounted(async () => {
  const runId = route.params.runId as string
  if (!runId) return
  try {
    report.value = await getUnifiedReport(runId)
    // 加载完成后延迟触发打印，让用户看到预览
    setTimeout(() => {
      window.print()
    }, 800)
  } catch (err) {
    alert('报告加载失败：' + (err instanceof Error ? err.message : String(err)))
  }
})

const highRiskSections = computed(() =>
  report.value?.top_risk_sections.filter(
    (s) => s.risk_level !== 'low'
  ) ?? []
)

const aigcRiskClass = computed(() => {
  const c = report.value!.summary.predicted_cnki_aigc.center_percent
  return c >= 30 ? 'risk-high' : c >= 15 ? 'risk-medium' : 'risk-low'
})

const aigcRiskText = computed(() => {
  const c = report.value!.summary.predicted_cnki_aigc.center_percent
  return c >= 30 ? '高风险' : c >= 15 ? '中风险' : '低风险'
})

const dupRiskClass = computed(() => {
  const c = report.value!.summary.predicted_cnki_dup.center_percent
  return c >= 20 ? 'risk-high' : c >= 10 ? 'risk-medium' : 'risk-low'
})

const dupRiskText = computed(() => {
  const c = report.value!.summary.predicted_cnki_dup.center_percent
  return c >= 20 ? '高风险' : c >= 10 ? '中风险' : '低风险'
})

const overallRiskClass = computed(() => {
  return 'risk-' + report.value!.summary.overall_risk
})

function riskText(level: 'low' | 'medium' | 'high') {
  return level === 'high' ? '高风险' : level === 'medium' ? '中风险' : '低风险'
}

function riskClass(level: 'low' | 'medium' | 'high') {
  return 'risk-' + level
}

function bandText(band: { low_percent: number; high_percent: number }) {
  return `${band.low_percent.toFixed(1)}%-${band.high_percent.toFixed(1)}%`
}

function formatDate(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.print-report {
  max-width: 800px;
  margin: 0 auto;
  padding: 40px;
  font-family: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-size: 14px;
  line-height: 1.8;
  color: #1a1a1a;
  background: #fff;
}

.report-header {
  position: relative;
  min-height: 56px;
  text-align: center;
  border-bottom: 3px double #333;
  padding-bottom: 20px;
  margin-bottom: 24px;
}

.report-logo {
  position: absolute;
  top: 0;
  left: 0;
  width: 48px;
  height: 48px;
  object-fit: contain;
}

.report-header h1 {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 12px;
  letter-spacing: 4px;
}

.report-meta {
  display: flex;
  justify-content: center;
  gap: 32px;
  font-size: 12px;
  color: #555;
}

section {
  margin-bottom: 28px;
}

section h2 {
  font-size: 16px;
  font-weight: 700;
  border-left: 4px solid #c41e3a;
  padding-left: 12px;
  margin: 0 0 16px;
  color: #1a1a1a;
}

.info-table,
.result-table,
.heatmap-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.info-table td,
.result-table th,
.result-table td,
.heatmap-table th,
.heatmap-table td {
  border: 1px solid #ccc;
  padding: 8px 12px;
  text-align: left;
}

.info-table .label {
  width: 100px;
  background: #f5f5f5;
  font-weight: 600;
  text-align: center;
}

.info-table .value {
  width: 35%;
}

.result-table thead,
.heatmap-table thead {
  background: #f0f0f0;
}

.result-table th,
.heatmap-table th {
  font-weight: 600;
  text-align: center;
}

.result-table td:nth-child(2),
.result-table td:nth-child(3),
.heatmap-table td:nth-child(2),
.heatmap-table td:nth-child(3),
.heatmap-table td:nth-child(4),
.heatmap-table td:nth-child(5) {
  text-align: center;
}

.summary-box {
  margin-top: 16px;
  padding: 14px 18px;
  border: 1px solid;
  border-radius: 4px;
  font-size: 13px;
}

.summary-box strong {
  display: block;
  font-size: 14px;
  margin-bottom: 6px;
}

.risk-high {
  color: #c41e3a;
  border-color: #f5c6cb;
  background: #f8d7da;
}

.risk-medium {
  color: #856404;
  border-color: #ffeeba;
  background: #fff3cd;
}

.risk-low {
  color: #155724;
  border-color: #c3e6cb;
  background: #d4edda;
}

.section-item {
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 14px;
  margin-bottom: 12px;
  page-break-inside: avoid;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.section-risk {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 3px;
}

.section-preview {
  color: #444;
  font-size: 13px;
  margin: 0 0 8px;
  line-height: 1.7;
}

.section-reasons {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.reason-tag {
  font-size: 11px;
  padding: 2px 8px;
  background: #f0f0f0;
  border-radius: 3px;
  color: #555;
}

.plan-item {
  border-left: 3px solid #2f7d67;
  padding-left: 14px;
  margin-bottom: 16px;
  page-break-inside: avoid;
}

.plan-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.plan-priority {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  background: #2f7d67;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  border-radius: 50%;
}

.plan-item p {
  margin: 4px 0;
  font-size: 13px;
}

.mentor-box {
  border: 1px solid #ddd;
  padding: 16px;
  border-radius: 4px;
  background: #fafafa;
}

.mentor-message {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #ccc;
}

.mentor-message p {
  margin: 4px 0 0;
  font-style: italic;
  color: #555;
}

.checklist {
  list-style: none;
  padding: 0;
  margin: 0;
}

.checklist li {
  padding: 6px 0;
  font-size: 13px;
}

.checklist li.checked {
  color: #2f7d67;
}

.report-footer {
  margin-top: 40px;
  padding-top: 20px;
  border-top: 1px solid #ccc;
  font-size: 11px;
  color: #666;
  line-height: 1.6;
}

.report-note {
  text-align: center;
  margin-top: 12px;
  color: #999;
}

.print-loading {
  text-align: center;
  padding: 80px;
  font-size: 16px;
  color: #666;
}

@media print {
  .print-report {
    padding: 0;
    max-width: 100%;
  }

  section {
    page-break-inside: avoid;
  }

  .section-item,
  .plan-item,
  .mentor-box {
    page-break-inside: avoid;
  }

  .report-footer {
    page-break-inside: avoid;
  }
}
</style>
