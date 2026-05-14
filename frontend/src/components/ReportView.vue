<template>
  <section class="summary-hero">
    <div class="hero-main">
      <p class="eyebrow">
        {{ latestFeedback ? '基于知网实测的风险指数' : '风险指数' }}
      </p>
      <div class="risk-score-line">
        <strong>{{ cnkiBasedRiskScore }}</strong>
        <span>/ 100</span>
      </div>
      <h2>{{ riskText(cnkiBasedRisk) }}</h2>
      <p class="hero-copy">{{ cnkiBasedJudgement }}</p>
      <div class="hero-actions report-action-row">
        <el-button type="success" plain @click="openPrintReport">
          导出 PDF 报告
        </el-button>
        <el-button plain @click="copyMentorBrief">复制导师沟通摘要</el-button>
        <el-button plain @click="copyRevisionPlan">复制修改行动计划</el-button>
        <el-button type="warning" plain @click="openRewriteEditor">
          在线改写
        </el-button>
      </div>
    </div>

    <div class="hero-metrics">
      <!-- 有知网实测数据时，以知网为准 -->
      <template v-if="latestFeedback">
        <article class="metric-card cnki-primary">
          <span>知网实测查重</span>
          <strong>{{ optionalPercent(latestFeedback.cnki_dup_percent) }}</strong>
          <small v-if="latestFeedback.cnki_dup_percent != null">
            本系统预测 {{ report.summary.predicted_cnki_dup.center_percent.toFixed(1) }}%
          </small>
        </article>
        <article class="metric-card cnki-primary">
          <span>知网实测 AIGC</span>
          <strong>{{ optionalPercent(latestFeedback.cnki_aigc_percent) }}</strong>
          <small v-if="latestFeedback.cnki_aigc_percent != null">
            本系统预测 {{ report.summary.predicted_cnki_aigc.center_percent.toFixed(1) }}%
          </small>
        </article>
        <article class="metric-card">
          <span>模型置信度</span>
          <strong>{{ Math.round(report.summary.confidence * 100) }}%</strong>
          <small>{{ report.local_metrics.segment_count }} 个分析片段</small>
        </article>
        <article class="metric-card">
          <span>改写策略</span>
          <strong>{{ cnkiBasedRisk === 'high' ? '全面改写' : cnkiBasedRisk === 'medium' ? '重点改写' : '精修即可' }}</strong>
          <small>已结合知网实测优化</small>
        </article>
      </template>

      <!-- 无知网数据时，显示原有布局 -->
      <template v-else>
        <article class="metric-card">
          <span>预测知网查重</span>
          <strong>{{ bandText(report.summary.predicted_cnki_dup) }}</strong>
          <small>中心值 {{ report.summary.predicted_cnki_dup.center_percent.toFixed(1) }}%</small>
        </article>
        <article class="metric-card">
          <span>预测知网 AIGC</span>
          <strong>{{ bandText(report.summary.predicted_cnki_aigc) }}</strong>
          <small>中心值 {{ report.summary.predicted_cnki_aigc.center_percent.toFixed(1) }}%</small>
        </article>
        <article class="metric-card">
          <span>模型置信度</span>
          <strong>{{ Math.round(report.summary.confidence * 100) }}%</strong>
          <small>{{ report.local_metrics.segment_count }} 个分析片段</small>
        </article>
        <article class="metric-card">
          <span>本地 AIGC 分</span>
          <strong>{{ (report.local_metrics.ai_like_score * 100).toFixed(1) }}%</strong>
          <small>高风险片段 {{ report.local_metrics.high_risk_segment_count }} 个</small>
        </article>
      </template>
    </div>
  </section>

  <!-- 知网校准提示 -->
  <section v-if="cnkiGapWarning" class="cnki-gap-alert">
    <div class="gap-alert-content">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
      <div>
        <strong>已结合知网官方实测数据优化分析</strong>
        <p>{{ cnkiGapWarning }}</p>
      </div>
    </div>
  </section>

  <section class="info-row">
    <div class="card soft-card">
      <div class="card-head">
        <p class="eyebrow">本次最该先改的 3 个地方</p>
        <h3>修改顺序比盲目大改更重要</h3>
      </div>
      <ul class="bullet-list">
        <li v-for="target in report.summary.first_fix_targets" :key="target">{{ target }}</li>
      </ul>
    </div>

    <div class="card soft-card">
      <div class="card-head">
        <p class="eyebrow">任务状态</p>
        <h3>{{ runStatus?.title || report.title }}</h3>
      </div>
      <div class="meta-chips">
        <el-tag>{{ report.subject || '未填写学科' }}</el-tag>
        <el-tag type="success">{{ report.degree_level || '未填写层级' }}</el-tag>
        <el-tag type="warning">生成于 {{ formatDate(report.generated_at) }}</el-tag>
      </div>
      <p class="helper-text">如果你修改的是这几个高风险位置，正式送检前的返工通常会少很多。</p>
    </div>
  </section>

  <section v-if="report.workflow_overview || report.calibration_insight" class="dual-grid">
    <section v-if="report.workflow_overview" class="card soft-card">
      <div class="card-head">
        <p class="eyebrow">分析完整性</p>
        <h3>{{ report.workflow_overview.closure_label }}</h3>
      </div>
      <div class="status-row workflow-score-row">
        <div class="soft-card status-tile">
          <span>分析完整度</span>
          <strong>{{ report.workflow_overview.closure_score }}/100</strong>
        </div>
        <div class="soft-card status-tile">
          <span>外部数据源</span>
          <strong>{{ report.workflow_overview.provider_result_count }}</strong>
        </div>
        <div class="soft-card status-tile">
          <span>知网报告数</span>
          <strong>{{ report.workflow_overview.feedback_count }}</strong>
        </div>
      </div>
      <p class="helper-text">最近知网报告：{{ report.workflow_overview.latest_feedback_at ? formatDate(report.workflow_overview.latest_feedback_at) : '暂无' }}</p>
      <p class="workflow-next-step">{{ report.workflow_overview.next_step }}</p>
    </section>

    <section v-if="report.calibration_insight" class="card soft-card">
      <div class="card-head">
        <p class="eyebrow">知网实测参考</p>
        <h3>已结合知网官方数据优化分析</h3>
      </div>
      <div class="mini-metrics">
        <span>知网实测查重 {{ optionalPercent(report.calibration_insight.latest_cnki_dup_percent) }}</span>
        <span>知网实测 AIGC {{ optionalPercent(report.calibration_insight.latest_cnki_aigc_percent) }}</span>
      </div>
      <p class="helper-text">{{ report.calibration_insight.message }}</p>
    </section>
  </section>

  <!-- 知网检测详情：扩展分析 -->
  <section v-if="report.cnki_report_details" class="card cnki-details-card">
    <div class="card-head">
      <p class="eyebrow">知网检测详情</p>
      <h3>基于知网报告的深度分析</h3>
    </div>

    <!-- 扩展指标 -->
    <div v-if="hasExtendedMetrics" class="cnki-extended-metrics">
      <div v-if="report.cnki_report_details.single_max_dup_percent != null" class="soft-card status-tile">
        <span>单篇最大复制比</span>
        <strong>{{ report.cnki_report_details.single_max_dup_percent.toFixed(1) }}%</strong>
        <small>某一篇文献的最高相似度</small>
      </div>
      <div v-if="report.cnki_report_details.remove_reference_dup_percent != null" class="soft-card status-tile">
        <span>去除引用后复制比</span>
        <strong>{{ report.cnki_report_details.remove_reference_dup_percent.toFixed(1) }}%</strong>
        <small>排除合理引用后的真实重复</small>
      </div>
      <div v-if="report.cnki_report_details.suspected_plagiarism && Object.keys(report.cnki_report_details.suspected_plagiarism).length > 0" class="soft-card status-tile">
        <span>疑似剽窃分类</span>
        <div class="plagiarism-tags">
          <el-tag v-for="(count, type) in report.cnki_report_details.suspected_plagiarism" :key="type" type="danger" size="small">
            {{ type }} {{ count }}处
          </el-tag>
        </div>
      </div>
    </div>

    <!-- 问题片段列表 -->
    <div v-if="report.cnki_report_details.fragments && report.cnki_report_details.fragments.length > 0" class="cnki-fragments">
      <p class="eyebrow">知网标记的具体问题片段</p>
      <p class="helper-text">以下片段来自知网检测报告，系统已尝试将其与您的论文原文匹配</p>

      <div class="fragment-list">
        <article
          v-for="(frag, idx) in report.cnki_report_details.fragments"
          :key="idx"
          class="fragment-card"
          :class="{ 'fragment-matched': frag.matched_section_index != null }"
        >
          <div class="fragment-header">
            <el-tag :type="frag.type === 'aigc' ? 'warning' : 'danger'" size="small">
              {{ frag.type === 'aigc' ? '疑似 AI 生成' : '疑似重复' }}
            </el-tag>
            <span v-if="frag.origin" class="fragment-origin">来源：{{ frag.origin }}</span>
            <span v-if="frag.match_ratio != null" class="fragment-match-ratio">
              匹配度 {{ (frag.match_ratio * 100).toFixed(0) }}%
            </span>
          </div>

          <div class="fragment-body">
            <div class="fragment-source">
              <label>被检测片段</label>
              <p>{{ frag.source_text }}</p>
            </div>
            <div v-if="frag.similar_text" class="fragment-similar">
              <label>相似来源</label>
              <p>{{ frag.similar_text }}</p>
            </div>
            <div v-if="frag.matched_section_index != null" class="fragment-match">
              <label>匹配到原文</label>
              <p><strong>{{ frag.matched_section_title || '段落' }}</strong></p>
              <p class="match-preview">{{ frag.matched_text_preview }}</p>
            </div>
          </div>

          <div class="fragment-actions">
            <el-button
              v-if="frag.matched_section_index != null"
              type="primary"
              size="small"
              plain
              @click="openRewriteAdvice(frag.matched_section_index)"
            >
              <el-icon><EditPen /></el-icon> 查看改写建议
            </el-button>
            <el-tag v-else type="info" size="small">未匹配到原文位置</el-tag>
          </div>
        </article>
      </div>
    </div>

    <div v-else-if="!hasExtendedMetrics" class="helper-text">
      知网报告已上传，但未解析到详细片段。建议上传更清晰的报告截图或 PDF，系统可以提取更多结构化信息。
    </div>
  </section>

  <!-- 锁定提示横幅 -->
  <section v-if="!reportUnlocked" class="card lock-banner">
    <div class="lock-content">
      <el-icon class="lock-icon"><Lock /></el-icon>
      <div class="lock-text">
        <h3>完整报告已锁定</h3>
        <p>预览已结束。解锁后可查看章节热力图、风险段落详情、改写建议和导师沟通摘要。</p>
      </div>
      <el-button type="primary" size="large" @click="openUnlockModal('unlock_report')">
        解锁全文检测报告 ¥29.90
      </el-button>
    </div>
  </section>

  <section v-if="reportUnlocked" class="card">
    <div class="card-head">
      <p class="eyebrow">章节风险热力图</p>
      <h3>先看哪一章最容易拖高整体结果</h3>
    </div>
    <div class="heat-grid">
      <article v-for="chapter in report.chapter_heatmap" :key="chapter.chapter_title" class="heat-card">
        <div class="segment-head">
          <strong>{{ chapter.chapter_title }}</strong>
          <el-tag :type="tagType(chapter.risk_level)">{{ riskText(chapter.risk_level) }}</el-tag>
        </div>
        <div class="mini-metrics">
          <span>AIGC {{ (chapter.avg_aigc_score * 100).toFixed(1) }}%</span>
          <span>查重 {{ (chapter.avg_duplication_score * 100).toFixed(1) }}%</span>
        </div>
        <div class="heat"><span :style="{ width: `${Math.round(chapter.combined_score * 100)}%` }"></span></div>
        <p>{{ chapter.advice }}</p>
      </article>
    </div>
  </section>

  <section v-if="reportUnlocked" class="dual-grid">
    <section class="card">
      <div class="card-head">
        <p class="eyebrow">Top 风险段落</p>
        <h3>先改这些段，通常最省力</h3>
      </div>
      <article v-for="section in report.top_risk_sections" :key="section.section_index" class="segment-card">
        <div class="segment-head">
          <div>
            <span class="segment-index">#{{ section.section_index + 1 }}</span>
            <strong>{{ section.title }}</strong>
          </div>
          <el-tag :type="tagType(section.risk_level)">{{ riskText(section.risk_level) }}</el-tag>
        </div>
        <p class="preview">{{ section.text_preview }}</p>
        <div class="mini-metrics">
          <span>AIGC {{ (section.aigc_score * 100).toFixed(1) }}%</span>
          <span>重复 {{ (section.duplication_score * 100).toFixed(1) }}%</span>
          <span>综合 {{ (section.combined_score * 100).toFixed(1) }}%</span>
        </div>
        <div v-if="section.sub_scores" class="sub-score-bars">
          <div class="sub-bar" title="AI 疑似度">
            <span class="sub-label">AI</span>
            <div class="sub-track"><div class="sub-fill sub-ai" :style="{ width: section.sub_scores.ai_likelihood + '%' }"></div></div>
            <span class="sub-value">{{ Math.round(section.sub_scores.ai_likelihood) }}</span>
          </div>
          <div class="sub-bar" title="模板化">
            <span class="sub-label">模板</span>
            <div class="sub-track"><div class="sub-fill sub-template" :style="{ width: section.sub_scores.template_score + '%' }"></div></div>
            <span class="sub-value">{{ Math.round(section.sub_scores.template_score) }}</span>
          </div>
          <div class="sub-bar" title="语义空洞">
            <span class="sub-label">空洞</span>
            <div class="sub-track"><div class="sub-fill sub-empty" :style="{ width: section.sub_scores.semantic_empty_score + '%' }"></div></div>
            <span class="sub-value">{{ Math.round(section.sub_scores.semantic_empty_score) }}</span>
          </div>
          <div class="sub-bar" title="重复表达">
            <span class="sub-label">重复</span>
            <div class="sub-track"><div class="sub-fill sub-repeat" :style="{ width: section.sub_scores.repetition_score + '%' }"></div></div>
            <span class="sub-value">{{ Math.round(section.sub_scores.repetition_score) }}</span>
          </div>
          <div class="sub-bar" title="引用风险">
            <span class="sub-label">引用</span>
            <div class="sub-track"><div class="sub-fill sub-cite" :style="{ width: section.sub_scores.citation_risk + '%' }"></div></div>
            <span class="sub-value">{{ Math.round(section.sub_scores.citation_risk) }}</span>
          </div>
        </div>
        <div class="reason-list">
          <el-tag v-for="reason in section.reasons" :key="reason" effect="plain">{{ reason }}</el-tag>
        </div>
        <el-button
          v-if="section.risk_level !== 'low'"
          class="rewrite-btn"
          type="primary"
          plain
          size="small"
          :loading="rewriteLoadingMap[section.section_index]"
          @click="openRewriteAdvice(section.section_index)"
        >
          <el-icon><EditPen /></el-icon>
          <span>查看 AI 改写建议</span>
        </el-button>
      </article>
    </section>

    <section class="card">
      <div class="card-head">
        <p class="eyebrow">相似证据</p>
        <h3>这些地方更值得定向处理</h3>
      </div>
      <article
        v-for="match in report.top_similarity_matches"
        :key="`${match.section_index}-${match.matched_source}-${match.matched_title}`"
        class="match-card"
      >
        <div class="segment-head">
          <strong>{{ match.section_title }}</strong>
          <el-tag type="warning">{{ match.match_type }}</el-tag>
        </div>
        <p class="match-title">{{ match.matched_title }}</p>
        <p class="preview">{{ match.matched_snippet }}</p>
        <div class="mini-metrics">
          <span>相似度 {{ match.similarity_percent.toFixed(1) }}%</span>
          <span>重合字符 {{ match.overlap_chars }}</span>
          <span>来源 {{ match.matched_source }}</span>
        </div>
      </article>
    </section>
  </section>

  <section v-if="report.provider_results.length || report.feedback_timeline.length" class="dual-grid">
    <section class="card">
      <div class="card-head">
        <p class="eyebrow">外部结果时间线</p>
        <h3>已经接入过哪些外部判断</h3>
      </div>
      <article v-for="item in report.provider_results" :key="item.payload_id" class="timeline-card">
        <div class="segment-head">
          <strong>{{ item.provider_label }}</strong>
          <el-tag effect="plain">{{ providerSourceText(item.source_type) }}</el-tag>
        </div>
        <div class="mini-metrics">
          <span>查重 {{ optionalPercent(item.duplication_percent) }}</span>
          <span>AIGC {{ optionalPercent(item.aigc_percent) }}</span>
          <span>置信度 {{ confidenceText(item.confidence) }}</span>
        </div>
        <p class="helper-text">版本：{{ item.version || '未填写' }}</p>
        <p v-if="item.notes" class="helper-text">{{ item.notes }}</p>
        <p class="timeline-time">{{ formatDate(item.created_at) }}</p>
      </article>
      <p v-if="!report.provider_results.length" class="helper-text">还没有导入或抓取外部结果。</p>
    </section>

    <section class="card">
      <div class="card-head">
        <p class="eyebrow">知网实测记录</p>
        <h3>已接入的知网官方数据</h3>
      </div>

      <!-- 通过提示 -->
      <div v-if="isPassed" class="pass-banner">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
        <div>
          <strong>当前知网指标已达标</strong>
          <span>查重 {{ latestFeedback?.cnki_dup_percent?.toFixed(1) }}%，AIGC {{ latestFeedback?.cnki_aigc_percent?.toFixed(1) }}%</span>
        </div>
      </div>

      <!-- 迭代对比 -->
      <div v-if="previousFeedback && latestFeedback" class="iteration-compare">
        <div class="compare-row">
          <span class="compare-label">本次 vs 上次</span>
          <div class="compare-values">
            <span v-if="latestFeedback.cnki_dup_percent != null && previousFeedback.cnki_dup_percent != null" :class="deltaClass(previousFeedback.cnki_dup_percent - latestFeedback.cnki_dup_percent)">
              查重 {{ deltaIcon(previousFeedback.cnki_dup_percent - latestFeedback.cnki_dup_percent) }} {{ Math.abs(previousFeedback.cnki_dup_percent - latestFeedback.cnki_dup_percent).toFixed(1) }}%
            </span>
            <span v-if="latestFeedback.cnki_aigc_percent != null && previousFeedback.cnki_aigc_percent != null" :class="deltaClass(previousFeedback.cnki_aigc_percent - latestFeedback.cnki_aigc_percent)">
              AIGC {{ deltaIcon(previousFeedback.cnki_aigc_percent - latestFeedback.cnki_aigc_percent) }} {{ Math.abs(previousFeedback.cnki_aigc_percent - latestFeedback.cnki_aigc_percent).toFixed(1) }}%
            </span>
          </div>
        </div>
      </div>

      <article v-for="item in report.feedback_timeline" :key="item.feedback_id" class="timeline-card">
        <div class="segment-head">
          <strong>{{ formatDate(item.created_at) }}</strong>
          <el-tag :type="item.verified ? 'success' : 'info'">{{ item.verified ? '已核验' : '未核验' }}</el-tag>
        </div>
        <div class="mini-metrics">
          <span>知网查重 {{ optionalPercent(item.cnki_dup_percent) }}</span>
          <span>知网 AIGC {{ optionalPercent(item.cnki_aigc_percent) }}</span>
        </div>
        <p class="helper-text">报告日期：{{ item.report_date || '未填写' }}</p>
        <p v-if="item.notes" class="helper-text">{{ item.notes }}</p>
      </article>
      <p v-if="!report.feedback_timeline.length" class="helper-text">上传知网检测报告后，系统会结合官方实测数据优化改写建议策略。</p>

      <div class="cnki-upload-action">
        <el-button type="primary" plain size="small" @click="openCnkiUploadDialog">
          <el-icon><Upload /></el-icon> 上传新知网报告
        </el-button>
      </div>
    </section>
  </section>

  <section v-if="reportUnlocked" class="card">
    <div class="card-head">
      <p class="eyebrow">三步提交计划</p>
      <h3>把返工压缩到最少</h3>
    </div>
    <div class="plan-list">
      <article v-for="plan in report.revision_plan" :key="plan.priority" class="plan-card">
        <span class="plan-badge">{{ plan.priority }}</span>
        <div>
          <strong>{{ plan.title }}</strong>
          <p>{{ plan.why }}</p>
          <p><b>怎么改：</b>{{ plan.how_to_fix }}</p>
          <p><b>预期收益：</b>{{ plan.expected_gain }}</p>
        </div>
      </article>
    </div>
  </section>

  <section class="card">
    <div class="card-head">
      <p class="eyebrow">模型状态</p>
      <h3>当前系统到底在用哪一版代理模型</h3>
    </div>
    <div class="info-row status-row">
      <div class="soft-card status-tile">
        <span>已回填样本</span>
        <strong>{{ modelStatus?.feedback_count || 0 }}</strong>
      </div>
      <div class="soft-card status-tile">
        <span>校准版本</span>
        <strong>{{ modelStatus?.calibration_version || '未加载' }}</strong>
      </div>
      <div class="soft-card status-tile">
        <span>自动重训</span>
        <strong>{{ modelStatus?.auto_train_enabled ? `开启 / 每 ${modelStatus.auto_train_every_feedbacks} 条` : '未开启' }}</strong>
      </div>
    </div>
    <div class="dual-grid">
      <section class="soft-card status-block">
        <div class="card-head">
          <p class="eyebrow">激活模型</p>
          <h3>线上当前生效版本</h3>
        </div>
        <article
          v-for="item in modelStatus?.active_models || []"
          :key="`active-${item.model_type}-${item.version}`"
          class="train-card"
        >
          <strong>{{ item.model_type }}</strong>
          <p>版本：{{ item.version }}</p>
          <p>样本：{{ metricNumber(item.metrics, 'train_count') }}，MAE：{{ metricNumber(item.metrics, 'mae', 4) }}</p>
          <p>场景：{{ item.scene_key || '全局通用' }}</p>
        </article>
        <p v-if="!(modelStatus?.active_models?.length)" class="helper-text">当前还没有激活模型，系统会回退到启发式预测。</p>
      </section>

      <section class="soft-card status-block">
        <div class="card-head">
          <p class="eyebrow">最近训练记录</p>
          <h3>方便你确认模型是否真的在迭代</h3>
        </div>
        <article
          v-for="item in modelStatus?.recent_models || []"
          :key="`recent-${item.model_type}-${item.version}`"
          class="train-card"
        >
          <strong>{{ item.model_type }}</strong>
          <p>版本：{{ item.version }}</p>
          <p>时间：{{ formatDate(item.created_at) }}</p>
          <p>RMSE：{{ metricNumber(item.metrics, 'rmse', 4) }}</p>
        </article>
        <p v-if="!(modelStatus?.recent_models?.length)" class="helper-text">还没有训练记录，先积累回填样本再训练会更稳。</p>
      </section>
    </div>
  </section>

  <section v-if="reportUnlocked" class="info-row">
    <div class="card mentor-card">
      <div class="card-head">
        <p class="eyebrow">导师沟通摘要</p>
        <h3>{{ report.mentor_brief.headline }}</h3>
      </div>
      <p>{{ report.mentor_brief.summary }}</p>
      <blockquote>{{ report.mentor_brief.suggested_message }}</blockquote>
    </div>

    <div class="card checklist-card">
      <div class="card-head">
        <p class="eyebrow">正式送检前检查清单</p>
        <h3>别把时间花在无效修改上</h3>
      </div>
      <div class="checklist-list">
        <label v-for="(item, index) in checklist" :key="item.label" class="check-item">
          <el-checkbox v-model="checklist[index].done">{{ item.label }}</el-checkbox>
        </label>
      </div>
    </div>
  </section>

  <section class="notice">
    <p>{{ report.disclaimer }}</p>
    <p>{{ report.retained_content_policy }}</p>
  </section>

  <!-- 上传新知网报告对话框 -->
  <el-dialog
    v-model="cnkiUploadDialogVisible"
    title="上传新知网检测报告"
    width="560px"
    destroy-on-close
  >
    <div class="cnki-upload-dialog">
      <p class="dialog-hint">改写后重新送检了？上传最新报告，系统会对比前后变化并更新改写建议。</p>

      <div
        v-if="!cnkiUploadFile"
        class="cnki-upload-drop"
        @click="cnkiUploadInputRef?.click()"
      >
        <input
          ref="cnkiUploadInputRef"
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.bmp"
          class="file-input-hidden"
          @change="handleCnkiUploadSelect"
        />
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
        <p>点击选择知网报告截图或 PDF</p>
        <span>支持 .pdf、.png、.jpg，最大 50MB</span>
      </div>

      <div v-else class="cnki-upload-preview">
        <div class="file-preview">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          <div>
            <strong>{{ cnkiUploadFile.name }}</strong>
            <span>{{ (cnkiUploadFile.size / 1024 / 1024).toFixed(1) }} MB</span>
          </div>
          <button type="button" class="btn-icon" @click="removeCnkiUploadFile">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
      </div>

      <div v-if="cnkiUploadOcrLoading" class="cnki-dialog-loading">
        <el-skeleton :rows="2" animated />
      </div>
      <div v-else-if="cnkiUploadOcrError" class="cnki-dialog-error">
        <el-alert :title="cnkiUploadOcrError" type="warning" :closable="false" show-icon />
      </div>
      <div v-else-if="cnkiUploadOcrPreview" class="cnki-ocr-preview-mini">
        <p>{{ cnkiUploadOcrPreview.extracted_text_preview }}</p>
      </div>

      <div class="cnki-dialog-form">
        <div class="form-row">
          <div class="form-field">
            <label>知网查重率（%）</label>
            <input v-model.number="cnkiUploadForm.cnkiDupPercent" type="number" step="0.1" min="0" max="100" placeholder="例如 12.5" />
          </div>
          <div class="form-field">
            <label>知网 AIGC 率（%）</label>
            <input v-model.number="cnkiUploadForm.cnkiAigcPercent" type="number" step="0.1" min="0" max="100" placeholder="例如 8.3" />
          </div>
        </div>
        <div class="form-field">
          <label>报告日期</label>
          <input v-model="cnkiUploadForm.reportDate" type="date" />
        </div>
        <div class="form-field">
          <label>备注（可选）</label>
          <input v-model="cnkiUploadForm.notes" type="text" placeholder="例如：第 2 次修改后检测" />
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="cnkiUploadDialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="cnkiUploadLoading" @click="submitNewCnkiReport">
        确认上传
      </el-button>
    </template>
  </el-dialog>

  <el-dialog
    v-model="rewriteDialogVisible"
    :title="`AI 改写建议 - ${currentRewriteSectionTitle}`"
    width="820px"
    destroy-on-close
    class="rewrite-dialog"
  >
    <div v-if="rewriteDialogLoading" class="rewrite-skeleton">
      <el-skeleton :rows="6" animated />
      <p class="skeleton-hint">正在连接 AI 改写服务，请稍候（若第三方服务繁忙，可能需要 30-90 秒）...</p>
    </div>
    <div v-else-if="currentRewriteAdvice?.error" class="rewrite-error">
      <el-result icon="error" title="改写建议获取失败" :sub-title="currentRewriteAdvice.error">
        <template #extra>
          <el-button type="primary" @click="retryRewriteAdvice">重试</el-button>
        </template>
      </el-result>
      <p class="helper-text">可能是第三方 API 限流或配置问题，点击重试即可。</p>
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
        AI 服务当前不可用，以下为系统离线生成的改写参考
      </el-tag>

      <div v-if="currentRewriteAdvice?.sentences?.length" class="rewrite-block">
        <h4 class="block-title">
          <el-icon><EditPen /></el-icon> 逐句改写对比
        </h4>
        <div v-for="(sentence, idx) in currentRewriteAdvice.sentences" :key="idx" class="sentence-card">
          <div class="sentence-header">
            <el-tag :type="tagType(sentence.risk)" size="small" effect="dark">{{ riskText(sentence.risk) }}</el-tag>
            <span class="sentence-num">第 {{ idx + 1 }} 句</span>
          </div>
          <div class="sentence-body">
            <div class="sentence-row original-box">
              <label>原句</label>
              <p>{{ sentence.original }}</p>
            </div>
            <div class="arrow-divider">
              <el-icon><Bottom /></el-icon>
            </div>
            <div class="sentence-row rewritten-box">
              <label>改写后</label>
              <p>{{ sentence.rewritten }}</p>
            </div>
            <div class="sentence-row explanation-box">
              <label>改动原理</label>
              <p>{{ sentence.explanation }}</p>
            </div>
          </div>
        </div>
      </div>

      <div v-if="currentRewriteAdvice?.rewritten_paragraph" class="rewrite-block">
        <h4 class="block-title">
          <el-icon><DocumentCopy /></el-icon> 改后完整段落参考
        </h4>
        <el-card shadow="never" class="paragraph-card">
          <p class="paragraph-text">{{ currentRewriteAdvice.rewritten_paragraph }}</p>
          <div class="paragraph-actions">
            <el-button
              type="primary"
              plain
              size="small"
              @click="copyText(currentRewriteAdvice.rewritten_paragraph, '已复制改后段落')"
            >
              <el-icon><DocumentCopy /></el-icon> 复制全文
            </el-button>
          </div>
        </el-card>
      </div>

      <div v-if="currentRewriteAdvice?.overall_advice" class="rewrite-block">
        <h4 class="block-title">
          <el-icon><Warning /></el-icon> 整体修改策略
        </h4>
        <el-alert :title="currentRewriteAdvice.overall_advice" type="warning" :closable="false" show-icon />
      </div>
    </div>
  </el-dialog>

  <UnlockModal
    v-model="unlockModalVisible"
    :run-id="runStatus?.run_id || ''"
    :package-code="currentUnlockPackageCode"
    :packages="unlockPackages"
    @unlocked="onUnlocked"
  />
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus/es/components/message/index'
import { EditPen, Bottom, DocumentCopy, Warning, Upload, Lock } from '@element-plus/icons-vue'
import { getRewriteAdvice, previewCnkiFeedbackOcr, submitCnkiFeedback, getUnlockStatus, getUnlockPackages } from '../api'
import type {
  AnalysisRunStatusResponse,
  ChecklistItem,
  ModelStatusResponse,
  RewriteAdviceResponse,
  ScoreBand,
  UnifiedReportResponse,
  UnlockPackage,
  UnlockOrder
} from '../types'
import UnlockModal from './UnlockModal.vue'

