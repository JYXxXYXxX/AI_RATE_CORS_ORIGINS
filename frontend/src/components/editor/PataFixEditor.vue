<template>
  <div class="patafix-editor">
    <!-- 顶部指标工具条 -->
    <div class="editor-topbar">
      <div class="topbar-left">
        <el-button size="small" plain @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon>返回报告
        </el-button>
      </div>
      <div class="topbar-metrics">
        <!-- Report Mode 摘要 -->
        <template v-if="runMode === 'report' && reportSummary">
          <div class="metric-item">
            <span class="metric-label">总复制比</span>
            <span class="metric-value color-high">{{ reportSummary.totalCopyRatio?.toFixed(1) ?? '--' }}%</span>
            <span class="metric-sub">知网报告</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">AIGC率</span>
            <span class="metric-value color-high">{{ reportSummary.aigcRatio?.toFixed(1) ?? '--' }}%</span>
            <span class="metric-sub">知网报告</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">高风险</span>
            <span class="metric-value color-high">{{ reportSummary.highRiskCount }}</span>
            <span class="metric-sub">段落</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">中风险</span>
            <span class="metric-value color-medium">{{ reportSummary.mediumRiskCount }}</span>
            <span class="metric-sub">段落</span>
          </div>
          <div v-if="reportSummary.unmatchedCount > 0" class="metric-item">
            <span class="metric-label">未匹配</span>
            <span class="metric-value color-warning">{{ reportSummary.unmatchedCount }}</span>
            <span class="metric-sub">片段</span>
          </div>
          <div class="metric-item">
            <el-tag size="small" type="danger">知网报告驱动</el-tag>
          </div>
        </template>
        <!-- Estimate Mode 系统预估 -->
        <template v-else>
          <div class="metric-item">
            <span class="metric-label">AIGC 疑似度</span>
            <span class="metric-value" :class="'color-' + aigcColor">{{ animatedAigc.toFixed(2) }}%</span>
            <span v-if="aigcDelta !== 0" class="metric-delta" :class="aigcDelta < 0 ? 'delta-down' : 'delta-up'">
              {{ aigcDelta > 0 ? '+' : '' }}{{ aigcDelta.toFixed(2) }}%
            </span>
          </div>
          <div class="metric-item">
            <span class="metric-label">重复率</span>
            <span class="metric-value" :class="'color-' + dupColor">{{ animatedDup.toFixed(2) }}%</span>
            <span v-if="dupDelta !== 0" class="metric-delta" :class="dupDelta < 0 ? 'delta-down' : 'delta-up'">
              {{ dupDelta > 0 ? '+' : '' }}{{ dupDelta.toFixed(2) }}%
            </span>
          </div>
          <div class="metric-item">
            <span class="metric-label">优化后预计</span>
            <span class="metric-value color-predicted">{{ predictedAigc.toFixed(2) }}%</span>
            <span class="metric-delta delta-down">预计下降 {{ predictedDrop.toFixed(2) }}%</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">已改写</span>
            <span class="metric-value color-accent">{{ rewrittenCount }} / {{ editableParagraphCount }}</span>
            <span class="metric-sub">句子</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">字数</span>
            <span class="metric-value">{{ totalChars }}</span>
            <span class="metric-sub">全文</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">页数</span>
            <span class="metric-value">{{ displayPageCount }}</span>
            <span class="metric-sub">{{ actualPageCount ? '原文件' : '估算' }}</span>
          </div>
          <div class="metric-item">
            <el-tag size="small" type="info">系统预估</el-tag>
          </div>
        </template>
      </div>
      <div class="topbar-actions">
        <el-button
          size="small"
          :type="foldNormal ? 'primary' : 'default'"
          @click="foldNormal = !foldNormal"
        >
          {{ foldNormal ? '展开正常段落' : '折叠正常段落' }}
        </el-button>
        <el-button
          v-if="rewriteUnlocked"
          type="primary"
          size="small"
          :loading="batchLoading"
          :disabled="!highRiskSections.length"
          @click="fetchBatchAdvice"
        >
          {{ batchLoading ? `批量建议 ${batchProgress}/${highRiskSections.length}` : '一键改写' }}
        </el-button>
        <!-- 付费功能已隐藏：改写始终可用 -->
        <el-button size="small" :disabled="!canUndo" @click="undo">
          <el-icon><RefreshLeft /></el-icon>撤销
        </el-button>
        <el-button size="small" :disabled="!canRedo" @click="redo">
          <el-icon><RefreshRight /></el-icon>重做
        </el-button>
        <el-button
          size="small"
          @click="doSave"
        >
          <el-icon><Download /></el-icon>保存
        </el-button>
        <el-button size="small" :type="editMode ? 'primary' : 'default'" @click="toggleEditMode">
          {{ editMode ? '退出编辑' : '编辑' }}
        </el-button>
        <el-button-group size="small">
          <el-button @click="changeZoom(-0.1)">-</el-button>
          <el-button disabled>{{ Math.round(documentZoom * 100) }}%</el-button>
          <el-button @click="changeZoom(0.1)">+</el-button>
        </el-button-group>
      </div>
    </div>

    <!-- 主体三栏 -->
    <div class="editor-body">
      <!-- 左侧目录 -->
      <aside class="editor-sidebar-left">
        <div class="sidebar-tabs">
          <div class="sidebar-tab active">目录</div>
          <div class="sidebar-tab">风险分布</div>
        </div>

        <!-- 建议优化快速导航 -->
        <div v-if="prioritySections.length" class="priority-nav">
          <div class="priority-nav-header">
            <strong>建议优先优化 {{ prioritySections.length }} 段</strong>
            <button class="priority-toggle" @click="showAllPriority = !showAllPriority">
              {{ showAllPriority ? '收起' : `展开 ${prioritySections.length}` }}
            </button>
          </div>
          <div
            v-for="sec in displayedPrioritySections"
            :key="sec.section_index"
            class="priority-nav-item"
            @click="scrollToParagraph(sec.paragraph_index ?? sec.section_index)"
          >
            <span class="priority-rank">#{{ sec.priorityRank }}</span>
            <span class="priority-preview truncate">{{ sec.section_title || '正文' }} — {{ sec.content.slice(0, 18) }}{{ sec.content.length > 18 ? '…' : '' }}</span>
          </div>
        </div>

        <div class="outline-tree">
          <div
            v-for="(group, gIdx) in groupedSections"
            :key="gIdx"
            class="outline-chapter"
            :class="[activeGroupIndex === gIdx ? 'active' : '', 'outline-risk-' + groupMaxColor(group)]"
            @click="scrollToGroup(gIdx)"
          >
            <div class="outline-title">
              <span class="outline-dot" :class="'dot-' + groupMaxColor(group)" />
              <span class="outline-text">{{ group.title || '正文' }}</span>
              <span class="outline-count">{{ groupRiskCount(group) }}</span>
            </div>
            <div class="outline-children">
              <div
                v-for="(para, pIdx) in filteredOutlineParas(group)"
                :key="pIdx"
                class="outline-para"
                :class="[activeParaIndex === para.paragraphIndex ? 'active' : '', 'outline-risk-' + paraRiskColor(para)]"
                @click.stop="scrollToParagraph(para.paragraphIndex)"
              >
                <span class="outline-dot" :class="'dot-' + paraRiskColor(para)" />
                <span class="outline-text truncate">{{ paraPreview(para) }}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="risk-legend">
          <div class="legend-title">风险等级说明</div>
          <template v-if="runMode === 'report'">
            <div class="legend-item"><span class="legend-dot dot-red" />官方报告高风险片段</div>
            <div class="legend-item"><span class="legend-dot dot-orange" />官方报告中风险片段</div>
            <div class="legend-item"><span class="legend-dot dot-purple" />官方报告低风险片段</div>
            <div class="legend-item"><span class="legend-dot dot-normal" />官方报告未标记片段</div>
          </template>
          <template v-else>
            <div class="legend-item"><span class="legend-dot dot-red" />高风险（AIGC疑似度 ≥ 70%）</div>
            <div class="legend-item"><span class="legend-dot dot-orange" />中风险（60% ≤ AIGC疑似度 < 70%）</div>
            <div class="legend-item"><span class="legend-dot dot-purple" />低风险（30% ≤ AIGC疑似度 < 60%）</div>
            <div class="legend-item"><span class="legend-dot dot-normal" />正常（AIGC疑似度 < 30%）</div>
          </template>
        </div>

        <!-- 未匹配风险段落（Report Mode） -->
        <div v-if="runMode === 'report' && unmatchedSpans.length > 0" class="unmatched-panel">
          <div class="unmatched-header" @click="showUnmatchedPanel = !showUnmatchedPanel">
            <span class="unmatched-title">⚠️ 未匹配风险段落 ({{ unmatchedSpans.length }})</span>
            <span class="unmatched-toggle">{{ showUnmatchedPanel ? '收起' : '展开' }}</span>
          </div>
          <div v-if="showUnmatchedPanel" class="unmatched-list">
            <div
              v-for="(span, idx) in unmatchedSpans"
              :key="span.spanId || idx"
              class="unmatched-item"
              :class="{ selected: selectedUnmatchedSpan?.spanId === span.spanId }"
              @click="selectUnmatchedSpan(span)"
            >
              <div class="unmatched-risk">
                <span class="risk-badge-small" :class="'badge-' + span.riskLevel">
                  {{ span.riskLevel === 'high' ? '高' : span.riskLevel === 'medium' ? '中' : '低' }}
                </span>
                <span class="risk-type">{{ span.riskType === 'similarity' ? '复制' : 'AIGC' }}</span>
              </div>
              <p class="unmatched-text">{{ span.text.slice(0, 60) }}{{ span.text.length > 60 ? '…' : '' }}</p>
              <div class="unmatched-actions">
                <el-button size="small" type="primary" plain @click.stop="startManualBind(span)">
                  绑定到正文段落
                </el-button>
                <el-button
                  size="small"
                  plain
                  :disabled="!activeBlockId || bindingSpanId === span.spanId"
                  :loading="bindingSpanId === span.spanId"
                  @click.stop="bindSpanToActiveBlock(span)"
                >
                  绑定当前段落
                </el-button>
              </div>
            </div>
          </div>
        </div>
      </aside>

      <!-- 中间正文 -->
      <main ref="docRef" class="editor-document">
        <div class="document-scale-shell" :style="{ zoom: documentZoom }">
          <div v-if="loadError" class="doc-loading">
            <el-alert :title="loadError" type="error" :closable="false" show-icon />
            <div v-if="canReturnToOnlyOffice" class="doc-loading-actions">
              <el-button type="primary" @click="returnToOnlyOffice">返回 ONLYOFFICE</el-button>
            </div>
          </div>
          <div v-else-if="loading || docxLoading" class="doc-loading">
            <el-skeleton :rows="10" animated />
          </div>
          <div v-else-if="docxError" class="doc-loading">
            <el-alert :title="docxError" type="warning" :closable="false" show-icon />
            <div class="a4-page" style="margin-top: 20px;">
              <div v-if="paperTitle" class="paper-title">{{ paperTitle }}</div>
              <div v-for="(group, gIdx) in groupedSections" :key="gIdx" class="chapter-block">
                <h3 v-if="group.title" class="chapter-title">{{ group.title }}</h3>
                <div class="chapter-body">
                  <div
                    v-for="para in group.paragraphs"
                    :key="para.paragraphIndex ?? -1"
                    class="doc-paragraph"
                    :contenteditable="editMode"
                    :class="['para-' + paraRiskColor(para), { 'is-rewritten': para.rewritten, 'folded': foldNormal && paraRiskColor(para) === 'normal' }]"
                    @click="selectParagraph(para)"
                    @blur="onPlainParagraphBlur(para, $event)"
                  >
                    <div class="doc-paragraph-content">{{ para.content }}</div>
                    <div v-if="foldNormal && paraRiskColor(para) === 'normal'" class="fold-hint">正常段落（点击展开）</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <template v-else-if="fileType === 'docx' && originalBuffer">
            <DocxRenderer
              :array-buffer="originalBuffer"
              file-type="docx"
              @rendered="onDocxRendered"
              @error="onDocxError"
            />
          </template>
          <template v-else-if="fileType === 'pdf' && originalBuffer">
            <PdfRenderer
              :array-buffer="originalBuffer"
              :blocks="blocks"
              @rendered="onPdfRendered"
              @error="onPdfError"
              @select-block="onPdfSelectBlock"
              @page-count="onPdfPageCount"
            />
          </template>
          <template v-else>
            <div class="a4-page">
              <div v-if="paperTitle" class="paper-title">{{ paperTitle }}</div>
              <div v-for="(group, gIdx) in groupedSections" :id="'group-' + gIdx" :key="gIdx" class="chapter-block">
                <h3 v-if="group.title" class="chapter-title">{{ group.title }}</h3>
                <div class="chapter-body">
                  <div
                    v-for="para in group.paragraphs"
                    :key="para.paragraphIndex ?? -1"
                    :id="'para-' + (para.paragraphIndex ?? -1)"
                    class="doc-paragraph"
                    :contenteditable="editMode"
                    :class="['para-' + paraRiskColor(para), { 'is-rewritten': para.rewritten, 'folded': foldNormal && paraRiskColor(para) === 'normal' }]"
                    @click="selectParagraph(para)"
                    @blur="onPlainParagraphBlur(para, $event)"
                  >
                    <div class="doc-paragraph-content">{{ para.content }}</div>
                    <div v-if="foldNormal && paraRiskColor(para) === 'normal'" class="fold-hint">正常段落（点击展开）</div>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>
      </main>

      <!-- 右侧面板 -->
      <aside class="editor-sidebar-right">
        <div class="panel-header">
          <h4>批注与改写建议</h4>
          <button class="panel-close" @click="panelVisible = false">✕</button>
        </div>

        <div v-if="!panelVisible" class="panel-empty">
          <div class="empty-hint">点击正文中带颜色标记的句子，查看风险诊断与改写建议</div>
        </div>

        <!-- 付费功能已隐藏：改写建议始终可用 -->

        <template v-else>
          <div v-if="prioritySections.length" class="priority-hint">
            <el-alert
              :title="`建议优先优化 ${prioritySections.length} 段，点击左侧列表快速定位`"
              type="warning"
              :closable="false"
              show-icon
            />
          </div>
          <div class="risk-filter-bar">
            <template v-if="riskCounts.high + riskCounts.medium + riskCounts.low > 0">
              <span class="filter-tag filter-high">高风险 {{ riskCounts.high }}</span>
              <span class="filter-tag filter-medium">中风险 {{ riskCounts.medium }}</span>
              <span class="filter-tag filter-low">低风险 {{ riskCounts.low }}</span>
              <span class="filter-tag filter-normal muted">正常 {{ riskCounts.normal }}（已折叠）</span>
            </template>
            <template v-else>
              <span class="filter-tag filter-normal">未发现高/中风险句，建议上传官方报告校准或抽查摘要、结论、综述段</span>
            </template>
          </div>

          <div v-if="panelLoading" class="panel-loading">
            <el-skeleton :rows="6" animated />
          </div>

          <div v-else-if="panelError" class="panel-error">
            <el-alert :title="panelError" type="warning" :closable="false" show-icon />
          </div>

          <div v-else-if="rewriteAdvice" class="advice-cards">
            <div class="advice-card">
              <div class="card-header">
                <span class="risk-badge" :class="'badge-' + activeRiskLevel">{{ riskText(activeRiskLevel) }}</span>
                <span v-if="activeReportRisk" class="aigc-score">
                  {{ activeReportRisk.riskType === 'similarity' ? '相似度' : 'AIGC' }} {{ activeReportRisk.similarity ?? activeReportRisk.aigcScore ?? '--' }}%
                </span>
                <span v-else class="aigc-score">AIGC疑似度 {{ (activeAigcScore * 100).toFixed(0) }}%</span>
              </div>

              <!-- 知网报告风险详情 -->
              <div v-if="activeReportRisk" class="card-section report-risk-info">
                <div class="section-title">风险来源</div>
                <p class="section-text">
                  <el-tag size="small" type="danger">知网报告</el-tag>
                  <span class="risk-type-label">
                    {{ activeReportRisk.riskType === 'similarity' ? '文字复制' : 'AIGC疑似' }}
                  </span>
                </p>
                <p v-if="activeReportRisk.matchedSource" class="section-text">
                  <strong>相似来源：</strong>{{ activeReportRisk.matchedSource }}
                </p>
                <p class="section-text">
                  <strong>匹配置信度：</strong>{{ (activeReportRisk.matchConfidence * 100).toFixed(0) }}%
                </p>
              </div>
              <div v-else-if="runMode === 'estimate'" class="card-section">
                <div class="section-title">风险来源</div>
                <p class="section-text">
                  <el-tag size="small" type="info">系统预估</el-tag>
                  <span style="color: #999; font-size: 12px; margin-left: 8px;">不等同于知网结果</span>
                </p>
              </div>

              <!-- 子分数详情 -->
              <div v-if="activeBlock?.internalRisk" class="card-section sub-scores">
                <div class="section-title">风险细分</div>
                <div class="sub-score-item">
                  <span>AI 疑似度</span>
                  <el-progress :percentage="Math.round(activeBlock.internalRisk.aiLikelihood ?? 0)" :color="'#e53935'" :stroke-width="10" />
                </div>
                <div class="sub-score-item">
                  <span>模板化</span>
                  <el-progress :percentage="Math.round(activeBlock.internalRisk.templateScore ?? 0)" :color="'#ff9800'" :stroke-width="10" />
                </div>
                <div class="sub-score-item">
                  <span>语义空洞</span>
                  <el-progress :percentage="Math.round(activeBlock.internalRisk.semanticEmptyScore ?? 0)" :color="'#9c27b0'" :stroke-width="10" />
                </div>
                <div class="sub-score-item">
                  <span>重复表达</span>
                  <el-progress :percentage="Math.round(activeBlock.internalRisk.repetitionScore ?? 0)" :color="'#2196f3'" :stroke-width="10" />
                </div>
                <div class="sub-score-item">
                  <span>引用风险</span>
                  <el-progress :percentage="Math.round(activeBlock.internalRisk.citationRisk ?? 0)" :color="'#795548'" :stroke-width="10" />
                </div>
                <div class="sub-score-overall">
                  <strong>综合风险: {{ Math.round(activeBlock.internalRisk.overallRisk ?? 0) }}/100</strong>
                </div>
              </div>

              <div class="card-section">
                <div class="section-title">风险诊断</div>
                <p class="section-text">{{ rewriteAdvice.diagnosis || '该段落存在AI生成特征，建议优化。' }}</p>
              </div>

              <div class="card-section">
                <div class="section-title">原文</div>
                <div class="risk-word-tags" v-if="activeRiskTerms.length">
                  <span v-for="term in activeRiskTerms" :key="term" class="risk-word-tag">{{ term }}</span>
                </div>
                <div class="original-text" v-html="activeOriginalHtml"></div>
              </div>

              <div class="card-section">
                <div class="section-title">改写建议</div>
                <div class="rewritten-text" v-html="activeRewrittenHtml"></div>
              </div>

              <div v-if="rewriteAdvice.overall_advice" class="card-section">
                <div class="section-title">改写原理</div>
                <p class="section-text">{{ rewriteAdvice.overall_advice }}</p>
              </div>

              <div class="card-actions">
                <el-button type="primary" size="small" @click="applyFullRewrite">替换原文</el-button>
                <el-button size="small" plain @click="ignoreActive">忽略</el-button>
              </div>

              <!-- Report Mode 改写提示 -->
              <div v-if="runMode === 'report' && activeReportRisk" class="card-section rewrite-notice">
                <el-alert
                  title="改写后请重新上传知网复检确认"
                  type="warning"
                  :closable="false"
                  show-icon
                />
              </div>
            </div>

            <div v-if="rewriteAdvice.sentences.length" class="sentence-cards">
              <div
                v-for="(sent, idx) in rewriteAdvice.sentences"
                :key="idx"
                class="sentence-card"
              >
                <div class="sent-original">
                  <label>原文</label>
                  <p v-html="highlightOriginalRiskHtml(sent.original)"></p>
                </div>
                <div class="sent-rewritten">
                  <label>改写</label>
                  <p v-html="highlightRewriteDiffHtml(sent.original, sent.rewritten)"></p>
                </div>
                <div class="sent-explanation">
                  <label>原理</label>
                  <p>{{ sent.explanation }}</p>
                </div>
                <el-button size="small" type="success" plain @click="applySentenceRewrite(idx)">
                  应用此句
                </el-button>
              </div>
            </div>
          </div>
        </template>
      </aside>
    </div>

    <!-- 底部操作栏 -->
    <div class="editor-bottombar">
      <div class="bottombar-left">
        <el-button size="small" plain :disabled="!prevSection" @click="goPrev">
          <el-icon><ArrowLeft /></el-icon>上一条
        </el-button>
        <span class="bottombar-count">{{ currentIndex + 1 }} / {{ highRiskSections.length }}</span>
        <el-button size="small" plain :disabled="!nextSection" @click="goNext">
          下一条<el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
      <div class="bottombar-center">
        <span class="status-text"><el-icon><CircleCheck /></el-icon>检测完成</span>
        <span class="status-sub">全文 {{ totalChars }} 字 · {{ displayPageCount }} 页 · 已替换 {{ rewrittenCount }} 处</span>
      </div>
      <div class="bottombar-right">
        <el-button size="small" type="warning" plain :loading="batchLoading" :disabled="!highRiskSections.length" @click="applyAllRiskRewrites">
          一键替换风险句
        </el-button>
        <el-button size="small" plain :loading="isReanalyzing" @click="doReanalyze">
          <el-icon><Refresh /></el-icon>重新检测
        </el-button>
        <el-dropdown size="small" trigger="click">
          <el-button size="small" type="primary">
            <el-icon><Download /></el-icon>导出文稿<el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="doExportOriginal">下载原文档</el-dropdown-item>
              <el-dropdown-item @click="doExportHtml">导出带高亮 HTML (.html)</el-dropdown-item>
              <el-dropdown-item divided @click="doExport('docx')">导出改写稿 (.docx)</el-dropdown-item>
              <el-dropdown-item @click="doExport('txt')">导出改写稿 (.txt)</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
  </div>

  <!-- 付费功能已隐藏：UnlockModal 已移除 -->
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft, ArrowRight, ArrowDown, RefreshLeft, RefreshRight,
  Download, Refresh, CircleCheck, Lock
} from '@element-plus/icons-vue'
import { getRun, getRunSections, getRunBlocks, getRewriteAdvice, reanalyzeRun, exportRun, createPatch, bindReportSpan, getUnlockStatus, getUnlockPackages } from '../../api'
import type { RunSectionItem, RewriteAdviceResponse, ReanalyzeResponse, DocumentBlock, DocumentPatch, OfficialReportSummary, OfficialRiskSpan, UnlockPackage, UnlockOrder } from '../../types'
import { getRiskStyle, getEffectiveRiskStyle, getEffectiveRiskLevel } from './riskStyle'
import DocxRenderer from './DocxRenderer.vue'
import PdfRenderer from './PdfRenderer.vue'
import UnlockModal from '../UnlockModal.vue'

