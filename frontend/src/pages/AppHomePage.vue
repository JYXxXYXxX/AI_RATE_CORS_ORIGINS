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
        <div class="paper-stack">
          <div class="paper-card paper-back" />
          <div class="paper-card paper-front">
            <span class="paper-line title" />
            <span class="paper-line" />
            <span class="paper-line short" />
            <span class="risk-note high">高风险句</span>
            <span class="paper-line" />
            <span class="risk-note medium">重复表达</span>
            <span class="paper-line short" />
          </div>
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
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAnalysisStore } from '../stores/analysis'

const router = useRouter()
const analysis = useAnalysisStore()

const latestRunId = computed(() => analysis.history.find(item => item.run_id)?.run_id || '')

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
}

.home-button.primary {
  color: #fff;
  background: #2f6f53;
}

.home-button.ghost {
  color: #2f3b34;
  background: #f0eadf;
}

.hero-board {
  position: relative;
  min-height: 360px;
  border-radius: 26px;
  overflow: hidden;
  background:
    linear-gradient(135deg, rgba(255, 253, 247, 0.92), rgba(235, 242, 231, 0.86));
}

.paper-stack {
  position: absolute;
  inset: 38px 64px 72px 46px;
}

.paper-card {
  position: absolute;
  inset: 0;
  border-radius: 10px;
  background: #fffefa;
  box-shadow: 0 16px 45px rgba(46, 56, 48, 0.12);
}

.paper-back {
  transform: rotate(-5deg) translate(-16px, 14px);
  background: #e8e0d1;
}

.paper-front {
  padding: 32px;
  display: grid;
  align-content: start;
  gap: 14px;
}

.paper-line {
  height: 8px;
  border-radius: 99px;
  background: #d9d4c8;
}

.paper-line.title {
  width: 66%;
  height: 13px;
  background: #56644f;
}

.paper-line.short {
  width: 48%;
}

.risk-note {
  width: fit-content;
  padding: 5px 9px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 700;
}

.risk-note.high {
  color: #8f332f;
  background: #f4d9d1;
}

.risk-note.medium {
  color: #8c5a1d;
  background: #f4e3bf;
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

@media (max-width: 980px) {
  .home-hero,
  .home-grid {
    grid-template-columns: 1fr;
  }

  .hero-board {
    min-height: 320px;
  }
}
</style>
