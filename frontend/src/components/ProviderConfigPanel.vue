<template>
  <div class="feedback-card config-card">
    <div class="card-head">
      <p class="eyebrow">供应商配置中心</p>
      <h3>把自动抓取参数放进系统里，后续接更多源会更稳</h3>
    </div>

    <el-form label-position="top" class="feedback-form">
      <div class="field-grid">
        <el-form-item label="供应商">
          <el-select v-model="selectedProvider">
            <el-option
              v-for="item in editableConfigs"
              :key="item.provider"
              :label="providerLabel(item.provider)"
              :value="item.provider"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="当前状态">
          <div class="provider-state">
            <el-tag :type="selectedConfig?.configured ? 'success' : 'warning'">
              {{ selectedConfig?.configured ? '可自动抓取' : '待配置' }}
            </el-tag>
            <el-tag type="info">{{ sourceLabel(selectedConfig?.source) }}</el-tag>
          </div>
        </el-form-item>
      </div>

      <div class="field-grid">
        <el-form-item label="接入模式">
          <el-radio-group v-model="form.mode" class="config-mode-group">
            <el-radio-button label="http">HTTP</el-radio-button>
            <el-radio-button label="file">File</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="版本标识">
          <el-input v-model="form.version" placeholder="例如 wanfang-web-2026q2" />
        </el-form-item>
      </div>

      <div v-if="form.mode === 'http'" class="field-grid">
        <el-form-item label="请求方式">
          <el-select v-model="form.method">
            <el-option label="POST" value="POST" />
            <el-option label="GET" value="GET" />
            <el-option label="PUT" value="PUT" />
            <el-option label="PATCH" value="PATCH" />
          </el-select>
        </el-form-item>

        <el-form-item label="超时秒数">
          <el-input-number v-model="form.timeoutSeconds" :min="1" :max="300" :step="1" />
        </el-form-item>
      </div>

      <el-form-item v-if="form.mode === 'http'" label="请求地址">
        <el-input v-model="form.url" placeholder="https://your-provider-endpoint" />
      </el-form-item>

      <div v-if="form.mode === 'http'" class="field-grid">
        <el-form-item label="认证方式">
          <el-select v-model="form.authType" clearable placeholder="可选">
            <el-option label="Bearer" value="bearer" />
            <el-option label="Basic" value="basic" />
            <el-option label="Custom" value="custom" />
          </el-select>
        </el-form-item>

        <el-form-item label="Token 环境变量">
          <el-input v-model="form.tokenEnv" placeholder="例如 WANFANG_API_TOKEN" />
        </el-form-item>
      </div>

      <el-form-item v-else label="本地结果文件路径">
        <el-input v-model="form.path" placeholder="例如 C:\\data\\wanfang_result.json" />
      </el-form-item>

      <div class="inline-tips">
        <p>建议把真实密钥放在环境变量里，这里只填 `token_env`，避免把 token 直接写进页面配置。</p>
        <p>`field_map` 支持点路径，例如 `result.duplication_percent`、`meta.version`。</p>
      </div>

      <el-form-item label="请求头 JSON">
        <el-input
          v-model="form.headersText"
          type="textarea"
          :rows="3"
          class="config-textarea"
          placeholder='例如 {"X-App":"paper-risk"}'
        />
      </el-form-item>

      <el-form-item label="字段映射 JSON">
        <el-input
          v-model="form.fieldMapText"
          type="textarea"
          :rows="5"
          class="config-textarea"
          placeholder='例如 {"duplication_percent":"result.duplication_percent"}'
        />
      </el-form-item>

      <div v-if="selectedConfig?.validation_errors?.length" class="error-list">
        <el-tag v-for="error in selectedConfig.validation_errors" :key="error" type="danger" effect="plain">
          {{ error }}
        </el-tag>
      </div>

      <div class="config-actions">
        <el-button type="primary" :loading="saving" @click="saveConfig">
          保存供应商配置
        </el-button>
        <el-button :disabled="!selectedConfig?.updated_in_registry" :loading="resetting" @click="resetConfig">
          恢复默认配置
        </el-button>
      </div>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus/es/components/message/index'