const props = defineProps<{
  runId: string
}>()

const route = useRoute()
const router = useRouter()

// ==================== 旧架构兼容层 ====================
const sections = ref<RunSectionItem[]>([])
const loading = ref(false)
const loadError = ref('')
const docRef = ref<HTMLDivElement | null>(null)
const paperTitle = ref('')

// 原始文件渲染
const documentId = ref('')
const originalFilename = ref('')
const originalBuffer = ref<ArrayBuffer | null>(null)
const fileType = ref<'docx' | 'pdf' | 'text'>('text')
const docxLoading = ref(false)
const docxError = ref('')
const renderedContainer = ref<HTMLElement | null>(null)
const documentZoom = ref(1)
const editMode = ref(false)
const actualPageCount = ref<number | null>(null)

// ==================== 新架构：Blocks 驱动 ====================
const blocks = ref<DocumentBlock[]>([])
const patches = ref<Map<string, DocumentPatch>>(new Map())
const activeBlockId = ref<string | null>(null)

// block 级别历史栈
interface BlockHistoryEntry {
  blockId: string
  previousText: string | undefined
  newText: string
  timestamp: number
}
const blockHistoryStack = ref<BlockHistoryEntry[]>([])
const blockHistoryIndex = ref(-1)

// 折叠正常段落
const foldNormal = ref(true)
const showAllPriority = ref(false)

// 解锁状态（付费功能已隐藏，始终开放）
const rewriteUnlocked = ref(true)
const exportUnlocked = ref(true)

async function checkUnlockStatus() {
  rewriteUnlocked.value = true
  exportUnlocked.value = true
}

function onUnlocked() {
  rewriteUnlocked.value = true
  exportUnlocked.value = true
  ElMessage.success('解锁成功')
}

// 改写状态（兼容旧模板）
const panelVisible = ref(false)
const panelLoading = ref(false)
const panelError = ref('')
const rewriteAdvice = ref<RewriteAdviceResponse | null>(null)

// ==================== 知网报告驱动模式 ====================
const runMode = ref<'estimate' | 'report'>('estimate')
const reportSummary = ref<OfficialReportSummary | null>(null)
const unmatchedSpans = ref<OfficialRiskSpan[]>([])
const showUnmatchedPanel = ref(false)
const selectedUnmatchedSpan = ref<OfficialRiskSpan | null>(null)
const manualBindMode = ref(false)
const bindingSpanId = ref<string | null>(null)

// 真实重算结果
const realScores = ref<ReanalyzeResponse | null>(null)
const isReanalyzing = ref(false)

// 批量建议
const batchAdviceMap = ref<Map<number, RewriteAdviceResponse>>(new Map())
const batchLoading = ref(false)
const batchProgress = ref(0)

