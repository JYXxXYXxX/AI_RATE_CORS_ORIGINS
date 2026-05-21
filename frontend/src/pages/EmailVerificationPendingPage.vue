<template>
  <div class="verify-page">
    <div class="verify-card">
      <router-link to="/" class="verify-logo">PataFix</router-link>
      <h1>等待邮箱验证</h1>
      <p class="verify-hint">
        我们已经向 <strong>{{ targetEmail }}</strong> 发送了一封验证邮件。请点击邮件中的验证链接，完成后再返回登录。
      </p>

      <div class="verify-actions">
        <button class="btn btn-primary" :disabled="loading" @click="handleResend">
          {{ loading ? '发送中...' : '重新发送验证邮件' }}
        </button>
        <router-link class="btn btn-ghost" :to="{ name: 'login', query: { email: targetEmail } }">
          返回登录
        </router-link>
      </div>

      <p v-if="message" class="verify-message">{{ message }}</p>

      <div v-if="devLink" class="dev-box">
        <strong>开发环境验证链接</strong>
        <a :href="devLink">{{ devLink }}</a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute } from 'vue-router'
import { resendVerificationEmail } from '../api'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const auth = useAuthStore()

const loading = ref(false)
const message = ref('')
const devLink = ref(auth.pendingDevVerificationUrl || '')

const targetEmail = computed(() => {
  const fromQuery = typeof route.query.email === 'string' ? route.query.email : ''
  return fromQuery || auth.pendingVerificationEmail || ''
})

async function handleResend() {
  if (!targetEmail.value) {
    message.value = '缺少待验证邮箱，请重新注册或登录。'
    return
  }
  loading.value = true
  message.value = ''
  try {
    const result = await resendVerificationEmail(targetEmail.value)
    auth.setPendingVerification(result.email, result.dev_verification_url)
    devLink.value = result.dev_verification_url || ''
    message.value = result.message || '验证邮件已重新发送。'
    ElMessage.success(message.value)
  } catch (error) {
    message.value = error instanceof Error ? error.message : '重发失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.verify-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 28px;
}

.verify-card {
  width: min(560px, 100%);
  padding: 34px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(31, 54, 73, 0.08);
  box-shadow: 0 18px 46px rgba(29, 45, 61, 0.08);
}

.verify-logo {
  display: block;
  width: fit-content;
  margin: 0 auto 20px;
  color: #2f7d67;
  text-decoration: none;
  font-size: 14px;
  font-weight: 700;
}

.verify-card h1 {
  margin: 0 0 10px;
  text-align: center;
  color: #172033;
}

.verify-hint {
  margin: 0;
  color: #53606f;
  text-align: center;
  line-height: 1.8;
}

.verify-actions {
  margin-top: 24px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.btn {
  min-height: 44px;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  font-weight: 700;
}

.btn-primary {
  background: linear-gradient(135deg, #2f7d67, #236451);
  color: #fff;
}

.btn-ghost {
  border: 1px solid rgba(47, 125, 103, 0.24);
  background: #fff;
  color: #2f7d67;
}

.verify-message {
  margin: 18px 0 0;
  color: #2f7d67;
  text-align: center;
}

.dev-box {
  margin-top: 22px;
  padding: 14px 16px;
  border-radius: 14px;
  background: #f6fbf8;
  border: 1px dashed rgba(47, 125, 103, 0.26);
  display: grid;
  gap: 8px;
}

.dev-box strong {
  color: #172033;
}

.dev-box a {
  color: #2f7d67;
  word-break: break-all;
}
</style>