const router = useRouter()

const props = defineProps<{
  report: UnifiedReportResponse
  runStatus: AnalysisRunStatusResponse | null
  modelStatus: ModelStatusResponse | null
}>()

const emit = defineEmits<{
  refresh: []
}>()

const checklist = ref<ChecklistItem[]>([])

// 解锁状态
const reportUnlocked = ref(false)
const unlockModalVisible = ref(false)
const unlockPackages = ref<UnlockPackage[]>([])
const currentUnlockPackageCode = ref('unlock_report')
const checkingUnlock = ref(false)

async function checkUnlockStatus() {
  if (!props.runStatus?.run_id) return
  checkingUnlock.value = true
  try {
    const status = await getUnlockStatus(props.runStatus.run_id, 'unlock_report')
    reportUnlocked.value = status.unlocked
  } catch {
    reportUnlocked.value = false
  } finally {
    checkingUnlock.value = false
  }
}

onMounted(async () => {
  unlockPackages.value = await getUnlockPackages().catch(() => [])
  await checkUnlockStatus()
})

watch(() => props.runStatus?.run_id, checkUnlockStatus)

function openUnlockModal(packageCode: string) {
  currentUnlockPackageCode.value = packageCode
  unlockModalVisible.value = true
}

function onUnlocked(order: UnlockOrder) {
  reportUnlocked.value = true
  ElMessage.success('解锁成功')
}

