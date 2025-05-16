import asyncio
import copy
import json
import logging
import os
from datetime import datetime
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.config import get_stream_writer
from langgraph.graph import END, StateGraph
from langgraph.types import Command, StreamWriter
from sse_starlette.sse import EventSourceResponse

from prompts import (
    CONTINUE_BRANCH_PROMPT,
    RESEARCH_PLAN_PROMPT,
    SEARCH_QUERY_PROMPT,
    SITE_SUMMARY_PROMPT,
)
from research_node import ResearchNode
from schema import ContinueBranch, ResearchPlan, SearchQuery
from scraper import CrawlForAIScraper

load_dotenv()

# Today's Date
DATE = datetime.now().strftime("%d %b, %Y")

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


class ResearchProgress:
    def __init__(self, master_node: ResearchNode):
        self.progress = 0
        self.master_node = master_node

    def send(self, writer: StreamWriter, progress: int, message: dict, ptype: str):
        if ptype == "update":
            self.progress = int(min(100, progress))  # max 100
            writer({"event": "progress", "data": {"progress": self.progress, **message, "research_tree": self.master_node.build_tree_structure()}})
        elif ptype == "setter":
            self.progress = int(min(100, self.progress + progress))  # max 100
            writer({"event": "progress", "data": {"progress": self.progress, **message, "research_tree": self.master_node.build_tree_structure()}})
        elif ptype == "result":
            self.progress = 100
            writer({"event": "result", "data": message})


# --- State schema for LangGraph ---
class ResearchState(TypedDict, total=False):
    scraper: CrawlForAIScraper
    progress: ResearchProgress

    # Paramters
    topic: str
    max_depth: int
    num_sites_per_query: int

    # Global State
    master_node: ResearchNode
    current_node: ResearchNode
    research_plan: list[str]
    idx_research_plan: int
    ctx_researcher: list[str]
    ctx_manager: list[str]
    raster_report: str
    token_count: int


async def research_plan_node(state: ResearchState) -> ResearchPlan:
    writer = get_stream_writer()

    if state["idx_research_plan"] == 0:
        topic = state["topic"]
        plan = llm.with_structured_output(ResearchPlan).invoke(RESEARCH_PLAN_PROMPT.format(topic=topic), config={"temperature": 1.5})
        if "steps" in plan:
            steps = plan["steps"]

        logger.info(f"Research plan:\n{json.dumps(steps, indent=2)}")
        state["progress"].send(writer, 0, {"message": "Starting research..."}, ptype="setter")

        return {"research_plan": steps}
    else:
        # TODO: Update the plan based on current information
        return dict()


async def scrape_node(state: ResearchState) -> ResearchState:
    writer = get_stream_writer()

    # Generate initial search query if first step
    # TODO: Add a condition based on 1st iter or successive iters
    # TODO: Wrap inference in backend.knet.generate_content
    if state["idx_research_plan"] == 0:
        query = (
            llm.with_structured_output(SearchQuery)
            .invoke(
                SEARCH_QUERY_PROMPT.format(
                    vertical=state["research_plan"][state["idx_research_plan"]],
                    topic=state["topic"],
                    research_plan="None",
                    past_queries="None",
                    ctx_manager="None",
                    n=1,
                ),
                config={"temperature": 1.5},
            )
            .get("branches", [""])[0]
        )
        new_master = copy.deepcopy(state["master_node"])
        curr_node = ResearchNode(query)
        new_master.add_child(curr_node.query, node=curr_node)
    else:
        # TODO: Manage the Research Tree like above
        query = (
            llm.with_structured_output(SearchQuery)
            .invoke(
                SEARCH_QUERY_PROMPT.format(
                    vertical=state["research_plan"][state["idx_research_plan"]],
                    topic=state["topic"],
                    research_plan="\n".join([f"[done] {step}" for i, step in enumerate(state["research_plan"]) if i < state["idx_research_plan"]]),
                    past_queries="\n".join([f"[done] {query}" for query in state["current_node"].get_path_to_root()[1:]]),
                    ctx_manager="\n\n---\n\n".join(state["ctx_manager"]),
                    n=1,
                ),
                config={"temperature": 1.5},
            )
            .get("branches", [""])[0]
        )

    # Update progress
    state["progress"].send(
        writer, 100 / (len(state["research_plan"]) + 1), {"message": f"{state['research_plan'][state['idx_research_plan']]}"}, ptype="update"
    )

    # Search and scrape
    data = await state["scraper"].search_and_scrape(query, state["num_sites_per_query"])  # node -> data = [{url:...}, {url:...}, ...]
    # Add data to context
    # src [1] : https://...
    # content...
    upd_ctx_researcher = state["ctx_researcher"] + ["\n\n---\n\n".join([f"src [{i + 1}] : {d['url']}\n{d['text']}" for i, d in enumerate(data)])]
    return {"ctx_researcher": upd_ctx_researcher, "master_node": new_master, "current_node": curr_node}


