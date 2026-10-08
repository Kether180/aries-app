# Testing guide

How to check that AriesNews works, from the automated suite to a manual walk-through of every feature. Takes about 15 minutes end to end.

## 1. Automated tests

From the project root:

```bash
npm run check
```

Expected: Ruff "All checks passed", 26 backend tests passed, ESLint and Prettier clean, `vue-tsc` and Vite build succeed. Runs in under a minute and needs no API keys; GNews and OpenAI are mocked.

To run the same tests against a real Postgres (what CI does):

```bash
docker compose up -d
cd backend
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/ariesnews uv run pytest -m "not llm"
```

Live tests against the real OpenAI and GNews APIs (needs both keys in `backend/.env`, uses about 1 GNews request and 10 OpenAI calls):

```bash
npm run test:llm
```

Expected: 4 passed. They check that an analysis is grounded in the article, that answers cite sources and admit when the sources do not contain the answer, that the agent searches before answering, and the whole user journey end to end.

## 2. Start the app

Local:

```bash
npm run dev
```

Open http://localhost:5173. Or use the live URL if one is deployed.

On the first request after a deploy, free hosting tiers can take 30 to 60 seconds to wake up.

## 3. Manual walk-through

### Discover page

1. The page opens on top headlines. You should see about 10 article cards with source, time and description.
2. Click the **Climate** chip. The URL changes to `/?q=Climate` and the cards reload. The chip is highlighted.
   Change the country selector to **Germany**: the URL gains `&country=de` and the results come from German outlets.
3. On one card click **Summarise & score**. The button shows "Analysing..." for 1 to 3 seconds, then the card shows:
   - an "AI summary" block with 2 to 3 sentences
   - a badge in words: Positive, Neutral or Negative, with "Strongly" or "Slightly" when the tone is clear or faint, and a small bar showing the same thing (hover it for the exact score)
   - one sentence starting "Why positive:" (or neutral, negative) explaining the label
4. The box above the cards now says "1 of 10 analysed" and shows a sentiment bar. Click **What do the labels mean?** under it for a plain-language explanation.
5. Click **Analyse the other 9**. The remaining cards analyse three at a time. When done, the box says "10 of 10 analysed" and the bar shows the split, for example "6 neutral (60%), 4 negative (40%)".
6. Click **Neutral** in the switch under the bar (or **6 neutral** in the legend). Only neutral cards remain and the other bar segments dim. Click **All** to reset. Tap any badge: the "What do the labels mean?" note opens.
7. Reload the page. It starts fresh: cards show no analysis. Click **Analyse all** again: the results appear almost instantly, because they come from the database and nothing is sent to OpenAI twice.
8. Search for a nonsense word such as `qwzxv`. Expected: "No articles found. Try a broader search."

### Research page

1. Click **Research** in the header.
2. Type `How is Tesla doing this quarter?` and click **Research**. A "Finding and reading articles" panel appears with a timer, and each step shows up as the agent finishes it ("Searched the news", then "Analysed articles"), listing the articles involved with links and sentiment badges, with the current activity underneath. The whole run takes 10 to 20 seconds.
3. Expected result:
   - an **Answer** of 2 to 5 sentences with small numbered chips like `1` and `2` after sentences
   - a numbered list of sources under the answer; cited ones are fully visible, uncited ones are dimmed
   - a **Behind this answer** list, for example "Searched the news: 'Tesla earnings'" then "Read and scored: 2 articles", each with the articles involved as links.
4. Click a numbered chip in the answer. The page scrolls to that source.
5. Ask something the news is unlikely to cover, such as `Who won the 1998 chess olympiad?`. Expected: the agent says the sources do not contain the answer, with no citations.

### Library page

1. Click **Library**. The articles analysed so far are listed newest first. The box at the top shows the count, the average score and a sentiment bar. If you have analysed more than one topic, a **Mood by topic** panel shows one bar per topic; clicking one filters the list.
2. Click **Negative** in the filter. Only negative articles remain and the count updates. Click **All** to reset.
3. Type part of a title in the filter box. The list narrows as you type.
4. In **Ask your library**, click the suggestion "What is the overall mood of the news?". Expected: an answer with citation chips and a source list, within a few seconds. **Ask another question** brings the suggestions back.
5. Ask something unrelated to what you analysed, such as `What is the weather in Lima?`. Expected: the answer says the sources do not cover it.
6. Click **Delete** on one card and confirm. The card disappears and the count goes down by one.

### Dark mode and mobile

- Switch your OS to dark mode. The app follows it; text and badges stay readable.
- Narrow the browser to phone width. Cards stack, thumbnails go full width, nothing scrolls sideways.

## 4. API checks

Open http://localhost:8000/docs (or `/docs` on the live URL). Every endpoint can be called from there. Quick checks with curl:

```bash
BASE=http://localhost:8000

curl $BASE/api/health
# {"status":"ok"}

curl "$BASE/api/news?q=space&max=3"
# {"query":"space","total":3,"articles":[...]}

curl $BASE/api/articles/stats
# {"total":N,"positive":..,"neutral":..,"negative":..,"average_score":..}

curl "$BASE/api/articles?sentiment=negative&limit=5"
# {"total":N,"items":[...]}

curl $BASE/api/articles/999999
# 404 {"detail":"Article not found"}

curl "$BASE/api/articles?sentiment=angry"
# 422 validation error

curl $BASE/api/nope
# 404 {"detail":"Not found"}

curl -X POST $BASE/api/ask -H "content-type: application/json" -d '{"question":"What is the mood of the news?"}'
# {"question":..,"answer":..,"retrieval":"search"|"recent"|"empty","sources":[...],"cited":[...]}
```

Posting the same article twice:

```bash
curl -X POST $BASE/api/articles -H "content-type: application/json" \
  -d '{"url":"https://example.com/test","title":"Test article","description":"A short test."}'
# first call: HTTP 201 with the analysis
# second call: HTTP 200 with the same id, no new OpenAI call
```

Every response carries an `X-Request-ID` header. Pass your own UUID in a request and the same value comes back:

```bash
curl -i $BASE/api/health -H "X-Request-ID: 123e4567-e89b-12d3-a456-426614174000" | grep -i x-request-id
```

## 5. Failure modes worth seeing

- Remove `GNEWS_API_KEY` from `.env` and restart: searches return 503 `{"detail":"GNEWS_API_KEY is not configured","service":"gnews"}` and the UI shows that message. The library and ask features still work.
- Remove `OPENAI_API_KEY`: analysing returns 503 with the same shape, and the card shows a Retry button.
- The GNews free tier allows 100 requests a day. Past that, searches switch to the Google News RSS feed automatically: results still appear, but without pictures (cards show the publisher's icon instead) and with shorter text for the analysis. Identical searches within 10 minutes are served from cache and do not count.

## 6. Docker

```bash
docker build -t ariesnews .
docker run --rm --name ariesnews -p 8000:8000 --env-file backend/.env ariesnews
```

Expected log lines on start: Alembic "Running upgrade -> 0001", then "Application startup complete". Open http://localhost:8000 and repeat section 3. `docker ps` shows the container as "healthy" after about 30 seconds.
