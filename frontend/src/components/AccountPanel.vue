<template>
  <section class="feedback-card account-card">
    <div class="card-head">
      <p class="eyebrow">账户与额度</p>
      <h3>{{ user ? '已登录，可直接走充值与预检闭环' : '先登录，再用额度跑正式预检流程' }}</h3>
    </div>

    <template v-if="user && billing">
      <div class="account-summary">
        <div class="status-tile soft-card">
          <span>当前用户</span>
          <strong>{{ user.display_name || user.email }}</strong>
          <small>{{ user.email }}</small>
        </div>
        <div class="status-tile soft-card">
          <span>剩余额度</span>
          <strong>{{ billing.user.credits_balance }}</strong>
          <small>每次分析默认消耗 1 次</small>
        </div>
      </div>

      <div class="payment-channel-section">
        <div class="section-title-row">
          <p class="helper-text">支付通道</p>
          <span class="helper-text">当前推荐：{{ selectedChannel?.title || '模拟支付' }}</span>
        </div>
        <div class="payment-channel-grid">
          <button
            v-for="channel in paymentChannels"
            :key="channel.code"
            type="button"
            class="payment-channel-card"
            :class="{ active: selectedProvider === channel.code, muted: !channel.ready }"
            @click="selectedProvider = channel.code"
          >
            <strong>{{ channel.title }}</strong>
            <span>{{ channel.ready ? '已就绪' : '已预留接入位' }}</span>
            <small>{{ channel.description }}</small>
          </button>
        </div>
      </div>

      <div class="package-list">
        <article v-for="item in billing.packages" :key="item.code" class="train-card package-card">
          <strong>{{ item.title }}</strong>
          <p>{{ item.description }}</p>
          <p>{{ item.credits }} 次 / ¥{{ (item.amount_cents / 100).toFixed(2) }}</p>
          <el-button type="primary" plain :loading="creatingOrder === item.code" @click="createOrder(item.code)">
            用{{ selectedChannel?.title || '模拟支付' }}创建订单
          </el-button>
        </article>
      </div>

      <div v-if="pendingOrder" class="recent-list">
        <p class="helper-text">当前待支付订单</p>
        <article class="mini-record pending-order-card">
          <strong>{{ pendingOrder.order.order_no }}</strong>
          <span>{{ pendingOrder.provider_label }}</span>
          <span>{{ orderStatusLabel(pendingOrder.order.status) }}</span>
          <span>¥{{ (pendingOrder.order.amount_cents / 100).toFixed(2) }}</span>
        </article>
        <p class="helper-text">{{ pendingOrder.pay_hint }}</p>
        <p v-if="pendingOrder.qr_content" class="helper-text">支付口令：{{ pendingOrder.qr_content }}</p>
        <p v-if="!pendingOrder.provider_ready" class="helper-text warning-text">
          这个通道现在还是预留接入位，适合先把订单、额度和支付页链路联调跑通。
        </p>
        <div class="inline-actions">
          <el-button
            v-if="pendingOrder.mock_pay_supported"
            type="success"
            :loading="payingOrder === pendingOrder.order.order_no"
            @click="payOrder(pendingOrder.order.order_no)"
          >
            模拟支付入账
          </el-button>
          <el-button
            v-else-if="pendingOrder.payment_url"
            type="primary"
            plain
            @click="openPaymentLink(pendingOrder.payment_url)"
          >
            前往支付
          </el-button>
        </div>
      </div>

      <div class="recent-list">
        <p class="helper-text">最近订单</p>
        <article v-for="order in billing.recent_orders.slice(0, 3)" :key="order.id" class="mini-record">
          <strong>{{ order.package_code }}</strong>
          <span>{{ providerTitle(order.provider) }}</span>
          <span>{{ orderStatusLabel(order.status) }}</span>
          <button
            v-if="order.status === 'pending'"
            type="button"
            class="inline-link"
            @click="resumeOrder(order.order_no)"
          >
            继续支付
          </button>
          <span v-else>+{{ order.credits }} 次</span>
        </article>
        <p v-if="!billing.recent_orders.length" class="helper-text">
          还没有订单记录，先创建一个订单把充值和额度链路跑通。
        </p>
      </div>

      <div class="recent-list">
        <p class="helper-text">最近检测</p>
        <article v-for="task in billing.recent_tasks.slice(0, 3)" :key="task.task_id" class="mini-record">
          <strong>{{ task.title || task.filename || `任务 ${task.task_id.slice(0, 8)}` }}</strong>
          <span>{{ taskLabel(task.status, task.progress) }}</span>
          <button
            v-if="task.run_id"
            type="button"
            class="inline-link"
            @click="emit('openTask', { taskId: task.task_id, runId: task.run_id })"
          >
            查看报告
          </button>
          <span v-else>{{ formatDate(task.created_at) }}</span>
        </article>
        <p v-if="!billing.recent_tasks.length" class="helper-text">
          还没有检测记录，上传论文后这里会自动沉淀你的任务历史。
        </p>
      </div>

      <el-button class="logout-button" @click="signOut">退出登录</el-button>
    </template>

    <template v-else>
      <el-tabs v-model="authMode" stretch>
        <el-tab-pane label="登录" name="login" />
        <el-tab-pane label="注册" name="register" />
      </el-tabs>

      <el-form label-position="top" class="feedback-form">
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="例如 you@example.com" />
        </el-form-item>
        <el-form-item v-if="authMode === 'register'" label="昵称">
          <el-input v-model="form.displayName" placeholder="例如 毕设同学" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="至少 8 位" />
        </el-form-item>
        <el-button type="primary" :loading="submitting" @click="submitAuth">
          {{ authMode === 'login' ? '登录并进入预检台' : '注册并领取试用额度' }}
        </el-button>
      </el-form>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus/es/components/message/index'
