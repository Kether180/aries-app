// Shared UI vocabulary: topic chips, countries, filter options and example questions.
// Views import from here so they hold only their own logic.

import type { Sentiment } from './types'

export const TOPICS = ['Artificial intelligence', 'Climate', 'Stock market', 'Elections', 'Space', 'Health']

// GNews country codes; '' means worldwide. The backend searches each country's press in its own language.
export const COUNTRIES = [
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

export const SENTIMENT_FILTERS: { label: string; value: Sentiment | null }[] = [
  { label: 'All', value: null },
  { label: 'Positive', value: 'positive' },
  { label: 'Neutral', value: 'neutral' },
  { label: 'Negative', value: 'negative' },
]

export const ASK_EXAMPLES = [
  'What is the overall mood of the news?',
  'What are the main stories about the economy?',
  'Is there any good news?',
]

export const RESEARCH_EXAMPLES = [
  'How is Tesla doing this quarter?',
  'What happened in the UK economy this week?',
  'Is the news about AI regulation positive or negative?',
]
