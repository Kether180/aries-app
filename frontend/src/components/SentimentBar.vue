<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ positive: number; neutral: number; negative: number }>()

const segments = computed(() => {
  const total = props.positive + props.neutral + props.negative
  return (['positive', 'neutral', 'negative'] as const).map((key) => ({
    key,
    count: props[key],
    percent: total ? (props[key] / total) * 100 : 0,
  }))
})
</script>

<template>
  <div class="sentiment-bar">
    <div class="track" role="img" :aria-label="segments.map((s) => `${s.count} ${s.key}`).join(', ')">
      <div
        v-for="s in segments"
        v-show="s.count"
        :key="s.key"
        class="segment"
        :class="s.key"
        :style="{ width: `${s.percent}%` }"
      />
    </div>
    <ul class="legend">
      <li v-for="s in segments" :key="s.key">
        <span class="dot" :class="s.key" />
        {{ s.count }} {{ s.key }}
        <span class="muted">({{ Math.round(s.percent) }}%)</span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.track {
  display: flex;
  height: 10px;
  border-radius: 999px;
  overflow: hidden;
  background: var(--border);
  gap: 2px;
}
.segment {
  transition: width 0.3s ease;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
  font-size: 0.85rem;
}
.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 4px;
}
.positive {
  background: var(--positive);
}
.neutral {
  background: var(--neutral);
}
.negative {
  background: var(--negative);
}
</style>