import {
  createBillingOrder,
  getBillingOrder,
  getBillingSummary,
  loginAccount,
  logoutAccount,
  mockPayBillingOrder,
  registerAccount
} from '../api'
import type {
  BillingOrderDetailResponse,
  BillingPaymentChannel,
  BillingSummaryResponse,
  UserSummary
} from '../types'

const props = defineProps<{
  user: UserSummary | null
  billing: BillingSummaryResponse | null
}>()

const emit = defineEmits<{
  sessionChange: [payload: { user: UserSummary | null; billing: BillingSummaryResponse | null }]
  openTask: [payload: { taskId: string; runId: string }]
}>()

const authMode = ref<'login' | 'register'>('login')
const submitting = ref(false)
const creatingOrder = ref('')
const payingOrder = ref('')
const pendingOrder = ref<BillingOrderDetailResponse | null>(null)
const selectedProvider = ref<'mock_qr' | 'alipay' | 'wechat'>('mock_qr')
const form = reactive({
  email: '',
  displayName: '',
  password: ''
})

const fallbackChannels: BillingPaymentChannel[] = [
  {
    code: 'mock_qr',
    title: '模拟支付',
    description: '开发环境与联调推荐，点击一次即可完成充值。',
    enabled: true,
    ready: true,
    mode: 'mock'
  },
  {
    code: 'alipay',
    title: '支付宝',
    description: '预留正式收银台接入位。',
    enabled: true,
    ready: false,
    mode: 'placeholder'
  },
  {
    code: 'wechat',
    title: '微信支付',
    description: '预留 Native / JSAPI 接入位。',
    enabled: true,
    ready: false,
    mode: 'placeholder'
  }
]

const paymentChannels = computed(() => {
  const channels = props.billing?.payment_channels?.length ? props.billing.payment_channels : fallbackChannels
  return channels.filter((item) => item.enabled)
})

const selectedChannel = computed(() => paymentChannels.value.find((item) => item.code === selectedProvider.value))

onMounted(() => {
  void restoreBilling()
})

function syncSelectedProvider(billing: BillingSummaryResponse | null) {
  const channels = billing?.payment_channels?.filter((item) => item.enabled) || fallbackChannels
  const stillExists = channels.some((item) => item.code === selectedProvider.value)
  if (!stillExists) {
    selectedProvider.value = channels[0]?.code || 'mock_qr'
  }
}

async function submitAuth() {
  submitting.value = true
  try {
    const session =
      authMode.value === 'login'
        ? await loginAccount({ email: form.email, password: form.password })
        : await registerAccount({ email: form.email, password: form.password, displayName: form.displayName })
    const billing = await getBillingSummary()
    syncSelectedProvider(billing)
    emit('sessionChange', { user: billing.user, billing })
    ElMessage.success(authMode.value === 'login' ? '登录成功' : '注册成功，试用额度已到账')
    form.password = ''
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '账号操作失败')
  } finally {
    submitting.value = false
  }
}

async function restoreBilling() {
  try {
    const billing = await getBillingSummary()
    syncSelectedProvider(billing)
    emit('sessionChange', { user: billing.user, billing })
  } catch {
    emit('sessionChange', { user: null, billing: null })
  }
}

async function createOrder(packageCode: string) {
  creatingOrder.value = packageCode
  try {
    pendingOrder.value = await createBillingOrder({ packageCode, provider: selectedProvider.value })
    ElMessage.success(`订单已创建，可继续使用${pendingOrder.value.provider_label}支付`)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '创建订单失败')
  } finally {
    creatingOrder.value = ''
  }
}

async function resumeOrder(orderNo: string) {
  try {
    pendingOrder.value = await getBillingOrder(orderNo)
    ElMessage.success('已恢复待支付订单')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '恢复订单失败')
  }
}

async function payOrder(orderNo: string) {
  payingOrder.value = orderNo
  try {
    const payment = await mockPayBillingOrder(orderNo)
    const billing = await getBillingSummary()
    syncSelectedProvider(billing)
    emit('sessionChange', { user: billing.user, billing })
    pendingOrder.value = null
    ElMessage.success(payment.credited ? '支付成功，额度已到账' : '订单已支付，无需重复入账')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '支付失败')
  } finally {
    payingOrder.value = ''
  }
}

function openPaymentLink(url: string) {
  window.open(url, '_blank', 'noopener,noreferrer')
}

async function signOut() {
  try {
    await logoutAccount()
  } catch {
    // ignore client-side sign-out fallback
  } finally {
    emit('sessionChange', { user: null, billing: null })
    ElMessage.success('已退出登录')
  }
}

function formatDate(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function taskLabel(status: string, progress: number) {
  if (status === 'completed') return '已完成'
  if (status === 'failed') return '失败'
  return `${status === 'processing' ? '分析中' : '排队中'} ${progress}%`
}

function orderStatusLabel(status: string) {
  if (status === 'paid') return '已支付'
  if (status === 'pending') return '待支付'
  return status
}

function providerTitle(provider: string) {
  const normalizedProvider =
    provider === 'mock' || provider === 'mock_qr_callback' ? 'mock_qr' : provider
  return (
    paymentChannels.value.find((item) => item.code === normalizedProvider)?.title ||
    pendingOrder.value?.provider_label ||
    normalizedProvider
  )
}
</script>
