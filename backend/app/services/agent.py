"""Research agent: a small tool-calling loop over the news and analysis services.

Given a question, the model decides what to search, which articles to analyse, and then
answers from those analyses with citations. Plain OpenAI tool calling, no framework: the loop
is short enough to read top to bottom.

Budget per run (keeps GNews quota and latency in check):
  - MAX_SEARCHES searches, MAX_ANALYSES analyses, MAX_STEPS model calls
"""

import json
import logging
from collections.abc import Callable

import openai
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Article
from app.schemas import NewsArticle
from app.services import articles as article_service
from app.services.ai import Answer, _client, analyze_article
from app.services.errors import UpstreamError
from app.services.news import fetch_news

logger = logging.getLogger(__name__)

MAX_STEPS = 5
MAX_SEARCHES = 2
MAX_ANALYSES = 5

SYSTEM_PROMPT = """You are a news research agent. Answer the user's question about current news.

Work in this order:
1. search_news with 1-2 focused queries (short keyword queries work best, e.g. "Tesla earnings").
2. analyze_articles on the relevant results that are not yet analysed (pass their URLs).
3. Answer in 2-5 sentences using ONLY the analysed articles, citing each one you use with its number
   in square brackets, e.g. "Sales fell 8% [2]." Mention how coverage leans when relevant.
If the search finds nothing useful, say so instead of guessing. cited_sources lists every number you cited."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_news",
            "description": "Search recent news articles. Returns up to 5 results with url, title, description and "
            "whether each is already analysed.",
            "strict": True,  # model output must match this schema exactly
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Short keyword search, e.g. 'Tesla earnings'"}
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_articles",
            "description": "Summarise and score the sentiment of articles found by search_news. "
            "Returns each article's number, summary and sentiment, for citing in the answer.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {"urls": {"type": "array", "items": {"type": "string"}, "description": "Article URLs"}},
                "required": ["urls"],
                "additionalProperties": False,
            },
        },
    },
]


class AgentStep(BaseModel):
    tool: str
    input: dict
    output: str


class ResearchResult(BaseModel):
    answer: str
    cited_sources: list[int]
    steps: list[AgentStep]
    sources: list[Article]

    model_config = {"arbitrary_types_allowed": True}


class ResearchAgent:
    def __init__(self, db: Session, on_step: Callable[[AgentStep], None] | None = None):
        self.db = db
        self.on_step = on_step  # called after each tool run, used to stream progress to the UI
        self.found: dict[str, NewsArticle] = {}  # url -> article from search, so analyze can use it
        self.sources: list[Article] = []  # numbered [1]..[n] in tool outputs and the answer
        self.steps: list[AgentStep] = []
        self.searches = 0
        self.analyses = 0

    # --- tools ----------------------------------------------------------------------------

    def search_news(self, query: str) -> str:
        if self.searches >= MAX_SEARCHES:
            return "Search budget used up. Answer with what you have."
        self.searches += 1
        try:
            results = fetch_news(query, max_results=5)
        except UpstreamError as exc:
            return f"Search failed: {exc.message}"
        analysed = article_service.get_by_urls(self.db, [str(a.url) for a in results])
        lines = []
        for a in results:
            url = str(a.url)
            self.found[url] = a
            if url in analysed:
                n = self._add_source(analysed[url])
                lines.append(f"- {url}\n  {a.title}\n  ALREADY ANALYSED as source [{n}]")
            else:
                lines.append(f"- {url}\n  {a.title}\n  {a.description or ''}")
        return "\n".join(lines) if lines else "No articles found for this query."

    def analyze_articles(self, urls: list[str]) -> str:
        lines = []
        for url in urls:
            article = self.found.get(url)
            if article is None:
                lines.append(f"{url}: unknown URL, search first")
                continue
            existing = article_service.get_by_url(self.db, url)
            if existing is None:
                if self.analyses >= MAX_ANALYSES:
                    lines.append(f"{url}: analysis budget used up")
                    continue
                self.analyses += 1
                analysis = analyze_article(article)
                payload = article.model_copy(update={"query": None})
                existing, _ = article_service.create(self.db, payload, analysis, model=settings.openai_model)
            n = self._add_source(existing)
            lines.append(f"[{n}] {existing.title}\n  Sentiment: {existing.sentiment}\n  Summary: {existing.summary}")
        return "\n".join(lines)

    def _add_source(self, article: Article) -> int:
        if article not in self.sources:
            self.sources.append(article)
        return self.sources.index(article) + 1

    # --- loop -----------------------------------------------------------------------------

    def run(self, question: str) -> ResearchResult:
        messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        for step in range(MAX_STEPS):
            last = step == MAX_STEPS - 1
            message = self._call_model(messages, first=step == 0, final=last)

            if not message.tool_calls:
                answer = message.parsed
                if answer is None:
                    raise UpstreamError("openai", "agent returned no answer")
                answer.cited_sources = sorted({n for n in answer.cited_sources if 1 <= n <= len(self.sources)})
                return ResearchResult(
                    answer=answer.answer, cited_sources=answer.cited_sources, steps=self.steps, sources=self.sources
                )

            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in message.tool_calls
                    ],
                }
            )
            for tc in message.tool_calls:
                output = self._run_tool(tc.function.name, tc.function.arguments)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": output})

        raise UpstreamError("openai", "agent did not finish within the step budget")

    def _run_tool(self, name: str, arguments: str) -> str:
        try:
            args = json.loads(arguments or "{}")
        except json.JSONDecodeError:
            args = {}
        if name == "search_news":
            output = self.search_news(str(args.get("query", "")))
        elif name == "analyze_articles":
            output = self.analyze_articles([str(u) for u in args.get("urls", [])])
        else:
            output = f"Unknown tool {name}"
        logger.info("agent tool %s(%s) -> %d chars", name, args, len(output))
        step = AgentStep(tool=name, input=args, output=output)
        self.steps.append(step)
        if self.on_step:
            self.on_step(step)
        return output

    def _call_model(self, messages: list[dict], *, first: bool, final: bool):
        """One model call. The first must use a tool; the final must answer."""
        if not settings.openai_api_key:
            raise UpstreamError("openai", "OPENAI_API_KEY is not configured", 503)
        try:
            completion = _client().chat.completions.parse(
                model=settings.openai_model,
                temperature=0,
                messages=messages,
                tools=TOOLS,
                tool_choice="none" if final else ("required" if first else "auto"),
                response_format=Answer,
            )
        except openai.OpenAIError as exc:
            logger.warning("OpenAI request failed: %s", exc)
            raise UpstreamError("openai", str(exc)) from exc
        return completion.choices[0].message