const rewriteDialogVisible = ref(false)
const rewriteDialogLoading = ref(false)
const currentRewriteAdvice = ref<RewriteAdviceResponse | null>(null)
const currentRewriteSectionTitle = ref('')
const currentRewriteSectionIndex = ref(0)
const rewriteLoadingMap = ref<Record<number, boolean>>({})

// CNKI iterative upload
const cnkiUploadDialogVisible = ref(false)
const cnkiUploadFile = ref<File | null>(null)
const cnkiUploadLoading = ref(false)
const cnkiUploadOcrLoading = ref(false)
const cnkiUploadOcrPreview = ref<any>(null)
const cnkiUploadOcrError = ref('')
const cnkiUploadInputRef = ref<HTMLInputElement | null>(null)
const cnkiUploadForm = ref({
  cnkiDupPercent: undefined as number | undefined,
  cnkiAigcPercent: undefined as number | undefined,
  reportDate: '',
  notes: '',
  removeReferenceDupPercent: undefined as number | undefined,
  singleMaxDupPercent: undefined as number | undefined,
  suspectedPlagiarism: undefined as Record<string, number> | undefined,
  fragments: undefined as any[] | undefined,
})

const latestFeedback = computed(() => {
  const tl = props.report.feedback_timeline
  return tl.length > 0 ? tl[0] : null
})

