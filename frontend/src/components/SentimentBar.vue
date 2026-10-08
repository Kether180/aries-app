<script setup lang="ts">
import { computed } from 'vue'

import type { Sentiment } from '@/types'

const props = defineProps<{
  positive: number
  neutral: number
  negative: number
  // When set, legend entries are buttons; the active one is highlighted and clicking it again clears
  selected?: Sentiment | null
  selectable?: boolean
}>()

const emit = defineEmits<{ select: [sentiment: Sentiment | null] }>()

const segments = computed(() => {
  const total = props.positive + props.neutral + props.negative
  return (['positive', 'neutral', 'negative'] as const).map((key) => ({
    key,
    count: props[key],
    percent: total ? (props[key] / total) * 100 : 0,
  }))
})

function toggle(key: Sentiment) {
  emit('select', props.selected === key ? null : key)
}
</script>

<template>
  <div class="sentiment-bar">
    <div class="track" role="img" :aria-label="segments.map((s) => `${s.count} ${s.key}`).join(', ')">
      <div
        v-for="s in segments"
        v-show="s.count"
        :key="s.key"
        class="segment"
        :class="[s.key, { dim: selected && selected !== s.key }]"
        :style="{ width: `${s.percent}%` }"
      />
    </div>
    <ul class="legend">
      <li v-for="s in segments" :key="s.key">
        <component
          :is="selectable ? 'button' : 'span'"
          class="entry"
          :class="{ active: selected === s.key, clickable: selectable }"
          :aria-pressed="selectable ? selected === s.key : undefined"
          :disabled="selectable && !s.count ? true : undefined"
          @click="selectable && toggle(s.key)"
        >
          <span class="dot" :class="s.key" />
          {{ s.count }} {{ s.key }}
          <span class="muted">({{ Math.round(s.percent) }}%)</span>
        </component>
      </li>
      <li v-if="selectable && selected">
        <button class="entry clickable clear" @click="emit('select', null)">Show all</button>
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
  transition:
    width 0.3s ease,
    opacity 0.2s ease;
}
.segment.dim {
  opacity: 0.25;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
  font-size: 0.85rem;
}
.entry {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: auto;
  padding: 2px 6px;
  margin: 0 -6px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--text);
  font: inherit;
  font-size: 0.85rem;
}
.entry.clickable {
  cursor: pointer;
}
.entry.clickable:hover:not(:disabled) {
  background: var(--surface-2);
}
.entry.active {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 10%, transparent);
}
.entry:disabled {
  opacity: 0.5;
  cursor: default;
}
.clear {
  color: var(--accent);
}
.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
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
