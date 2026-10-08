# Working in this repo

Guidance for coding agents and new contributors. Keep changes small and in the existing style.

## Stack

- Backend: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, OpenAI SDK, httpx. Package manager: uv.
- Frontend: Vue 3 (script setup), TypeScript, Vite, vue-router. Plain CSS with design tokens in `src/assets/main.css`. No state library, no CSS framework.
- Database: PostgreSQL in production (Railway), SQLite locally when `DATABASE_URL` is empty.
- External APIs: GNews (search, 100 requests a day), Google News RSS (fallback, no key), OpenAI gpt-4.1-nano (analysis, RAG answers, agent).

## Commands (run from the repo root)

```bash
npm run dev          # API :8000 + UI :5173
npm run check        # everything CI runs: ruff, eslint, prettier, tests, vue-tsc, build
npm run test         # backend tests, external APIs mocked
npm run test:llm     # tests against the real OpenAI API (and news feeds), need keys in backend/.env
npm run format       # fix formatting (ruff + prettier)
npm run migrate      # alembic upgrade head
npm run migration -- "message"   # autogenerate a migration after changing models.py
```

Run `npm run check` before committing. CI fails on lint or format issues. CI runs the backend tests against a real Postgres, so Postgres-only code paths (full-text search) are covered there.

## Where things go

- `backend/app/routers/`: HTTP only. Parse the request, call a service, return a schema. No queries here.
- `backend/app/services/articles.py`: all database queries, including `search_relevant()` (RAG retrieval) and `stats_by_topic()`.
- `backend/app/services/news.py`: GNews client, Google News RSS fallback, country-to-language mapping, in-memory cache.
- `backend/app/services/ai.py`: every OpenAI call goes through `_complete()` with a Pydantic `response_format`. Holds the analysis prompt, the RAG answer prompt, `reconcile_sentiment()` and `finalize_citations()`.
- `backend/app/services/agent.py`: the research agent (tool loop). Tools: `search_news`, `analyze_articles`. Each step records both the raw text the model saw (`output`) and structured `items` for the UI.
- `backend/app/routers/research.py`: `POST /api/research` (JSON) and `POST /api/research/stream` (server-sent events: `step` events, then `answer` or `error`).
- `backend/app/schemas.py`: request and response models. `frontend/src/types.ts` mirrors them; update both.
- `backend/app/models.py`: the single `articles` table. Any change needs a migration.
- `frontend/src/api.ts`: the only place that calls `fetch`. Add a method there for a new endpoint. `researchStream()` parses the SSE stream.
- `frontend/src/components/`: `SearchBar` and `ResultsToolbar` (the Discover page's search row and results header), `ResearchSteps` (the "Behind this answer" panel), `ArticleCard` (one article, placeholder tile when the image fails), `SentimentBadge` (label in words plus meter; tapping it opens the help note), `SentimentBar`, `SentimentHelp`, `TopicMood`, `AskPanel`, `CitedAnswer`. Views hold page state and API calls only.
- `frontend/src/constants.ts`: topics, countries, filter options and example questions shared by views.
- Tests live in `backend/tests/`. Mock external calls at the router module (`monkeypatch.setattr(articles_router, "analyze_article", ...)`), not at the service module, because routers import functions directly. Fake `fetch_news` must accept `country=None`.

## Conventions

- External failures raise `UpstreamError(service, message, status)`; `main.py` maps it to JSON. Do not catch it in routers.
- Sentiment is defined as "good or bad news for the people the article is about", not the tone of the writing. The prompt, the UI note (`SentimentHelp.vue`), the badge tooltips and the labelled evaluation test in `tests/test_live_openai.py` all state that definition; keep them in sync.
- The label always follows the score (`reconcile_sentiment`): below 0.2 in magnitude is neutral.
- Citations: the model returns `cited_sources`; `finalize_citations()` drops numbers with no source and appends `[n]` markers if the model wrote none.
- Agent tools must be `strict: true` with `additionalProperties: false`, or the SDK's `parse()` rejects them.
- Tool errors are returned to the model as text, not raised, so the agent can still answer. Tool messages are also shown to users when a step has no items, so keep them readable.
- Keep the agent budgets (`MAX_SEARCHES`, `MAX_ANALYSES`, `MAX_STEPS`).
- A country filter switches the search language to that country's own language (`COUNTRY_LANGUAGE`), so results come from its press; summaries are always written in English.
- UI wording is for readers, not developers: no "model", "agent", "raw output" on the page. The research panel is "Behind this answer".
- Line length 120 in both languages. Prettier: no semicolons, single quotes.
- Plain prose in docs: no em dashes.
- Commits are authored by the repo owner only; do not add co-author trailers.

## Gotchas

- The text-search config in `models.py` must stay a `literal_column`; a plain string breaks `create_all` on Postgres.
- Full-text retrieval only runs on Postgres. SQLite uses the keyword fallback in `search_relevant()`.
- GNews signals the daily limit with HTTP 403 and a "request limit" message, not 429. Both trigger the RSS fallback. The per-second limit is a 429 and gets one retry.
- RSS results have no image and no body text; descriptions that only repeat the headline are dropped.
- `env_ignore_empty=True` in `config.py`: a blank `DATABASE_URL=` in `.env` means SQLite, not an error. `GET /api/health` reports the engine in use and the raw state of `DATABASE_URL` (unset, empty, unresolved reference, or scheme). On Railway, the app's `DATABASE_URL` must be `${{Postgres.DATABASE_URL}}` and the Postgres service must keep its own default `DATABASE_URL` template.
- A blank `OPENAI_API_KEY` returns 503 from analysis; startup logs a warning.
- Some news sites block hotlinked thumbnails. `ArticleCard` swaps in a placeholder tile with the publisher's favicon; keep that behaviour.
- On Windows, scripts that write files may produce CRLF; Git normalises to LF on commit, Prettier may complain locally until the file is rewritten.
- Never commit `backend/.env`, `*.db`, or `frontend/dist`.
