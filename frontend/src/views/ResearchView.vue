<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'

import { ApiError, api } from '@/api'
import CitedAnswer from '@/components/CitedAnswer.vue'
import SentimentBadge from '@/components/SentimentBadge.vue'
import type { ResearchResponse, ResearchStep, ResearchStepItem } from '@/types'

const EXAMPLES = [
  'How is Tesla doing this quarter?',
  'What happened in the UK economy this week?',
  'Is the news about AI regulation positive or negative?',
]

const TOOL_LABELS: Record<string, string> = {
  search_news: 'Searched the news',
  analyze_articles: 'Analysed articles',
}

const STATUS_LABELS: Record<ResearchStepItem['status'], string> = {
  found: 'found',
  already_analysed: 'already in library',
  analysed: 'analysed',
  skipped: 'skipped',
}

const question = ref('')
const result = ref<ResearchResponse | null>(null)
const steps = ref<ResearchStep[]>([]) // filled live while the agent runs
const loading = ref(false)
const error = ref<string | null>(null)
const elapsed = ref(0)
let timer: ReturnType<typeof setInterval> | undefined

// What the agent is doing right now, inferred from the last step it finished
const currentActivity = computed(() => {
  if (!loading.value) return ''
  const last = steps.value[steps.value.length - 1]
  if (!last) return 'Deciding what to search'
  if (last.tool === 'search_news') return 'Reading the results and picking articles to analyse'
  return 'Writing the answer, or analysing more articles'
})

async function research(q: string) {
  const trimmed = q.trim()
  if (trimmed.length < 3 || loading.value) return
  question.value = trimmed
  loading.value = true
  error.value = null
  result.value = null
  steps.value = []
  elapsed.value = 0
  timer = setInterval(() => elapsed.value++, 1000)
  try {
    result.value = await api.researchStream(trimmed, (step) => steps.value.push(step))
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : 'Connection lost while researching. Please try again.'
  } finally {
    loading.value = false
    clearInterval(timer)
  }
}

onUnmounted(() => clearInterval(timer))

// One readable sentence per step, so nobody needs the raw tool output
function summarize(step: ResearchStep): string {
  const n = step.items.length
  const plural = (count: number, word: string) => `${count} ${word}${count === 1 ? '' : 's'}`
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
    return 'The news search did not work this time, so the agent continued with what it already had.'
  if (output.startsWith('No articles found')) return 'No articles matched this search.'
  if (output.startsWith('Search budget'))
    return 'The agent reached its search limit for this question and answered with what it had found.'
  return output
}

function describe(step: ResearchStep): string {
  if (step.tool === 'search_news') return `“${step.input.query}”`
  if (step.tool === 'analyze_articles') return `${step.items.length} article${step.items.length === 1 ? '' : 's'}`
  return JSON.stringify(step.input)
}
</script>

<template>
  <section class="hero">
    <h1>Research a question</h1>
    <p class="muted">
      An agent searches the news, analyses the relevant articles and answers with citations. Everything it analyses is
      saved to your <RouterLink to="/library">Library</RouterLink>.
    </p>

    <form class="search" @submit.prevent="research(question)">
      <input
        v-model="question"
        type="search"
        placeholder="Ask about anything in the news…"
        aria-label="Research question"
      />
      <button class="primary" type="submit" :disabled="loading || question.trim().length < 3">
        <span v-if="loading" class="spinner" aria-hidden="true" />
        {{ loading ? 'Researching…' : 'Research' }}
      </button>
    </form>

    <div v-if="!result && !loading && !steps.length" class="chips">
      <button v-for="ex in EXAMPLES" :key="ex" class="chip" @click="research(ex)">{{ ex }}</button>
    </div>
  </section>

  <p v-if="error" class="error-box">{{ error }}</p>

  <Transition name="fade">
    <section v-if="result" class="panel">
      <h2>Answer</h2>
      <CitedAnswer
        :answer="result.answer"
        :sources="result.sources"
        :cited="result.cited"
        anchor-prefix="research-source"
      />
    </section>
  </Transition>

  <section v-if="steps.length || loading" class="panel" aria-live="polite">
    <div class="panel-head">
      <h2>{{ loading ? 'What the agent is doing' : 'What the agent did' }}</h2>
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
.search {
  display: flex;
  gap: 8px;
  margin-top: 18px;
}
.search input {
  flex: 1;
  min-width: 0;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
.chip {
  height: auto;
  min-height: 32px;
  white-space: normal;
  text-align: left;
}
.panel h2 {
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
