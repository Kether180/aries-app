# Working in this repo

Guidance for coding agents and new contributors. Keep changes small and in the existing style.

## Stack

- Backend: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, OpenAI SDK, httpx. Package manager: uv.
- Frontend: Vue 3 (script setup), TypeScript, Vite, vue-router. No state library.
- Database: PostgreSQL in production (Railway), SQLite locally when `DATABASE_URL` is empty.
- External APIs: GNews (search), OpenAI gpt-4.1-nano (analysis, RAG answers, agent).

## Commands (run from the repo root)

```bash
npm run dev          # API :8000 + UI :5173
npm run check        # everything CI runs: ruff, eslint, prettier, tests, vue-tsc, build
npm run test         # backend tests, external APIs mocked
npm run test:llm     # tests against the real APIs, need keys in backend/.env
npm run format       # fix formatting (ruff + prettier)
npm run migrate      # alembic upgrade head
npm run migration -- "message"   # autogenerate a migration after changing models.py
```

Run `npm run check` before committing. CI fails on lint or format issues.

## Where things go

- `backend/app/routers/`: HTTP only. Parse the request, call a service, return a schema. No queries here.
- `backend/app/services/articles.py`: all database queries.
- `backend/app/services/news.py`, `ai.py`, `agent.py`: all calls to GNews and OpenAI.
- `backend/app/schemas.py`: request and response models. `frontend/src/types.ts` mirrors them; update both.
- `backend/app/models.py`: the single `articles` table. Any change needs a migration.
- `frontend/src/api.ts`: the only place that calls `fetch`. Add a method there for a new endpoint.
- Tests live in `backend/tests/`. Mock external calls at the router module (`monkeypatch.setattr(articles_router, "analyze_article", ...)`), not at the service module, because routers import functions directly.

## Conventions

- External failures raise `UpstreamError(service, message, status)`; `main.py` maps it to JSON. Do not catch it in routers.
- OpenAI calls go through `_complete()` in `services/ai.py` with a Pydantic `response_format`. Do not parse model output by hand.
- Agent tools must be `strict: true` with `additionalProperties: false`, or the SDK's `parse()` rejects them.
- Tool errors are returned to the model as text, not raised, so the agent can still answer.
- Keep the agent budgets (`MAX_SEARCHES`, `MAX_ANALYSES`, `MAX_STEPS`) unless asked; GNews allows 100 requests a day.
- Line length 120 in both languages. Prettier: no semicolons, single quotes.
- Plain prose in docs: no em dashes.
- Commits are authored by the repo owner only; do not add co-author trailers.

## Gotchas

- The text-search config in `models.py` must stay a `literal_column`; a plain string breaks `create_all` on Postgres.
- Full-text retrieval only runs on Postgres. SQLite uses the keyword fallback in `search_relevant()`.
- `env_ignore_empty=True` in `config.py`: a blank `DATABASE_URL=` in `.env` means SQLite, not an error.
- A blank `OPENAI_API_KEY` or `GNEWS_API_KEY` returns 503 from the feature that needs it; startup logs a warning.
- Some news sites block hotlinked thumbnails. `ArticleCard` drops the image on error; keep that behaviour.
- On Windows, scripts that write files may produce CRLF; Git normalises to LF on commit, Prettier may complain locally until the file is rewritten.
- Never commit `backend/.env`, `*.db`, or `frontend/dist`.
