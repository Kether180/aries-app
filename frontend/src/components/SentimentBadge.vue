<script setup lang="ts">
import { formatScore } from '@/format'
import type { Sentiment } from '@/types'

defineProps<{ sentiment: Sentiment; score?: number }>()
</script>

<template>
  <span class="badge" :class="sentiment">
    {{ sentiment }}
    <span v-if="score !== undefined" class="score">{{ formatScore(score) }}</span>
  </span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: capitalize;
  color: var(--tone);
  background: color-mix(in srgb, var(--tone) 14%, transparent);
}
.score {
  font-variant-numeric: tabular-nums;
  font-weight: 500;
  opacity: 0.85;
}
.positive {
  --tone: var(--positive);
}
.neutral {
  --tone: var(--neutral);
}
.negative {
  --tone: var(--negative);
}
</style>
