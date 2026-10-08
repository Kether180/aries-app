<script setup lang="ts">
import { computed } from 'vue'

import SentimentBadge from '@/components/SentimentBadge.vue'
import type { ResearchStep, ResearchStepItem } from '@/types'

const props = defineProps<{
  steps: ResearchStep[] // grows live while the agent runs
  loading: boolean
  elapsed: number // seconds since the question was asked
}>()

const TOOL_LABELS: Record<string, string> = {
  search_news: 'Searched the news',
  analyze_articles: 'Read and scored',
}

const STATUS_LABELS: Record<ResearchStepItem['status'], string> = {
  found: 'found',
  already_analysed: 'already in library',
  analysed: 'analysed',
  skipped: 'skipped',
}

// Current activity, inferred from the last step that finished
const currentActivity = computed(() => {
  if (!props.loading) return ''
  const last = props.steps[props.steps.length - 1]
  if (!last) return 'Choosing what to search for'
  if (last.tool === 'search_news') return 'Picking the articles worth reading'
  return 'Writing the answer'
})

const plural = (count: number, word: string) => `${count} ${word}${count === 1 ? '' : 's'}`

function describe(step: ResearchStep): string {
  if (step.tool === 'search_news') return `“${step.input.query}”`
  if (step.tool === 'analyze_articles') return plural(step.items.length, 'article')
  return JSON.stringify(step.input)
}

// One readable sentence per step, so nobody needs the raw tool output
function summarize(step: ResearchStep): string {
  const n = step.items.length
  if (step.tool === 'search_news') {
    if (!n) return friendly(step.output)
    const known = step.items.filter((i) => i.status === 'already_analysed').length
    return `Found ${plural(n, 'article')}${known ? `, ${known} already in your library` : ''}.`
  }
  if (step.tool === 'analyze_articles') {
    const done = step.items.filter((i) => i.status === 'analysed').length
    const skipped = n - done
    const parts = [done ? `Summarised and scored ${plural(done, 'article')} and saved them to your library` : '']
    if (skipped) parts.push(`${plural(skipped, 'article')} skipped`)
    return parts.filter(Boolean).join('; ') + '.'
  }
  return friendly(step.output)
}

// Tool messages are written for the model; soften the ones a person may see
function friendly(output: string): string {
  if (output.startsWith('Search failed'))
    return 'The news search did not work this time, so the answer is based on what was already found.'
  if (output.startsWith('No articles found')) return 'No articles matched this search.'
  if (output.startsWith('Search budget'))
    return 'Reached the search limit for one question; the answer uses what was found so far.'
  return output
}
</script>

<template>
  <section class="panel" aria-live="polite">
    <div class="panel-head">
      <h2>{{ loading ? 'Finding and reading articles…' : 'Behind this answer' }}</h2>
      <span v-if="loading" class="muted elapsed">{{ elapsed }}s</span>
    </div>
    <ol class="steps">
      <TransitionGroup name="fade">
        <li v-for="(step, i) in steps" :key="i">
          <span class="step-num done">✓</span>
          <div class="step-body">
            <p class="step-title">
              <strong>{{ TOOL_LABELS[step.tool] ?? step.tool }}</strong>
              <span class="muted"> · {{ describe(step) }}</span>
            </p>
            <p class="step-summary muted">{{ summarize(step) }}</p>

            <ul v-if="step.items.length" class="items">
              <li v-for="item in step.items" :key="item.url" class="item">
                <span v-if="item.source_number" class="item-num">{{ item.source_number }}</span>
                <div class="item-body">
                  <a :href="item.url" target="_blank" rel="noopener noreferrer">{{ item.title }}</a>
                  <span class="muted item-meta">
                    {{ item.source_name || '' }}{{ item.source_name ? ' · ' : '' }}{{ STATUS_LABELS[item.status] }}
                    <template v-if="item.note"> ({{ item.note }})</template>
                  </span>
                </div>
                <SentimentBadge v-if="item.sentiment" :sentiment="item.sentiment" />
              </li>
            </ul>
          </div>
        </li>
      </TransitionGroup>
      <li v-if="loading" class="pending">
        <span class="step-num"><span class="spinner" aria-hidden="true" /></span>
        <span class="muted">{{ currentActivity }}…</span>
      </li>
    </ol>
  </section>
</template>

<style scoped>
h2 {
  margin: 0 0 12px;
  font-size: 1.05rem;
  font-weight: 700;
}
.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}
.elapsed {
  font-variant-numeric: tabular-nums;
  font-size: 0.85rem;
}
/* Timeline: a vertical line connects the step markers */
.steps {
  position: relative;
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.steps::before {
  content: '';
  position: absolute;
  left: 11px;
  top: 12px;
  bottom: 12px;
  width: 2px;
  background: var(--border);
}
.steps > li {
  position: relative;
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.steps > li.pending {
  align-items: center;
}
.step-num {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--muted);
  background: var(--surface-3);
  box-shadow: 0 0 0 3px var(--surface);
}
.step-num.done {
  color: #fff;
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
}
.step-num .spinner {
  width: 12px;
  height: 12px;
  color: var(--accent);
}
.step-body {
  flex: 1;
  min-width: 0;
}
.step-title {
  margin: 1px 0 8px;
}
.step-summary {
  margin: 0 0 8px;
  font-size: 0.9rem;
}
.items {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 10px;
  background: var(--surface-2);
}
.item-num {
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
.item-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.item-body a {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text);
  font-size: 0.92rem;
  font-weight: 500;
  text-decoration: none;
}
.item-body a:hover {
  color: var(--accent);
}
.item-meta {
  font-size: 0.76rem;
}
</style>