const previousFeedback = computed(() => {
  const tl = props.report.feedback_timeline
  return tl.length > 1 ? tl[1] : null
})

const isPassed = computed(() => {
  const latest = latestFeedback.value
  if (!latest) return false
  const dup = latest.cnki_dup_percent
  const aigc = latest.cnki_aigc_percent
  if (dup == null || aigc == null) return false
  // 知网通常要求查重 < 20%，AIGC < 30%（不同学校有差异，这里用通用标准）
  return dup < 20 && aigc < 30
})

const hasExtendedMetrics = computed(() => {
  const d = props.report.cnki_report_details
  if (!d) return false
  return (
    d.single_max_dup_percent != null ||
    d.remove_reference_dup_percent != null ||
    (d.suspected_plagiarism && Object.keys(d.suspected_plagiarism).length > 0) ||
    (d.fragments && d.fragments.length > 0)
  )
})

const cnkiGapWarning = computed(() => {
  const latest = latestFeedback.value
  if (!latest) return ''
  const cnkiAigc = latest.cnki_aigc_percent
  const cnkiDup = latest.cnki_dup_percent
  const parts: string[] = []
  if (cnkiAigc != null && cnkiAigc >= 40) {
    parts.push(`知网实测 AIGC 率为 ${cnkiAigc.toFixed(1)}%，处于极高风险区间。当前改写建议已按知网最严格标准调整，建议对全文进行深度改写。`)
  } else if (cnkiAigc != null && cnkiAigc >= 30) {
    parts.push(`知网实测 AIGC 率为 ${cnkiAigc.toFixed(1)}%，已超出安全阈值。当前改写建议已按知网高标准调整，建议全面改写。`)
  }
  if (cnkiDup != null && cnkiDup >= 30) {
    parts.push(`知网实测查重率为 ${cnkiDup.toFixed(1)}%，重复风险较高，建议优先处理重复片段。`)
  }
  return parts.join('')
})

