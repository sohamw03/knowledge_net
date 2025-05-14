import asyncio
import json
import logging
import os
from datetime import datetime
from textwrap import dedent
from typing import Any, Dict, List, Optional, TypedDict

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph
from sse_starlette.sse import EventSourceResponse

from schema import ResearchPlan
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


# --- Prompt templates ---
RESEARCH_PLAN_PROMPT = dedent("""You are an expert Deep Research agent, part of a Multiagent system.

<User query>
{topic}
</User query>

---
Generate few very high level steps on which other agents can do info collection runs. Provide only data collection steps, no data identification, summarization, manipulation, selection, etc.
Do not presume any knowledge about the topic.
Return a string array of steps.""")

REPORT_OUTLINE_PROMPT = dedent("""Generate a outline for a report based on the findings:
<Original user query>
{topic}
</Original user query>

<Findings>
{ctx_manager}
</Findings>

Deduplicate, reorganize and analyze the findings to create the outline.
If there are multiple comparisons, use a table instead of multiple headings.
The outline should include:
- Title
- List of h2 headings
Do not include hashtags""")

REPORT_FILLIN_PROMPT = dedent("""Fill in the content for the current outline heading based on the findings:
<Findings>
{ctx_manager}
</Findings>

<The outline>
{report_outline}
</The outline>

<Current outline heading to fill in>
## {slot}
...
</Current outline heading to fill in>

Assume [done] headings have their respective content.
The content should be comprehensive, detailed and well-structured, providing detailed information on current heading.
If needed use tables, lists. Do not include subheadings.
Do not include the heading in the content.
""")

# --- LangChain LLM setup (Gemini, correct usage) ---
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=os.getenv("GOOGLE_API_KEY"))


# --- State schema for LangGraph ---
class ResearchState(TypedDict, total=False):
    topic: str
    scraper: Any
    max_depth: int
    num_sites_per_query: int
    steps: List[str]
    findings: Any
    outline: str
    progress: int
    message: str
    timestamp: str
    content: str
    media: dict
    research_tree: dict
    metadata: dict


# --- LangGraph node: LLM step for research plan ---
async def research_plan_node(state: dict) -> dict:
    topic = state["topic"]
    prompt = RESEARCH_PLAN_PROMPT.format(topic=topic)
    result = await llm.with_structured_output(ResearchPlan).ainvoke(prompt)
    try:
        steps = json.loads(result.content) if hasattr(result, "content") else json.loads(str(result))
        # TODO: split this module another knet module to handle global state
    except Exception:
        steps = [str(result)]
    logger.info(f"Research plan:\n{json.dumps(steps, indent=2)}")
    return {"progress": 10, "message": "Generated research plan"}


# --- LangGraph node: Scrape for each step ---
async def scrape_node(state: dict) -> dict:
    steps = state["steps"]
    scraper = state["scraper"]
    num_sites_per_query = state["num_sites_per_query"]
    findings = []
    for idx, step in enumerate(steps):
        scraped = await scraper.search_and_scrape(step, num_sites=num_sites_per_query)
        findings.append({"step": step, "data": scraped})
    return {"findings": findings, "progress": 70, "message": "Scraping complete"}


# --- LangGraph node: Generate report outline ---
async def outline_node(state: dict) -> dict:
    topic = state["topic"]
    findings = state["findings"]
    findings_text = json.dumps(findings, indent=2)
    prompt = REPORT_OUTLINE_PROMPT.format(topic=topic, findings=findings_text)
    result = await llm.ainvoke(prompt)
    outline = result.content if hasattr(result, "content") else str(result)
    return {"outline": outline, "progress": 90, "message": "Generated report outline"}


# --- LangGraph node: Fill in report content for each heading ---
async def fillin_node(state: dict) -> dict:
    findings = state["findings"]
    outline = state["outline"]
    topic = state["topic"]
    # Try to parse outline as JSON, else fallback to text splitting
    try:
        outline_obj = json.loads(outline)
        title = outline_obj["title"]
        headings = outline_obj["headings"]
    except Exception:
        # Fallback: try to extract headings from text
        lines = outline.splitlines()
        title = lines[0].strip("# ") if lines else topic
        headings = [line.strip("# ") for line in lines if line.strip().startswith("## ")]
    findings_text = json.dumps(findings, indent=2)
    report = f"# {title}\n\n"
    for idx, heading in enumerate(headings):
        prompt = REPORT_FILLIN_PROMPT.format(
            findings=findings_text,
            outline=outline,
            slot=heading,
        )
        result = await llm.ainvoke(prompt)
        content = result.content if hasattr(result, "content") else str(result)
        # Remove heading if LLM included it
        if content.strip().startswith(heading):
            content = content.strip()[len(heading) :].strip()
        report += f"\n\n## {heading}\n\n{content}\n"
    return {"content": report, "progress": 95, "message": "Filled in report content"}


# --- LangGraph node: Finalize report ---
def finalize_node(state: dict) -> dict:
    findings = state.get("findings", [])
    media = {"images": [], "videos": [], "links": []}
    for step in findings:
        for site in step.get("data", []):
            media["images"].extend(site.get("images", []))
            media["videos"].extend(site.get("videos", []))
            media["links"].extend(site.get("links", []))
    # Dedupe
    media["images"] = list(set(media["images"]))
    media["videos"] = list(set(media["videos"]))
    # Links: dedupe by URL
    seen_links = set()
    deduped_links = []
    for link in media["links"]:
        url = link["href"] if isinstance(link, dict) and "href" in link else str(link)
        if url not in seen_links:
            seen_links.add(url)
            deduped_links.append(link)
    media["links"] = deduped_links
    return {
        "topic": state["topic"],
        "timestamp": datetime.now().isoformat(),
        "content": state["content"],
        "media": media,
        "research_tree": {},
        "metadata": {"steps": state.get("steps", [])},
        "progress": 100,
        "message": "Research complete!",
    }


# --- Main research logic using LangGraph ---
async def run_research(topic, scraper, max_depth, num_sites_per_query):
    # Build the research graph
    graph = StateGraph(state_schema=ResearchState)
    graph.add_node("plan", research_plan_node)
    graph.add_node("scrape", scrape_node)
    graph.add_node("outline_node", outline_node)
    graph.add_node("fillin", fillin_node)
    graph.add_node("finalize", finalize_node)

    graph.add_edge("plan", "scrape")
    graph.add_edge("scrape", "outline_node")
    graph.add_edge("outline_node", "fillin")
    graph.add_edge("fillin", "finalize")
    graph.add_edge("finalize", END)
    graph.set_entry_point("plan")
    graph = graph.compile()

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
