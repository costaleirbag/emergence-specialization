<script setup>
defineProps({ label: String, value: [String, Number], detail: String, accent: { type: String, default: 'teal' } })
</script>
<template>
  <div class="metric-card" :class="`accent-${accent}`">
    <div class="metric-label">{{ label }}</div><div class="metric-value">{{ value }}</div>
    <div v-if="detail" class="metric-detail">{{ detail }}</div>
  </div>
</template>
