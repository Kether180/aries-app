<script setup lang="ts">
import SentimentBar from '@/components/SentimentBar.vue'
import SentimentHelp from '@/components/SentimentHelp.vue'
import { SENTIMENT_FILTERS, countryName } from '@/constants'
import type { Sentiment } from '@/types'

defineProps<{
  activeQuery: string | null
  country: string
  total: number
  analysedCount: number
  pendingCount: number
  analysingCount: number
  breakdown: { positive: number; neutral: number; negative: number }
  filter: Sentiment | null
}>()

defineEmits<{ analyseAll: []; 'update:filter': [value: Sentiment | null] }>()
</script>

<template>
  <section class="toolbar">
    <div class="toolbar-head">
      <h2>
        {{ activeQuery ? `Results for “${activeQuery}”` : 'Top headlines'
        }}<span v-if="country" class="muted where"> · {{ countryName(country) }}</span>
        <span class="muted count" aria-live="polite">{{ analysedCount }}/{{ total }} analysed</span>
      </h2>
      <button v-if="pendingCount" class="primary" :disabled="analysingCount > 0" @click="$emit('analyseAll')">
        {{ analysingCount ? `Analysing ${analysingCount}…` : `Analyse all ${pendingCount}` }}
      </button>
    </div>

    <template v-if="analysedCount">
      <SentimentBar v-bind="breakdown" selectable :selected="filter" @select="$emit('update:filter', $event)" />
      <div class="toolbar-foot">
        <div class="segmented" role="group" aria-label="Show only">
          <button
            v-for="f in SENTIMENT_FILTERS"
            :key="f.label"
            :class="{ active: filter === f.value }"
            @click="$emit('update:filter', f.value)"
          >
            {{ f.label }}
          </button>
        </div>
        <p class="muted definition">Labels say whether each story is good or bad news for the people it is about.</p>
      </div>
      <SentimentHelp />
    </template>
    <p v-else class="muted hint">Analyse articles to see how coverage of this topic leans.</p>
  </section>
</template>

<style scoped>
.toolbar {
  position: relative;
  overflow: hidden;
  margin-bottom: 16px;
  padding: 16px 18px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  box-shadow: var(--shadow);
}
.toolbar::before {
  content: '';
  position: absolute;
  inset: 0 0 auto;
  height: 3px;
  background: linear-gradient(90deg, var(--accent), var(--accent-2));
}
.toolbar-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
h2 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
}
.where {
  font-weight: 500;
  font-size: 0.9rem;
}
.count {
  margin-left: 8px;
  font-size: 0.85rem;
  font-weight: 500;
}
.toolbar-foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px 16px;
  margin-top: 12px;
}
.definition {
  margin: 0;
  font-size: 0.85rem;
}
.hint {
  margin: 0;
  font-size: 0.9rem;
}
</style>
