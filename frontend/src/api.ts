import type {
  Article,
  ArticleList,
  AskResponse,
  NewsArticle,
  ResearchResponse,
  ResearchStep,
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

  // Same as research(), but reports each agent step as it happens (server-sent events over POST)
  researchStream: async (question: string, onStep: (step: ResearchStep) => void): Promise<ResearchResponse> => {
    const res = await fetch('/api/research/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    })
    if (!res.ok || !res.body) {
      const body = await res.json().catch(() => null)
      throw new ApiError(res.status, typeof body?.detail === 'string' ? body.detail : res.statusText)
    }
    const reader = res.body.pipeThrough(new TextDecoderStream()).getReader()
    let buffer = ''
    let answer: ResearchResponse | null = null
    for (;;) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += value
      // Events are separated by a blank line; keep any incomplete trailing event in the buffer
      const blocks = buffer.split('\n\n')
      buffer = blocks.pop() ?? ''
      for (const block of blocks) {
        const event = /^event: (.+)$/m.exec(block)?.[1]
        const data = /^data: (.+)$/m.exec(block)?.[1]
        if (!event || !data) continue
        const payload = JSON.parse(data)
        if (event === 'step') onStep(payload as ResearchStep)
        else if (event === 'answer') answer = payload as ResearchResponse
        else if (event === 'error') throw new ApiError(502, payload.detail ?? 'Research failed')
      }
    }
    if (!answer) throw new ApiError(502, 'The research ended without an answer')
    return answer
  },
}
