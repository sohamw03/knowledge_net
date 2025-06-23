import json
import logging
import os
from datetime import datetime
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from agent_tools import invoke_agent

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


@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    message = data.get("message")
    thread_id = data.get("thread_id")
    create_report = data.get("create_report", False)

    async def event_generator():
        async for event in invoke_agent(message, thread_id, create_report):
            # Format the event as SSE (Server-Sent Events)
            event_data = json.dumps(event)
            yield f"data: {event_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        },
    )


@app.post("/abort")
async def abort(request: Request):
    data = await request.json()
    session_id = data.get("session_id")
    if session_id in sessions:
        scraper = sessions[session_id]["scraper"]
        await scraper.close()
        del sessions[session_id]
    return {"status": "aborted"}


if __name__ == "__main__":
    logger.info("Starting KnowledgeNet server...")
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5000)
