from typing import Any, Generator

from anthropic.types import ToolUnionParam

from .base import BaseAgent


class AnalystAgent(BaseAgent):
    """
    Agent that analyzes article text already collected in SharedMemory.
    It does not call external tools.
    """

    DEFAULT_ARTICLES_KEY = "articles"

    def __init__(self, client, memory=None):
        super().__init__(name="analyst_agent", client=client, memory=memory)

        self.system_prompt = """
            You are a news analysis agent.
            Reason only over article content provided in the user message.

            Your output must include exactly these sections:
            1) Top 3 Trend Themes
            2) Company Comparison
            3) Executive Summary

            Keep claims grounded in the provided articles and call out uncertainty.
        """

        # No external tools: this agent is text-only reasoning.
        self.tools = {}

    def _tool_schemas(self) -> list[ToolUnionParam]:
        return []

    def _read_articles_from_memory(self) -> Any:
        if not self.memory:
            return None
        return self.memory.read(self.DEFAULT_ARTICLES_KEY)

    def _format_articles_for_prompt(self, articles: Any) -> str:
        if not articles:
            return "No articles found in shared memory."

        if isinstance(articles, str):
            return articles

        if isinstance(articles, list):
            lines: list[str] = []
            for idx, article in enumerate(articles, 1):
                if isinstance(article, dict):
                    title = article.get("title", "No title")
                    source = article.get("source", "Unknown")
                    summary = article.get("summary") or article.get("description") or ""
                    content = article.get("content") or ""
                    lines.append(
                        f"[{idx}] {title}\n"
                        f"Source: {source}\n"
                        f"Summary: {summary}\n"
                        f"Content: {content}"
                    )
                else:
                    lines.append(f"[{idx}] {str(article)}")
            return "\n\n".join(lines)

        return str(articles)

    def _build_analysis_task(self, task: str) -> str:
        articles = self._read_articles_from_memory()
        article_context = self._format_articles_for_prompt(articles)

        return (
            "Analyze the following article set.\n\n"
            f"User request: {task or 'Provide a standard analysis report.'}\n\n"
            "Articles:\n"
            f"{article_context}\n\n"
            "Required output format:\n"
            "Top 3 Trend Themes:\n"
            "- Theme 1\n"
            "- Theme 2\n"
            "- Theme 3\n\n"
            "Company Comparison:\n"
            "- Compare key companies mentioned across the articles.\n\n"
            "Executive Summary:\n"
            "- Provide a concise synthesis for leadership."
        )

    def run(self, task: str) -> Generator[dict, None, str]:
        analysis_task = self._build_analysis_task(task)
        final = yield from super().run(analysis_task)
        return final