import { resetProviderConfig, saveProviderConfig } from '../api'
import type { ProviderConfigDetail } from '../types'

const props = defineProps<{
  configs: ProviderConfigDetail[]
}>()

const emit = defineEmits<{
  changed: []
}>()

const editableConfigs = computed(() => props.configs.filter((item) => item.supports_auto_fetch))
const selectedProvider = ref('wanfang')
const saving = ref(false)
const resetting = ref(false)

const form = reactive({
  mode: 'http' as 'http' | 'file',
  method: 'POST',
  url: '',
  path: '',
  authType: 'bearer',
  tokenEnv: '',
  version: '',
  timeoutSeconds: 30,
  headersText: '{}',
  fieldMapText: JSON.stringify(defaultFieldMap(), null, 2)
})

const selectedConfig = computed(
  () => editableConfigs.value.find((item) => item.provider === selectedProvider.value) || editableConfigs.value[0] || null
)

watch(
  editableConfigs,
  (items) => {
    if (!items.length) return
    if (!items.some((item) => item.provider === selectedProvider.value)) {
      selectedProvider.value = items[0].provider
    }
  },
  { immediate: true }
)

watch(
  selectedConfig,
  (config) => {
    if (!config) return
    form.mode = config.mode || 'http'
    form.method = config.method || 'POST'
    form.url = config.url || ''
    form.path = config.path || ''
    form.authType = config.auth_type || 'bearer'
    form.tokenEnv = config.token_env || ''
    form.version = config.version || ''
    form.timeoutSeconds = Math.max(1, Math.round(config.timeout_seconds || 30))
    form.headersText = formatObjectText(config.headers || {})
    form.fieldMapText = formatObjectText(
      Object.keys(config.field_map || {}).length ? config.field_map : defaultFieldMap()
    )
  },
  { immediate: true }
)

async function saveConfig() {
  if (!selectedConfig.value) return
  saving.value = true
  try {
    const headers = parseStringMap(form.headersText, '请求头 JSON')
    const fieldMap = parseStringMap(form.fieldMapText, '字段映射 JSON')
    await saveProviderConfig(selectedConfig.value.provider, {
      mode: form.mode,
      method: form.method,
      url: form.url,
      path: form.path,
      authType: form.authType,
      tokenEnv: form.tokenEnv,
      version: form.version,
      timeoutSeconds: form.timeoutSeconds,
      headers,
      fieldMap
    })
    ElMessage.success(`${providerLabel(selectedConfig.value.provider)} 配置已保存`)
    emit('changed')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '保存配置失败')
  } finally {
    saving.value = false
  }
}

async function resetConfig() {
  if (!selectedConfig.value) return
  resetting.value = true
  try {
    await resetProviderConfig(selectedConfig.value.provider)
    ElMessage.success(`${providerLabel(selectedConfig.value.provider)} 已恢复默认配置`)
    emit('changed')
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '恢复默认配置失败')
  } finally {
    resetting.value = false
  }
}

function parseStringMap(text: string, label: string) {
  const trimmed = text.trim()
  if (!trimmed) return {}
  const parsed = JSON.parse(trimmed) as unknown
  if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
    throw new Error(`${label} 必须是 JSON 对象`)
  }
  return Object.fromEntries(
    Object.entries(parsed as Record<string, unknown>).map(([key, value]) => [String(key), String(value)])
  )
}

function formatObjectText(value: Record<string, string>) {
  return JSON.stringify(value || {}, null, 2)
}

function providerLabel(provider: string) {
  const labels: Record<string, string> = {
    wanfang: '万方',
    vip: '维普',
    turnitin: 'Turnitin'
  }
  return labels[provider] || provider
}

function sourceLabel(source?: ProviderConfigDetail['source']) {
  const labels: Record<string, string> = {
    default: '环境默认',
    override: '本地覆盖',
    merged: '默认 + 覆盖',
    none: '暂无来源'
  }
  return source ? labels[source] || source : '暂无来源'
}

function defaultFieldMap() {
  return {
    duplication_percent: 'result.duplication_percent',
    aigc_percent: 'result.aigc_percent',
    confidence: 'result.confidence',
    version: 'version'
  }
}
</script>
