"""HTTP client for the Israeli news aggregator API."""

import httpx

from config import NEWS_API_URL


async def fetch_news(source: str | None = None, category: str | None = None) -> dict:
    """Fetch news articles from the aggregator API."""
    if source:
        url = f"{NEWS_API_URL}/api/news/source/{source}"
    elif category:
        url = f"{NEWS_API_URL}/api/news/category/{category}"
    else:
        url = f"{NEWS_API_URL}/api/news"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


async def fetch_sources() -> list[dict]:
    """Fetch available news sources."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{NEWS_API_URL}/api/sources")
        resp.raise_for_status()
        return resp.json()
