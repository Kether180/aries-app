<script setup lang="ts">
import { onUnmounted, ref } from 'vue'

import { ApiError, api } from '@/api'
import CitedAnswer from '@/components/CitedAnswer.vue'
import ResearchSteps from '@/components/ResearchSteps.vue'
import { RESEARCH_EXAMPLES } from '@/constants'
import type { ResearchResponse, ResearchStep } from '@/types'

const question = ref('')
const result = ref<ResearchResponse | null>(null)
const steps = ref<ResearchStep[]>([]) // filled live while the agent runs
const loading = ref(false)
const error = ref<string | null>(null)
const elapsed = ref(0)
let timer: ReturnType<typeof setInterval> | undefined

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
</script>

<template>
  <section class="hero">
    <h1>Research a question</h1>
    <p class="muted">
      Ask anything about what is in the news. We search, read the relevant articles and answer with sources you can
      check. Every article we read is saved to your <RouterLink to="/library">Library</RouterLink>.
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
      <button v-for="ex in RESEARCH_EXAMPLES" :key="ex" class="chip" @click="research(ex)">{{ ex }}</button>
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

  <ResearchSteps v-if="steps.length || loading" :steps="steps" :loading="loading" :elapsed="elapsed" />
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
</style>
