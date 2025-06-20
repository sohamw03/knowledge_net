import asyncio
import os
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

from prompts import SITE_SUMMARY_PROMPT
from scraper import CrawlForAIScraper

load_dotenv()
scraper_inst = CrawlForAIScraper()
model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=os.getenv("GOOGLE_API_KEY"))


@tool
def calc(a: int, b: int) -> int:
    """
    Takes in two integers and returns their integer sum.
    """
    return str(a + b)


@tool
async def scrape(query: str, num_sites_per_query: int) -> List[Dict[str, Any]]:
    """
    Search in a search engine.

    Args:
        query: string query for the search engine.
        num_sites_per_query: number of sites to read after searching.

    Returns:
        Results related to the search.
    """
    sites = await scraper_inst.search_and_scrape(query, num_sites_per_query)
    # Add data to context
    # src [1] : https://...
    # content...
    agg_sites_ctx = ["\n\n---\n\n".join([f"src [{i + 1}] : {d['url']}\n{d['text']}" for i, d in enumerate(sites)])]
    summ_sites_ctx = []
    for idx in range(0, len(sites), 3):
        summary = model.invoke(SITE_SUMMARY_PROMPT.format(query=query, findings=agg_sites_ctx), config={"temperature": 0.2}).text()
        summ_sites_ctx.append(summary)

    return "\n\n---\n\n".join(summ_sites_ctx)