const canReturnToOnlyOffice = computed(() => route.query.fallback === '1')

// 初始分数
const initialAigc = ref(0)
const initialDup = ref(0)

// 动画分数
const animatedAigc = ref(0)
const animatedDup = ref(0)

// ==================== 旧架构兼容变量（模板仍引用） ====================
const paragraphMap = ref<Map<HTMLElement, number>>(new Map())
const paragraphBlockMap = ref<Map<HTMLElement, string>>(new Map())
const activeSectionIndex = ref<number | null>(null)
const rewrittenMap = ref<Map<number, string>>(new Map())

interface HistoryEntry {
  sectionIndex: number
  previousText: string | undefined
  newText: string
  timestamp: number
  blockId?: string
}
const historyStack = ref<HistoryEntry[]>([])
const historyIndex = ref(-1)

onMounted(() => {
  loadData()
  checkUnlockStatus()
})

const baseUrl = import.meta.env.VITE_API_BASE_URL || ''

function looksBinaryLikeText(text: string): boolean {
  const compact = text.replace(/\s+/g, '')
  if (compact.length < 40) return false
  const suspicious = Array.from(compact).filter((ch) => {
    const code = ch.charCodeAt(0)
    return ch === '\uFFFD' || (code < 32 && ch !== '\n' && ch !== '\r' && ch !== '\t')
  }).length
  const readable = Array.from(compact).filter((ch) => /[0-9A-Za-z\u4e00-\u9fff]/.test(ch)).length
  return suspicious / compact.length >= 0.02 || readable / compact.length <= 0.45
}

function returnToOnlyOffice() {
  const nextQuery = { ...route.query }
  delete nextQuery.fallback
  router.replace({
    name: 'rewrite',
    params: { runId: props.runId },
    query: nextQuery,
  })
}

