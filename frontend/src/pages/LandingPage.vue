<template>
  <div class="landing">
    <section class="hero">
      <div class="hero-content">
        <span class="hero-badge">论文提交前的最后一道防线</span>
        <h1>AI 查重 & AIGC 风险<br/>预检平台</h1>
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
          <p>支持 .docx、.pdf、.txt 等格式，最大 10MB</p>
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
      <p>论文风险预检台 &copy; {{ new Date().getFullYear() }}</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getCurrentAccount } from '../api'

const router = useRouter()

onMounted(() => {
  getCurrentAccount().then(() => {
    router.replace('/app')
  }).catch(() => {
    // 未登录，留在 landing page
  })
})
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
  .feature-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .hero h1 {
    font-size: 32px;
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
