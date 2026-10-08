<script setup lang="ts">
import SentimentBadge from '@/components/SentimentBadge.vue'
import { timeAgo } from '@/format'
import type { Article, NewsArticle } from '@/types'

defineProps<{
  article: NewsArticle
  analysis: Article | null
  loading?: boolean
  error?: string | null
  deletable?: boolean
}>()

defineEmits<{ analyze: []; delete: [] }>()
</script>

<template>
  <article class="card" :class="{ analysed: analysis }">
    <img
      v-if="article.image_url"
      :src="article.image_url"
      alt=""
      class="thumb"
      loading="lazy"
      @error="($event.target as HTMLImageElement).hidden = true"
    />

    <div class="body">
      <p class="meta">
        <span class="source">{{ article.source_name }}</span>
        <span v-if="article.published_at"> · {{ timeAgo(article.published_at) }}</span>
        <span v-if="analysis?.query" class="muted"> · from “{{ analysis.query }}”</span>
      </p>

      <h3 class="title">
        <a :href="article.url" target="_blank" rel="noopener noreferrer">{{ article.title }}</a>
      </h3>

      <p v-if="!analysis" class="description">{{ article.description }}</p>

      <section v-if="analysis" class="analysis">
        <div class="analysis-head">
          <span class="label">AI summary</span>
          <SentimentBadge :sentiment="analysis.sentiment" :score="analysis.sentiment_score" />
        </div>
        <p class="summary">{{ analysis.summary }}</p>
        <p class="reason">{{ analysis.sentiment_reason }}</p>
      </section>

      <p v-if="error" class="error">{{ error }}</p>

      <div class="actions">
        <button v-if="!analysis" class="primary" :disabled="loading" @click="$emit('analyze')">
          <span v-if="loading" class="spinner" aria-hidden="true" />
          {{ loading ? 'Analysing…' : error ? 'Retry' : 'Summarise & score' }}
        </button>
        <a :href="article.url" target="_blank" rel="noopener noreferrer" class="button ghost">Read original ↗</a>
        <button v-if="deletable && analysis" class="ghost danger" @click="$emit('delete')">Delete</button>
      </div>
    </div>
  </article>
</template>

<style scoped>
.card {
  display: grid;
  grid-template-columns: 160px 1fr;
  gap: 16px;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
}
.card:not(:has(.thumb)) {
  grid-template-columns: 1fr;
}
.thumb {
  width: 160px;
  height: 110px;
  object-fit: cover;
  border-radius: 8px;
  background: var(--border);
}
.body {
  min-width: 0;
}
.meta {
  margin: 0 0 4px;
  font-size: 0.8rem;
  color: var(--muted);
}
.source {
  font-weight: 600;
  color: var(--text);
}
.title {
  margin: 0 0 6px;
  font-size: 1.05rem;
  line-height: 1.35;
}
.title a {
  color: inherit;
  text-decoration: none;
}
.title a:hover {
  text-decoration: underline;
}
.description {
  margin: 0;
  color: var(--muted);
  font-size: 0.92rem;
}
.analysis {
  margin-top: 8px;
  padding: 12px;
  border-radius: 8px;
  background: var(--surface-2);
}
.analysis-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}
.label {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
}
.summary {
  margin: 0 0 6px;
}
.reason {
  margin: 0;
  font-size: 0.85rem;
  color: var(--muted);
  font-style: italic;
}
.error {
  margin: 8px 0 0;
  color: var(--negative);
  font-size: 0.88rem;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
@media (max-width: 600px) {
  .card {
    grid-template-columns: 1fr;
  }
  .thumb {
    width: 100%;
    height: 160px;
  }
}
</style>
