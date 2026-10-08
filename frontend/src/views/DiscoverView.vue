<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '@/api'
import ArticleCard from '@/components/ArticleCard.vue'
import SentimentBar from '@/components/SentimentBar.vue'
import type { NewsSearchResult } from '@/types'

const TOPICS = ['Artificial intelligence', 'Climate', 'Stock market', 'Elections', 'Space', 'Health']

const route = useRoute()
const router = useRouter()

const input = ref('')
const activeQuery = ref<string | null>(null)
const results = ref<NewsSearchResult[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

// Per-article analysis state, keyed by URL
const analysing = reactive(new Set<string>())
const analyseErrors = reactive(new Map<string, string>())

const analysed = computed(() => results.value.filter((r) => r.analysis))
const pending = computed(() => results.value.filter((r) => !r.analysis))
const breakdown = computed(() => {
  const counts = { positive: 0, neutral: 0, negative: 0 }
  for (const r of analysed.value) counts[r.analysis!.sentiment]++
  return counts
})

async function load(q: string | null) {
  loading.value = true
  error.value = null
  analyseErrors.clear()
  try {
    const res = await api.searchNews(q ?? undefined)
    results.value = res.articles
    activeQuery.value = res.query
  } catch (e) {
    error.value = (e as Error).message
    results.value = []
  } finally {
    loading.value = false
  }
}

// The URL (?q=...) is the source of truth, so searches are linkable and back/forward works
watch(
  () => route.query.q,
  (q) => {
    const value = typeof q === 'string' ? q : ''
    input.value = value
    load(value || null)
  },
  { immediate: true },
)

function search(q: string) {
  router.push({ query: q.trim() ? { q: q.trim() } : {} })
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
    <h1>What's the mood of the news?</h1>
    <p class="muted">
      Search recent articles, get an AI summary and sentiment score, and see how coverage of a topic leans.
    </p>

    <form class="search" role="search" @submit.prevent="search(input)">
      <input v-model="input" type="search" placeholder="Search a topic, company or person…" aria-label="Search news" />
      <button class="primary" type="submit" :disabled="loading">Search</button>
    </form>

    <div class="chips">
      <button
        v-for="topic in TOPICS"
        :key="topic"
        class="chip"
        :class="{ active: activeQuery?.toLowerCase() === topic.toLowerCase() }"
        @click="search(topic)"
      >
        {{ topic }}
      </button>
      <button v-if="activeQuery" class="chip" @click="search('')">✕ Top headlines</button>
    </div>
  </section>

  <section v-if="!loading && results.length" class="toolbar">
    <div class="toolbar-head">
      <h2>
        {{ activeQuery ? `Results for “${activeQuery}”` : 'Top headlines' }}
        <span class="muted count">{{ analysed.length }}/{{ results.length }} analysed</span>
      </h2>
      <button v-if="pending.length" class="primary" :disabled="analysing.size > 0" @click="analyseAll">
        {{ analysing.size ? `Analysing ${analysing.size}…` : `Analyse all ${pending.length}` }}
      </button>
    </div>
    <SentimentBar v-if="analysed.length" v-bind="breakdown" />
    <p v-else class="muted hint">Analyse articles to see how coverage of this topic leans.</p>
  </section>

  <p v-if="error" class="error-box">{{ error }}</p>

  <div v-if="loading" class="list">
    <div v-for="n in 4" :key="n" class="skeleton" />
  </div>

  <p v-else-if="!error && !results.length" class="empty">No articles found. Try a broader search.</p>

  <div v-else class="list">
    <ArticleCard
      v-for="item in results"
      :key="item.url"
      :article="item"
      :analysis="item.analysis"
      :loading="analysing.has(item.url)"
      :error="analyseErrors.get(item.url)"
      @analyze="analyse(item)"
    />
  </div>
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
.toolbar {
  margin-bottom: 16px;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
}
.toolbar-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.toolbar h2 {
  margin: 0;
  font-size: 1.05rem;
}
.count {
  margin-left: 8px;
  font-size: 0.85rem;
  font-weight: 400;
}
.hint {
  margin: 0;
  font-size: 0.9rem;
}
</style>
