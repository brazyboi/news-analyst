import json
from typing import AsyncGenerator

import anthropic

from agents.analyst_agent import AnalystAgent
from agents.memory import SharedMemory
from agents.news_agent import NewsAgent


def _to_sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def orchestrate_news_analysis(
    query: str,
    days_back: int = 7,
    limit: int = 5,
) -> AsyncGenerator[str, None]:
    """
    Run the news-analyst agent pipeline and stream SSE-formatted JSON strings.
    """
    memory = SharedMemory()
    client = anthropic.Anthropic()

    news_agent = NewsAgent(client=client, memory=memory)
    analyst_agent = AnalystAgent(client=client, memory=memory)

    try:
        yield _to_sse({"stage": "news_agent", "status": "started", "query": query})

        news_results = news_agent.search_news(
            query=query,
            days_back=days_back,
            limit=limit,
        )
        yield _to_sse({"stage": "news_agent", "status": "completed"})

        memory.store("articles", news_results, written_by=news_agent.name)
        yield _to_sse(
            {
                "stage": "memory",
                "status": "stored",
                "key": "articles",
                "written_by": news_agent.name,
            }
        )

        yield _to_sse({"stage": "analyst_agent", "status": "started"})

        run_iter = analyst_agent.run(
            task=f"Analyze latest coverage for query: {query}",
        )
        while True:
            try:
                step = next(run_iter)
                yield _to_sse(
                    {
                        "stage": "analyst_agent",
                        "status": "step",
                        "step": step,
                    }
                )
            except StopIteration as stop:
                final_text = stop.value
                break

        yield _to_sse(
            {
                "stage": "analyst_agent",
                "status": "completed",
                "result": final_text,
            }
        )
        yield _to_sse({"stage": "pipeline", "status": "done"})
    except Exception as exc:
        yield _to_sse(
            {
                "stage": "pipeline",
                "status": "error",
                "error": str(exc),
            }
        )
