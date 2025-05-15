import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph
from sse_starlette.sse import EventSourceResponse

from prompts import RESEARCH_PLAN_PROMPT, SEARCH_QUERY_PROMPT
from schema import ResearchPlan, SearchQuery
from scraper import CrawlForAIScraper

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI()
CORS_ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", ",").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session management (in-memory for now)
sessions: Dict[str, Dict[str, Any]] = {}


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# --- LangChain LLM setup (Gemini, correct usage) ---
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=os.getenv("GOOGLE_API_KEY"))


# --- State schema for LangGraph ---
class ResearchState(TypedDict, total=False):
    topic: str

    research_plan: list[str]
    idx_research_plan: int
    ctx_researcher: list[str]
    ctx_manager: list[str]
    token_count: int

    scraper: CrawlForAIScraper
    max_depth: int
    num_sites_per_query: int


async def research_plan_node(state: ResearchState) -> ResearchPlan:
    topic = state["topic"]
    plan = await llm.with_structured_output(ResearchPlan).ainvoke(RESEARCH_PLAN_PROMPT.format(topic=topic), temperature=1.5)
    if hasattr(plan, "steps"):
        steps = plan["steps"]
    logger.info(f"Research plan:\n{json.dumps(steps, indent=2)}")
    return steps


async def scrape_node(state: ResearchState) -> ResearchState:
    topic = state["topic"]
    scraper = state["scraper"]
    max_depth = state["max_depth"]
    num_sites_per_query = state["num_sites_per_query"]

    # Generate initial search query
    query = llm.with_structured_output(SearchQuery).invoke(
        SEARCH_QUERY_PROMPT.format(
            vertical=state["research_plan"][state["idx_research_plan"]], topic=topic, research_plan="None", past_queries="None", ctx_manager="None", n=1
        ),
        temperature=1.5,
    )

    # Search and scrape
    data = await state["scraper"].search_and_scrape(
        query, num_sites_per_query
    )  # node -> data = [{url:...}, {url:...}, ...]
    state["ctx_researcher"].append(json.dumps(data, indent=2))
    pass
    # TODO: Implement the scraping logic and update the state with the scraped data


# --- Main research logic using LangGraph ---
async def run_research(topic, scraper, max_depth, num_sites_per_query):
    # Build the research graph
    graph = StateGraph(state_schema=ResearchState)
    graph.add_node("plan", research_plan_node)
    graph.add_node("scrape", scrape_node)
    graph.add_node("gen_report", gen_report_node)

    graph.add_edge("plan", "scrape")
    graph.add_edge("scrape", "conditional", "plan", "gen_report")
    graph.add_edge("gen_report", END)
    graph.set_entry_point("plan")
    graph = graph.compile()
    print(graph.get_graph().draw_mermaid())

    state = {
        "topic": topic,
        "scraper": scraper,
        "max_depth": max_depth,
        "num_sites_per_query": num_sites_per_query,
    }
    async for step in graph.astream(state):
        progress = step.get("progress", 0)
        message = step.get("message", "")
        yield {
            "event": "status",
            "data": json.dumps({"progress": progress, "message": message}),
        }
    yield {
        "event": "research_complete",
        "data": json.dumps(
            {
                "topic": step["topic"],
                "timestamp": step["timestamp"],
                "content": step["content"],
                "media": step["media"],
                "research_tree": step["research_tree"],
                "metadata": step["metadata"],
            }
        ),
    }


@app.post("/start_research")
async def start_research(request: Request):
    data = await request.json()
    topic = data.get("topic", "").strip()
    max_depth = int(data.get("max_depth", 1))
    num_sites_per_query = int(data.get("num_sites_per_query", 5))
    session_id = data.get("session_id") or os.urandom(8).hex()

    if session_id not in sessions:
        scraper = CrawlForAIScraper()
        await scraper.start()
        sessions[session_id] = {"scraper": scraper}
    else:
        scraper = sessions[session_id]["scraper"]

    async def event_generator():
        async for event in run_research(topic, scraper, max_depth, num_sites_per_query):
            yield event

    return EventSourceResponse(event_generator())


@app.post("/abort_research")
async def abort_research(request: Request):
    data = await request.json()
    session_id = data.get("session_id")
    if session_id in sessions:
        scraper = sessions[session_id]["scraper"]
        await scraper.close()
        del sessions[session_id]
    return {"status": "aborted"}


# Add more endpoints as needed for test, etc.

if __name__ == "__main__":
    logger.info("Starting KnowledgeNet server...")
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5000)
