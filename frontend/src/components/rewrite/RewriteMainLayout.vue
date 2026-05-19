<template>
  <main class="rewrite-main-layout">
    <slot />
  </main>
</template>

<style scoped>
.rewrite-main-layout {
  min-height: 0;
  height: 0;
  flex: 1 1 0;
  display: grid;
  grid-template-columns: 260px minmax(560px, 1fr) 420px;
  gap: 18px;
  padding: 18px 22px;
  background: #f7f8f4;
  overflow: hidden;
}

@media (max-width: 1280px) {
  .rewrite-main-layout {
    grid-template-columns: 240px minmax(460px, 1fr) 360px;
  }
}

@media (max-width: 1020px) {
  .rewrite-main-layout {
    overflow: auto;
    grid-template-columns: 1fr;
    min-height: 760px;
  }
}
</style>
