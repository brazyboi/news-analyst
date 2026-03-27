from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse

from orchestrator import orchestrate_news_analysis


app = FastAPI()


@app.get("/stream")
async def stream(
    query: str = Query(..., description="News topic/query to analyze"),
    days_back: int = Query(7, ge=1, le=30),
    limit: int = Query(5, ge=1, le=10),
) -> StreamingResponse:
    generator = orchestrate_news_analysis(
        query=query,
        days_back=days_back,
        limit=limit,
    )
    return StreamingResponse(generator, media_type="text/event-stream")
