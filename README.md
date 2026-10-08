# NewsPulse

Search recent news, get an AI summary and sentiment score for each article, see how coverage of a topic leans,
and ask questions that are answered from the analysed articles with citations.

**Stack:** FastAPI · SQLAlchemy · Alembic · PostgreSQL · OpenAI (`gpt-4.1-nano`) · GNews · Vue 3 + TypeScript + Vite

## Product

The question the app answers: *"What's the mood of the news about X?"*

- **Discover** (`/`): opens on top headlines. Search any topic, or pick a suggested one. Each result can be
  summarised and scored individually, or you can **Analyse all** at once. A sentiment bar above the
  results shows how coverage of the current search leans. Articles that were analysed before show their
  stored analysis straight away and are never re-processed. Searches live in the URL (`/?q=climate`),
  so they can be shared and the back button works.
- **Research** (`/research`): ask a question like *"How is Tesla doing this quarter?"*. An agent decides
  what to search, analyses the relevant articles, and answers with citations. The steps it took are shown,
  and the articles it analysed land in the library.
- **Library** (`/library`): everything that has been analysed, newest first, with overall stats (count,
  average score, sentiment split), filters by sentiment or free text, and delete. **Ask your library**
  answers questions from the saved articles only (RAG), citing its sources.

Each analysis has a 2–3 sentence summary, a sentiment label (positive / neutral / negative), a score
from -1 to 1, and a one-line explanation of the label, so the score isn't a black box.

## AI features

| Feature | How it works |
| --- | --- |
| **Summary + sentiment** | One structured-output call per article (`services/ai.py`). The response is validated against a Pydantic model, so the label is always one of three values and the score is within [-1, 1]. The prompt scores the article's tone, not the model's opinion, and tells the model the text may be truncated. |
| **Ask your library (RAG)** | Retrieval: Postgres full-text search (`to_tsvector` + `ts_rank_cd`, GIN-indexed) over title, description, summary and search topic; terms are OR-ed so a natural-language question still matches. If nothing matches, the newest articles are used instead (for "what's the overall mood?"). Generation: the model answers only from the numbered sources and returns the citation numbers, which the UI turns into links. The provided API key has no embeddings access, so lexical retrieval is used; swapping in pgvector would only touch `search_relevant()`. |
| **Research agent** | A tool-calling loop (`services/agent.py`) with two tools, `search_news` and `analyze_articles`, both strict-schema. The first model call must use a tool, the last must answer, and each run is capped at 2 searches, 5 analyses and 5 model calls, which protects the GNews quota and bounds latency. Tool failures (e.g. GNews rate limit) are returned to the model as text so it can still answer with what it has. Written against the OpenAI SDK directly: the loop is ~80 lines and reads top to bottom, which I preferred over a framework for a codebase that has to be edited live without AI help. |

## API

| Method   | Path                  | Description                                                                                                                     |
| -------- | --------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `GET`    | `/api/news`           | Search GNews (`q`, `lang`, `max`). Omit `q` for top headlines. Each result includes `analysis` if it is already stored.         |
| `POST`   | `/api/articles`       | Analyse an article and store it. `201` when created, or `200` with the existing record if the URL was analysed already.         |
| `GET`    | `/api/articles`       | List stored analyses. Filters: `sentiment`, `q`; paging: `limit`, `offset`. Returns `{ total, items }`.                         |
| `GET`    | `/api/articles/stats` | Counts per sentiment and the average score.                                                                                     |
| `GET`    | `/api/articles/{id}`  | One stored analysis.                                                                                                            |
| `DELETE` | `/api/articles/{id}`  | Delete an analysis (`204`).                                                                                                     |
| `POST`   | `/api/ask`            | Answer a question from stored articles (RAG). Returns the answer, numbered sources, which were cited, and how they were chosen. |
| `POST`   | `/api/research`       | Run the research agent. Returns the answer, sources, citations and the steps the agent took.                                    |
| `GET`    | `/api/health`         | Health check.                                                                                                                   |

Interactive docs are at `/docs` while the backend is running.

Errors: `404` for unknown IDs and `422` for invalid input. When GNews or OpenAI fails, the API returns
`502` with `{ "detail", "service" }`; a GNews rate limit returns `429`, and a missing API key returns `503`.

### Design notes

- **One resource, `articles`.** A stored article *is* its analysis; they are created together and
  never exist apart, so a separate `analyses` table would only add a join.
