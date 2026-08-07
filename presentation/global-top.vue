<script setup>
import { getCurrentInstance } from 'vue'
import data from './data/presentation-data.json'
const app = getCurrentInstance().appContext.app
const p = data.private
const f = p.final
const cp0 = p.checkpoints.find(x => x.checkpoint === 0) || p.checkpoints[0]
const cp20 = p.checkpoints.find(x => x.checkpoint === 20) || p.checkpoints.at(-1)
const agents = ['agent_0','agent_1','agent_2','agent_3']
const worlds = ['ALPHA','BETA','GAMMA','DELTA']
const pct = x => x == null ? '—' : `${(x * 100).toFixed(1)}%`
const num = x => x == null ? '—' : Number(x).toFixed(2)
const mins = x => x == null ? '—' : `${(x / 60).toFixed(1)} min`
const routing = f.routing_counts_by_world_agent || {}
Object.assign(app.config.globalProperties, { p, f, cp0, cp20, agents, worlds, pct, num, mins, routing })
</script>
<template><div style="display:none" /></template>
