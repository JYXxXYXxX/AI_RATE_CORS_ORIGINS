<template>
  <div class="verify-page">
    <div class="verify-card">
      <router-link to="/" class="verify-logo">PataFix</router-link>
      <h1>{{ title }}</h1>
      <p class="verify-hint">{{ description }}</p>

      <div class="verify-actions">
        <router-link class="btn btn-primary" :to="{ name: 'login', query: loginQuery }">
          去登录
        </router-link>
        <router-link class="btn btn-ghost" to="/">返回首页</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { verifyEmailToken } from '../api'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const auth = useAuthStore()

const title = ref('正在验证邮箱...')
const description = ref('请稍候，我们正在处理你的验证链接。')
const verifiedEmail = ref('')

const loginQuery = computed(() => {
  if (!verifiedEmail.value) return {}
  return { email: verifiedEmail.value, verified: '1' }
})

onMounted(async () => {
  const token = typeof route.query.token === 'string' ? route.query.token : ''
  if (!token) {
    title.value = '验证链接无效'
    description.value = '当前链接缺少验证参数，请回到等待验证页重新发送。'
    return
  }

  try {
    const result = await verifyEmailToken(token)
    auth.clearPendingVerification()
    verifiedEmail.value = result.email
    title.value = result.already_verified ? '邮箱已验证' : '邮箱验证成功'
    description.value = result.already_verified
      ? '这个邮箱之前已经验证过了，现在可以直接登录。'
      : '验证已经完成，现在你可以使用邮箱和密码正常登录。'
  } catch (error) {
    title.value = '验证失败'
    description.value = error instanceof Error ? error.message : '验证链接已失效，请重新发送验证邮件。'
  }
})
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
</style>
