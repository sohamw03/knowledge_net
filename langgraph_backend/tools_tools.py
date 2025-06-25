import asyncio
import os
from datetime import datetime
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

from prompts import REPORT_FILLIN_PROMPT, REPORT_OUTLINE_PROMPT, SITE_SUMMARY_PROMPT_V3
from schema import ReportFillin, ReportOutline
from scraper import CrawlForAIScraper

load_dotenv()
scraper_inst = CrawlForAIScraper()
model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite", google_api_key=os.getenv("GOOGLE_API_KEY"))


@tool
async def search(query: str) -> str:
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

    return "\n\n---\n\n".join(summ_sites_ctx) + "\n\nPlease call the search tool to get more information."


def gen_report(findings: str, topic: str):
    # Generate report outline
    outline = model.with_structured_output(ReportOutline).invoke(REPORT_OUTLINE_PROMPT.format(topic=topic, ctx_manager=findings))
    report = []
    raster_report = f"# {outline['title']}\n\n"

    # Fill in report outline
    for i, heading in enumerate(outline["headings"]):
        content = model.with_structured_output(ReportFillin).invoke(
            REPORT_FILLIN_PROMPT.format(
                topic=topic,
                ctx_manager=findings,
                report_progress=raster_report,
                report_outline=["[done] " + outline["title"]] + [f"[done] {h}" for _, h in enumerate(outline["headings"]) if i < _],
                slot=heading,
            ),
        )["content"]
        # Remove heading if LLM put it there regardless
        idx_heading = content.find(heading)
        if idx_heading != -1:
            content = content[idx_heading + len(heading) :].strip()
        report.append({"heading": heading, "content": content})
        raster_report += f"\n\n## {heading}\n\n{content}"

    return {
        "topic": topic,
        "timestamp": datetime.now().isoformat(),
        "content": raster_report,
        "metadata": {},
    }