// 基于知网实测数据重新计算风险等级和风险指数
const cnkiBasedRisk = computed(() => {
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
  // 基于知网数据重新计算：查重权重 42%，AIGC 权重 38%，高阈值惩罚
  let score = 100 - dup * 0.42 - aigc * 0.38
  if (aigc >= 30) score -= 15
  if (dup >= 20) score -= 10
  return Math.max(10, Math.min(95, Math.round(score)))
})

const cnkiBasedJudgement = computed(() => {
  const latest = latestFeedback.value
  if (!latest) return props.report.summary.one_line_judgement
  const aigc = latest.cnki_aigc_percent
  const dup = latest.cnki_dup_percent
  if (aigc != null && aigc >= 40) {
    return `知网实测 AIGC 率为 ${aigc.toFixed(1)}%，处于极高风险区间。建议对全文进行深度改写，系统已按知网最严格标准优化改写建议。`
  }
  if (aigc != null && aigc >= 30) {
    return `知网实测 AIGC 率为 ${aigc.toFixed(1)}%，已超出安全阈值。建议按知网标准全面改写，系统已优化改写策略。`
  }
  if (dup != null && dup >= 30) {
    return `知网实测查重率为 ${dup.toFixed(1)}%，重复风险较高。建议优先处理重复片段，再进行 AIGC 优化。`
  }
  return `知网实测数据显示当前论文风险可控（AIGC ${aigc?.toFixed(1) ?? '-'}%，查重 ${dup?.toFixed(1) ?? '-'}%），可针对局部问题进行精修。`
})

