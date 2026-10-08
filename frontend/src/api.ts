import type {
  Article,
  ArticleList,
  AskResponse,
  NewsArticle,
  ResearchResponse,
  NewsSearchResponse,
  Sentiment,
  SentimentStats,
} from './types'

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    // FastAPI validation errors put a list in `detail`; everything else is a string
    const detail = typeof body?.detail === 'string' ? body.detail : res.statusText
    throw new ApiError(res.status, detail || `Request failed (${res.status})`)
  }
  return (res.status === 204 ? undefined : await res.json()) as T
}

function query(params: Record<string, string | number | null | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== '') search.set(key, String(value))
  }
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

export const api = {
  searchNews: (q?: string) => request<NewsSearchResponse>(`/api/news${query({ q })}`),

  analyzeArticle: (article: NewsArticle, searchQuery: string | null) =>
    request<Article>('/api/articles', {
      method: 'POST',
      body: JSON.stringify({ ...article, query: searchQuery }),
    }),

  listArticles: (params: { sentiment?: Sentiment | null; q?: string; limit?: number; offset?: number }) =>
    request<ArticleList>(`/api/articles${query(params)}`),

  getStats: () => request<SentimentStats>('/api/articles/stats'),

  deleteArticle: (id: number) => request<void>(`/api/articles/${id}`, { method: 'DELETE' }),

  ask: (question: string) => request<AskResponse>('/api/ask', { method: 'POST', body: JSON.stringify({ question }) }),

  research: (question: string) =>
    request<ResearchResponse>('/api/research', { method: 'POST', body: JSON.stringify({ question }) }),
}
