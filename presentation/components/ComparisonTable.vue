<script setup>
defineProps({ rows: Array })
</script>
<template>
  <table class="comparison-table"><thead><tr><th>Observable</th><th>t = 0</th><th>t = 20</th><th>Reading</th></tr></thead>
  <tbody><tr v-for="row in rows" :key="row.label"><th>{{ row.label }}</th><td>{{ row.start }}</td><td>{{ row.end }}</td><td>{{ row.reading }}</td></tr></tbody></table>
</template>