const cnkiGapSummary = computed(() => {
  const latest = latestFeedback.value
  if (!latest) return '-'
  const aigcGap = latest.cnki_aigc_percent != null ? (latest.cnki_aigc_percent - props.report.local_metrics.ai_like_score * 100).toFixed(0) : null
  const dupGap = latest.cnki_dup_percent != null ? (latest.cnki_dup_percent - props.report.local_metrics.duplication_score * 100).toFixed(0) : null
  const parts: string[] = []
  if (aigcGap != null && Math.abs(Number(aigcGap)) > 5) parts.push(`AIGC ${aigcGap > '0' ? '+' : ''}${aigcGap}%`)
  if (dupGap != null && Math.abs(Number(dupGap)) > 5) parts.push(`查重 ${dupGap > '0' ? '+' : ''}${dupGap}%`)
  return parts.length ? parts.join(' / ') : '基本吻合'
})

function openCnkiUploadDialog() {
  cnkiUploadFile.value = null
  cnkiUploadOcrPreview.value = null
  cnkiUploadOcrError.value = ''
  cnkiUploadForm.value = { cnkiDupPercent: undefined, cnkiAigcPercent: undefined, reportDate: '', notes: '', removeReferenceDupPercent: undefined, singleMaxDupPercent: undefined, suspectedPlagiarism: undefined, fragments: undefined }
  cnkiUploadDialogVisible.value = true
}

function handleCnkiUploadSelect(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) processCnkiUploadFile(file)
  input.value = ''
}

async function processCnkiUploadFile(file: File) {
  if (file.size > 50 * 1024 * 1024) {
    ElMessage.warning('文件大小不能超过 50MB')
    return
  }
  cnkiUploadFile.value = file
  cnkiUploadOcrLoading.value = true
  cnkiUploadOcrError.value = ''
  try {
    const preview = await previewCnkiFeedbackOcr(file)
    cnkiUploadOcrPreview.value = preview
    if (preview.cnki_dup_percent != null) cnkiUploadForm.value.cnkiDupPercent = preview.cnki_dup_percent
    if (preview.cnki_aigc_percent != null) cnkiUploadForm.value.cnkiAigcPercent = preview.cnki_aigc_percent
    if (preview.report_date) cnkiUploadForm.value.reportDate = preview.report_date
    if (preview.remove_reference_dup_percent != null) cnkiUploadForm.value.removeReferenceDupPercent = preview.remove_reference_dup_percent
    if (preview.single_max_dup_percent != null) cnkiUploadForm.value.singleMaxDupPercent = preview.single_max_dup_percent
    if (preview.suspected_plagiarism) cnkiUploadForm.value.suspectedPlagiarism = preview.suspected_plagiarism
    if (preview.fragments && preview.fragments.length > 0) cnkiUploadForm.value.fragments = preview.fragments
  } catch (err) {
    cnkiUploadOcrError.value = err instanceof Error ? err.message : 'OCR 识别失败'
  } finally {
    cnkiUploadOcrLoading.value = false
  }
}

function removeCnkiUploadFile() {
  cnkiUploadFile.value = null
  cnkiUploadOcrPreview.value = null
  cnkiUploadOcrError.value = ''
  cnkiUploadForm.value = { cnkiDupPercent: undefined, cnkiAigcPercent: undefined, reportDate: '', notes: '', removeReferenceDupPercent: undefined, singleMaxDupPercent: undefined, suspectedPlagiarism: undefined, fragments: undefined }
}

async function submitNewCnkiReport() {
  if (!cnkiUploadFile.value && cnkiUploadForm.value.cnkiDupPercent == null && cnkiUploadForm.value.cnkiAigcPercent == null) {
    ElMessage.warning('请上传报告文件或至少填写一项指标')
    return
  }
  cnkiUploadLoading.value = true
  try {
    await submitCnkiFeedback({
      documentId: props.report.document_id,
      predictedRunId: props.report.run_id,
      cnkiDupPercent: cnkiUploadForm.value.cnkiDupPercent ?? null,
      cnkiAigcPercent: cnkiUploadForm.value.cnkiAigcPercent ?? null,
      reportDate: cnkiUploadForm.value.reportDate || undefined,
      notes: cnkiUploadForm.value.notes || undefined,
      removeReferenceDupPercent: cnkiUploadForm.value.removeReferenceDupPercent ?? null,
      singleMaxDupPercent: cnkiUploadForm.value.singleMaxDupPercent ?? null,
      suspectedPlagiarism: cnkiUploadForm.value.suspectedPlagiarism ?? null,
      fragments: cnkiUploadForm.value.fragments ?? null,
      evidenceFile: cnkiUploadFile.value
    })
    ElMessage.success('知网报告已上传成功')
    cnkiUploadDialogVisible.value = false
    emit('refresh')
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '上传失败')
  } finally {
    cnkiUploadLoading.value = false
  }
}