- **`POST /api/articles` is idempotent per URL.** `url` is unique in the database, and posting an article
  that is already stored returns it without calling OpenAI again. This saves cost, and it means the UI's
  "Analyse all" is safe to click twice. A concurrent duplicate is caught by the unique constraint.
- **`/ask` and `/research` are `POST` actions, not resources.** They compute an answer and store nothing
  of their own (the agent stores articles through the same path as `POST /api/articles`).
- **The client sends the article body to `POST`.** GNews has no "get by URL" endpoint, so the frontend
  sends back what it got from `/api/news`. The trade-off is that the client could submit edited text; a
  server-side cache of search results keyed by URL would close that gap.
- **The GNews free tier allows 100 requests/day.** Identical searches are cached in memory for 10
  minutes (`NEWS_CACHE_SECONDS`), and the agent is capped at 2 searches per run.
- **Routers are thin.** HTTP concerns live in `routers/`; queries live in `services/articles.py`;
  external APIs live in `services/news.py`, `services/ai.py` and `services/agent.py`.

## Project layout

```
backend/
  app/
    main.py               FastAPI app, error handling, serves the built frontend in production
    config.py             Settings from env / .env
    db.py                 SQLAlchemy engine + session dependency
    models.py             Article table + full-text search expression
    schemas.py            Pydantic request/response models
    routers/              news, articles, ask, research  (HTTP only)
    services/
      news.py             GNews client + cache
      ai.py               OpenAI: article analysis, RAG answering
      agent.py            Research agent (tool-calling loop)
      articles.py         Database queries, incl. full-text retrieval
  migrations/             Alembic migrations
  tests/                  API + service tests (external services mocked)
frontend/
  src/
    api.ts                Typed API client
    types.ts              Types matching backend schemas
    views/                DiscoverView, ResearchView, LibraryView
    components/           ArticleCard, SentimentBadge, SentimentBar, AskPanel, CitedAnswer
```

## Running locally

Requirements: Python 3.12 with [uv](https://docs.astral.sh/uv/), and Node 22+.

```bash
cp backend/.env.example backend/.env   # add GNEWS_API_KEY and OPENAI_API_KEY
npm install && npm run setup           # backend deps (uv) + frontend deps (npm)
npm run dev                            # API on :8000 (migrations run first), UI on :5173
```

The root `package.json` is just a task runner; the backend lives in `backend/` (uv) and the frontend in
`frontend/` (npm).

| Command | What it does |
| --- | --- |
| `npm run dev` | Runs API and UI together. `dev:api` / `dev:web` run one. |
| `npm run check` | Everything CI runs: lint, format check, tests, type-check and build. |
| `npm run test` | Backend tests (external services mocked). `test:llm` runs the live OpenAI checks, which skip without a key. |
| `npm run lint` / `npm run format` | Ruff + ESLint + Prettier, check or fix. |
| `npm run migrate` | Apply Alembic migrations. `npm run migration -- "add x"` generates one from the models. |

`DATABASE_URL` defaults to a local SQLite file, so nothing needs installing to try it. SQLite uses a
simpler keyword match for "Ask your library"; Postgres uses full-text search. For local Postgres, run
`docker compose up -d` and set `DATABASE_URL=postgresql://postgres:postgres@localhost:5433/newspulse`.

CI (`.github/workflows/ci.yml`) runs the same checks, applying the migrations to a real Postgres and
running the tests against it.

### Operational notes

- Every response carries an `X-Request-ID` (a client-supplied UUID is honoured), and every log line
  includes it, so a failed request in the UI can be matched to its log entry.
- Unhandled errors return a generic `500`; the traceback goes to the log, never to the client.
- Startup logs which API keys are missing rather than failing on the first request.
- The Docker image runs as a non-root user with a `HEALTHCHECK` on `/api/health`.

## Deployment

The `Dockerfile` builds the Vue app and serves it from FastAPI, running migrations on start, so the whole
app is one service. `render.yaml` is a Render Blueprint for that service plus a free Postgres database:
create a Blueprint from the repo in Render, then fill in `GNEWS_API_KEY` and `OPENAI_API_KEY`. Railway
works the same way with the Dockerfile and a Postgres plugin.

## What I'd do next

- Stream the agent's steps to the UI (SSE) instead of showing them when it finishes.
- Re-analyse an article after a prompt change, keeping the history.
- Track sentiment over time per topic (score against `published_at`).
- Move "Analyse all" and the agent to a background job queue for large batches.
- Add auth if the library should be per user rather than shared.
