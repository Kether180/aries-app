<script setup lang="ts">
import { computed } from 'vue'

import { formatScore } from '@/format'
import type { Sentiment } from '@/types'

const props = defineProps<{ sentiment: Sentiment; score?: number }>()

// Small meter: the fill starts at the centre and extends towards the score's side
const meter = computed(() => {
  const s = props.score ?? 0
  const half = Math.abs(s) * 50
  return s >= 0 ? { left: '50%', width: `${half}%` } : { left: `${50 - half}%`, width: `${half}%` }
})
</script>

<template>
  <span
    class="badge"
    :class="sentiment"
    :title="score !== undefined ? `Score ${formatScore(score)} (from -1 to +1)` : undefined"
  >
    <span class="dot" aria-hidden="true" />
    <span class="label">{{ sentiment }}</span>
    <template v-if="score !== undefined">
      <span class="meter" aria-hidden="true"><span class="fill" :style="meter" /></span>
      <span class="score">{{ formatScore(score) }}</span>
    </template>
  </span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 26px;
  padding: 0 10px 0 8px;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
  text-transform: capitalize;
  color: var(--tone);
  background: var(--tone-soft);
  white-space: nowrap;
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--tone);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--tone) 22%, transparent);
}
.meter {
  position: relative;
  width: 36px;
  height: 4px;
  border-radius: 2px;
  background: color-mix(in srgb, var(--tone) 22%, transparent);
  overflow: hidden;
}
.meter::after {
  content: '';
  position: absolute;
  left: 50%;
  top: -1px;
  width: 1px;
  height: 6px;
  background: color-mix(in srgb, var(--tone) 45%, transparent);
}
.fill {
  position: absolute;
  top: 0;
  height: 100%;
  background: var(--tone);
  border-radius: 2px;
}
.score {
  font-variant-numeric: tabular-nums;
  font-weight: 500;
  text-transform: none;
}
.positive {
  --tone: var(--positive);
  --tone-soft: var(--positive-soft);
}
.neutral {
  --tone: var(--neutral);
  --tone-soft: var(--neutral-soft);
}
.negative {
  --tone: var(--negative);
  --tone-soft: var(--negative-soft);
}
</style>
