<template>
  <div class="auth-page">
    <div class="auth-card">
      <router-link to="/" class="auth-logo">论文风险预检台</router-link>
      <h1>注册</h1>
      <p class="auth-hint">创建账号后可获得免费体验额度</p>

      <form class="auth-form" @submit.prevent="handleRegister">
        <div class="form-field">
          <label>昵称（可选）</label>
          <input v-model="displayName" type="text" placeholder="你希望怎么称呼" />
        </div>
        <div class="form-field">
          <label>邮箱</label>
          <input v-model="email" type="email" placeholder="your@email.com" required autofocus />
        </div>
        <div class="form-field">
          <label>密码</label>
          <input v-model="password" type="password" placeholder="至少 6 位" required minlength="6" />
        </div>
        <p v-if="errorMsg" class="form-error">{{ errorMsg }}</p>
        <button type="submit" class="btn btn-primary btn-full" :disabled="auth.loading">
          {{ auth.loading ? '注册中...' : '注册' }}
        </button>
      </form>

      <p class="auth-switch">
        已有账号？<router-link to="/login">去登录</router-link>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const displayName = ref('')
const email = ref('')
const password = ref('')
const errorMsg = ref('')

async function handleRegister() {
  errorMsg.value = ''
  try {
    await auth.register(email.value, password.value, displayName.value || undefined)
    router.push('/app')
  } catch (err) {
    errorMsg.value = err instanceof Error ? err.message : '注册失败'
  }
}
</script>

<style scoped>
.auth-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 28px;
}

.auth-card {
  width: 100%;
  max-width: 400px;
  padding: 40px 36px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(31, 54, 73, 0.08);
  box-shadow: 0 16px 45px rgba(29, 45, 61, 0.08);
  backdrop-filter: blur(14px);
}

.auth-logo {
  display: block;
  text-align: center;
  font-size: 15px;
  font-weight: 700;
  color: #2f7d67;
  text-decoration: none;
  margin-bottom: 28px;
}

.auth-card h1 {
  font-size: 26px;
  color: #172033;
  margin: 0 0 6px;
  text-align: center;
}

.auth-hint {
  text-align: center;
  color: #53606f;
  font-size: 14px;
  margin: 0 0 28px;
}

.auth-form {
  display: grid;
  gap: 18px;
}

.form-field {
  display: grid;
  gap: 6px;
}

.form-field label {
  font-size: 13px;
  font-weight: 600;
  color: #344150;
}

.form-field input {
  width: 100%;
  padding: 10px 14px;
  border: 1.5px solid rgba(31, 54, 73, 0.15);
  border-radius: 10px;
  font-size: 15px;
  color: #172033;
  background: #fff;
  transition: border-color 0.15s;
  outline: none;
  box-sizing: border-box;
}

.form-field input:focus {
  border-color: #2f7d67;
}

.form-error {
  color: #c84b52;
  font-size: 13px;
  margin: 0;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 11px 24px;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 0.18s ease;
}

.btn-primary {
  background: linear-gradient(135deg, #2f7d67, #236451);
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(47, 125, 103, 0.25);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-full {
  width: 100%;
}

.auth-switch {
  text-align: center;
  margin: 24px 0 0;
  font-size: 14px;
  color: #53606f;
}

.auth-switch a {
  color: #2f7d67;
  font-weight: 600;
  text-decoration: none;
}

.auth-switch a:hover {
  text-decoration: underline;
}
</style>