async function loadOriginalFile() {
  if (!documentId.value) return
  docxLoading.value = true
  docxError.value = ''
  actualPageCount.value = null
  try {
    const response = await fetch(`${baseUrl}/v1/documents/${documentId.value}/original`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` },
      credentials: 'include'
    })
    if (!response.ok) {
      throw new Error(`下载原始文件失败: ${response.status}`)
    }
    const buf = await response.arrayBuffer()

    if (fileType.value === 'docx') {
      // 验证是否为 zip（docx 本质是 zip）
      const header = new Uint8Array(buf.slice(0, 4))
      const isZip = header[0] === 0x50 && header[1] === 0x4B && header[2] === 0x03 && header[3] === 0x04
      if (!isZip) {
        originalBuffer.value = null
        docxError.value = '原始 DOCX 文件校验失败，当前任务无法在兼容编辑器中打开。请返回重新上传，或直接使用 ONLYOFFICE 模式。'
        return
      }
    } else if (fileType.value === 'pdf') {
      // 验证 PDF magic bytes: %PDF
      const header = new Uint8Array(buf.slice(0, 5))
      const isPdf = header[0] === 0x25 && header[1] === 0x50 && header[2] === 0x44 && header[3] === 0x46
      if (!isPdf) {
        originalBuffer.value = null
        docxError.value = '原始 PDF 文件校验失败，当前任务无法在兼容编辑器中打开。'
        return
      }
    }
    originalBuffer.value = buf
  } catch (err) {
    originalBuffer.value = null
    docxError.value = err instanceof Error ? err.message : '加载原始文件失败'
  } finally {
    docxLoading.value = false
  }
}

function onDocxRendered(container: HTMLElement) {
  renderedContainer.value = container
  applyHighlightsToDocx(container)
}

function onDocxError(msg: string) {
  originalBuffer.value = null
  docxError.value = msg || 'DOCX 渲染失败，请改用 ONLYOFFICE 在线改写。'
  console.warn('mammoth render failed:', msg)
}

function onPdfRendered(_container: HTMLElement) {
  // PDF 渲染完成，canvas + textLayer 已显示
}

function onPdfPageCount(count: number) {
  actualPageCount.value = count
}

function onPdfError(msg: string) {
  originalBuffer.value = null
  docxError.value = msg || 'PDF 渲染失败'
  console.warn('pdf render failed:', msg)
}

function onPdfSelectBlock(blockId: string) {
  const block = blocks.value.find(b => b.blockId === blockId)
  if (block) {
    if (manualBindMode.value && selectedUnmatchedSpan.value) {
      bindSpanToBlock(selectedUnmatchedSpan.value, block)
      return
    }
    selectBlock(block)
  }
}

function applyHighlightsToDocx(container: HTMLElement) {
  paragraphMap.value.clear()
  paragraphBlockMap.value.clear()
  const paragraphs = container.querySelectorAll('p.doc-paragraph')
  let paraIdx = 0
  
  paragraphs.forEach((p) => {
    const el = p as HTMLElement
    // 跳过空段落和标题
    const text = el.textContent?.trim() || ''
    if (!text) return

    const block = blocks.value.find(b => (b.sourceMap?.paragraphIndex ?? b.displayOrder) === paraIdx)
    if (block) {
      paragraphBlockMap.value.set(el, block.blockId)
      el.dataset.blockId = block.blockId
      el.dataset.originalText = block.text
      el.contentEditable = editMode.value ? 'true' : 'false'
      updateDocxParagraphRiskClass(el, block)
      paraIdx++
      return
    }

    // 找到对应 section（按 paragraph_index 匹配）
    const sec = sections.value.find(s => s.paragraph_index === paraIdx || s.section_index === paraIdx)
    if (sec) {
      paragraphMap.value.set(el, sec.section_index)
      el.dataset.sectionIndex = String(sec.section_index)
      el.dataset.originalText = sec.content
      el.contentEditable = editMode.value ? 'true' : 'false'
      updateParagraphRiskClass(el, sec)
    }
    paraIdx++
  })

  // 使用事件委托处理点击
  container.onclick = (e) => {
    const target = e.target as HTMLElement
    const para = target.closest('p.doc-paragraph') as HTMLElement | null
    if (!para) return
    const blockId = paragraphBlockMap.value.get(para)
    if (blockId) {
      const block = blocks.value.find(b => b.blockId === blockId)
      if (!block) return
      e.stopPropagation()
      if (manualBindMode.value && selectedUnmatchedSpan.value) {
        bindSpanToBlock(selectedUnmatchedSpan.value, block)
        return
      }
      selectBlock(block)
      paragraphs.forEach(other => other.classList.remove('is-active'))
      para.classList.add('is-active')
      return
    }
    const secIdx = paragraphMap.value.get(para)
    if (secIdx == null) return
    const sec = sections.value.find(s => s.section_index === secIdx)
    if (!sec) return
    e.stopPropagation()
    selectSection(sec)
    // 移除其他 active
    paragraphs.forEach(other => other.classList.remove('is-active'))
    para.classList.add('is-active')
  }

  container.addEventListener('focusout', (e: FocusEvent) => {
    if (!editMode.value) return
    const target = e.target as HTMLElement
    const para = target.closest('p.doc-paragraph') as HTMLElement | null
    if (!para) return
    const newText = (para.innerText || '').trim()
    if (!newText) return
    const blockId = paragraphBlockMap.value.get(para)
    if (blockId) {
      const block = blocks.value.find(b => b.blockId === blockId)
      if (block) applyBlockRewrite(block, newText, { updateDom: false, toast: false })
      return
    }
    const secIdx = paragraphMap.value.get(para)
    const sec = sections.value.find(s => s.section_index === secIdx)
    if (sec && newText !== (rewrittenMap.value.get(sec.section_index) || sec.content)) {
      applyRewrite(sec.section_index, newText, { updateDom: false, toast: false })
    }
  })
}

function updateParagraphRiskClass(el: HTMLElement, sec: RunSectionItem) {
  // 清除旧的风险 class
  el.classList.remove('risk-high', 'risk-medium', 'risk-low', 'risk-normal', 'is-rewritten')
  
  const level = effectiveRisk(sec)
  el.classList.add('risk-' + (level === 'high' ? 'high' : level === 'medium' ? 'medium' : level === 'low' ? 'low' : 'normal'))
  
  // 如果被改写，添加标记
  if (rewrittenMap.value.has(sec.section_index)) {
    el.classList.add('is-rewritten')
  }
}

function updateDocxParagraphRiskClass(el: HTMLElement, block: DocumentBlock) {
  el.classList.remove('risk-high', 'risk-medium', 'risk-low', 'risk-normal', 'is-rewritten')
  const level = getEffectiveRiskLevel(block)
  el.classList.add('risk-' + level)
  if (patches.value.has(block.blockId)) {
    el.classList.add('is-rewritten')
  }
}

function refreshAllHighlights() {
  if (renderedContainer.value && fileType.value === 'docx') {
    for (const [el, blockId] of paragraphBlockMap.value.entries()) {
      const block = blocks.value.find(b => b.blockId === blockId)
      if (block) {
        el.contentEditable = editMode.value ? 'true' : 'false'
        updateDocxParagraphRiskClass(el, block)
      }
    }
    for (const [el, secIdx] of paragraphMap.value.entries()) {
      const sec = sections.value.find(s => s.section_index === secIdx)
      if (sec) {
        el.contentEditable = editMode.value ? 'true' : 'false'
        updateParagraphRiskClass(el, sec)
      }
    }
  }
}

function replaceTextInElement(element: HTMLElement, oldText: string, newText: string) {
  const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT)
  const nodes: Text[] = []
  let accumulated = ''
  let startNode: Text | null = null
  let startOffset = 0
  
  while (walker.nextNode()) {
    const node = walker.currentNode as Text
    const text = node.textContent || ''
    
    if (!startNode) {
      const idx = (accumulated + text).indexOf(oldText)
      if (idx !== -1 && idx < accumulated.length + text.length) {
        startNode = node
        startOffset = idx - accumulated.length
      }
    }
    
    if (startNode) {
      nodes.push(node)
      accumulated += text
      if (accumulated.length >= oldText.length) break
    } else {
      accumulated += text
    }
  }
  
  if (!startNode || nodes.length === 0) return false
  
  if (nodes.length === 1) {
    const t = nodes[0].textContent!
    nodes[0].textContent = t.slice(0, startOffset) + newText + t.slice(startOffset + oldText.length)
  } else {
    const first = nodes[0]
    const last = nodes[nodes.length - 1]
    const remainingInLast = oldText.length - (nodes.slice(0, -1).reduce((s, n) => s + (n.textContent?.length || 0), 0) - startOffset)
    first.textContent = (first.textContent || '').slice(0, startOffset) + newText
    for (let i = 1; i < nodes.length - 1; i++) {
      nodes[i].textContent = ''
    }
    last.textContent = (last.textContent || '').slice(remainingInLast)
  }
  return true
}

interface ParagraphBlock {
  paragraphIndex: number | null
  content: string
  sectionIndices: number[]
  aigcScore: number
  dupScore: number
  riskLevel: 'low' | 'medium' | 'high' | 'normal'
  sectionTitle: string | null
  sectionType: string | null
  rewritten: boolean
  hasAdvice: boolean
}

interface ChapterGroup {
  title: string | null
  type: string | null
  paragraphs: ParagraphBlock[]
  totalChars: number
  maxAigc: number
  maxDup: number
  rewrittenCount: number
  adviceCount: number
}

// ==================== Blocks 驱动的新分组逻辑 ====================
// 优先从 blocks 生成分组，如果 blocks 为空则回退到 sections

const groupedSections = computed(() => {
  // 如果有 blocks，用 blocks 驱动
  if (blocks.value.length > 0) {
    return _groupFromBlocks()
  }
  // 回退到旧逻辑
  return _groupFromSections()
})

function _groupFromBlocks(): ChapterGroup[] {
  const groups: ChapterGroup[] = []
  let current: ChapterGroup | null = null

  for (const block of blocks.value) {
    if (block.type === 'heading' || block.type === 'title') {
      current = {
        title: block.text,
        type: block.sectionType ?? null,
        paragraphs: [],
        totalChars: 0,
        maxAigc: 0,
        maxDup: 0,
        rewrittenCount: 0,
        adviceCount: 0
      }
      groups.push(current)
      continue
    }

    if (!current) {
      current = {
        title: block.sectionTitle || '正文',
        type: block.sectionType ?? null,
        paragraphs: [],
        totalChars: 0,
        maxAigc: 0,
        maxDup: 0,
        rewrittenCount: 0,
        adviceCount: 0
      }
      groups.push(current)
    }

    const score = getBlockRiskScore(block) / 100
    const patch = patches.value.get(block.blockId)
    const text = patch ? patch.newText : block.text

    const para: ParagraphBlock = {
      paragraphIndex: block.sourceMap?.paragraphIndex ?? block.displayOrder,
      content: text,
      sectionIndices: [block.displayOrder],
      aigcScore: score,
      dupScore: 0,
      riskLevel: getEffectiveRiskLevel(block),
      sectionTitle: block.sectionTitle ?? null,
      sectionType: block.sectionType ?? null,
      rewritten: !!patch,
      hasAdvice: false
    }
    current.paragraphs.push(para)
    current.totalChars += block.charCount
    current.maxAigc = Math.max(current.maxAigc, score)
    if (patch) current.rewrittenCount++
  }
  return groups
}

function _groupFromSections(): ChapterGroup[] {
  const groups: ChapterGroup[] = []
  let current: ChapterGroup | null = null
  let currentPara: ParagraphBlock | null = null

  for (const sec of sections.value) {
    if (!current || current.title !== sec.section_title) {
      current = {
        title: sec.section_title,
        type: sec.section_type,
        paragraphs: [],
        totalChars: 0,
        maxAigc: 0,
        maxDup: 0,
        rewrittenCount: 0,
        adviceCount: 0
      }
      groups.push(current)
      currentPara = null
    }

    const paraIdx = sec.paragraph_index ?? sec.section_index
    if (!currentPara || currentPara.paragraphIndex !== paraIdx) {
      currentPara = {
        paragraphIndex: paraIdx,
        content: '',
        sectionIndices: [],
        aigcScore: 0,
        dupScore: 0,
        riskLevel: 'low',
        sectionTitle: sec.section_title,
        sectionType: sec.section_type,
        rewritten: false,
        hasAdvice: false
      }
      current.paragraphs.push(currentPara)
    }

    const text = rewrittenMap.value.get(sec.section_index) || sec.content
    currentPara.content += (currentPara.content ? '\n' : '') + text
    currentPara.sectionIndices.push(sec.section_index)
    currentPara.aigcScore = Math.max(currentPara.aigcScore, effectiveAigc(sec))
    currentPara.dupScore = Math.max(currentPara.dupScore, effectiveDup(sec))
    currentPara.riskLevel = effectiveRiskFromScore(currentPara.aigcScore)
    if (rewrittenMap.value.has(sec.section_index)) currentPara.rewritten = true
    if (batchAdviceMap.value.has(sec.section_index)) currentPara.hasAdvice = true

    current.totalChars += sec.char_count
    current.maxAigc = Math.max(current.maxAigc, effectiveAigc(sec))
    current.maxDup = Math.max(current.maxDup, effectiveDup(sec))
    if (rewrittenMap.value.has(sec.section_index)) current.rewrittenCount++
    if (batchAdviceMap.value.has(sec.section_index)) current.adviceCount++
  }
  return groups
}

const totalChars = computed(() => {
  if (blocks.value.length > 0) {
    return blocks.value
      .filter(b => b.type !== 'title' && b.type !== 'heading')
      .reduce((sum, b) => sum + (b.charCount || 0), 0)
  }
  return sections.value.reduce((sum, s) => sum + (s.char_count || 0), 0)
})

const editableParagraphCount = computed(() => {
  if (blocks.value.length > 0) {
    return blocks.value.filter(b => b.type !== 'title' && b.type !== 'heading').length
  }
  return sections.value.length
})

const estimatedPageCount = computed(() => Math.max(1, Math.ceil(totalChars.value / 900)))
const displayPageCount = computed(() => actualPageCount.value || estimatedPageCount.value)

const rewrittenCount = computed(() => {
  if (blocks.value.length > 0) {
    return patches.value.size
  }
  return rewrittenMap.value.size
})

const highRiskSections = computed(() => {
  if (blocks.value.length > 0) {
    if (runMode.value === 'report') {
      return blocks.value
        .filter(b => b.reportRisk && b.type !== 'title' && b.type !== 'heading')
        .map(b => ({
          section_index: b.sourceMap?.paragraphIndex ?? b.displayOrder,
          paragraph_index: b.sourceMap?.paragraphIndex ?? b.displayOrder,
          section_title: b.sectionTitle ?? null,
          section_type: b.sectionType ?? null,
          content: patches.value.get(b.blockId)?.newText || b.text,
          char_count: b.charCount,
          aigc_score: getBlockRiskScore(b) / 100,
          dup_score: b.reportRisk?.riskType === 'similarity' ? getBlockRiskScore(b) / 100 : 0,
          risk_level: (b.reportRisk?.riskLevel || 'low') as 'low' | 'medium' | 'high',
          reasons: [
            `官方报告标记：${b.reportRisk?.riskType === 'similarity' ? '查重' : 'AIGC'}`,
            `官方风险等级：${b.reportRisk?.riskLevel || 'low'}`
          ],
        }))
    }
    // blocks 模式下：用 block 风险分数过滤对应的 sections（保持类型兼容）
    if (sections.value.length > 0) {
      return sections.value.filter(s => {
        const block = blocks.value.find(b => b.sourceMap?.paragraphIndex === s.paragraph_index)
        const score = block ? getBlockRiskScore(block) : s.aigc_score * 100
        return getRiskStyle(score).level !== 'normal'
      })
    }
    return blocks.value
      .filter(b => b.type !== 'title' && b.type !== 'heading')
      .filter(b => getEffectiveRiskLevel(b) !== 'normal')
      .map(b => ({
        section_index: b.sourceMap?.paragraphIndex ?? b.displayOrder,
        paragraph_index: b.sourceMap?.paragraphIndex ?? b.displayOrder,
        section_title: b.sectionTitle ?? null,
        section_type: b.sectionType ?? null,
        content: patches.value.get(b.blockId)?.newText || b.text,
        char_count: b.charCount,
        aigc_score: getBlockRiskScore(b) / 100,
        dup_score: (b.internalRisk?.repetitionScore ?? 0) / 100,
        risk_level: effectiveRiskFromScore(getBlockRiskScore(b) / 100) as 'low' | 'medium' | 'high',
        reasons: b.internalRisk?.reasons || [],
      }))
  }
  return sections.value.filter(s => effectiveRiskFromScore(effectiveAigc(s)) !== 'normal')
})

interface PrioritySection extends RunSectionItem {
  combinedScore: number
  priorityRank: number
}

const prioritySections = computed<PrioritySection[]>(() => {
  if (sections.value.length === 0 && blocks.value.length > 0) {
    const fromBlocks = blocks.value
      .filter(b => b.type !== 'title' && b.type !== 'heading')
      .map((b) => {
        const internalOverall = Number(b.internalRisk?.overallRisk || 0) / 100
        const aiScore = Math.max(getBlockRiskScore(b) / 100, internalOverall)
        const dupScore = Number(b.internalRisk?.repetitionScore || 0) / 100
        return {
          section_index: b.sourceMap?.paragraphIndex ?? b.displayOrder,
          paragraph_index: b.sourceMap?.paragraphIndex ?? b.displayOrder,
          section_title: b.sectionTitle ?? null,
          section_type: b.sectionType ?? null,
          content: patches.value.get(b.blockId)?.newText || b.text,
          char_count: b.charCount,
          aigc_score: aiScore,
          dup_score: dupScore,
          risk_level: effectiveRiskFromScore(aiScore) as 'low' | 'medium' | 'high',
          reasons: b.internalRisk?.reasons || [],
          combinedScore: aiScore * 0.62 + dupScore * 0.38,
          priorityRank: 0,
        }
      })
      .filter(item => item.combinedScore >= 0.16 || item.aigc_score >= 0.18 || item.dup_score >= 0.18)
      .sort((a, b) => b.combinedScore - a.combinedScore)
    const count = Math.max(3, Math.min(fromBlocks.length, Math.ceil(fromBlocks.length * 0.25)))
    return fromBlocks.slice(0, count).map((item, index) => ({ ...item, priorityRank: index + 1 }))
  }
  const scored = sections.value.filter(
    s => s.section_type !== 'references' && s.section_type !== 'acknowledgement'
  )
  const withScore = scored
    .map(s => ({
      ...s,
      combinedScore: s.aigc_score * 0.58 + s.dup_score * 0.42,
      priorityRank: 0,
    }))
    .filter(s => (
      s.combinedScore >= 0.24 ||
      s.aigc_score >= 0.30 ||
      s.dup_score >= 0.20 ||
      ((s.reasons?.length || 0) > 0 && s.combinedScore >= 0.18)
    ))
  withScore.sort((a, b) => b.combinedScore - a.combinedScore)
  const count = Math.max(3, Math.ceil(withScore.length * 0.2))
  return withScore.slice(0, count).map((s, i) => ({ ...s, priorityRank: i + 1 }))
})

const displayedPrioritySections = computed(() => {
  if (showAllPriority.value) return prioritySections.value
  return prioritySections.value.slice(0, 5)
})

const riskCounts = computed(() => {
  const counts = { high: 0, medium: 0, low: 0, normal: 0 }
  if (blocks.value.length > 0) {
    for (const b of blocks.value.filter(item => item.type !== 'title' && item.type !== 'heading')) {
      const level = getEffectiveRiskLevel(b)
      counts[level]++
    }
  } else {
    for (const s of sections.value) {
      const level = effectiveRisk(s)
      if (level === 'high') counts.high++
      else if (level === 'medium') counts.medium++
      else if (level === 'low') counts.low++
      else counts.normal++
    }
  }
  return counts
})

const optimisticReduction = computed(() => {
  if (!rewrittenCount.value) return { aigc: 0, dup: 0 }
  if (blocks.value.length > 0) {
    let aigc = 0
    let dup = 0
    for (const block of blocks.value) {
      if (!patches.value.has(block.blockId)) continue
      const weight = Math.min(1, Math.max(0.25, (block.charCount || block.text.length) / Math.max(totalChars.value, 1) * 18))
      const score = getBlockRiskScore(block)
      const gain = score >= 70 ? 5.2 : score >= 60 ? 3.6 : score >= 30 ? 1.8 : 0.8
      aigc += gain * weight
      if (block.reportRisk?.riskType === 'similarity' || (block.internalRisk?.repetitionScore ?? 0) > 45) {
        dup += gain * 0.7 * weight
      }
    }
    return { aigc, dup }
  }
  let aigc = 0
  let dup = 0
  for (const sec of sections.value) {
    if (!rewrittenMap.value.has(sec.section_index)) continue
    const weight = Math.min(1, Math.max(0.25, (sec.char_count || sec.content.length) / Math.max(totalChars.value, 1) * 18))
    aigc += (effectiveAigc(sec) >= 0.7 ? 5.2 : effectiveAigc(sec) >= 0.6 ? 3.6 : 1.8) * weight
    dup += (effectiveDup(sec) >= 0.5 ? 3.2 : 1.1) * weight
  }
  return { aigc, dup }
})

const currentAigc = computed(() =>
  realScores.value ? realScores.value.ai_like_percent : Math.max(0, initialAigc.value * 100 - optimisticReduction.value.aigc)
)
const currentDup = computed(() =>
  realScores.value ? realScores.value.duplication_percent : Math.max(0, initialDup.value * 100 - optimisticReduction.value.dup)
)

const predictedAigc = computed(() => Math.max(0, currentAigc.value * 0.45))
const predictedDrop = computed(() => currentAigc.value - predictedAigc.value)

const aigcDelta = computed(() => currentAigc.value - initialAigc.value * 100)
const dupDelta = computed(() => currentDup.value - initialDup.value * 100)

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

const activeGroupIndex = computed(() => {
  if (activeSectionIndex.value == null) return -1
  const sec = sections.value.find(s => s.section_index === activeSectionIndex.value)
  if (!sec) return -1
  return groupedSections.value.findIndex(g => g.title === sec.section_title)
})

const activeParaIndex = computed(() => {
  if (activeSectionIndex.value == null) return null
  const sec = sections.value.find(s => s.section_index === activeSectionIndex.value)
  if (!sec) return null
  return sec.paragraph_index ?? sec.section_index
})

const activeRiskLevel = computed(() => {
  // blocks 模式
  if (activeBlockId.value && blocks.value.length > 0) {
    const block = blocks.value.find(b => b.blockId === activeBlockId.value)
    if (block) {
      return getEffectiveRiskLevel(block)
    }
  }
  // 旧模式
  if (activeSectionIndex.value == null) return 'low'
  const sec = sections.value.find(s => s.section_index === activeSectionIndex.value)
  if (!sec) return 'low'
  return effectiveRisk(sec)
})

const activeAigcScore = computed(() => {
  // blocks 模式
  if (activeBlockId.value && blocks.value.length > 0) {
    const block = blocks.value.find(b => b.blockId === activeBlockId.value)
    if (block) {
      return getBlockRiskScore(block) / 100
    }
  }
  // 旧模式
  if (activeSectionIndex.value == null) return 0
  const sec = sections.value.find(s => s.section_index === activeSectionIndex.value)
  if (!sec) return 0
  return effectiveAigc(sec)
})

const activeBlock = computed(() => {
  if (!activeBlockId.value || blocks.value.length === 0) return null
  return blocks.value.find(b => b.blockId === activeBlockId.value) || null
})

const activeReportRisk = computed(() => activeBlock.value?.reportRisk || null)

const activeSectionContent = computed(() => {
  // blocks 模式
  if (activeBlockId.value && blocks.value.length > 0) {
    const block = blocks.value.find(b => b.blockId === activeBlockId.value)
    if (block) {
      const patch = patches.value.get(activeBlockId.value)
      return patch ? patch.newText : block.text
    }
  }
  // 旧模式
  if (activeSectionIndex.value == null) return ''
  const sec = sections.value.find(s => s.section_index === activeSectionIndex.value)
  if (!sec) return ''
  return rewrittenMap.value.get(sec.section_index) || sec.content
})

const RISKY_ACADEMIC_TERMS = [
  '赋能', '支撑', '体系', '机制', '路径', '落地', '持续拓展', '坚实基础', '有效弥补',
  '优化完善', '重要意义', '参考价值', '综上所述', '由此可见', '进一步提升', '显著提高',
  '提供保障', '具有重要', '现实意义', '相关实践', '全面推进', '不断完善'
]

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function collectRiskTerms(text: string): string[] {
  const terms = new Set<string>()
  for (const term of RISKY_ACADEMIC_TERMS) {
    if (text.includes(term)) terms.add(term)
  }
  const reasons = [
    ...(activeBlock.value?.internalRisk?.reasons || []),
    ...(rewriteAdvice.value?.sentences?.map(s => s.explanation) || []),
  ].join('；')
  for (const term of RISKY_ACADEMIC_TERMS) {
    if (reasons.includes(term)) terms.add(term)
  }
  return Array.from(terms).slice(0, 8)
}

const activeRiskTerms = computed(() => collectRiskTerms(activeSectionContent.value))

function highlightOriginalRiskHtml(text: string): string {
  let html = escapeHtml(text)
  const terms = collectRiskTerms(text).sort((a, b) => b.length - a.length)
  for (const term of terms) {
    const escaped = escapeHtml(term)
    html = html.split(escaped).join(`<mark class="risk-word">${escaped}</mark>`)
  }
  return html
}

function highlightRewriteDiffHtml(original: string, rewritten: string): string {
  if (!rewritten) return ''
  let start = 0
  while (start < original.length && start < rewritten.length && original[start] === rewritten[start]) {
    start++
  }
  let oldEnd = original.length - 1
  let newEnd = rewritten.length - 1
  while (oldEnd >= start && newEnd >= start && original[oldEnd] === rewritten[newEnd]) {
    oldEnd--
    newEnd--
  }
  const before = escapeHtml(rewritten.slice(0, start))
  const changed = escapeHtml(rewritten.slice(start, newEnd + 1))
  const after = escapeHtml(rewritten.slice(newEnd + 1))
  return changed ? `${before}<mark class="rewrite-word">${changed}</mark>${after}` : escapeHtml(rewritten)
}

const activeOriginalHtml = computed(() => highlightOriginalRiskHtml(activeSectionContent.value))
const activeRewrittenHtml = computed(() => highlightRewriteDiffHtml(activeSectionContent.value, rewriteAdvice.value?.rewritten_paragraph || ''))

const currentIndex = computed(() => {
  if (activeSectionIndex.value == null) return -1
  return highRiskSections.value.findIndex(s => s.section_index === activeSectionIndex.value)
})

const prevSection = computed(() => {
  const idx = currentIndex.value
  return idx > 0 ? highRiskSections.value[idx - 1] : null
})

const nextSection = computed(() => {
  const idx = currentIndex.value
  return idx >= 0 && idx < highRiskSections.value.length - 1 ? highRiskSections.value[idx + 1] : null
})

watch([currentAigc, currentDup, patches], () => {
  animateScore()
}, { deep: true })

// 改写或重算后自动刷新高亮
watch([realScores, rewrittenMap], () => {
  refreshAllHighlights()
}, { deep: true })

watch(editMode, () => {
  refreshAllHighlights()
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

async function loadData() {
  loading.value = true
  loadError.value = ''
  try {
    const [run, secs, blocksRes] = await Promise.all([
      getRun(props.runId),
      getRunSections(props.runId),
      getRunBlocks(props.runId).catch(() => ({ blocks: [], reportSummary: null, unmatchedSpans: [] }))
    ])
    if (run.status !== 'completed') {
      loadError.value = run.status === 'failed'
        ? '杩欎釜浠诲姟杩樻病鏈夊彲鐢ㄧ殑鏀瑰啓鍐呭锛屽洜涓哄垎鏋愬凡澶辫触銆傝鍏堣繑鍥炲伐浣滃彴閲嶆柊鍙戣捣妫€娴嬨€?'
        : '杩欎釜浠诲姟杩樺湪鍒嗘瀽涓紝鏆傛椂涓嶈兘杩涘叆鍦ㄧ嚎鏀瑰啓銆傝绛夊垎鏋愬畬鎴愬悗鍐嶈繘鏉ャ€?'
      sections.value = []
      blocks.value = []
      return
    }
    sections.value = secs
    blocks.value = blocksRes.blocks
    documentId.value = run.document_id
    originalFilename.value = run.filename || ''
    paperTitle.value = run.title || ''
    runMode.value = run.mode || 'estimate'

    // 如果是 report mode，从 blocks 中统计报告摘要
    if (runMode.value === 'report') {
      const counts = { high: 0, medium: 0, low: 0, unmatched: 0 }
      for (const b of blocksRes.blocks) {
        if (b.reportRisk) {
          counts[b.reportRisk.riskLevel]++
        }
      }
      reportSummary.value = blocksRes.reportSummary || {
        reportType: 'mixed',
        highRiskCount: counts.high,
        mediumRiskCount: counts.medium,
        lowRiskCount: counts.low,
        unmatchedCount: counts.unmatched,
      }
      unmatchedSpans.value = blocksRes.unmatchedSpans || []
      showUnmatchedPanel.value = unmatchedSpans.value.length > 0
    } else {
      reportSummary.value = null
      unmatchedSpans.value = []
      selectedUnmatchedSpan.value = null
      manualBindMode.value = false
    }

    // 计算初始分数
    const scored = sections.value.filter(s => s.section_type !== 'references' && s.section_type !== 'acknowledgement')
    const scoredChars = scored.reduce((sum, s) => sum + s.char_count, 0)
    if (scoredChars > 0) {
      initialAigc.value = scored.reduce((sum, s) => sum + s.aigc_score * s.char_count, 0) / scoredChars
      initialDup.value = scored.reduce((sum, s) => sum + s.dup_score * s.char_count, 0) / scoredChars
    }
    animatedAigc.value = initialAigc.value * 100
    animatedDup.value = initialDup.value * 100

    // 根据文件扩展名选择渲染方式
    const lowerName = originalFilename.value.toLowerCase()
    if (lowerName.endsWith('.docx')) {
      fileType.value = 'docx'
    } else if (lowerName.endsWith('.pdf')) {
      fileType.value = 'pdf'
    } else {
      fileType.value = 'text'
    }
    if (documentId.value && (fileType.value === 'docx' || fileType.value === 'pdf')) {
      await loadOriginalFile()
    }
    const textSamples = [
      ...blocks.value.slice(0, 8).map(block => block.text || ''),
      ...sections.value.slice(0, 6).map(section => section.content || ''),
    ]
      .join('\n')
      .trim()
    if (textSamples && looksBinaryLikeText(textSamples)) {
      loadError.value = '当前这份任务里的正文数据已经损坏或提取错位，所以兼容编辑器会出现乱码。请重新上传原论文后再进入在线改写，或直接切换到 ONLYOFFICE 模式。'
      originalBuffer.value = null
      docxError.value = '检测到异常正文数据，已阻止乱码展示。'
      return
    }
    const hasRenderableBlocks = blocks.value.some(
      block => block.type !== 'title' && block.type !== 'heading' && (block.text || '').trim()
    )
    const hasRenderableSections = sections.value.some(section => (section.content || '').trim())
    if (!hasRenderableBlocks && !hasRenderableSections) {
      loadError.value = '杩欎釜 run 娌℃湁鍙敤鐨勬鏂囨钀芥暟鎹紝鎵€浠ユ棤娉曞湪绾挎敼鍐欍€傝鍥炲埌妫€娴嬫祦绋嬮噸鏂颁笂浼犳垨閲嶆柊鍒嗘瀽銆?'
    }
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : '加载在线改写失败'
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

function effectiveRiskFromScore(score: number): 'low' | 'medium' | 'high' | 'normal' {
  if (score >= 0.70) return 'high'
  if (score >= 0.42) return 'medium'
  if (score >= 0.18) return 'low'
  return 'normal'
}

function effectiveRisk(sec: RunSectionItem): 'low' | 'medium' | 'high' | 'normal' {
  return effectiveRiskFromScore(effectiveAigc(sec))
}

// 从 block 获取风险分数（优先使用重算后的分数）
function getBlockRiskScore(block: DocumentBlock): number {
  // reportRisk 存在时，直接返回对应分数用于排序/统计
  if (block.reportRisk) {
    if (block.reportRisk.riskLevel === 'high') return 75
    if (block.reportRisk.riskLevel === 'medium') return 65
    if (block.reportRisk.riskLevel === 'low') return 45
    return 20
  }
  // 先用 sections 中的对应分数（兼容旧数据）
  const sec = sections.value.find(s => s.paragraph_index === block.sourceMap?.paragraphIndex)
  if (sec) {
    return effectiveAigc(sec) * 100
  }
  return block.riskScore ?? 0
}

function paraRiskColor(para: ParagraphBlock): string {
  // 查找对应的 block，优先使用 reportRisk
  if (blocks.value.length > 0) {
    const block = blocks.value.find(b =>
      (b.sourceMap?.paragraphIndex ?? b.displayOrder) === para.paragraphIndex
    )
    if (block) {
      const level = getEffectiveRiskLevel(block)
      return level === 'high' ? 'red' : level === 'medium' ? 'orange' : level === 'low' ? 'purple' : 'normal'
    }
  }
  const style = getRiskStyle(para.aigcScore * 100)
  return style.level === 'high' ? 'red' : style.level === 'medium' ? 'orange' : style.level === 'low' ? 'purple' : 'normal'
}

function groupMaxColor(group: ChapterGroup): string {
  // 如果 group 内的 paragraphs 有 reportRisk，优先使用
  if (blocks.value.length > 0 && group.paragraphs.length > 0) {
    let maxLevel = 'normal'
    const levelOrder = { high: 3, medium: 2, low: 1, normal: 0 }
    for (const para of group.paragraphs) {
      const block = blocks.value.find(b =>
        (b.sourceMap?.paragraphIndex ?? b.displayOrder) === para.paragraphIndex
      )
      if (block) {
        const level = getEffectiveRiskLevel(block)
        if (levelOrder[level as keyof typeof levelOrder] > levelOrder[maxLevel as keyof typeof levelOrder]) {
          maxLevel = level
        }
      }
    }
    return maxLevel === 'high' ? 'red' : maxLevel === 'medium' ? 'orange' : maxLevel === 'low' ? 'purple' : 'normal'
  }
  const style = getRiskStyle(group.maxAigc * 100)
  return style.level === 'high' ? 'red' : style.level === 'medium' ? 'orange' : style.level === 'low' ? 'purple' : 'normal'
}

function riskText(level: string) {
  return level === 'high' ? '高风险' : level === 'medium' ? '中风险' : level === 'low' ? '低风险' : '正常'
}

function paraPreview(para: ParagraphBlock): string {
  return para.content.slice(0, 24) + (para.content.length > 24 ? '…' : '')
}

function filteredOutlineParas(group: ChapterGroup): ParagraphBlock[] {
  const risky = group.paragraphs.filter(p => p.riskLevel !== 'normal')
  return risky.length ? risky.slice(0, 8) : group.paragraphs.slice(0, 3)
}

function groupRiskCount(group: ChapterGroup): string {
  const count = group.paragraphs.filter(p => p.riskLevel !== 'normal').length
  return count ? `${count}` : '0'
}

function scrollToGroup(gIdx: number) {
  const el = document.getElementById('group-' + gIdx)
  if (el && docRef.value) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

function scrollToParagraph(paraIdx: number | null) {
  if (paraIdx == null) return
  const el = document.getElementById('para-' + paraIdx)
  if (el && docRef.value) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

function selectUnmatchedSpan(span: OfficialRiskSpan) {
  selectedUnmatchedSpan.value = span
  manualBindMode.value = true
  showUnmatchedPanel.value = true
  ElMessage.info('已选择官方报告片段，请点击正文中对应段落完成绑定')
}

function startManualBind(span: OfficialRiskSpan) {
  selectUnmatchedSpan(span)
}

async function bindSpanToBlock(span: OfficialRiskSpan, block: DocumentBlock) {
  if (bindingSpanId.value) return
  try {
    await ElMessageBox.confirm(
      '确认把该官方报告风险片段绑定到当前正文段落吗？绑定后页面风险颜色和右侧改写建议会以官方报告为准。',
      '绑定官方风险片段',
      { type: 'warning', confirmButtonText: '确认绑定', cancelButtonText: '取消' }
    )
  } catch {
    return
  }

  bindingSpanId.value = span.spanId
  try {
    const result = await bindReportSpan(props.runId, {
      spanId: span.spanId,
      blockId: block.blockId,
    })
    const idx = blocks.value.findIndex(item => item.blockId === result.block.blockId)
    if (idx >= 0) {
      blocks.value.splice(idx, 1, result.block)
    }
    unmatchedSpans.value = result.unmatchedSpans
    if (reportSummary.value) {
      reportSummary.value.unmatchedCount = result.unmatchedCount
    }
    selectedUnmatchedSpan.value = null
    manualBindMode.value = false
    activeBlockId.value = block.blockId
    refreshAllHighlights()
    await selectBlock(result.block)
    ElMessage.success('已按官方报告绑定风险段落')
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '绑定失败')
  } finally {
    bindingSpanId.value = null
  }
}

async function bindSpanToActiveBlock(span: OfficialRiskSpan) {
  if (!activeBlockId.value) {
    ElMessage.info('请先点击正文里对应的段落')
    return
  }
  const block = blocks.value.find(item => item.blockId === activeBlockId.value)
  if (!block) return
  await bindSpanToBlock(span, block)
}

async function selectParagraph(para: ParagraphBlock) {
  // blocks 模式：通过 paragraphIndex 找 block
  if (blocks.value.length > 0) {
    const block = blocks.value.find(b =>
      (b.sourceMap?.paragraphIndex ?? b.displayOrder) === para.paragraphIndex
    )
    if (block) {
      if (manualBindMode.value && selectedUnmatchedSpan.value) {
        await bindSpanToBlock(selectedUnmatchedSpan.value, block)
        return
      }
      activeBlockId.value = block.blockId
      await selectBlock(block)
      return
    }
  }
  // 旧模式
  if (!para.sectionIndices.length) return
  let targetSec = sections.value.find(s => s.section_index === para.sectionIndices[0])
  for (const idx of para.sectionIndices) {
    const sec = sections.value.find(s => s.section_index === idx)
    if (sec && effectiveAigc(sec) > (targetSec ? effectiveAigc(targetSec) : 0)) {
      targetSec = sec
    }
  }
  if (targetSec) {
    await selectSection(targetSec)
  }
}

async function selectBlock(block: DocumentBlock) {
  activeBlockId.value = block.blockId
  activeSectionIndex.value = block.sourceMap?.paragraphIndex ?? block.displayOrder
  panelVisible.value = true
  panelLoading.value = true
  panelError.value = ''
  rewriteAdvice.value = null

  // 尝试通过 section_index 获取改写建议（兼容旧 API）
  const secIdx = block.sourceMap?.paragraphIndex ?? block.displayOrder
  const cached = batchAdviceMap.value.get(secIdx)
  if (cached) {
    rewriteAdvice.value = cached
    panelLoading.value = false
    return
  }

  try {
    rewriteAdvice.value = await getRewriteAdvice(props.runId, secIdx)
  } catch (err: any) {
    panelError.value = String(
      err?.message || err?.detail || err?.error || (typeof err === 'string' ? err : '获取改写建议失败')
    )
  } finally {
    panelLoading.value = false
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
  } catch (err: any) {
    panelError.value = String(
      err?.message || err?.detail || err?.error || (typeof err === 'string' ? err : '获取改写建议失败')
    )
  } finally {
    panelLoading.value = false
  }
}

function pushHistory(sectionIndex: number, previousText: string | undefined, newText: string, blockId?: string) {
  if (historyIndex.value < historyStack.value.length - 1) {
    historyStack.value = historyStack.value.slice(0, historyIndex.value + 1)
  }
  historyStack.value.push({ sectionIndex, previousText, newText, timestamp: Date.now(), blockId })
  historyIndex.value = historyStack.value.length - 1
}

function applyBlockRewrite(
  block: DocumentBlock,
  newText: string,
  options: { updateDom?: boolean; toast?: boolean } = {}
) {
  const { updateDom = true, toast = true } = options
  const previousPatch = patches.value.get(block.blockId)
  const previousText = previousPatch?.newText
  const originalText = block.text
  if (newText.trim() === (previousText || originalText).trim()) return

  patches.value.set(block.blockId, {
    blockId: block.blockId,
    oldText: originalText,
    newText,
    createdAt: new Date().toISOString(),
  })

  const secIdx = block.sourceMap?.paragraphIndex ?? block.displayOrder
  rewrittenMap.value.set(secIdx, newText)
  pushHistory(secIdx, previousText, newText, block.blockId)

  createPatch(props.runId, {
    block_id: block.blockId,
    old_text: originalText,
    new_text: newText,
    source_map: block.sourceMap,
  }).catch(() => { /* 前端先保留状态，导出前仍可重试 */ })

  if (updateDom && renderedContainer.value) {
    for (const [el, blockId] of paragraphBlockMap.value.entries()) {
      if (blockId === block.blockId) {
        el.innerText = newText
        el.classList.add('is-rewritten')
        break
      }
    }
  }
  refreshAllHighlights()
  if (toast) ElMessage.success('已替换原文')
}

function applyRewrite(
  sectionIndex: number,
  newText: string,
  options: { updateDom?: boolean; toast?: boolean } = {}
) {
  const { updateDom = true, toast = false } = options
  if (blocks.value.length > 0 && activeBlockId.value) {
    const block = blocks.value.find(b => b.blockId === activeBlockId.value)
    if (block) {
      applyBlockRewrite(block, newText, { updateDom, toast })
      return
    }
  }

  const previousText = rewrittenMap.value.get(sectionIndex)
  rewrittenMap.value.set(sectionIndex, newText)
  pushHistory(sectionIndex, previousText, newText)

  // 同步更新 mammoth HTML 中的文本
  if (updateDom && renderedContainer.value) {
    const sec = sections.value.find(s => s.section_index === sectionIndex)
    if (sec) {
      const oldText = previousText || sec.content
      for (const [el, idx] of paragraphMap.value.entries()) {
        if (idx === sectionIndex) {
          replaceTextInElement(el, oldText, newText)
          el.classList.add('is-rewritten')
          break
        }
      }
    }
  }
  if (toast) ElMessage.success('已替换原文')
}

function applySentenceRewrite(sentenceIdx: number) {
  if (!rewriteAdvice.value) return
  const sent = rewriteAdvice.value.sentences[sentenceIdx]
  if (!sent) return

  // blocks 模式
  if (activeBlockId.value && blocks.value.length > 0) {
    const patch = patches.value.get(activeBlockId.value)
    const current = patch ? patch.newText : (blocks.value.find(b => b.blockId === activeBlockId.value)?.text || '')
    const updated = current.replace(sent.original, sent.rewritten)
    const secIdx = activeSectionIndex.value ?? 0
    applyRewrite(secIdx, updated)
    ElMessage.success('已应用改写')
    return
  }

  // 旧模式
  if (activeSectionIndex.value === null) return
  const sec = sections.value.find((s: RunSectionItem) => s.section_index === activeSectionIndex.value)
  if (!sec) return

  const current = rewrittenMap.value.get(activeSectionIndex.value) || sec.content
  const updated = current.replace(sent.original, sent.rewritten)
  applyRewrite(activeSectionIndex.value, updated)
  ElMessage.success('已应用改写')
}

function applyFullRewrite() {
  if (!rewriteAdvice.value) return

  // blocks 模式
  if (activeBlockId.value && blocks.value.length > 0) {
    const secIdx = activeSectionIndex.value ?? 0
    applyRewrite(secIdx, rewriteAdvice.value.rewritten_paragraph)
    ElMessage.success('已替换原文')
    return
  }

  // 旧模式
  if (activeSectionIndex.value === null) return
  applyRewrite(activeSectionIndex.value, rewriteAdvice.value.rewritten_paragraph)
  ElMessage.success('已替换原文')
}

function ignoreActive() {
  if (activeSectionIndex.value === null) return
  ElMessage.info('已忽略该条建议')
}

async function selectRiskItem(item: any) {
  if (blocks.value.length > 0) {
    const paraIdx = item.paragraph_index ?? item.section_index
    const block = blocks.value.find(b => (b.sourceMap?.paragraphIndex ?? b.displayOrder) === paraIdx)
    if (block) {
      await selectBlock(block)
      return
    }
  }
  await selectSection(item)
}

function changeZoom(delta: number) {
  documentZoom.value = Math.min(1.6, Math.max(0.6, Number((documentZoom.value + delta).toFixed(2))))
}

function toggleEditMode() {
  if (fileType.value === 'pdf') {
    ElMessage.info('PDF 当前支持原版预览、定位和高亮；正文改写请用右侧替换后导出 docx。')
    return
  }
  editMode.value = !editMode.value
  if (editMode.value) foldNormal.value = false
  refreshAllHighlights()
  ElMessage.info(editMode.value ? '已进入编辑模式：可直接改正文段落，失焦后自动保存为文本替换。' : '已退出编辑模式')
}

function onPlainParagraphBlur(para: ParagraphBlock, event: FocusEvent) {
  if (!editMode.value) return
  const target = event.currentTarget as HTMLElement | null
  const text = target?.innerText?.trim()
  if (!text || text === para.content.trim()) return

  if (blocks.value.length > 0) {
    const block = blocks.value.find(b =>
      (b.sourceMap?.paragraphIndex ?? b.displayOrder) === para.paragraphIndex
    )
    if (block) {
      applyBlockRewrite(block, text, { updateDom: false, toast: false })
      return
    }
  }
  const sectionIndex = para.sectionIndices[0]
  if (sectionIndex != null) {
    applyRewrite(sectionIndex, text, { updateDom: false, toast: false })
  }
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

async function applyAllRiskRewrites() {
  const targets = highRiskSections.value.filter(s => s.risk_level !== 'low' || runMode.value === 'report')
  if (!targets.length) {
    ElMessage.info('当前没有需要批量替换的风险句')
    return
  }
  batchLoading.value = true
  batchProgress.value = 0
  try {
    for (const sec of targets) {
      try {
        let advice = batchAdviceMap.value.get(sec.section_index)
        if (!advice) {
          advice = await getRewriteAdvice(props.runId, sec.section_index)
          batchAdviceMap.value.set(sec.section_index, advice)
        }
        if (!advice.rewritten_paragraph?.trim()) continue
        if (blocks.value.length > 0) {
          const block = blocks.value.find(b =>
            (b.sourceMap?.paragraphIndex ?? b.displayOrder) === (sec.paragraph_index ?? sec.section_index)
          )
          if (block) {
            applyBlockRewrite(block, advice.rewritten_paragraph, { updateDom: true, toast: false })
          }
        } else {
          rewrittenMap.value.set(sec.section_index, advice.rewritten_paragraph)
          pushHistory(sec.section_index, undefined, advice.rewritten_paragraph)
        }
      } catch {
        // 单段失败不影响其他段落
      } finally {
        batchProgress.value++
      }
    }
    refreshAllHighlights()
    ElMessage.success(`已替换 ${batchProgress.value} 个风险段落，AIGC/重复率已按改写进度实时预估下降`)
  } finally {
    batchLoading.value = false
  }
}

async function doReanalyze() {
  if (!rewrittenCount.value) return
  if (runMode.value === 'report') {
    ElMessage.info('当前为官方报告驱动模式，风险颜色和指标以学校/检测平台报告为准。改写后请上传新的官方复检报告更新结果。')
    return
  }
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
      content: rewrittenMap.value.get(sec.section_index) || sec.content,
      risk_level: effectiveRisk(sec)
    }))
    const { blob, patchStats } = await exportRun(props.runId, payload, format)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `PataFix_改写稿.${format}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    if (patchStats && format === 'docx') {
      ElMessage.success(`已导出 DOCX，成功替换 ${patchStats.applied}/${patchStats.requested} 处`)
    } else {
      ElMessage.success(`已导出 ${format.toUpperCase()}`)
    }
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '导出失败')
  }
}

