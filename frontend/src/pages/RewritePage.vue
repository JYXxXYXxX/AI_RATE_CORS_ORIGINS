<template>
  <div class="rewrite-page">
    <PataFixEditor v-if="useFallback" :run-id="runId" />
    <OnlyOfficeRewriteWorkspace v-else :run-id="runId" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import OnlyOfficeRewriteWorkspace from '../components/editor/OnlyOfficeRewriteWorkspace.vue'
import PataFixEditor from '../components/editor/PataFixEditor.vue'

defineProps<{
  runId: string
}>()

const route = useRoute()
const useFallback = computed(() => route.query.fallback === '1')
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
