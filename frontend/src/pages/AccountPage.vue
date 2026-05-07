<template>
  <div class="account-page">
    <div class="page-header">
      <h1>账户</h1>
      <p>管理你的账户信息和额度</p>
    </div>

    <div class="account-grid">
      <!-- 用户信息卡 -->
      <section class="card">
        <h2>基本信息</h2>
        <div class="info-list">
          <div class="info-item">
            <span class="info-label">昵称</span>
            <span>{{ auth.user?.display_name || '未设置' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">邮箱</span>
            <span>{{ auth.user?.email }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">注册时间</span>
            <span>{{ formatDate(auth.user?.created_at) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">状态</span>
            <span class="status-badge">{{ auth.user?.status || '正常' }}</span>
          </div>
        </div>
      </section>

      <!-- 额度卡 -->
      <section class="card">
        <h2>额度</h2>
        <div class="credits-display">
          <strong>{{ auth.credits }}</strong>
          <span>次分析额度</span>
        </div>
        <p class="card-hint">每次分析消耗 1 次额度</p>
      </section>
    </div>

    <!-- 充值区 -->
    <section class="card" v-if="auth.billing">
      <h2>充值</h2>
      <p class="card-hint">选择套餐进行充值</p>

      <!-- 支付通道 -->
      <div class="channel-row" v-if="auth.billing.payment_channels.length">
        <span class="channel-label">支付方式：</span>
        <div class="channel-options">
          <button
            v-for="ch in auth.billing.payment_channels"
            :key="ch.code"
            type="button"
            class="channel-btn"
            :class="{ active: selectedChannel === ch.code, muted: !ch.ready }"
            @click="selectedChannel = ch.code"
          >
            <strong>{{ ch.title }}</strong>
            <small>{{ ch.ready ? '可用' : '即将接入' }}</small>
          </button>
        </div>
      </div>

      <div class="package-grid">
        <article v-for="pkg in auth.billing.packages" :key="pkg.code" class="package-card">
          <h3>{{ pkg.title }}</h3>
          <p class="package-desc">{{ pkg.description }}</p>
          <div class="package-price">
            <strong>&yen;{{ (pkg.amount_cents / 100).toFixed(2) }}</strong>
            <span>/ {{ pkg.credits }} 次</span>
          </div>
          <button
            class="btn btn-primary btn-full"
            :disabled="creatingOrder === pkg.code"
            @click="createOrder(pkg.code)"
          >
            {{ creatingOrder === pkg.code ? '创建中...' : '购买' }}
          </button>
        </article>
      </div>

      <!-- 待支付订单 -->
      <div v-if="pendingOrder" class="pending-section">
        <h3>待支付订单</h3>
        <div class="pending-card">
          <div class="pending-info">
            <span>单号：{{ pendingOrder.order.order_no }}</span>
            <span>&yen;{{ (pendingOrder.order.amount_cents / 100).toFixed(2) }}</span>
          </div>
          <p class="card-hint" v-if="pendingOrder.pay_hint">{{ pendingOrder.pay_hint }}</p>
          <button
            v-if="pendingOrder.mock_pay_supported"
            class="btn btn-primary"
            :disabled="paying"
            @click="payOrder"
          >{{ paying ? '支付中...' : '模拟支付' }}</button>
          <a
            v-else-if="pendingOrder.payment_url"
            :href="pendingOrder.payment_url"
            target="_blank"
            class="btn btn-primary"
          >前往支付</a>
        </div>
      </div>
    </section>

    <!-- 最近订单 -->
    <section class="card" v-if="auth.billing?.recent_orders.length">
      <h2>最近订单</h2>
      <div class="order-list">
        <div v-for="order in auth.billing.recent_orders" :key="order.id" class="order-row">
          <span class="order-no">{{ order.order_no }}</span>
          <span>{{ order.package_code }}</span>
          <span>&yen;{{ (order.amount_cents / 100).toFixed(2) }}</span>
          <span class="order-status" :class="order.status">{{ statusLabel(order.status) }}</span>
          <span class="order-time">{{ formatDate(order.created_at) }}</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { createBillingOrder, getBillingOrder, mockPayBillingOrder } from '../api'
import type { BillingOrderDetailResponse } from '../types'

const auth = useAuthStore()
const selectedChannel = ref<string>('mock_qr')
const creatingOrder = ref('')
const pendingOrder = ref<BillingOrderDetailResponse | null>(null)
const paying = ref(false)

function formatDate(iso: string | undefined) {
  if (!iso) return '-'
  return new Date(iso).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

function statusLabel(status: string) {
  const map: Record<string, string> = { pending: '待支付', paid: '已支付', completed: '已完成', cancelled: '已取消' }
  return map[status] || status
}

async function createOrder(packageCode: string) {
  creatingOrder.value = packageCode
  try {
    const detail = await createBillingOrder({ packageCode, provider: selectedChannel.value as 'mock_qr' | 'alipay' | 'wechat' })
    pendingOrder.value = detail
  } catch (err) {
    alert(err instanceof Error ? err.message : '创建订单失败')
  } finally {
    creatingOrder.value = ''
  }
}

async function payOrder() {
  if (!pendingOrder.value) return
  paying.value = true
  try {
    await mockPayBillingOrder(pendingOrder.value.order.order_no)
    pendingOrder.value = null
    await auth.refreshBilling()
  } catch (err) {
    alert(err instanceof Error ? err.message : '支付失败')
  } finally {
    paying.value = false
  }
}
</script>

<style scoped>
.account-page {
  max-width: 860px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 28px;
}

.page-header h1 {
  font-size: 28px;
  color: #172033;
  margin: 0 0 6px;
}

.page-header p {
  color: #53606f;
  font-size: 15px;
  margin: 0;
}

.account-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}

.card {
  padding: 24px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(31, 54, 73, 0.06);
  box-shadow: 0 4px 16px rgba(29, 45, 61, 0.04);
  margin-bottom: 16px;
}

.card h2 {
  font-size: 18px;
  color: #172033;
  margin: 0 0 16px;
}

.card h3 {
  font-size: 16px;
  color: #172033;
  margin: 0 0 8px;
}

.card-hint {
  color: #8b95a2;
  font-size: 13px;
  margin: 4px 0 16px;
}

.info-list {
  display: grid;
  gap: 12px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid rgba(31, 54, 73, 0.04);
  font-size: 14px;
  color: #344150;
}

.info-label {
  color: #8b95a2;
  font-size: 13px;
}

.status-badge {
  padding: 2px 10px;
  border-radius: 6px;
  background: rgba(47, 125, 103, 0.1);
  color: #2f7d67;
  font-size: 13px;
  font-weight: 600;
}

.credits-display {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 6px;
}

.credits-display strong {
  font-size: 48px;
  color: #2f7d67;
  line-height: 1;
}

.credits-display span {
  font-size: 16px;
  color: #53606f;
}

.channel-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}

.channel-label {
  font-size: 13px;
  color: #53606f;
  font-weight: 600;
}

.channel-options {
  display: flex;
  gap: 8px;
}

.channel-btn {
  padding: 8px 16px;
  border: 1.5px solid rgba(31, 54, 73, 0.12);
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s;
  display: grid;
  gap: 2px;
}

.channel-btn strong {
  font-size: 14px;
  color: #344150;
}

.channel-btn small {
  font-size: 11px;
  color: #8b95a2;
}

.channel-btn.active {
  border-color: #2f7d67;
  background: rgba(47, 125, 103, 0.04);
}

.channel-btn.muted {
  opacity: 0.6;
}

.package-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 14px;
}

.package-card {
  padding: 20px;
  border-radius: 14px;
  border: 1px solid rgba(31, 54, 73, 0.06);
  background: #f9fbfa;
}

.package-desc {
  font-size: 13px;
  color: #53606f;
  margin: 0 0 12px;
  line-height: 1.5;
}

.package-price {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 14px;
}

.package-price strong {
  font-size: 24px;
  color: #172033;
}

.package-price span {
  font-size: 13px;
  color: #8b95a2;
}

.pending-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid rgba(31, 54, 73, 0.06);
}

.pending-card {
  padding: 16px;
  border-radius: 12px;
  background: #fffbf0;
  border: 1px solid rgba(212, 154, 75, 0.2);
}

.pending-info {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: #344150;
  margin-bottom: 10px;
}

.order-list {
  display: grid;
  gap: 6px;
}

.order-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(31, 54, 73, 0.04);
  font-size: 13px;
  color: #344150;
}

.order-no {
  font-family: "JetBrains Mono", monospace;
  color: #8b95a2;
  font-size: 12px;
}

.order-status {
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.order-status.paid,
.order-status.completed {
  background: rgba(47, 125, 103, 0.1);
  color: #2f7d67;
}

.order-status.pending {
  background: rgba(212, 154, 75, 0.15);
  color: #a1720d;
}

.order-time {
  color: #8b95a2;
  margin-left: auto;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10px 22px;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  text-decoration: none;
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
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-full {
  width: 100%;
}

@media (max-width: 640px) {
  .account-grid {
    grid-template-columns: 1fr;
  }

  .package-grid {
    grid-template-columns: 1fr;
  }
}
</style>
