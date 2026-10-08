<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { api } from '@/api'
import ArticleCard from '@/components/ArticleCard.vue'
import SentimentBar from '@/components/SentimentBar.vue'
import SentimentHelp from '@/components/SentimentHelp.vue'
import type { NewsSearchResult, Sentiment } from '@/types'

const TOPICS = ['Artificial intelligence', 'Climate', 'Stock market', 'Elections', 'Space', 'Health']

// GNews country codes; '' means worldwide
const COUNTRIES = [
  ['', 'Worldwide'],
  ['us', 'United States'],
  ['gb', 'United Kingdom'],
  ['de', 'Germany'],
  ['fr', 'France'],
  ['es', 'Spain'],
  ['it', 'Italy'],
  ['nl', 'Netherlands'],
  ['in', 'India'],
  ['br', 'Brazil'],
  ['au', 'Australia'],
  ['ca', 'Canada'],
] as const

const FILTERS: { label: string; value: Sentiment | null }[] = [
  { label: 'All', value: null },
  { label: 'Positive', value: 'positive' },
  { label: 'Neutral', value: 'neutral' },
  { label: 'Negative', value: 'negative' },
]

const route = useRoute()
const router = useRouter()

const input = ref('')
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
const visible = computed(() =>
  sentimentFilter.value ? results.value.filter((r) => r.analysis?.sentiment === sentimentFilter.value) : results.value,
)
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
    const res = await api.searchNews(q ?? undefined, country.value || undefined)
    results.value = res.articles
    activeQuery.value = res.query
    sentimentFilter.value = null
  } catch (e) {
    error.value = (e as Error).message
    results.value = []
  } finally {
    loading.value = false
  }
}

// The URL (?q=...&country=..) is the source of truth, so searches are linkable and back/forward works
watch(
  () => [route.query.q, route.query.country],
  ([q, c]) => {
    const value = typeof q === 'string' ? q : ''
    input.value = value
    country.value = typeof c === 'string' && COUNTRIES.some(([code]) => code === c) ? c : ''
    load(value || null)
  },
  { immediate: true },
)

function search(q: string, c: string = country.value) {
  router.push({ query: { ...(q.trim() ? { q: q.trim() } : {}), ...(c ? { country: c } : {}) } })
}

function changeCountry(event: Event) {
  search(input.value, (event.target as HTMLSelectElement).value)
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

    <form class="search" role="search" @submit.prevent="search(input)">
      <input v-model="input" type="search" placeholder="Search a topic, company or person…" aria-label="Search news" />
      <select :value="country" aria-label="Country" class="country" @change="changeCountry">
        <option v-for="[code, name] in COUNTRIES" :key="code" :value="code">{{ name }}</option>
      </select>
      <button class="primary" type="submit" :disabled="loading">Search</button>
    </form>
    <p v-if="country" class="muted country-hint">
      Showing the {{ COUNTRIES.find(([c]) => c === country)?.[1] }} press in its own language, summarised in English.
    </p>

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
        {{ activeQuery ? `Results for “${activeQuery}”` : 'Top headlines'
        }}<span v-if="country" class="muted where"> · {{ COUNTRIES.find(([c]) => c === country)?.[1] }}</span>
        <span class="muted count" aria-live="polite">{{ analysed.length }}/{{ results.length }} analysed</span>
      </h2>
      <button v-if="pending.length" class="primary" :disabled="analysing.size > 0" @click="analyseAll">
        {{ analysing.size ? `Analysing ${analysing.size}…` : `Analyse all ${pending.length}` }}
      </button>
    </div>
    <SentimentBar
      v-if="analysed.length"
      v-bind="breakdown"
      selectable
      :selected="sentimentFilter"
      @select="sentimentFilter = $event"
    />
    <div v-if="analysed.length" class="toolbar-foot">
      <div class="segmented" role="group" aria-label="Show only">
        <button
          v-for="f in FILTERS"
          :key="f.label"
          :class="{ active: sentimentFilter === f.value }"
          @click="sentimentFilter = f.value"
        >
          {{ f.label }}
        </button>
      </div>
      <p class="muted definition">Labels say whether each story is good or bad news for the people it is about.</p>
    </div>
    <SentimentHelp v-if="analysed.length" />
    <p v-else class="muted hint">Analyse articles to see how coverage of this topic leans.</p>
  </section>

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
.search {
  display: flex;
  gap: 8px;
  margin-top: 18px;
}
.search input {
  flex: 1;
  min-width: 0;
}
.country {
  height: 44px;
  max-width: 180px;
  padding: 0 32px 0 12px;
  border: 1px solid var(--border-strong);
  border-radius: 12px;
  background: var(--surface);
  color: var(--text);
  font: inherit;
  font-size: 0.92rem;
  box-shadow: var(--shadow);
  appearance: none;
  background-image:
    linear-gradient(45deg, transparent 50%, var(--muted) 50%),
    linear-gradient(135deg, var(--muted) 50%, transparent 50%);
  background-position:
    calc(100% - 18px) 19px,
    calc(100% - 13px) 19px;
  background-size:
    5px 5px,
    5px 5px;
  background-repeat: no-repeat;
}
.country:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 18%, transparent);
}
.country-hint {
  margin: 8px 0 0;
  font-size: 0.85rem;
}
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
.where {
  font-weight: 500;
  font-size: 0.9rem;
}
.toolbar-foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px 16px;
  margin-top: 12px;
}
.definition {
  margin: 0;
  font-size: 0.85rem;
}
@media (max-width: 600px) {
  .search {
    flex-wrap: wrap;
  }
  .search input {
    flex-basis: 100%;
  }
  .country {
    flex: 1;
    max-width: none;
  }
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
.toolbar {
  position: relative;
  overflow: hidden;
  margin-bottom: 16px;
  padding: 16px 18px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  box-shadow: var(--shadow);
}
.toolbar::before {
  content: '';
  position: absolute;
  inset: 0 0 auto;
  height: 3px;
  background: linear-gradient(90deg, var(--accent), var(--accent-2));
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
  font-weight: 700;
}
.count {
  margin-left: 8px;
  font-size: 0.85rem;
  font-weight: 500;
}
.hint {
  margin: 0;
  font-size: 0.9rem;
}
</style>
