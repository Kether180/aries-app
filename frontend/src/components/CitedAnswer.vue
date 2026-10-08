<script setup lang="ts">
import { computed } from 'vue'

import SentimentBadge from '@/components/SentimentBadge.vue'
import type { Article } from '@/types'

const props = withDefaults(
  defineProps<{
    answer: string
    sources: Article[] // numbered [1]..[n] in the answer, in this order
    cited: number[]
    anchorPrefix?: string // keeps anchors unique when two answers are on one page
  }>(),
  { anchorPrefix: 'source' },
)

// Split "text [1] more [2][3]" into text and citation chips that link to the source list
const parts = computed(() =>
  props.answer
    .split(/(\[\d+\])/)
    .filter(Boolean)
    .map((part) => {
      const n = /^\[(\d+)\]$/.exec(part)
      return n ? { cite: Number(n[1]) } : { text: part }
    }),
)
</script>

<template>
  <div>
    <p class="answer">
      <template v-for="(part, i) in parts" :key="i">
        <a v-if="'cite' in part" :href="`#${anchorPrefix}-${part.cite}`" class="cite">{{ part.cite }}</a>
        <template v-else>{{ part.text }}</template>
      </template>
    </p>

    <ol v-if="sources.length" class="sources">
      <li
        v-for="(s, i) in sources"
        :id="`${anchorPrefix}-${i + 1}`"
        :key="s.id"
        :class="{ cited: cited.includes(i + 1) }"
      >
        <span class="num">{{ i + 1 }}</span>
        <div class="src-body">
          <a :href="s.url" target="_blank" rel="noopener noreferrer">{{ s.title }}</a>
          <span class="muted src-meta">{{ s.source_name }}</span>
        </div>
        <SentimentBadge :sentiment="s.sentiment" />
      </li>
    </ol>
  </div>
</template>

<style scoped>
.answer {
  margin: 0;
  font-size: 1.05rem;
  line-height: 1.65;
}
.cite {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 19px;
  height: 19px;
  margin: 0 2px;
  padding: 0 5px;
  border-radius: 6px;
  font-size: 0.72rem;
  font-weight: 700;
  text-decoration: none;
  vertical-align: 3px;
  color: var(--accent);
  background: var(--accent-soft);
  transition: background 0.15s ease;
}
.cite:hover {
  background: color-mix(in srgb, var(--accent) 24%, transparent);
}
.sources {
  margin: 14px 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.sources li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: var(--surface-2);
  opacity: 0.55;
  transition:
    opacity 0.15s ease,
    border-color 0.15s ease;
}
.sources li.cited {
  opacity: 1;
}
.sources li:hover {
  border-color: var(--border-strong);
}
.sources li:target {
  border-color: var(--accent);
  background: var(--accent-soft);
}
.num {
  flex: none;
  width: 22px;
  height: 22px;
  border-radius: 7px;
  font-size: 0.72rem;
  font-weight: 700;
  line-height: 22px;
  text-align: center;
  color: var(--accent-text);
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
}
.src-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.src-body a {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text);
  font-size: 0.92rem;
  font-weight: 500;
  text-decoration: none;
}
.src-body a:hover {
  color: var(--accent);
}
.src-meta {
  font-size: 0.76rem;
}
</style>
