<template>
  <el-dialog
    v-model="visible"
    :title="currentPackage?.title || '解锁服务'"
    width="520px"
    destroy-on-close
    :close-on-click-modal="false"
    class="unlock-modal"
  >
    <div v-if="!order" class="unlock-intro">
      <p class="unlock-desc">{{ currentPackage?.description }}</p>
      <div class="unlock-price">
        <span class="price-label">应付金额</span>
        <span class="price-num">¥{{ currentPackage?.amount_yuan }}</span>
      </div>
      <el-button type="primary" size="large" class="btn-generate" @click="handleCreateOrder">
        生成订单并付款
      </el-button>
    </div>

    <div v-else class="unlock-payment">
      <div class="order-info">
        <div class="order-row">
          <span class="order-label">订单号</span>
          <span class="order-no">{{ order.order_no }}</span>
          <el-button link type="primary" size="small" @click="copyOrderNo">
            <el-icon><CopyDocument /></el-icon> 复制
          </el-button>
        </div>
        <div class="order-row">
          <span class="order-label">套餐</span>
          <span>{{ currentPackage?.title }}</span>
        </div>
        <div class="order-row">
          <span class="order-label">金额</span>
          <span class="price-num-small">¥{{ currentPackage?.amount_yuan }}</span>
        </div>
        <div class="order-row">
          <span class="order-label">状态</span>
          <el-tag :type="statusTagType">{{ statusLabel }}</el-tag>
        </div>
      </div>

      <el-divider />

      <!-- 付款码区域 -->
      <div v-if="order.status === 'pending_payment'" class="qr-section">
        <div class="qr-main">
          <p class="qr-title">
            <el-icon><Money /></el-icon>
            支付宝商家收款码（推荐）
          </p>
          <div class="qr-frame">
            <img
              src="/pay/alipay-merchant.png"
              alt="支付宝收款码"
              class="qr-img"
              @error="onQrError"
            />
            <div v-if="qrError" class="qr-placeholder">
              <p>支付宝商家收款码</p>
              <p class="qr-hint">请管理员放置 /pay/alipay-merchant.png</p>
            </div>
          </div>
          <p class="qr-hint">
            请使用支付宝扫描上方二维码付款，并在备注中填写订单号：<strong>{{ order.order_no }}</strong>
          </p>
        </div>

        <el-divider>或</el-divider>

        <div class="qr-backup">
          <p class="qr-title">
            <el-icon><ChatDotRound /></el-icon>
            微信备用付款
          </p>
          <div class="qr-frame small">
            <img
              src="/pay/wechat-backup.png"
              alt="微信收款码"
              class="qr-img"
              @error="onWechatQrError"
            />
            <div v-if="wechatQrError" class="qr-placeholder">
              <p>微信个人收款码</p>
              <p class="qr-hint">请管理员放置 /pay/wechat-backup.png</p>
            </div>
          </div>
          <p class="qr-hint warn">
            微信付款后需上传截图，由人工确认到账。支付宝商家码可实时到账（推荐）。
          </p>
        </div>
      </div>

      <!-- 截图上传区域 -->
      <div v-if="order.status === 'pending_payment' || order.status === 'rejected'" class="upload-section">
        <p class="upload-label">上传付款截图</p>
        <el-upload
          class="upload-screenshot"
          action="#"
          :auto-upload="false"
          :on-change="handleFileChange"
          :show-file-list="true"
          :limit="1"
          accept="image/*"
        >
          <el-button type="default">
            <el-icon><Picture /></el-icon> 选择截图
          </el-button>
          <template #tip>
            <div class="upload-tip">支持 PNG、JPG 格式，单张不超过 5MB</div>
          </template>
        </el-upload>

        <el-radio-group v-model="selectedPaymentMethod" class="payment-method">
          <el-radio label="alipay">支付宝</el-radio>
          <el-radio label="wechat">微信</el-radio>
        </el-radio-group>

        <el-button
          type="primary"
          size="large"
          class="btn-submit"
          :loading="submitting"
          :disabled="!screenshotFile"
          @click="handleSubmitScreenshot"
        >
          我已付款，提交审核
        </el-button>
      </div>

      <!-- 等待审核 -->
      <div v-if="order.status === 'pending_review'" class="review-waiting">
        <el-result icon="info" title="付款截图已提交">
          <template #sub-title>
            <p>管理员正在核对付款信息，预计 10 分钟内完成审核。</p>
            <p>请勿重复提交，如有问题请联系客服。</p>
          </template>
        </el-result>
        <div v-if="order.screenshot_url" class="screenshot-preview">
          <p>已上传截图：</p>
          <img :src="order.screenshot_url" alt="付款截图" class="screenshot-img" />
        </div>
      </div>

      <!-- 已解锁 -->
      <div v-if="order.status === 'unlocked'" class="unlocked-success">
        <el-result icon="success" title="解锁成功">
          <template #sub-title>
            <p>该服务已解锁，您可以正常使用全部功能。</p>
          </template>
        </el-result>
      </div>

      <!-- 免责声明 -->
      <el-alert
        type="warning"
        :closable="false"
        class="disclaimer"
      >
        <template #title>
          <el-icon><Warning /></el-icon> 免责声明
        </template>
        本工具用于辅助识别和优化论文 AIGC 疑似表达风险，修改效果以学校或检测平台复检结果为准，不承诺保证通过任何检测。
      </el-alert>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument, Money, ChatDotRound, Picture, Warning } from '@element-plus/icons-vue'
