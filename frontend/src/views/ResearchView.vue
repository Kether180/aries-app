<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'

import { ApiError, api } from '@/api'
import CitedAnswer from '@/components/CitedAnswer.vue'
import type { ResearchResponse, ResearchStep } from '@/types'

const EXAMPLES = [
  'How is Tesla doing this quarter?',
  'What happened in the UK economy this week?',
  'Is the news about AI regulation positive or negative?',
]

const TOOL_LABELS: Record<string, string> = {
  search_news: 'Searched the news',
  analyze_articles: 'Analysed articles',
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

function describe(step: ResearchStep): string {
  if (step.tool === 'search_news') return `“${step.input.query}”`
  if (step.tool === 'analyze_articles') return `${(step.input.urls as string[] | undefined)?.length ?? 0} article(s)`
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
          <details>
            <summary>
              <strong>{{ TOOL_LABELS[step.tool] ?? step.tool }}</strong>
              <span class="muted"> · {{ describe(step) }}</span>
            </summary>
            <pre>{{ step.output }}</pre>
          </details>
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
.hero {
  margin: 8px 0 24px;
}
h1 {
  margin: 0 0 6px;
  font-size: clamp(1.6rem, 4vw, 2.2rem);
  letter-spacing: -0.02em;
}
.search {
  display: flex;
  gap: 8px;
  margin-top: 16px;
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
  min-height: 30px;
  white-space: normal;
  text-align: left;
}
.panel {
  margin-bottom: 16px;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
}
.panel h2 {
  margin: 0 0 10px;
  font-size: 1.05rem;
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
.steps {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.steps li {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}
.steps li.pending {
  align-items: center;
}
.step-num {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  margin-top: 1px;
  border-radius: 50%;
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--muted);
  background: var(--surface-2);
}
.step-num.done {
  color: var(--positive);
  background: color-mix(in srgb, var(--positive) 14%, transparent);
}
.step-num .spinner {
  width: 12px;
  height: 12px;
  color: var(--accent);
}
details {
  flex: 1;
  min-width: 0;
}
summary {
  cursor: pointer;
}
pre {
  margin: 8px 0 0;
  padding: 10px;
  border-radius: 8px;
  background: var(--surface-2);
  font-size: 0.8rem;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
