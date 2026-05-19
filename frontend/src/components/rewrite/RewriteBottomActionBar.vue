<template>
  <footer class="rewrite-bottom-action-bar">
    <div class="meta">
      <span>文档格式保护模式</span>
      <span>风险高亮仅用于页面交互</span>
      <span>替换记录可用于导出改写稿</span>
    </div>
    <div class="actions">
      <button type="button" @click="$emit('reanalyze')">重新检测</button>
      <button type="button" @click="$emit('download-report')">下载报告</button>
      <button class="primary" type="button" :disabled="exportLoading" @click="$emit('export-document')">
        导出文档
      </button>
    </div>
  </footer>
</template>

<script setup lang="ts">
defineProps<{
  exportLoading: boolean
}>()

defineEmits<{
  (e: 'reanalyze'): void
  (e: 'download-report'): void
  (e: 'export-document'): void
}>()
</script>

<style scoped>
.rewrite-bottom-action-bar {
  min-height: 66px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 12px 24px;
  background: #fbfcf8;
  border-top: 1px solid #e5e7eb;
}

.meta,
.actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.meta span {
  color: #64748b;
  font-size: 13px;
  font-weight: 650;
}

.actions button {
  min-height: 40px;
  padding: 0 15px;
  border: 1px solid #d1d5db;
  border-radius: 12px;
  background: #fff;
  color: #1f2937;
  font-size: 14px;
  font-weight: 850;
  cursor: pointer;
}

.actions button.primary {
  border-color: #0f8f4f;
  background: #0f8f4f;
  color: #fff;
}

.actions button:disabled {
  opacity: 0.48;
  cursor: not-allowed;
}

@media (max-width: 900px) {
  .rewrite-bottom-action-bar {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