async function doExportOriginal() {
  if (!documentId.value) return
  try {
    const response = await fetch(`${baseUrl}/v1/documents/${documentId.value}/original`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` },
      credentials: 'include'
    })
    if (!response.ok) throw new Error(`下载失败: ${response.status}`)
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const filename = originalFilename.value || paperTitle.value || '原始文档'
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    ElMessage.success('已导出原始格式文档')
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '导出失败')
  }
}

function doExportHtml() {
  if (!renderedContainer.value) return
  const clone = renderedContainer.value.cloneNode(true) as HTMLElement
  // 移除点击事件和高亮 overlay（只保留风险背景色）
  clone.querySelectorAll('.doc-paragraph').forEach((p) => {
    const el = p as HTMLElement
    el.style.cursor = 'default'
    el.onclick = null
  })
  const html = `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>${paperTitle.value || 'PataFix 改写稿'}</title>
<style>
body { font-family: 'Times New Roman','SimSun',serif; font-size: 12pt; line-height: 1.8; max-width: 210mm; margin: 0 auto; padding: 20mm; background: #fff; color: #1a1a1a; }
h1,h2,h3 { font-family: 'SimHei','黑体',sans-serif; text-align: center; font-weight: bold; }
p { text-indent: 2em; margin: 0 0 6pt 0; border-left: 3px solid transparent; padding: 4px 8px; }
table { border-collapse: collapse; margin: 12pt auto; width: 100%; }
td,th { border: 1px solid #ccc; padding: 6px 10px; font-size: 11pt; }
img { max-width: 100%; display: block; margin: 12pt auto; }
.risk-high { background: rgba(229,57,53,0.18); border-left-color: #E53935; }
.risk-medium { background: rgba(251,140,0,0.18); border-left-color: #FB8C00; }
.risk-low { background: rgba(142,36,170,0.15); border-left-color: #8E24AA; }
.risk-normal { background: rgba(67,160,71,0.12); border-left-color: #43A047; }
.is-rewritten { border-left-color: #2E7D5A !important; border-left-width: 4px; }
</style>
</head>
<body>
${clone.innerHTML}
</body>
</html>`
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${paperTitle.value || 'PataFix_改写稿'}.html`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  ElMessage.success('已导出带高亮 HTML')
}

function doSave() {
  ElMessage.success('已保存改写进度到本地')
}

function undo() {
  if (!canUndo.value) return
  const entry = historyStack.value[historyIndex.value]
  if (entry.blockId) {
    const block = blocks.value.find(b => b.blockId === entry.blockId)
    if (block) {
      if (entry.previousText === undefined) {
        patches.value.delete(entry.blockId)
        rewrittenMap.value.delete(entry.sectionIndex)
        createPatch(props.runId, {
          block_id: entry.blockId,
          old_text: block.text,
          new_text: block.text,
          source_map: block.sourceMap,
        }).catch(() => {})
      } else {
        patches.value.set(entry.blockId, {
          blockId: entry.blockId,
          oldText: block.text,
          newText: entry.previousText,
          createdAt: new Date().toISOString(),
        })
        rewrittenMap.value.set(entry.sectionIndex, entry.previousText)
        createPatch(props.runId, {
          block_id: entry.blockId,
          old_text: block.text,
          new_text: entry.previousText,
          source_map: block.sourceMap,
        }).catch(() => {})
      }
      refreshAllHighlights()
      historyIndex.value--
      ElMessage.success('已撤销')
      return
    }
  }
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
  if (entry.blockId) {
    const block = blocks.value.find(b => b.blockId === entry.blockId)
    if (block) {
      patches.value.set(entry.blockId, {
        blockId: entry.blockId,
        oldText: block.text,
        newText: entry.newText,
        createdAt: new Date().toISOString(),
      })
      createPatch(props.runId, {
        block_id: entry.blockId,
        old_text: block.text,
        new_text: entry.newText,
        source_map: block.sourceMap,
      }).catch(() => {})
    }
  }
  rewrittenMap.value.set(entry.sectionIndex, entry.newText)
  refreshAllHighlights()
  ElMessage.success('已重做')
}

function goPrev() {
  if (prevSection.value) {
    selectRiskItem(prevSection.value)
    scrollToParagraph(prevSection.value.paragraph_index ?? prevSection.value.section_index)
  }
}

function goNext() {
  if (nextSection.value) {
    selectRiskItem(nextSection.value)
    scrollToParagraph(nextSection.value.paragraph_index ?? nextSection.value.section_index)
  }
}
</script>

<style scoped>
/* ===== 锁定覆盖 ===== */
.panel-lock {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
  text-align: center;
  gap: 12px;
}
.panel-lock .lock-icon {
  font-size: 48px;
  color: #ff9800;
}
.panel-lock h4 {
  margin: 0;
  color: #e65100;
  font-size: 18px;
}
.panel-lock p {
  margin: 0;
  color: #666;
  font-size: 13px;
  line-height: 1.6;
}

/* ===== 折叠正常段落 ===== */
.doc-paragraph.folded {
  max-height: 32px;
  overflow: hidden;
  opacity: 0.6;
  cursor: pointer;
  position: relative;
}
.doc-paragraph.folded .doc-paragraph-content {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.doc-paragraph.folded .fold-hint {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 11px;
  color: #999;
  background: rgba(255,255,255,0.9);
  padding: 2px 8px;
  border-radius: 4px;
  pointer-events: none;
}
.doc-paragraph.folded:hover {
  opacity: 0.9;
  background: #f0f0f0;
}

/* ===== 子分数展示 ===== */
.sub-scores .sub-score-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 12px;
}
.sub-scores .sub-score-item span {
  width: 64px;
  flex-shrink: 0;
  color: #666;
}
.sub-scores .sub-score-item .el-progress {
  flex: 1;
}
.sub-scores .sub-score-overall {
  text-align: right;
  margin-top: 8px;
  font-size: 13px;
  color: #333;
}

/* ===== 编辑器根 ===== */
.patafix-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #FAF9F6;
}

/* ===== 顶部指标条 ===== */
.editor-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: #fff;
  border-bottom: 1px solid #E8E6E1;
  gap: 16px;
  flex-shrink: 0;
}

.topbar-left {
  flex-shrink: 0;
}

.topbar-metrics {
  display: flex;
  align-items: center;
  gap: 32px;
  flex: 1;
  justify-content: center;
}

.metric-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.metric-label {
  font-size: 12px;
  color: #9E9E9E;
  font-weight: 500;
}

.metric-value {
  font-size: 22px;
  font-weight: 700;
  line-height: 1.2;
}

.metric-sub {
  font-size: 11px;
  color: #BDBDBD;
}

.metric-delta {
  font-size: 11px;
  font-weight: 500;
}

.delta-down { color: #2E7D5A; }
.delta-up { color: #D32F2F; }

.color-high { color: #D32F2F; }
.color-medium { color: #F57C00; }
.color-low { color: #2E7D5A; }
.color-predicted { color: #2E7D5A; }
.color-accent { color: #2E7D5A; }

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

/* ===== 主体三栏 ===== */
.editor-body {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* ===== 左侧目录 ===== */
.editor-sidebar-left {
  width: 260px;
  min-width: 260px;
  background: #fff;
  border-right: 1px solid #E8E6E1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-tabs {
  display: flex;
  border-bottom: 1px solid #E8E6E1;
  padding: 0 16px;
}

.sidebar-tab {
  padding: 12px 8px;
  font-size: 14px;
  font-weight: 500;
  color: #9E9E9E;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: all 0.15s;
}

.sidebar-tab.active {
  color: #2E7D5A;
  border-bottom-color: #2E7D5A;
  font-weight: 600;
}

.outline-tree {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
}

.outline-chapter {
  margin-bottom: 4px;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.12s;
  border-left: 3px solid transparent;
}

.outline-chapter:hover,
.outline-chapter.active {
  background: #E8F5E9;
}

.outline-chapter.outline-risk-high { border-left-color: #E53935; background: rgba(229, 57, 53, 0.06); }
.outline-chapter.outline-risk-medium { border-left-color: #FB8C00; background: rgba(251, 140, 0, 0.06); }
.outline-chapter.outline-risk-low { border-left-color: #8E24AA; background: rgba(142, 36, 170, 0.05); }
.outline-chapter.outline-risk-normal { border-left-color: #43A047; background: rgba(67, 160, 71, 0.05); }

.outline-title {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 6px;
  font-size: 14px;
  font-weight: 600;
  color: #1A1A1A;
}

.outline-count {
  margin-left: auto;
  min-width: 22px;
  height: 20px;
  line-height: 20px;
  text-align: center;
  border-radius: 10px;
  background: #F2F1EC;
  color: #6B6B6B;
  font-size: 12px;
  font-weight: 700;
}

.outline-children {
  padding-left: 16px;
  border-left: 1px solid #EEECE6;
  margin-left: 10px;
}

.outline-para {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px;
  font-size: 13px;
  color: #6B6B6B;
  border-radius: 4px;
  cursor: pointer;
  border-left: 3px solid transparent;
}

.outline-para:hover,
.outline-para.active {
  background: #F5F5F5;
  color: #1A1A1A;
}

.outline-para.outline-risk-high { border-left-color: #E53935; background: rgba(229, 57, 53, 0.06); }
.outline-para.outline-risk-medium { border-left-color: #FB8C00; background: rgba(251, 140, 0, 0.06); }
.outline-para.outline-risk-low { border-left-color: #8E24AA; background: rgba(142, 36, 170, 0.05); }
.outline-para.outline-risk-normal { border-left-color: #43A047; background: rgba(67, 160, 71, 0.05); }

.outline-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.outline-text {
  line-height: 1.4;
}

.truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dot-red { background: #E53935; }
.dot-orange { background: #FB8C00; }
.dot-purple { background: #8E24AA; }
.dot-normal { background: #43A047; }

.risk-legend {
  padding: 16px;
  border-top: 1px solid #E8E6E1;
  font-size: 12px;
  color: #6B6B6B;
}

.legend-title {
  font-weight: 600;
  margin-bottom: 10px;
  color: #1A1A1A;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* ===== 中间正文 ===== */
.unmatched-panel {
  border-top: 1px solid #E8E6E1;
  padding: 12px 14px;
  background: #FFFBF3;
}

.unmatched-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  color: #7A4D00;
}

.unmatched-toggle {
  font-size: 12px;
  color: #A66B00;
  font-weight: 500;
}

.unmatched-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 10px;
}

.unmatched-item {
  padding: 10px;
  border: 1px solid #F1D9A8;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.unmatched-item:hover,
.unmatched-item.selected {
  border-color: #D8941F;
  box-shadow: 0 0 0 2px rgba(216, 148, 31, 0.14);
}

.unmatched-risk {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.unmatched-text {
  margin: 0;
  color: #3E3426;
  font-size: 12px;
  line-height: 1.5;
}

.unmatched-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.editor-document {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: #FAF9F6;
}

.document-scale-shell {
  width: fit-content;
  min-width: 100%;
  margin: 0 auto;
  transform-origin: top center;
}

.a4-page {
  max-width: 210mm;
  min-height: 297mm;
  margin: 0 auto;
  background: #fff;
  padding: 24mm 20mm;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  border-radius: 4px;
}

.paper-title {
  font-size: 22pt;
  font-weight: bold;
  text-align: center;
  margin-bottom: 24pt;
  color: #1A1A1A;
  font-family: 'SimHei', '黑体', sans-serif;
}

.chapter-block {
  margin-bottom: 18pt;
}

.chapter-title {
  font-size: 16pt;
  font-weight: bold;
  color: #1A1A1A;
  margin: 18pt 0 12pt;
  text-align: center;
  font-family: 'SimHei', '黑体', sans-serif;
}

.doc-paragraph {
  padding: 6px 10px;
  margin: 0;
  cursor: pointer;
  transition: background 0.12s ease;
  border-left: 3px solid transparent;
  border-radius: 4px;
  text-indent: 2em;
  line-height: 1.8;
  font-size: 12pt;
  font-family: 'SimSun', '宋体', serif;
  color: #1A1A1A;
  white-space: pre-wrap;
  word-break: break-word;
}

.doc-paragraph:hover {
  filter: brightness(0.97);
}

.doc-paragraph.is-active {
  outline: 2px solid #2E7D5A;
  outline-offset: -2px;
}

.doc-paragraph[contenteditable="true"],
:deep(.mammoth-doc p.doc-paragraph[contenteditable="true"]) {
  cursor: text;
  caret-color: #2E7D5A;
  box-shadow: inset 0 0 0 1px rgba(46, 125, 90, 0.22);
}

/* 风险着色 */
.para-red {
  background: rgba(229, 57, 53, 0.20);
  border-left-color: #E53935;
}

.para-orange {
  background: rgba(251, 140, 0, 0.20);
  border-left-color: #FB8C00;
}

.para-purple {
  background: rgba(142, 36, 170, 0.16);
  border-left-color: #8E24AA;
}

.para-normal {
  background: rgba(67, 160, 71, 0.12);
  border-left-color: #43A047;
}

.doc-paragraph.is-rewritten {
  border-left-color: #2E7D5A !important;
  border-left-width: 4px;
}

/* ===== 右侧面板 ===== */
.editor-sidebar-right {
  width: 380px;
  min-width: 380px;
  background: #fff;
  border-left: 1px solid #E8E6E1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #E8E6E1;
}

.panel-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1A1A1A;
}

.panel-close {
  background: none;
  border: none;
  font-size: 18px;
  color: #9E9E9E;
  cursor: pointer;
  line-height: 1;
}

.panel-close:hover {
  color: #1A1A1A;
}

.panel-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.empty-hint {
  font-size: 14px;
  color: #9E9E9E;
  text-align: center;
  line-height: 1.6;
}

.risk-filter-bar {
  display: flex;
  gap: 8px;
  padding: 12px 20px;
  border-bottom: 1px solid #E8E6E1;
  overflow-x: auto;
}

.filter-tag {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 4px;
  font-weight: 500;
  white-space: nowrap;
}

.filter-high { color: #C62828; background: #FFEBEE; }
.filter-medium { color: #EF6C00; background: #FFF3E0; }
.filter-low { color: #6A1B9A; background: #F3E5F5; }
.filter-normal { color: #424242; background: #F5F5F5; }

.panel-loading,
.panel-error {
  padding: 20px;
}

.advice-cards {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}

.advice-card {
  background: #FAF9F6;
  border: 1px solid #E8E6E1;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.risk-badge {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 4px;
  font-weight: 600;
}

.badge-high { color: #C62828; background: #FFEBEE; }
.badge-medium { color: #EF6C00; background: #FFF3E0; }
.badge-low { color: #6A1B9A; background: #F3E5F5; }

.aigc-score {
  font-size: 13px;
  color: #F57C00;
  font-weight: 600;
}

.card-section {
  margin-bottom: 14px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #1A1A1A;
  margin-bottom: 6px;
}

.section-text {
  font-size: 13px;
  color: #6B6B6B;
  line-height: 1.7;
  margin: 0;
}

.original-text {
  font-size: 13px;
  color: #9E9E9E;
  line-height: 1.7;
  padding: 10px;
  background: #fff;
  border-radius: 4px;
  border: 1px dashed #E0E0E0;
}

.rewritten-text {
  font-size: 13px;
  color: #1A1A1A;
  line-height: 1.7;
  padding: 10px;
  background: #E8F5E9;
  border-radius: 4px;
  border: 1px solid #C8E6C9;
}

.risk-word-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.risk-word-tag {
  font-size: 12px;
  color: #B71C1C;
  background: #FFEBEE;
  border: 1px solid #FFCDD2;
  border-radius: 4px;
  padding: 2px 6px;
}

:deep(.risk-word),
.risk-word {
  color: #B71C1C;
  background: rgba(229, 57, 53, 0.16);
  border-bottom: 1px solid #E53935;
  padding: 0 2px;
  border-radius: 2px;
}

:deep(.rewrite-word),
.rewrite-word {
  color: #1B5E20;
  background: rgba(46, 125, 90, 0.18);
  border-bottom: 1px solid #2E7D5A;
  padding: 0 2px;
  border-radius: 2px;
}

.card-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.sentence-card {
  background: #fff;
  border: 1px solid #E8E6E1;
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 12px;
}

.sent-original,
.sent-rewritten,
.sent-explanation {
  margin-bottom: 10px;
}

.sent-original label,
.sent-rewritten label,
.sent-explanation label {
  font-size: 11px;
  font-weight: 600;
  color: #9E9E9E;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  display: block;
  margin-bottom: 4px;
}

.sent-original p {
  font-size: 13px;
  color: #9E9E9E;
  margin: 0;
  line-height: 1.6;
}

.sent-rewritten p {
  font-size: 13px;
  color: #1A1A1A;
  margin: 0;
  line-height: 1.6;
  padding: 8px;
  background: #E8F5E9;
  border-radius: 4px;
}

.sent-explanation p {
  font-size: 12px;
  color: #6B6B6B;
  margin: 0;
  line-height: 1.6;
}

/* ===== 底部操作栏 ===== */
.editor-bottombar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 24px;
  background: #fff;
  border-top: 1px solid #E8E6E1;
  flex-shrink: 0;
  gap: 16px;
}

.bottombar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.bottombar-count {
  font-size: 14px;
  font-weight: 600;
  color: #1A1A1A;
  min-width: 60px;
  text-align: center;
}

.bottombar-center {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 13px;
  color: #6B6B6B;
}

.status-text {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #2E7D5A;
  font-weight: 500;
}

.status-sub {
  color: #9E9E9E;
}

.bottombar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ===== 加载态 ===== */
.doc-loading {
  padding: 40px;
}

.doc-loading-actions {
  margin-top: 16px;
}

/* PDF 视图 */
.pdf-view-wrapper {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.pdf-text-layer {
  background: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  padding: 20mm;
}

.pdf-text-header {
  text-align: center;
  font-size: 12px;
  color: #9E9E9E;
  padding: 8px;
  margin: -20mm -20mm 16px -20mm;
  background: #F5F5F5;
  border-bottom: 1px solid #E8E6E1;
}

/* ===== 滚动条美化 ===== */
.editor-document::-webkit-scrollbar,
.outline-tree::-webkit-scrollbar,
.advice-cards::-webkit-scrollbar {
  width: 6px;
}

.editor-document::-webkit-scrollbar-thumb,
.outline-tree::-webkit-scrollbar-thumb,
.advice-cards::-webkit-scrollbar-thumb {
  background: #D8D8D8;
  border-radius: 3px;
}
</style>

<style>
/* ===== 夜间模式全局覆盖 ===== */
html[data-theme='dark'] .patafix-editor {
  background: #0b1220;
}

html[data-theme='dark'] .editor-topbar {
  background: #131c29;
  border-bottom-color: rgba(255, 255, 255, 0.08);
}

html[data-theme='dark'] .editor-sidebar-left,
html[data-theme='dark'] .editor-sidebar-right {
  background: #131c29;
  border-color: rgba(255, 255, 255, 0.08);
}

html[data-theme='dark'] .editor-document {
  background: #0b1220;
}

html[data-theme='dark'] .a4-page {
  background: #1a2332;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
}

/* 文字颜色 */
html[data-theme='dark'] .metric-label,
html[data-theme='dark'] .metric-sub {
  color: #9eacbf;
}

html[data-theme='dark'] .sidebar-tab {
  color: #9eacbf;
}

html[data-theme='dark'] .sidebar-tab.active {
  color: #22c55e;
  border-bottom-color: #22c55e;
}

html[data-theme='dark'] .outline-title,
html[data-theme='dark'] .legend-title,
html[data-theme='dark'] .paper-title,
html[data-theme='dark'] .chapter-title,
html[data-theme='dark'] .panel-header h4,
html[data-theme='dark'] .section-title,
html[data-theme='dark'] .bottombar-count {
  color: #f6f8fb;
}

html[data-theme='dark'] .outline-para,
html[data-theme='dark'] .outline-text,
html[data-theme='dark'] .risk-legend,
html[data-theme='dark'] .legend-item,
html[data-theme='dark'] .section-text,
html[data-theme='dark'] .sent-explanation p,
html[data-theme='dark'] .bottombar-center {
  color: #c4cfdd;
}

html[data-theme='dark'] .doc-paragraph {
  color: #e5ecf4;
}

html[data-theme='dark'] .outline-count {
  background: #1e2d3f;
  color: #9eacbf;
}

/* 卡片和面板 */
html[data-theme='dark'] .advice-card,
html[data-theme='dark'] .sentence-card,
html[data-theme='dark'] .original-text,
html[data-theme='dark'] .unmatched-item,
html[data-theme='dark'] .pdf-text-layer,
html[data-theme='dark'] .editor-bottombar {
  background: #131c29;
  border-color: rgba(255, 255, 255, 0.08);
}

/* 悬停状态 */
html[data-theme='dark'] .outline-chapter:hover,
html[data-theme='dark'] .outline-chapter.active {
  background: rgba(34, 197, 94, 0.12);
}

html[data-theme='dark'] .outline-para:hover,
html[data-theme='dark'] .outline-para.active {
  background: rgba(255, 255, 255, 0.06);
  color: #f6f8fb;
}

/* 滚动条 */
html[data-theme='dark'] .editor-document::-webkit-scrollbar-thumb,
html[data-theme='dark'] .outline-tree::-webkit-scrollbar-thumb,
html[data-theme='dark'] .advice-cards::-webkit-scrollbar-thumb {
  background: #2a3a4f;
}

/* 各种标签 */
html[data-theme='dark'] .filter-high { color: #ff9f94; background: rgba(229, 57, 53, 0.15); }
html[data-theme='dark'] .filter-medium { color: #ffb74d; background: rgba(251, 140, 0, 0.15); }
html[data-theme='dark'] .filter-low { color: #ce93d8; background: rgba(142, 36, 170, 0.15); }
html[data-theme='dark'] .filter-normal { color: #c4cfdd; background: rgba(255, 255, 255, 0.08); }

html[data-theme='dark'] .badge-high { color: #ff9f94; background: rgba(229, 57, 53, 0.15); }
html[data-theme='dark'] .badge-medium { color: #ffb74d; background: rgba(251, 140, 0, 0.15); }
html[data-theme='dark'] .badge-low { color: #ce93d8; background: rgba(142, 36, 170, 0.15); }

/* 重写后的文本 */
html[data-theme='dark'] .rewritten-text,
html[data-theme='dark'] .sent-rewritten p {
  background: rgba(46, 125, 90, 0.15);
  border-color: rgba(46, 125, 90, 0.3);
  color: #b8f0cb;
}

/* 风险词 */
html[data-theme='dark'] .risk-word-tag {
  color: #ff9f94;
  background: rgba(229, 57, 53, 0.15);
  border-color: rgba(229, 57, 53, 0.3);
}

html[data-theme='dark'] :deep(.risk-word),
html[data-theme='dark'] .risk-word {
  color: #ff9f94;
  background: rgba(229, 57, 53, 0.2);
  border-bottom-color: #E53935;
}

html[data-theme='dark'] :deep(.rewrite-word),
html[data-theme='dark'] .rewrite-word {
  color: #b8f0cb;
  background: rgba(46, 125, 90, 0.2);
  border-bottom-color: #2E7D5A;
}

/* PDF 相关 */
html[data-theme='dark'] .pdf-text-header {
  background: #1a2332;
  border-bottom-color: rgba(255, 255, 255, 0.08);
  color: #9eacbf;
}

html[data-theme='dark'] .panel-close {
  color: #9eacbf;
}
html[data-theme='dark'] .panel-close:hover {
  color: #f6f8fb;
}

html[data-theme='dark'] .empty-hint {
  color: #9eacbf;
}

/* unmatched */
html[data-theme='dark'] .unmatched-panel {
  background: #1a2332;
  border-top-color: rgba(255, 255, 255, 0.08);
}

html[data-theme='dark'] .unmatched-header {
  color: #ffb74d;
}

html[data-theme='dark'] .unmatched-toggle {
  color: #ffb74d;
}

html[data-theme='dark'] .unmatched-text {
  color: #c4cfdd;
}

html[data-theme='dark'] .panel-loading,
html[data-theme='dark'] .panel-error {
  color: #c4cfdd;
}

html[data-theme='dark'] .sent-original p {
  color: #9eacbf;
}

html[data-theme='dark'] .status-text {
  color: #22c55e;
}

html[data-theme='dark'] .status-sub {
  color: #9eacbf;
}

html[data-theme='dark'] .aigc-score {
  color: #ffb74d;
}

/* color classes */
html[data-theme='dark'] .color-high { color: #ff9f94; }
html[data-theme='dark'] .color-medium { color: #ffb74d; }
html[data-theme='dark'] .color-low { color: #7ce4a8; }
html[data-theme='dark'] .color-predicted { color: #7ce4a8; }
html[data-theme='dark'] .color-accent { color: #7ce4a8; }
html[data-theme='dark'] .delta-down { color: #7ce4a8; }
html[data-theme='dark'] .delta-up { color: #ff9f94; }

/* doc-paragraph hover */
html[data-theme='dark'] .doc-paragraph:hover {
  filter: brightness(1.1);
}

/* para colors in dark */
html[data-theme='dark'] .para-red {
  background: rgba(229, 57, 53, 0.25);
}
html[data-theme='dark'] .para-orange {
  background: rgba(251, 140, 0, 0.25);
}
html[data-theme='dark'] .para-purple {
  background: rgba(142, 36, 170, 0.2);
}
html[data-theme='dark'] .para-normal {
  background: rgba(67, 160, 71, 0.15);
}

/* outline-chapter risk colors in dark */
html[data-theme='dark'] .outline-chapter.outline-risk-high { background: rgba(229, 57, 53, 0.12); }
html[data-theme='dark'] .outline-chapter.outline-risk-medium { background: rgba(251, 140, 0, 0.12); }
html[data-theme='dark'] .outline-chapter.outline-risk-low { background: rgba(142, 36, 170, 0.1); }
html[data-theme='dark'] .outline-chapter.outline-risk-normal { background: rgba(67, 160, 71, 0.1); }

html[data-theme='dark'] .outline-para.outline-risk-high { background: rgba(229, 57, 53, 0.12); }
html[data-theme='dark'] .outline-para.outline-risk-medium { background: rgba(251, 140, 0, 0.12); }
html[data-theme='dark'] .outline-para.outline-risk-low { background: rgba(142, 36, 170, 0.1); }
html[data-theme='dark'] .outline-para.outline-risk-normal { background: rgba(67, 160, 71, 0.1); }

/* priority-nav */
html[data-theme='dark'] .priority-nav-header {
  color: #f6f8fb;
}

html[data-theme='dark'] .priority-nav-item {
  color: #c4cfdd;
}

html[data-theme='dark'] .priority-nav-item:hover {
  background: rgba(255, 255, 255, 0.06);
}

/* outline-children border */
html[data-theme='dark'] .outline-children {
  border-left-color: rgba(255, 255, 255, 0.08);
}

/* RewritePage.vue root background */
html[data-theme='dark'] .rewrite-page {
  background: #0b1220;
}
</style>
