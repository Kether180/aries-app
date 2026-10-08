<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import { api } from '@/api'
import ArticleCard from '@/components/ArticleCard.vue'
import AskPanel from '@/components/AskPanel.vue'
import SentimentBar from '@/components/SentimentBar.vue'
import { formatScore } from '@/format'
import type { Article, Sentiment, SentimentStats } from '@/types'

const PAGE_SIZE = 20
const FILTERS: { label: string; value: Sentiment | null }[] = [
  { label: 'All', value: null },
  { label: 'Positive', value: 'positive' },
  { label: 'Neutral', value: 'neutral' },
  { label: 'Negative', value: 'negative' },
]

const items = ref<Article[]>([])
const total = ref(0)
const stats = ref<SentimentStats | null>(null)
const sentiment = ref<Sentiment | null>(null)
const q = ref('')
const loading = ref(false)
const error = ref<string | null>(null)

async function load(append = false) {
  loading.value = true
  error.value = null
  try {
    const res = await api.listArticles({
      sentiment: sentiment.value,
      q: q.value.trim(),
      limit: PAGE_SIZE,
      offset: append ? items.value.length : 0,
    })
    items.value = append ? [...items.value, ...res.items] : res.items
    total.value = res.total
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  stats.value = await api.getStats().catch(() => null)
}

async function remove(article: Article) {
  if (!confirm(`Delete the analysis of “${article.title}”?`)) return
  try {
    await api.deleteArticle(article.id)
    items.value = items.value.filter((a) => a.id !== article.id)
    total.value--
    loadStats()
  } catch (e) {
    error.value = (e as Error).message
  }
}

let debounce: ReturnType<typeof setTimeout>
watch(sentiment, () => load())
watch(q, () => {
  clearTimeout(debounce)
  debounce = setTimeout(() => load(), 300)
})

onMounted(() => {
  load()
  loadStats()
})
</script>

<template>
  <section class="overview">
    <div>
      <h1>Library</h1>
      <p class="muted">Every article you've analysed, newest first.</p>
    </div>
    <div v-if="stats && stats.total" class="stats">
      <div class="numbers">
        <div>
          <strong>{{ stats.total }}</strong
          ><span class="muted">articles</span>
        </div>
        <div v-if="stats.average_score !== null">
          <strong>{{ formatScore(stats.average_score) }}</strong
          ><span class="muted">avg. score</span>
        </div>
      </div>
      <SentimentBar
        :positive="stats.positive"
        :neutral="stats.neutral"
        :negative="stats.negative"
        selectable
        :selected="sentiment"
        @select="sentiment = $event"
      />
    </div>
  </section>

  <AskPanel v-if="stats && stats.total" />

  <div class="filters">
    <div class="segmented" role="group" aria-label="Filter by sentiment">
      <button
        v-for="f in FILTERS"
        :key="f.label"
        :class="{ active: sentiment === f.value }"
        @click="sentiment = f.value"
      >
        {{ f.label }}
      </button>
    </div>
    <input v-model="q" type="search" placeholder="Filter by title, summary or topic…" aria-label="Filter library" />
  </div>

  <p v-if="error" class="error-box">{{ error }}</p>

  <div v-if="loading && !items.length" class="list">
    <div v-for="n in 3" :key="n" class="skeleton" />
  </div>

  <div v-else-if="!items.length" class="empty">
    <p v-if="sentiment || q">Nothing matches these filters.</p>
    <p v-else>Nothing here yet. <RouterLink to="/">Find some news</RouterLink> and analyse it.</p>
  </div>

  <template v-else>
    <p class="muted results-count">{{ total }} {{ total === 1 ? 'article' : 'articles' }}</p>
    <div class="list">
      <ArticleCard v-for="a in items" :key="a.id" :article="a" :analysis="a" deletable @delete="remove(a)" />
    </div>
    <div v-if="items.length < total" class="more">
      <button :disabled="loading" @click="load(true)">{{ loading ? 'Loading…' : 'Load more' }}</button>
    </div>
  </template>
</template>

<style scoped>
.overview {
  display: grid;
  grid-template-columns: 1fr minmax(280px, 400px);
  gap: 24px;
  align-items: end;
  margin: 4px 0 24px;
}
.overview h1 {
  margin: 0 0 6px;
  font-size: clamp(1.75rem, 4vw, 2.4rem);
  font-weight: 800;
  letter-spacing: -0.03em;
}
.stats {
  position: relative;
  overflow: hidden;
  padding: 16px 18px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  box-shadow: var(--shadow);
}
.stats::before {
  content: '';
  position: absolute;
  inset: 0 0 auto;
  height: 3px;
  background: linear-gradient(90deg, var(--accent), var(--accent-2));
}
.numbers {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}
.numbers > div {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--surface-2);
}
.numbers strong {
  font-size: 1.5rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}
.numbers span {
  font-size: 0.76rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}
.filters input {
  flex: 1;
  min-width: 200px;
}
.results-count {
  margin: 0 0 10px;
  font-size: 0.85rem;
}
.more {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}
@media (max-width: 700px) {
  .overview {
    grid-template-columns: 1fr;
  }
}
</style>
