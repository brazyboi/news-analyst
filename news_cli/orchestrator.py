from typing import Generator

import anthropic

from .agents.analyst_agent import AnalystAgent
from .agents.memory import SharedMemory
from .agents.news_agent import NewsAgent


def orchestrate_news_analysis(
    query: str,
    companies: list[str] | None = None,
    days_back: int = 7,
    limit: int = 5,
) -> Generator[dict, None, str]:
    """
    Run the in-process news-analysis pipeline and stream status dictionaries.
    """
    memory = SharedMemory()
    client = anthropic.Anthropic()

    news_agent = NewsAgent(client=client, memory=memory)
    analyst_agent = AnalystAgent(client=client, memory=memory)
    total_iterations = 0

    try:
        yield {
            "stage": "news_agent",
            "status": "started",
            "agent": news_agent.name,
            "query": query,
        }

        news_results = news_agent.search_news(
            query=query,
            days_back=days_back,
            limit=limit,
        )
        total_iterations += 1

        memory.store("articles", news_results, written_by=news_agent.name)
        article_count = news_results.count("\n[") + 1 if news_results.startswith("[1]") else 0
        yield {
            "stage": "news_agent",
            "status": "step",
            "agent": news_agent.name,
            "iteration": 1,
            "action": "search_news",
            "input": {"query": query, "days_back": days_back, "limit": limit},
            "result_status": "ok",
            "article_count": article_count,
            "observation": news_results[:300],
        }
        yield {
            "stage": "memory",
            "status": "stored",
            "key": "articles",
            "written_by": news_agent.name,
        }

        yield {"stage": "analyst_agent", "status": "started", "agent": analyst_agent.name}

        run_iter = analyst_agent.run(
            task=(
                f"Analyze latest coverage for query: {query}. "
                f"Focus on these companies: {', '.join(companies or [])}."
            ),
        )
        while True:
            try:
                step = next(run_iter)
                total_iterations += 1
                yield {
                    "stage": "analyst_agent",
                    "status": "step",
                    **step,
                }
            except StopIteration as stop:
                final_text = stop.value
                break

        yield {"stage": "analyst_agent", "status": "completed"}
        yield {
            "stage": "pipeline",
            "status": "done",
            "iterations": total_iterations,
        }
        return final_text
    except Exception as exc:
        yield {"stage": "pipeline", "status": "error", "error": str(exc)}
        return ""
