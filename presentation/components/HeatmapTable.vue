<script setup>
const props = defineProps({ rows: Array, columns: Array, values: Object, digits: { type: Number, default: 2 } })
function value(row, col) { return Number(props.values?.[row]?.[col] ?? 0) }
function shade(v) { return `rgba(55, 211, 188, ${0.10 + Math.min(1, v) * 0.78})` }
function format(v) { return Number(v).toFixed(props.digits) }
</script>
<template>
  <table class="heatmap-table"><thead><tr><th></th><th v-for="column in columns" :key="column">{{ column }}</th></tr></thead>
  <tbody><tr v-for="row in rows" :key="row"><th>{{ row }}</th><td v-for="column in columns" :key="column" :style="{ background: shade(value(row, column)) }">{{ format(value(row, column)) }}</td></tr></tbody></table>
</template>
