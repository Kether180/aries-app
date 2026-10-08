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
  font-size: 1.02rem;
  line-height: 1.6;
}
.cite {
  display: inline-block;
  min-width: 18px;
  margin: 0 1px;
  padding: 0 4px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  line-height: 18px;
  text-align: center;
  text-decoration: none;
  vertical-align: 2px;
  color: var(--accent);
  background: color-mix(in srgb, var(--accent) 14%, transparent);
}
.sources {
  margin: 12px 0 0;
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
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--surface-2);
  opacity: 0.6;
}
.sources li.cited {
  opacity: 1;
}
.num {
  flex: none;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  font-size: 0.75rem;
  font-weight: 700;
  line-height: 22px;
  text-align: center;
  color: var(--accent);
  background: color-mix(in srgb, var(--accent) 14%, transparent);
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
  text-decoration: none;
}
.src-body a:hover {
  text-decoration: underline;
}
.src-meta {
  font-size: 0.78rem;
}
</style>