async def summarize_node(state: ResearchState) -> ResearchState:
    # Generate summary of key findings into the manager's context
    upd_ctx_manager = state["ctx_manager"]
    if state["current_node"].data:
        for idx in range(0, len(state["current_node"].data), 3):
            data = state["current_node"].data[idx : idx + 3]
            findings = ("\n" + "-" * 10 + "Next data" + "-" * 10 + "\n").join([json.dumps(d, indent=2) for d in data])
            summary = llm.invoke(SITE_SUMMARY_PROMPT.format(query=state["current_node"].query, findings=findings), config={"temperature": 0.2})
            upd_ctx_manager.append(summary) if isinstance(summary, str) else None
    return {"ctx_manager": upd_ctx_manager}


async def should_continue(state: ResearchState) -> Command[Literal["plan", "scrape", "gen_report"]]:
    # If max depth is reached and we are at the last step of the research plan, generate report
    if state["current_node"].depth > state["max_depth"] and state["idx_research_plan"] >= len(state["research_plan"]) - 1:
        logger.info(f"Branch decision '{state['current_node'].query}': False")
        return Command(goto="gen_report")

    # If max depth is reached and we are not at the last step of the research plan, continue with the next step
    elif state["current_node"].depth > state["max_depth"] and state["idx_research_plan"] < len(state["research_plan"]) - 1:
        logger.info(f"Branch decision '{state['current_node'].query}': False")
        return Command(goto="plan", update={"idx_research_plan": state["idx_research_plan"] + 1})

    # If we have not reached max depth and not on last step of the research plan, continue with the next step
    decision = llm.with_structured_output(ContinueBranch).invoke(
        CONTINUE_BRANCH_PROMPT.format(
            research_plan="\n".join([f"[done] {step}" for i, step in enumerate(state["research_plan"]) if i < state["idx_research_plan"]]),
            query=state["current_node"].query,
            past_queries="\n".join([f"[done] {query}" for query in state["current_node"].get_path_to_root()[1:]]),
            ctx_manager="\n\n---\n\n".join(state["ctx_manager"]),
        )
    )
    logger.info(f"Branch decision '{state['current_node'].query}': {decision['decision']}")
    return Command(goto="scrape") if decision["decision"] else Command(goto="plan", update={"idx_research_plan": state["idx_research_plan"] + 1})


async def gen_report_node(state: ResearchState) -> ResearchState:
    return


# --- Main research logic using LangGraph ---
async def start_research_workflow(topic: str, scraper: CrawlForAIScraper, max_depth: int, num_sites_per_query: int):
    # Build the research graph
    graph = StateGraph(state_schema=ResearchState)
    graph.add_node("plan", research_plan_node)
    graph.add_node("scrape", scrape_node)
    graph.add_node("summarize_node", summarize_node)
    graph.add_node("should_continue", should_continue)
    graph.add_node("gen_report", gen_report_node)

    graph.add_edge("plan", "scrape")
    graph.add_edge("scrape", "summarize_node")
    graph.add_edge("summarize_node", "should_continue")
    graph.add_edge("gen_report", END)
    graph.set_entry_point("plan")
    graph = graph.compile()
    print(graph.get_graph().draw_mermaid())

    master_node = ResearchNode()
    state: ResearchState = {
        "scraper": scraper,
        "progress": ResearchProgress(master_node),
        "topic": topic,
        "max_depth": max_depth,
        "num_sites_per_query": num_sites_per_query,
        "master_node": master_node,
        "research_plan": [],
        "idx_research_plan": 0,
        "ctx_researcher": [],
        "ctx_manager": [],
        "raster_report": "",
        "token_count": 0,
    }
    async for update in graph.astream(state, stream_mode="custom"):
        yield update


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
        async for event in start_research_workflow(topic, scraper, max_depth, num_sites_per_query):
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