function deltaClass(delta: number | null | undefined) {
  if (delta == null) return ''
  return delta < 0 ? 'delta-good' : delta > 0 ? 'delta-bad' : 'delta-neutral'
}

function deltaIcon(delta: number | null | undefined) {
  if (delta == null) return ''
  return delta < 0 ? '↓' : delta > 0 ? '↑' : '→'
}

watch(
  () => props.report.submission_checklist,
  (items) => {
    checklist.value = items.map((item) => ({ ...item }))
  },
  { immediate: true, deep: true }
)


async function openRewriteAdvice(sectionIndex: number) {
  const section = props.report.top_risk_sections.find((s) => s.section_index === sectionIndex)
  currentRewriteSectionTitle.value = section?.title || `段落 ${sectionIndex + 1}`
  currentRewriteSectionIndex.value = sectionIndex
  rewriteLoadingMap.value[sectionIndex] = true
  rewriteDialogLoading.value = true
  currentRewriteAdvice.value = null
  rewriteDialogVisible.value = true
  try {
    const advice = await getRewriteAdvice(props.report.run_id, sectionIndex)
    currentRewriteAdvice.value = advice
  } catch (error) {
    currentRewriteAdvice.value = {
      run_id: props.report.run_id,
      section_index: sectionIndex,
      diagnosis: '',
      sentences: [],
      rewritten_paragraph: '',
      overall_advice: '',
      error: error instanceof Error ? error.message : '获取改写建议失败',
    }
  } finally {
    rewriteDialogLoading.value = false
    rewriteLoadingMap.value[sectionIndex] = false
  }
}

async function retryRewriteAdvice() {
  const sectionIndex = currentRewriteSectionIndex.value
  rewriteDialogLoading.value = true
  try {
    const advice = await getRewriteAdvice(props.report.run_id, sectionIndex)
    currentRewriteAdvice.value = advice
  } catch (error) {
    currentRewriteAdvice.value = {
      run_id: props.report.run_id,
      section_index: sectionIndex,
      diagnosis: '',
      sentences: [],
      rewritten_paragraph: '',
      overall_advice: '',
      error: error instanceof Error ? error.message : '重试失败',
    }
  } finally {
    rewriteDialogLoading.value = false
  }
}

function openPrintReport() {
  const url = router.resolve({
    name: 'report-print',
    params: { runId: props.report.run_id }
  }).href
  window.open(url, '_blank')
}

function openRewriteEditor() {
  router.push(`/app/rewrite/${props.report.run_id}`)
}

async function copyMentorBrief() {
  const text = `${props.report.mentor_brief.headline}\n\n${props.report.mentor_brief.summary}\n\n${props.report.mentor_brief.suggested_message}`
  await copyText(text, '导师沟通摘要已复制')
}

async function copyRevisionPlan() {
  const planText = props.report.revision_plan
    .map((item) => `Step ${item.priority} ${item.title}\n为什么先改：${item.why}\n怎么改：${item.how_to_fix}\n预期收益：${item.expected_gain}`)
    .join('\n\n')
  await copyText(planText, '修改行动计划已复制')
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
    ElMessage.error(error instanceof Error ? error.message : '复制失败')
  }
}

function riskText(level: 'low' | 'medium' | 'high') {
  return level === 'high' ? '高风险' : level === 'medium' ? '中风险' : '低风险'
}

function tagType(level: 'low' | 'medium' | 'high') {
  return level === 'high' ? 'danger' : level === 'medium' ? 'warning' : 'success'
}

function bandText(band: ScoreBand) {
  return `${band.low_percent.toFixed(1)}%-${band.high_percent.toFixed(1)}%`
}

