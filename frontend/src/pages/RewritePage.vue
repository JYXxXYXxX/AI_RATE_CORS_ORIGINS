<template>
  <div class="rewrite-page">
    <OnlyOfficeRewriteWorkspace v-if="useOnlyOffice" :run-id="runId" />
    <RewriteWorkspacePage v-else :run-id="runId" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import OnlyOfficeRewriteWorkspace from '../components/editor/OnlyOfficeRewriteWorkspace.vue'
import RewriteWorkspacePage from './RewriteWorkspacePage.vue'

defineProps<{
  runId: string
}>()

const route = useRoute()
const useOnlyOffice = computed(() => route.query.onlyoffice === '1')
</script>

<style scoped>
.rewrite-page {
  min-height: 100vh;
  height: 100vh;
  background: #f4f5ef;
  overflow: hidden;
}
</style>
