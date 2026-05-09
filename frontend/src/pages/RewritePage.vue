<template>
  <div class="rewrite-page">
    <PataFixEditor :run-id="runId" />
  </div>
</template>

<script setup lang="ts">
import PataFixEditor from '../components/editor/PataFixEditor.vue'

defineProps<{
  runId: string
}>()
</script>

<style scoped>
.rewrite-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #FAF9F6;
}
</style>
