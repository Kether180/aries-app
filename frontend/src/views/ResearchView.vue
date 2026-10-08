<script setup lang="ts">
import { ref } from 'vue'

import { api } from '@/api'
import CitedAnswer from '@/components/CitedAnswer.vue'
import type { ResearchResponse } from '@/types'

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
const loading = ref(false)
const error = ref<string | null>(null)

async function research(q: string) {
  const trimmed = q.trim()
  if (trimmed.length < 3 || loading.value) return
  question.value = trimmed
  loading.value = true
  error.value = null
  result.value = null
  try {
    result.value = await api.research(trimmed)
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
}

function describe(step: ResearchResponse['steps'][number]): string {
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

    <div v-if="!result && !loading" class="chips">
      <button v-for="ex in EXAMPLES" :key="ex" class="chip" @click="research(ex)">{{ ex }}</button>
    </div>
  </section>

  <p v-if="loading" class="muted working">
    Searching the news and analysing articles. This usually takes 10–20 seconds.
  </p>

  <p v-if="error" class="error-box">{{ error }}</p>

  <template v-if="result">
    <section class="panel">
      <h2>Answer</h2>
      <CitedAnswer
        :answer="result.answer"
        :sources="result.sources"
        :cited="result.cited"
        anchor-prefix="research-source"
      />
    </section>

    <section class="panel">
      <h2>What the agent did</h2>
      <ol class="steps">
        <li v-for="(step, i) in result.steps" :key="i">
          <span class="step-num">{{ i + 1 }}</span>
          <details>
            <summary>
              <strong>{{ TOOL_LABELS[step.tool] ?? step.tool }}</strong>
              <span class="muted"> · {{ describe(step) }}</span>
            </summary>
            <pre>{{ step.output }}</pre>
          </details>
        </li>
      </ol>
    </section>
  </template>
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
.working {
  margin: 0 0 16px;
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
.step-num {
  flex: none;
  width: 22px;
  height: 22px;
  margin-top: 1px;
  border-radius: 50%;
  font-size: 0.75rem;
  font-weight: 700;
  line-height: 22px;
  text-align: center;
  color: var(--muted);
  background: var(--surface-2);
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
