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
      >
        <span v-if="s.percent >= 12" class="pct">{{ Math.round(s.percent) }}%</span>
      </div>
    </div>
    <ul class="legend">
      <li v-for="s in segments" :key="s.key">
        <component
          :is="selectable ? 'button' : 'span'"
          class="entry"
          :class="[s.key, { active: selected === s.key, clickable: selectable }]"
          :aria-pressed="selectable ? selected === s.key : undefined"
          :disabled="selectable && !s.count ? true : undefined"
          @click="selectable && toggle(s.key)"
        >
          <span class="dot" />
          <strong>{{ s.count }}</strong> {{ s.key }}
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
  height: 14px;
  border-radius: 999px;
  overflow: hidden;
  background: var(--surface-3);
  gap: 2px;
}
.segment {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
  transition:
    width 0.35s cubic-bezier(0.2, 0.8, 0.2, 1),
    opacity 0.2s ease;
}
.segment.dim {
  opacity: 0.25;
}
.pct {
  font-size: 0.62rem;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.02em;
  text-shadow: 0 1px 1px rgb(0 0 0 / 0.25);
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 8px;
  margin: 10px 0 0;
  padding: 0;
  list-style: none;
  font-size: 0.84rem;
}
.entry {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 10px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: var(--surface-2);
  color: var(--text);
  font: inherit;
  font-size: 0.84rem;
  font-weight: 500;
  box-shadow: none;
}
.entry strong {
  font-weight: 700;
}
.entry.clickable {
  cursor: pointer;
}
.entry.clickable:hover:not(:disabled) {
  background: var(--surface-3);
}
.entry.active {
  border-color: var(--tone);
  background: var(--tone-soft);
  color: var(--tone);
}
.entry:disabled {
  opacity: 0.45;
  cursor: default;
}
.clear {
  color: var(--accent);
  background: var(--accent-soft);
}
.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--tone);
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
.segment.positive {
  background: var(--positive);
}
.segment.neutral {
  background: var(--neutral);
}
.segment.negative {
  background: var(--negative);
}
</style>
