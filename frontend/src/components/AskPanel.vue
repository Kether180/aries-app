<script setup lang="ts">
import { ref } from 'vue'

import { api } from '@/api'
import CitedAnswer from '@/components/CitedAnswer.vue'
import type { AskResponse } from '@/types'

const EXAMPLES = [
  'What is the overall mood of the news?',
  'What are the main stories about the economy?',
  'Is there any good news?',
]

const question = ref('')
const result = ref<AskResponse | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

async function ask(q: string) {
  const trimmed = q.trim()
  if (trimmed.length < 3 || loading.value) return
  question.value = trimmed
  loading.value = true
  error.value = null
  try {
    result.value = await api.ask(trimmed)
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="ask">
    <div class="ask-head">
      <h2>Ask your library</h2>
      <p class="muted">Answers come only from the articles you've analysed, with sources cited.</p>
    </div>

    <form class="search" @submit.prevent="ask(question)">
      <input
        v-model="question"
        type="search"
        placeholder="e.g. What's the news saying about interest rates?"
        aria-label="Question"
      />
      <button class="primary" type="submit" :disabled="loading || question.trim().length < 3">
        <span v-if="loading" class="spinner" aria-hidden="true" />
        {{ loading ? 'Thinking…' : 'Ask' }}
      </button>
    </form>

    <div v-if="!result" class="chips">
      <button v-for="ex in EXAMPLES" :key="ex" class="chip" :disabled="loading" @click="ask(ex)">{{ ex }}</button>
    </div>

    <p v-if="error" class="error-box">{{ error }}</p>

    <div v-if="result" class="result">
      <CitedAnswer :answer="result.answer" :sources="result.sources" :cited="result.cited" anchor-prefix="ask-source" />
      <p v-if="result.retrieval === 'recent'" class="muted note">
        No saved articles matched this question directly, so the answer is based on your most recent ones.
      </p>
    </div>
  </section>
</template>

<style scoped>
.ask {
  margin-bottom: 24px;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
}
.ask-head h2 {
  margin: 0 0 2px;
  font-size: 1.05rem;
}
.ask-head p {
  margin: 0 0 12px;
  font-size: 0.9rem;
}
.search {
  display: flex;
  gap: 8px;
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
.result {
  margin-top: 16px;
}
.note {
  margin: 8px 0 0;
  font-size: 0.85rem;
}
</style>
