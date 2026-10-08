<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { api } from '@/api'
import { formatScore } from '@/format'
import type { TopicStats } from '@/types'

const emit = defineEmits<{ select: [topic: string] }>()

const topics = ref<TopicStats[]>([])

onMounted(async () => {
  topics.value = await api.getTopicStats().catch(() => [])
})

function pct(t: TopicStats, key: 'positive' | 'neutral' | 'negative') {
  return t.total ? (t[key] / t.total) * 100 : 0
}

function mood(t: TopicStats): string {
  const s = t.average_score ?? 0
  if (s >= 0.3) return 'mostly good news'
  if (s <= -0.3) return 'mostly bad news'
  if (t.negative > t.positive) return 'leans negative'
  if (t.positive > t.negative) return 'leans positive'
  return 'mixed'
}
</script>

<template>
  <section v-if="topics.length > 1" class="panel topics">
    <div class="head">
      <h2>Mood by topic</h2>
      <p class="muted">How the coverage you have analysed leans, topic by topic. Click one to see its articles.</p>
    </div>
    <ul>
      <li v-for="t in topics" :key="t.topic">
        <button
          class="topic"
          :title="`Average score ${formatScore(t.average_score ?? 0)}`"
          @click="emit('select', t.topic)"
        >
          <span class="name">{{ t.topic }}</span>
          <span class="bar" aria-hidden="true">
            <span class="seg positive" :style="{ width: `${pct(t, 'positive')}%` }" />
            <span class="seg neutral" :style="{ width: `${pct(t, 'neutral')}%` }" />
            <span class="seg negative" :style="{ width: `${pct(t, 'negative')}%` }" />
          </span>
          <span class="muted verdict">{{ mood(t) }} · {{ t.total }} article{{ t.total === 1 ? '' : 's' }}</span>
        </button>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.topics {
  margin-bottom: 24px;
}
.head h2 {
  margin: 0 0 2px;
  font-size: 1.05rem;
  font-weight: 700;
}
.head p {
  margin: 0 0 12px;
  font-size: 0.9rem;
}
ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 10px;
}
.topic {
  display: grid;
  grid-template-columns: 1fr;
  gap: 6px;
  width: 100%;
  height: auto;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface-2);
  text-align: left;
  white-space: normal;
  box-shadow: none;
}
.topic:hover {
  border-color: var(--accent);
  background: var(--surface-2);
}
.name {
  font-weight: 700;
  text-transform: capitalize;
}
.bar {
  display: flex;
  height: 8px;
  gap: 2px;
  border-radius: 999px;
  overflow: hidden;
  background: var(--surface-3);
}
.seg.positive {
  background: var(--positive);
}
.seg.neutral {
  background: var(--neutral);
}
.seg.negative {
  background: var(--negative);
}
.verdict {
  font-size: 0.8rem;
  font-weight: 500;
}
</style>
