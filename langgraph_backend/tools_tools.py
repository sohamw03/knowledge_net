import asyncio
import os
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

from prompts import SITE_SUMMARY_PROMPT_V3
from scraper import CrawlForAIScraper

load_dotenv()
scraper_inst = CrawlForAIScraper()
model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite", google_api_key=os.getenv("GOOGLE_API_KEY"))


@tool
async def search(query: str) -> List[Dict[str, Any]]:
    """
    Search in a search engine.
    Always call this tool if there is any knowledge gap in performing the task.

    Args:
        query: string query for the search engine.

    Returns:
        Results related to the search.
    """
    sites = await scraper_inst.search_and_scrape(query, 5)
    # Add data to context
    # src [1] : https://...
    # content...
    agg_sites_ctx = ["\n\n---\n\n".join([f"src [{i + 1}] : {d['url']}\n{d['text']}" for i, d in enumerate(sites)])]
    summ_sites_ctx = []
    for idx in range(0, len(sites), 3):
        summary = model.invoke(SITE_SUMMARY_PROMPT_V3.format(query=query, findings=agg_sites_ctx), config={"temperature": 0.5}).text()
        summ_sites_ctx.append(summary)

    return "\n\n---\n\n".join(summ_sites_ctx)
