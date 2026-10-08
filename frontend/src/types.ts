// Mirrors backend/app/schemas.py

export type Sentiment = 'positive' | 'neutral' | 'negative'

export interface NewsArticle {
  url: string
  title: string
  description: string | null
  content: string | null
  source_name: string | null
  source_url: string | null
  image_url: string | null
  published_at: string | null
}

export interface Article extends NewsArticle {
  id: number
  query: string | null
  summary: string
  sentiment: Sentiment
  sentiment_score: number
  sentiment_reason: string
  model: string
  created_at: string
}

export interface NewsSearchResult extends NewsArticle {
  analysis: Article | null
}

export interface NewsSearchResponse {
  query: string | null
  total: number
  articles: NewsSearchResult[]
}

export interface ArticleList {
  total: number
  items: Article[]
}

export interface SentimentStats {
  total: number
  positive: number
  neutral: number
  negative: number
  average_score: number | null
}

export interface AskResponse {
  question: string
  answer: string
  retrieval: 'search' | 'recent' | 'empty'
  sources: Article[] // numbered [1]..[n] in the answer, in this order
  cited: number[]
}

export interface ResearchStep {
  tool: string
  input: Record<string, unknown>
  output: string
}

export interface ResearchResponse {
  question: string
  answer: string
  steps: ResearchStep[]
  sources: Article[]
  cited: number[]
}