import type { UnlockOrder, UnlockPackage } from '../types'
import { createUnlockOrder, uploadUnlockScreenshot } from '../api'

const props = defineProps<{
  modelValue: boolean
  runId: string
  packageCode: string
  packages: UnlockPackage[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'unlocked', order: UnlockOrder): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const currentPackage = computed(() =>
  props.packages.find((p) => p.code === props.packageCode)
)

const order = ref<UnlockOrder | null>(null)
const screenshotFile = ref<File | null>(null)
const selectedPaymentMethod = ref<'alipay' | 'wechat'>('alipay')
const submitting = ref(false)
const qrError = ref(false)
const wechatQrError = ref(false)

const statusLabel = computed(() => {
  const map: Record<string, string> = {
    pending_payment: '待付款',
    pending_review: '待审核',
    unlocked: '已解锁',
    rejected: '已驳回',
  }
  return map[order.value?.status || ''] || order.value?.status || ''
})

const statusTagType = computed(() => {
  const map: Record<string, 'primary' | 'success' | 'warning' | 'danger' | undefined> = {
    pending_payment: 'warning',
    pending_review: 'primary',
    unlocked: 'success',
    rejected: 'danger',
  }
  return map[order.value?.status || '']
})

watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      order.value = null
      screenshotFile.value = null
      selectedPaymentMethod.value = 'alipay'
      qrError.value = false
      wechatQrError.value = false
    }
  }
)

async function handleCreateOrder() {
  if (!props.packageCode || !props.runId) return
  try {
    const o = await createUnlockOrder(props.runId, props.packageCode)
    order.value = o
  } catch (err: any) {
    ElMessage.error(err.message || '创建订单失败')
  }
}

function handleFileChange(file: any) {
  screenshotFile.value = file.raw as File
}

async function handleSubmitScreenshot() {
  if (!order.value || !screenshotFile.value) return
  submitting.value = true
  try {
    const updated = await uploadUnlockScreenshot(
      props.runId,
      order.value.order_no,
      screenshotFile.value,
      selectedPaymentMethod.value
    )
    order.value = updated
    ElMessage.success('截图已提交，请等待审核')
  } catch (err: any) {
    ElMessage.error(err.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

function copyOrderNo() {
  if (!order.value) return
  navigator.clipboard.writeText(order.value.order_no)
    .then(() => ElMessage.success('订单号已复制'))
    .catch(() => ElMessage.error('复制失败'))
}

function onQrError() {
  qrError.value = true
}

function onWechatQrError() {
  wechatQrError.value = true
}
</script>

<style scoped>
.unlock-modal :deep(.el-dialog__body) {
  padding-top: 8px;
}

.unlock-intro {
  text-align: center;
  padding: 12px 0;
}

.unlock-desc {
  color: #666;
  margin-bottom: 20px;
}

.unlock-price {
  margin-bottom: 24px;
}

.price-label {
  color: #999;
  font-size: 14px;
  margin-right: 8px;
}

.price-num {
  color: #e53935;
  font-size: 32px;
  font-weight: 700;
}

.price-num-small {
  color: #e53935;
  font-weight: 600;
}

.btn-generate {
  width: 100%;
}

.order-info {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
}

.order-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.order-row:last-child {
  margin-bottom: 0;
}

.order-label {
  color: #999;
  font-size: 13px;
  width: 56px;
  flex-shrink: 0;
}

.order-no {
  font-family: monospace;
  font-weight: 600;
  color: #333;
}

.qr-section {
  margin-top: 8px;
}

.qr-main {
  text-align: center;
}

.qr-backup {
  text-align: center;
}

.qr-title {
  font-weight: 600;
  color: #333;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.qr-frame {
  width: 220px;
  height: 220px;
  margin: 0 auto 12px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fafafa;
}

.qr-frame.small {
  width: 160px;
  height: 160px;
}

.qr-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.qr-placeholder {
  text-align: center;
  color: #999;
  font-size: 13px;
}

.qr-hint {
  font-size: 12px;
  color: #888;
  line-height: 1.6;
}

.qr-hint.warn {
  color: #e6a23c;
}

.upload-section {
  margin-top: 16px;
}

.upload-label {
  font-weight: 600;
  margin-bottom: 8px;
  color: #333;
}

.upload-screenshot {
  margin-bottom: 12px;
}

.upload-tip {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.payment-method {
  margin-bottom: 16px;
}

.btn-submit {
  width: 100%;
}

.review-waiting {
  margin-top: 8px;
}

.screenshot-preview {
  text-align: center;
}

.screenshot-img {
  max-width: 100%;
  max-height: 300px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
}

.unlocked-success {
  margin-top: 8px;
}

.disclaimer {
  margin-top: 16px;
}
</style>
