# NewsPulse

Search recent news, get an AI summary and sentiment score per article, and see how coverage of a topic leans. Ask questions and get answers built only from the analysed articles, with sources cited.

Stack: FastAPI, SQLAlchemy, Alembic, PostgreSQL (SQLite locally), OpenAI gpt-4.1-nano, GNews, Vue 3 + TypeScript + Vite.

## How to run it

Requirements: Python 3.12 with [uv](https://docs.astral.sh/uv/), Node 22+. Docker optional.

```bash
cp backend/.env.example backend/.env   # then fill in GNEWS_API_KEY and OPENAI_API_KEY
npm install
npm run setup                          # backend deps (uv) + frontend deps (npm)
npm run dev                            # API on :8000, UI on :5173
```

Open http://localhost:5173. API docs: http://localhost:8000/docs.

Leave `DATABASE_URL` empty to use a local SQLite file. Nothing else needs installing.

Without the task runner:

```bash
cd backend && uv sync && uv run alembic upgrade head && uv run uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
```

Other commands (from the root):

```bash
npm run check       # lint, format, tests, type check, build (same as CI)
npm run test        # backend tests, external APIs mocked
npm run test:llm    # tests against the real OpenAI and GNews APIs (skipped without keys)
npm run lint        # ruff, eslint, prettier
npm run format      # fix formatting
npm run migrate     # apply migrations
npm run migration -- "describe change"   # generate a migration from the models
```

### Docker

One container runs the API and the built frontend:

```bash
docker build -t newspulse .
docker run --rm --name newspulse -p 8000:8000 --env-file backend/.env newspulse
```

Open http://localhost:8000. Migrations run on start. For a local Postgres: `docker compose up -d`, then set `DATABASE_URL=postgresql://postgres:postgres@localhost:5433/newspulse`.

## What the app does

**Discover** (`/`)
- Opens on top headlines. Search any topic or pick a suggestion.
- "Summarise & score" per article, or "Analyse all" for the page.
- A bar shows how coverage of the current search leans. Click a legend entry to filter the cards.
- Already-analysed articles show their stored result; nothing is sent to OpenAI twice.
- The search is in the URL (`/?q=climate`), so it can be shared.

**Research** (`/research`)
- Ask a question like "How is Tesla doing this quarter?".
- An agent searches, analyses the relevant articles, and answers with numbered citations.
- The steps appear live while it works (server-sent events). Analysed articles land in the library.

**Library** (`/library`)
- Everything analysed, newest first, with counts per sentiment and the average score.
- Filter by sentiment or text. Delete entries.
- "Ask your library" answers questions from stored articles only, with sources cited.

Each analysis: a 2 to 3 sentence summary, a label (positive / neutral / negative), a score from -1 to 1, and one sentence explaining the label.

## AI features

**Summary and sentiment** (`services/ai.py`, `analyze_article`)
- One OpenAI call per article using structured outputs, validated by a Pydantic model: the label is always one of three values, the score always in range.
- The prompt asks for the tone of the news for the people involved, not the model's opinion, and warns that the text may be truncated (GNews free tier cuts article bodies).

**Ask your library, RAG** (`services/articles.py` retrieval, `services/ai.py` generation, `routers/ask.py`)
- Retrieval: Postgres full-text search over title, description, summary and search topic, with a GIN index. Question words are OR-ed so natural questions still match.
- No match: falls back to the newest articles, which covers "what is the overall mood?".
- Generation: the model answers only from the numbered sources and returns the numbers it cited; the UI turns them into links.
- The provided key has no embeddings access, so retrieval is lexical. Switching to pgvector would change one function, `search_relevant()`.
- SQLite (local default) falls back to a keyword match.

**Research agent** (`services/agent.py`, `routers/research.py`)
- A tool-calling loop with two strict-schema tools: `search_news` and `analyze_articles`.
- First model call must use a tool; last must answer.
- Budgets per run: 2 searches, 5 analyses, 5 model calls. Keeps the GNews quota and response time bounded.
- Tool failures (e.g. GNews rate limit) go back to the model as text so it can still answer.
- Written against the OpenAI SDK directly. The loop is about 80 lines; a framework would add more than it removes at this size.

## Architecture

Three backend layers: routers handle HTTP only; services hold the logic and are the only layer that touches the database or external APIs; models and schemas define the data. In production the API serves the built frontend, so it is one process.

```mermaid
flowchart LR
    subgraph Browser
        UI[Vue app<br/>Discover / Research / Library]
    end

    subgraph FastAPI
        direction TB
        R1[routers/news.py<br/>GET /api/news]
        R2[routers/articles.py<br/>/api/articles]
        R3[routers/ask.py<br/>POST /api/ask]
        R4[routers/research.py<br/>POST /api/research]

        S1[services/news.py<br/>GNews client + cache]
        S2[services/ai.py<br/>analyze_article<br/>answer_question]
        S3[services/articles.py<br/>queries + full-text retrieval]
        S4[services/agent.py<br/>ResearchAgent tool loop]
    end

    DB[(Postgres / SQLite<br/>articles table)]
    GN[GNews API]
    OA[OpenAI API<br/>gpt-4.1-nano]

    UI -->|JSON| R1 & R2 & R3 & R4
    R1 --> S1 & S3
    R2 --> S2 & S3
    R3 --> S3 & S2
    R4 --> S4
    S4 --> S1 & S2 & S3
    S1 --> GN
    S2 --> OA
    S3 --> DB
```

The agent, step by step:

```mermaid
sequenceDiagram
    participant UI as Research page
    participant A as ResearchAgent
    participant M as OpenAI
    participant G as GNews
    participant DB as articles table

    UI->>A: POST /api/research {question}
    A->>M: question + tool schemas (tool_choice=required)
    M-->>A: call search_news("...")
    A->>G: search
    G-->>A: up to 5 articles
    A->>DB: which are already analysed?
    A->>M: tool result (titles, urls, analysed flags)
    M-->>A: call analyze_articles([urls])
    A->>M: analyze each article (structured output)
    A->>DB: store analyses
    A->>M: tool result ([1] summary + sentiment, [2] ...)
    M-->>A: final answer with citations [1][2]
    A-->>UI: answer, sources, cited numbers, steps
```

## API

| Method | Path | What it does |
| --- | --- | --- |
| GET | `/api/news` | Search GNews (`q`, `lang`, `max`). No `q` = top headlines. Results already stored include their `analysis`. |
| POST | `/api/articles` | Analyse and store an article. 201, or 200 with the stored record if the URL was analysed before. |
| GET | `/api/articles` | List stored analyses. Filters `sentiment`, `q`; paging `limit`, `offset`. |
| GET | `/api/articles/stats` | Counts per sentiment and average score. |
| GET | `/api/articles/{id}` | One stored analysis. |
| DELETE | `/api/articles/{id}` | Delete. 204. |
| POST | `/api/ask` | Answer from stored articles (RAG): answer, sources, which were cited, how they were chosen. |
| POST | `/api/research` | Run the agent: answer, sources, citations, steps. |
| POST | `/api/research/stream` | Same, as server-sent events: one `step` event per tool call as it happens, then `answer` or `error`. The Research page uses this. |
| GET | `/api/health` | Health check. |

Errors and headers:
- 404 unknown id, 422 invalid input.
- 502 `{"detail", "service"}` when GNews or OpenAI fails; 429 on GNews rate limit; 503 when a key is missing.
- Every response has an `X-Request-ID`, also present in the server log line for that request.

Design decisions:
- One table, `articles`. A stored article is its analysis; they are always created together.
- `POST /api/articles` is idempotent per URL (unique column). Re-posting returns the stored record with no OpenAI call, so "Analyse all" is safe to repeat. A race on the same URL is caught by the constraint.
- `/ask` and `/research` are POST actions, not resources. They store nothing of their own.
- The client sends the article body because GNews has no fetch-by-URL. Caching search results server-side would close the gap of a client sending edited text.
- GNews free tier: 100 requests/day. Identical searches are cached for 10 minutes.
- Routers only do HTTP. Queries live in `services/articles.py`; external calls in `services/news.py`, `services/ai.py`, `services/agent.py`.

## Project layout

```
backend/
  app/
    main.py                 app setup, middleware, error handlers, serves the built frontend
    config.py               settings from env / .env
    db.py                   engine and session dependency
    models.py               articles table + full-text search expression
    schemas.py              request and response models
    middleware.py           request IDs, security headers
    routers/
      news.py               GET /api/news
      articles.py           /api/articles
      ask.py                POST /api/ask (RAG)
      research.py           POST /api/research (agent)
    services/
      news.py               GNews client + cache
      ai.py                 OpenAI: analysis, RAG answering
      agent.py              research agent (tool loop)
      articles.py           queries, full-text retrieval
      errors.py             UpstreamError
  migrations/               Alembic
  tests/
    test_api.py             articles and news endpoints
    test_ask.py             RAG endpoint
    test_research.py        agent loop with a scripted fake model
    test_full_flow.py       whole user journey, mocked and live
    test_services.py        GNews parsing, caching, citation cleanup
    test_middleware.py      request IDs, headers, 404 / 500 handling
    test_live_openai.py     real model checks (marked llm)
frontend/
  src/
    api.ts                  typed API client
    types.ts                types matching backend schemas
    format.ts               date and score formatting
    views/                  DiscoverView, ResearchView, LibraryView
    components/             ArticleCard, SentimentBadge, SentimentBar, AskPanel, CitedAnswer
```

## Tests and CI

See [TESTING.md](TESTING.md) for a step by step guide: automated suite, manual walk-through of every page, API checks and failure modes.

- `backend/tests/`: API, services, RAG, agent loop (scripted fake model), middleware, and one test for the whole user journey. External services mocked; runs in under a second without keys.
- Four tests marked `llm` hit the real OpenAI and GNews APIs. Skipped without keys.
- CI: Ruff, migrations and tests against Postgres 16, then ESLint, Prettier, type check and frontend build.

## Deployment

Railway (one project holds the app and the database):

1. New Project → Deploy from GitHub repo → `Kether180/aries-app`. `railway.json` tells Railway to build the Dockerfile and to health-check `/api/health`.
2. In the project, Create → Database → PostgreSQL.
3. On the app service, Variables: `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`, plus `GNEWS_API_KEY` and `OPENAI_API_KEY`.
4. Settings → Networking → Generate Domain.

Migrations run on start. The image runs as a non-root user with a health check.

## Scaling

What already helps:

- The app is stateless apart from one in-memory search cache, so several instances can run behind a load balancer with no session affinity.
- Analyses are keyed by article URL and never computed twice, which caps OpenAI spend at one call per unique article.
- The database has indexes on `url`, `sentiment`, `created_at` and a GIN index for full-text search. Listing is paginated.
- The agent has hard budgets per run, so one request cannot consume unbounded GNews quota or model calls.
- Request IDs in logs make it possible to trace a slow or failed request across instances.

What breaks first, and the fix for each, in the order I would do them:

1. **Blocking I/O.** Routes are synchronous, so each OpenAI call (1 to 3 s) occupies a worker thread. First step is more Uvicorn workers; the proper fix is `AsyncOpenAI`, `httpx.AsyncClient` and async SQLAlchemy, and analysing a batch concurrently with `asyncio.gather` under a semaphore.
2. **Long requests.** "Analyse all" and the agent run inside the HTTP request (up to 20 s). Move them to a job queue (Celery or RQ on Redis, or Postgres-backed with `SKIP LOCKED`), return a job id, and let the UI poll or subscribe over SSE for progress. This also survives client disconnects and allows retries.
3. **The in-memory cache.** It is per process, so two instances would call GNews twice for the same search. Move it to Redis with the same 10 minute TTL, or store raw search results in Postgres keyed by query and time.
4. **GNews quota.** 100 requests a day is the real ceiling. Besides caching, pre-fetch popular topics on a schedule, store the results, and serve searches from the database first. A paid tier or a second news source behind the same `fetch_news` interface would be the next step.
5. **OpenAI rate limits and cost.** Add retry with backoff on 429 (the SDK does some of this), a per-user or per-IP quota on analyse and research endpoints, and track tokens per request (already logged) into a table for cost reporting.
6. **Database.** Postgres handles this schema to millions of rows without changes. Beyond that: partition `articles` by `created_at`, add a read replica for the library and stats, and move the stats query to a materialised view refreshed on a schedule.
7. **Retrieval quality.** Full-text search is fine for keyword questions. With embeddings access, add a `vector` column (pgvector), embed summaries on insert, and combine lexical and vector scores. Only `search_relevant()` changes.
8. **Multi-user.** Add authentication and a `user_id` column; filter every query by it. The library and the "Ask your library" retrieval are then per user.

Rough capacity today: one free instance handles a few concurrent users comfortably. Items 1 to 3 take it to hundreds of concurrent users; items 4 and 5 are about cost, not throughput.

## Next steps

- Re-analyse an article after a prompt change, keeping history.
- Sentiment over time per topic.
- Job queue for "Analyse all" and the agent on large batches.
- Login, if the library should be per user.
