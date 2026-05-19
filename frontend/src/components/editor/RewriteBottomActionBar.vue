<template>
  <footer class="rewrite-bottom-bar">
    <div class="rewrite-bottom-bar__meta">
      <span>兼容模式工作区</span>
      <span>原文格式优先保留</span>
      <span>改写后可继续导出与复检</span>
    </div>

    <div class="rewrite-bottom-bar__actions">
      <button type="button" class="bottom-btn" @click="$emit('download-original')">下载原文档</button>
      <button type="button" class="bottom-btn" @click="$emit('download-report')">查看报告</button>
      <button
        type="button"
        class="bottom-btn bottom-btn--primary"
        :disabled="exportLoading"
        @click="$emit('export')"
      >
        导出修改后文档
      </button>
    </div>
  </footer>
</template>

<script setup lang="ts">
defineProps<{
  exportLoading: boolean
}>()

defineEmits<{
  (e: 'download-original'): void
  (e: 'download-report'): void
  (e: 'export'): void
}>()
</script>

<style scoped>
.rewrite-bottom-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 14px 24px 20px;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(249, 250, 245, 0.96);
}

.rewrite-bottom-bar__meta {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  color: #6b7280;
  font-size: 13px;
}

.rewrite-bottom-bar__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.bottom-btn {
  min-height: 42px;
  padding: 0 16px;
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: #ffffff;
  color: #1f2937;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.bottom-btn--primary {
  background: #0f8f4f;
  border-color: #0f8f4f;
  color: #ffffff;
}

.bottom-btn:disabled {
  opacity: 0.48;
  cursor: not-allowed;
}

@media (max-width: 900px) {
  .rewrite-bottom-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .rewrite-bottom-bar__actions {
    width: 100%;
  }

  .bottom-btn {
    flex: 1;
  }
}
</style>
