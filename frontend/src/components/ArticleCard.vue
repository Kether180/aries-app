<script setup lang="ts">
import { computed, ref } from 'vue'

import SentimentBadge from '@/components/SentimentBadge.vue'
import { timeAgo } from '@/format'
import type { Article, NewsArticle } from '@/types'

const props = defineProps<{
  article: NewsArticle
  analysis: Article | null
  loading?: boolean
  error?: string | null
  deletable?: boolean
}>()

defineEmits<{ analyze: []; delete: [] }>()

// Some news sites block hotlinking; when the image fails we drop it so the card uses the full width
const imageFailed = ref(false)
const faviconFailed = ref(false)

// Publisher icon for the placeholder tile, via Google's favicon service (works for any domain)
const faviconUrl = computed(() => {
  if (faviconFailed.value) return null
  try {
    const host = new URL(props.article.source_url || props.article.url).hostname
    return `https://www.google.com/s2/favicons?domain=${host}&sz=64`
  } catch {
    return null
  }
})
</script>

<template>
  <article class="card has-thumb" :class="{ analysed: analysis }">
    <a
      :href="article.url"
      target="_blank"
      rel="noopener noreferrer"
      class="thumb-link"
      tabindex="-1"
      aria-hidden="true"
    >
      <img
        v-if="article.image_url && !imageFailed"
        :src="article.image_url"
        alt=""
        class="thumb"
        loading="lazy"
        @error="imageFailed = true"
      />
      <!-- No usable picture (some publishers block hotlinking): a tile with the publisher's icon keeps the card's shape -->
      <span v-else class="thumb placeholder">
        <img v-if="faviconUrl" :src="faviconUrl" alt="" class="favicon" loading="lazy" @error="faviconFailed = true" />
        <span v-else class="initial">{{ (article.source_name || '?').charAt(0) }}</span>
      </span>
    </a>

    <div class="body">
      <p class="meta">
        <span class="source">{{ article.source_name }}</span>
        <span v-if="article.published_at" class="sep">·</span>
        <span v-if="article.published_at">{{ timeAgo(article.published_at) }}</span>
        <span v-if="analysis?.query" class="topic">{{ analysis.query }}</span>
      </p>

      <h3 class="title">
        <a :href="article.url" target="_blank" rel="noopener noreferrer">{{ article.title }}</a>
      </h3>

      <p v-if="!analysis" class="description">{{ article.description }}</p>

      <Transition name="fade" appear>
        <section v-if="analysis" class="analysis">
          <div class="analysis-head">
            <span class="label">
              <svg viewBox="0 0 16 16" aria-hidden="true">
                <path
                  d="M8 1.5l1.6 3.9 3.9 1.6-3.9 1.6L8 12.5 6.4 8.6 2.5 7l3.9-1.6L8 1.5zM13 11l.7 1.8 1.8.7-1.8.7L13 16l-.7-1.8-1.8-.7 1.8-.7L13 11z"
                  fill="currentColor"
                />
              </svg>
              AI summary
            </span>
            <SentimentBadge :sentiment="analysis.sentiment" :score="analysis.sentiment_score" />
          </div>
          <p class="summary">{{ analysis.summary }}</p>
          <p class="reason">
            <strong>Why {{ analysis.sentiment }}:</strong> {{ analysis.sentiment_reason }}
          </p>
        </section>
      </Transition>

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
  grid-template-columns: 1fr;
  gap: 18px;
  padding: 18px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  box-shadow: var(--shadow);
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease,
    border-color 0.18s ease;
}
.card:hover {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--accent) 35%, var(--border));
  box-shadow: var(--shadow-hover);
}
.card.has-thumb {
  grid-template-columns: 168px 1fr;
}
.thumb-link {
  display: block;
  align-self: start;
}
.thumb {
  display: block;
  width: 168px;
  height: 118px;
  object-fit: cover;
  border-radius: 10px;
  background: var(--surface-3);
}
.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--surface-2), var(--surface-3));
}
.favicon {
  width: 36px;
  height: 36px;
  border-radius: 9px;
  opacity: 0.9;
}
.initial {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  font-size: 1.1rem;
  font-weight: 800;
  line-height: 40px;
  text-align: center;
  color: var(--accent);
  background: var(--accent-soft);
}
.body {
  min-width: 0;
}
.meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin: 0 0 6px;
  font-size: 0.78rem;
  color: var(--muted);
}
.source {
  font-weight: 600;
  color: var(--text);
}
.sep {
  opacity: 0.6;
}
.topic {
  margin-left: 2px;
  padding: 1px 8px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
  font-size: 0.72rem;
}
.title {
  margin: 0 0 6px;
  font-size: 1.08rem;
  font-weight: 700;
  line-height: 1.35;
  letter-spacing: -0.01em;
}
.title a {
  color: inherit;
  text-decoration: none;
}
.title a:hover {
  color: var(--accent);
}
.description {
  margin: 0;
  color: var(--muted);
  font-size: 0.93rem;
}
.analysis {
  margin-top: 10px;
  padding: 12px 14px;
  border-left: 3px solid var(--accent);
  border-radius: 10px;
  background: var(--surface-2);
}
.analysis-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.label {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--accent);
}
.label svg {
  width: 13px;
  height: 13px;
}
.summary {
  margin: 0 0 6px;
  line-height: 1.55;
}
.reason {
  margin: 0;
  font-size: 0.86rem;
  color: var(--muted);
}
.reason strong {
  color: var(--text);
  font-weight: 600;
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
  .card,
  .card.has-thumb {
    grid-template-columns: 1fr;
  }
  .thumb {
    width: 100%;
    height: 170px;
  }
}
</style>
