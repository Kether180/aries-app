<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { api } from '@/api'
import ArticleCard from '@/components/ArticleCard.vue'
import ResultsToolbar from '@/components/ResultsToolbar.vue'
import SearchBar from '@/components/SearchBar.vue'
import { COUNTRIES } from '@/constants'
import type { NewsSearchResult, Sentiment } from '@/types'

const query = ref('')
const country = ref('')
const activeQuery = ref<string | null>(null)
const results = ref<NewsSearchResult[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

// Per-article analysis state, keyed by URL
const analysing = reactive(new Set<string>())
const analyseErrors = reactive(new Map<string, string>())

const sentimentFilter = ref<Sentiment | null>(null)
const analysed = computed(() => results.value.filter((r) => r.analysis))
const pending = computed(() => results.value.filter((r) => !r.analysis))
const visible = computed(() =>
  sentimentFilter.value ? results.value.filter((r) => r.analysis?.sentiment === sentimentFilter.value) : results.value,
)
const breakdown = computed(() => {
  const counts = { positive: 0, neutral: 0, negative: 0 }
  for (const r of analysed.value) counts[r.analysis!.sentiment]++
  return counts
})

async function load() {
  loading.value = true
  error.value = null
  analyseErrors.clear()
  try {
    const res = await api.searchNews(query.value || undefined, country.value || undefined)
    // Every load starts fresh: saved analyses are not shown until the user asks. Analysing an article that
    // is already in the library returns the stored result instantly, without another model call.
    results.value = res.articles.map((a) => ({ ...a, analysis: null }))
    activeQuery.value = res.query
    sentimentFilter.value = null
  } catch (e) {
    error.value = (e as Error).message
    results.value = []
  } finally {
    loading.value = false
  }
}

// Every page load starts clean on top headlines; searches are not kept in the URL
onMounted(load)

function search(q: string, c: string) {
  query.value = q.trim()
  country.value = COUNTRIES.some(([code]) => code === c) ? c : ''
  load()
}

async function analyse(item: NewsSearchResult) {
  if (analysing.has(item.url)) return
  analysing.add(item.url)
  analyseErrors.delete(item.url)
  try {
    const { analysis: _, ...article } = item
    item.analysis = await api.analyzeArticle(article, activeQuery.value)
  } catch (e) {
    analyseErrors.set(item.url, (e as Error).message)
  } finally {
    analysing.delete(item.url)
  }
}

async function analyseAll() {
  // Small concurrency limit: fast, but polite to the OpenAI rate limit
  const queue = [...pending.value]
  const worker = async () => {
    for (let item = queue.shift(); item; item = queue.shift()) await analyse(item)
  }
  await Promise.all([worker(), worker(), worker()])
}
</script>

<template>
  <section class="hero">
    <h1>What's the <em>mood</em> of the news?</h1>
    <ul class="value-points">
      <li>
        <strong>Every article scored.</strong> A short summary, and whether it is good or bad news for those involved.
      </li>
      <li><strong>Every topic at a glance.</strong> See how coverage leans, worldwide or in one country.</li>
      <li>
        <strong>Answers with sources.</strong> Ask a question and get an answer built only from articles you can check.
      </li>
    </ul>
    <SearchBar :query="query" :country="country" :active-query="activeQuery" :loading="loading" @search="search" />
  </section>

  <ResultsToolbar
    v-if="!loading && results.length"
    v-model:filter="sentimentFilter"
    :active-query="activeQuery"
    :country="country"
    :total="results.length"
    :analysed-count="analysed.length"
    :pending-count="pending.length"
    :analysing-count="analysing.size"
    :breakdown="breakdown"
    @analyse-all="analyseAll"
  />

  <p v-if="error" class="error-box">{{ error }}</p>

  <div v-if="loading" class="list">
    <div v-for="n in 4" :key="n" class="skeleton" />
  </div>

  <p v-else-if="!error && !results.length" class="empty">No articles found. Try a broader search.</p>

  <p v-else-if="!visible.length" class="empty">No {{ sentimentFilter }} articles in these results.</p>

  <TransitionGroup v-else tag="div" name="fade" class="list">
    <ArticleCard
      v-for="item in visible"
      :key="item.url"
      :article="item"
      :analysis="item.analysis"
      :loading="analysing.has(item.url)"
      :error="analyseErrors.get(item.url)"
      @analyze="analyse(item)"
    />
  </TransitionGroup>
</template>

<style scoped>
.value-points {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 6px 20px;
  font-size: 0.93rem;
  color: var(--muted);
}
.value-points strong {
  color: var(--text);
  font-weight: 700;
}
</style>
