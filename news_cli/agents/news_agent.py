from datetime import datetime, timedelta, timezone
import os

import httpx
from anthropic.types import ToolUnionParam

from .base import BaseAgent

class NewsAgent(BaseAgent):
    def __init__(self, client, memory=None):
        super().__init__(name="news_agent", client=client, memory=memory)

        self.system_prompt = """
            You are a tech news research agent. 
            Find recent, relevant technology news and summarize clearly. 
            Prefer the most recent credible sources.
        """

        self.tools = {
            "search_news": self.search_news,
        }

    def search_news(self, query: str, days_back: int = 7, limit: int = 5) -> str:
        api_key = os.getenv("NEWS_API_KEY")
        if not api_key:
            return "No API key found for NewsAPI (NEWS_API_KEY)"

        now_utc = datetime.now(timezone.utc)
        from_date = (now_utc - timedelta(days=days_back)).strftime("%Y-%m-%d")

        params = {
            "apiKey": api_key,
            "q": query,
            "from": from_date,
            "to": now_utc.strftime("%Y-%m-%d"),
            "sortBy": "relevancy",
            "pageSize": limit,
        }

        try:
            response = httpx.get("https://newsapi.org/v2/everything", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            return f"There was an error during search: {str(exc)}"

        articles = data.get("articles", None)
        if not articles:
            return f"No articles found for query: '{query}'."

        formatted = []
        for i, article in enumerate(articles, 1):
            formatted.append(
                f"[{i}] {article.get('title', 'No title')}\n"
                f"    Source: {article.get('source', {}).get('name', 'Unknown')}\n"
                f"    Date:   {article.get('publishedAt', 'Unknown')[:10]}\n"
                f"    URL:    {article.get('url', '')}\n"
                f"    Summary: {article.get('description', 'No description')}\n"
            )

        return "\n".join(formatted)


    def _tool_schemas(self) -> list[ToolUnionParam]:
        return [
            {
                "name": "search_news", 
                "description": "Search for recent tech news articles.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search keywords"},
                        "days_back": {"type": "integer", "minimum": 1, "maximum": 30},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 10},
                    },
                    "required": ["query"],
                },
            }
        ]