function formatDate(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function metricNumber(metrics: Record<string, unknown>, key: string, digits = 0) {
  const value = metrics[key]
  if (typeof value !== 'number') return digits > 0 ? (0).toFixed(digits) : '0'
  return digits > 0 ? value.toFixed(digits) : String(value)
}

function providerSourceText(value: string) {
  return value === 'manual_import' ? '手工导入' : '自动抓取'
}

function optionalPercent(value: number | null | undefined) {
  if (value == null) return '-'
  return `${value.toFixed(1)}%`
}

function confidenceText(value: number | null | undefined) {
  if (value == null) return '-'
  return `${Math.round(value * 100)}%`
}

function deltaText(value: number | null | undefined) {
  if (value == null) return '-'
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)} 个百分点`
}
</script>

<style scoped>
.lock-banner {
  background: linear-gradient(135deg, #fff8e1, #fff3e0);
  border: 1px dashed #ff9800;
}
.lock-content {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 20px;
}
.lock-icon {
  font-size: 40px;
  color: #ff9800;
  flex-shrink: 0;
}
.lock-text {
  flex: 1;
}
.lock-text h3 {
  margin: 0 0 6px;
  color: #e65100;
  font-size: 18px;
}
.lock-text p {
  margin: 0;
  color: #666;
  font-size: 14px;
}
.rewrite-btn {
  margin-top: 12px;
}

.sub-score-bars {
  margin: 10px 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.sub-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
}
.sub-label {
  width: 28px;
  color: #888;
  flex-shrink: 0;
}
.sub-track {
  flex: 1;
  height: 6px;
  background: #eee;
  border-radius: 3px;
  overflow: hidden;
}
.sub-fill {
  height: 100%;
  border-radius: 3px;
}
.sub-ai { background: #e53935; }
.sub-template { background: #ff9800; }
.sub-empty { background: #9c27b0; }
.sub-repeat { background: #2196f3; }
.sub-cite { background: #795548; }
.sub-value {
  width: 22px;
  text-align: right;
  color: #666;
}
.rewrite-btn .el-icon {
  margin-right: 4px;
}
.rewrite-skeleton {
  padding: 20px;
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
  margin: 0 0 12px 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}
.diagnosis-alert {
  margin-bottom: 16px;
}
.sentence-card {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 16px;
  background: #fff;
}
.sentence-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.sentence-num {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.sentence-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.sentence-row {
  border-radius: 8px;
  padding: 12px;
}
.sentence-row label {
  display: block;
  font-weight: 600;
  font-size: 12px;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.sentence-row p {
  margin: 0;
  line-height: 1.7;
  font-size: 14px;
}
.original-box {
  background: var(--el-fill-color-light);
  border-left: 3px solid var(--el-text-color-disabled);
}
.original-box label {
  color: var(--el-text-color-secondary);
}
.arrow-divider {
  display: flex;
  justify-content: center;
  color: var(--el-color-primary);
  font-size: 18px;
}
.rewritten-box {
  background: var(--el-color-primary-light-9);
  border-left: 3px solid var(--el-color-primary);
}
.rewritten-box label {
  color: var(--el-color-primary);
}
.rewritten-box p {
  color: var(--el-text-color-primary);
  font-weight: 500;
}
.explanation-box {
  background: #fffbe6;
  border-left: 3px solid #f0c040;
  margin-top: 4px;
}
.explanation-box label {
  color: #a67c00;
}
.explanation-box p {
  font-size: 13px;
  color: var(--el-text-color-regular);
}
.paragraph-card {
  background: var(--el-fill-color-lighter);
}
.paragraph-text {
  margin: 0 0 12px 0;
  line-height: 1.8;
  white-space: pre-wrap;
  font-size: 14px;
  color: var(--el-text-color-primary);
}
.paragraph-actions {
  display: flex;
  justify-content: flex-end;
}
.rewrite-error {
  padding: 20px 0;
}
.skeleton-hint {
  margin-top: 12px;
  font-size: 13px;
  color: #8b95a2;
  text-align: center;
}
.fallback-tag {
  margin-bottom: 16px;
}

/* CNKI upload dialog */
.cnki-upload-dialog {
  display: grid;
  gap: 16px;
}
.dialog-hint {
  margin: 0;
  font-size: 13px;
  color: #8b95a2;
  line-height: 1.6;
}
.cnki-upload-drop {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 120px;
  padding: 24px;
  border: 2px dashed rgba(31, 54, 73, 0.15);
  border-radius: 12px;
  cursor: pointer;
  color: #8b95a2;
  transition: all 0.2s;
}
.cnki-upload-drop:hover {
  border-color: #2f7d67;
  background: rgba(47, 125, 103, 0.03);
  color: #2f7d67;
}
.cnki-upload-drop p {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
}
.cnki-upload-drop span {
  font-size: 12px;
}
.cnki-upload-preview {
  padding: 12px;
  background: #f8f9fa;
  border-radius: 10px;
}
.cnki-dialog-loading,
.cnki-dialog-error {
  margin-top: 4px;
}
.cnki-ocr-preview-mini {
  padding: 10px;
  background: #f8f9fa;
  border-radius: 8px;
}
.cnki-ocr-preview-mini p {
  margin: 0;
  font-size: 12px;
  color: #8b95a2;
  line-height: 1.5;
}
.cnki-dialog-form {
  display: grid;
  gap: 14px;
}
.cnki-dialog-form .form-field input {
  width: 100%;
  padding: 10px 14px;
  border: 1.5px solid rgba(31, 54, 73, 0.15);
  border-radius: 10px;
  font-size: 15px;
  color: #172033;
  background: #fff;
  outline: none;
  box-sizing: border-box;
}
.cnki-dialog-form .form-field input:focus {
  border-color: #2f7d67;
}
.cnki-dialog-form .form-field label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #344150;
  margin-bottom: 6px;
}

/* Pass banner */
.pass-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
  border-radius: 12px;
  margin-bottom: 16px;
  color: #2e7d32;
}
.pass-banner svg {
  flex-shrink: 0;
}
.pass-banner strong {
  display: block;
  font-size: 15px;
  margin-bottom: 2px;
}
.pass-banner span {
  font-size: 13px;
  opacity: 0.85;
}

/* CNKI primary metric cards */
.metric-card.cnki-primary {
  background: linear-gradient(135deg, rgba(47, 125, 103, 0.08), rgba(47, 125, 103, 0.03));
  border: 1.5px solid rgba(47, 125, 103, 0.2);
}
.metric-card.cnki-primary span {
  color: #2f7d67;
  font-weight: 600;
}
.metric-card.cnki-primary strong {
  color: #ffffff;
  font-size: 28px;
  text-shadow: 0 1px 2px rgba(0,0,0,0.15);
}

/* CNKI gap alert */
.cnki-gap-alert {
  margin-bottom: 20px;
}
.gap-alert-content {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 16px 18px;
  background: linear-gradient(135deg, #ffebee, #ffcdd2);
  border-radius: 14px;
  color: #c62828;
  border: 1px solid rgba(198, 40, 40, 0.15);
}
.gap-alert-content svg {
  flex-shrink: 0;
  margin-top: 2px;
}
.gap-alert-content strong {
  display: block;
  font-size: 15px;
  margin-bottom: 6px;
}
.gap-alert-content p {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  opacity: 0.9;
}

/* Iteration compare */
.iteration-compare {
  padding: 12px 14px;
  background: #f5f7f9;
  border-radius: 10px;
  margin-bottom: 16px;
}
.compare-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.compare-label {
  font-size: 13px;
  font-weight: 600;
  color: #344150;
}
.compare-values {
  display: flex;
  gap: 14px;
}
.compare-values span {
  font-size: 13px;
  font-weight: 500;
}
.delta-good {
  color: #2e7d32;
}
.delta-bad {
  color: #c84b52;
}
.delta-neutral {
  color: #8b95a2;
}

/* CNKI upload action */
.cnki-upload-action {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(31, 54, 73, 0.06);
  display: flex;
  justify-content: center;
}

/* CNKI report details */
.cnki-details-card {
  background: linear-gradient(135deg, #f8fafb, #ffffff);
  border: 1.5px solid rgba(47, 125, 103, 0.12);
}
.cnki-extended-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}
.cnki-extended-metrics .status-tile {
  padding: 14px 16px;
}
.cnki-extended-metrics .status-tile strong {
  font-size: 20px;
  color: #1f3649;
}
.plagiarism-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}
.cnki-fragments {
  margin-top: 8px;
}
.fragment-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 12px;
}
.fragment-card {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  padding: 16px;
  background: #fff;
  transition: all 0.2s;
}
.fragment-card.fragment-matched {
  border-color: rgba(47, 125, 103, 0.25);
  background: linear-gradient(135deg, #f8fafb, #ffffff);
}
.fragment-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.fragment-origin {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.fragment-match-ratio {
  font-size: 12px;
  color: #2f7d67;
  font-weight: 600;
  margin-left: auto;
}
.fragment-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.fragment-body > div {
  border-radius: 8px;
  padding: 12px;
  background: var(--el-fill-color-light);
}
.fragment-body > div.fragment-similar {
  background: #fff2f0;
  border-left: 3px solid var(--el-color-danger);
}
.fragment-body > div.fragment-match {
  background: #f0f9ff;
  border-left: 3px solid #2f7d67;
}
.fragment-body label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--el-text-color-secondary);
  margin-bottom: 6px;
}
.fragment-body p {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--el-text-color-primary);
}
.fragment-body .match-preview {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-top: 4px;
}
.fragment-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.rewrite-editor-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 2000;
  background: #fff;
  display: flex;
  flex-direction: column;
}

.rewrite-editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  border-bottom: 1px solid #e8e8e8;
  background: #fafbfc;
}

.rewrite-editor-header h2 {
  margin: 0;
  font-size: 18px;
  color: #172033;
}

.rewrite-editor-overlay .rewrite-editor {
  flex: 1;
  overflow: hidden;
}
</style>
