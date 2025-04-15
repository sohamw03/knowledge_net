import asyncio
import json
import logging
import os
import time
from typing import Dict

import socketio
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from knet import KNet
from scraper import CrawlForAIScraper, WebScraper

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
CORS_ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", ",").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sio = socketio.AsyncServer(
    cors_allowed_origins=CORS_ALLOWED_ORIGINS,
    ping_timeout=1200,
    ping_interval=10,
    async_mode="asgi",
)
app.mount("/", socketio.ASGIApp(sio))


class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, tuple[KNet, CrawlForAIScraper]] = {}
        self.tasks: Dict[str, asyncio.Task] = {}  # Track research tasks for each session

    async def get_or_create_session(self, sid: str) -> tuple[KNet, CrawlForAIScraper]:
        if sid not in self.sessions:
            scraper = CrawlForAIScraper()
            await scraper.start()
            knet = KNet(scraper)
            self.sessions[sid] = (knet, scraper)
        return self.sessions[sid]

    async def cleanup_session(self, sid: str):
        # Cancel running task if it exists
        if sid in self.tasks and not self.tasks[sid].done():
            self.tasks[sid].cancel()
            try:
                await self.tasks[sid]
            except asyncio.CancelledError:
                logger.info(f"Research task for session {sid} was cancelled")
            except Exception as e:
                logger.error(f"Error while cancelling task for {sid}: {str(e)}")
            finally:
                del self.tasks[sid]

        # Clean up session resources
        if sid in self.sessions:
            _, scraper = self.sessions[sid]
            await scraper.close()
            del self.sessions[sid]

    def register_task(self, sid: str, task: asyncio.Task):
        self.tasks[sid] = task


session_manager = SessionManager()


@sio.event
async def connect(sid, environ, auth):
    logger.info(f"Client connected: {sid}")
    await session_manager.get_or_create_session(sid)


@sio.event
async def disconnect(sid, reason):
    logger.info(f"Client disconnected: {sid}")
    await session_manager.cleanup_session(sid)


@sio.event
async def health_check(sid, data):
    logger.debug("Health check received")
    await sio.emit("health_check", {"status": "ok"}, room=sid)


@sio.event
async def start_research(sid, data):
    try:
        data = json.loads(data) if type(data) is not dict else data
        topic = data.get("topic").strip()
        max_depth: int = data.get("max_depth")
        num_sites_per_query: int = data.get("num_sites_per_query")

        knet, _ = await session_manager.get_or_create_session(sid)

        session_id = sid
        logger.info(f"Starting research for client {session_id}.\nTopic '{topic}'")

        async def progress_callback(status: dict):
            await sio.emit("status", status, room=session_id)

        task = asyncio.create_task(knet.conduct_research(topic, progress_callback, max_depth, num_sites_per_query))
        session_manager.register_task(sid, task)
        research_results = await task

        if not research_results:
            sio.emit("research_aborted", room=session_id)

        logger.info(f"Research completed for topic: {topic}")
        await sio.emit("research_complete", research_results, room=session_id)

    except Exception as e:
        logger.error(f"Research error: {str(e)}")
        await sio.emit("error", {"message": str(e)}, room=session_id)


@sio.event
async def abort_research(sid):
    logger.info(f"Aborting research for client {sid}")
    await session_manager.cleanup_session(sid)


@sio.event
async def test(sid, data):
    data = json.loads(data) if type(data) is not dict else data
    topic = data.get("topic").strip().replace("\n", "")
    logger.info(json.dumps(data, indent=2))

    knet, _ = await session_manager.get_or_create_session(sid)
    time.sleep(1)

    async def progress_callback(status: dict):
        await sio.emit("status", status, room=sid)

    # Create a task and register it for proper cancellation
    task = asyncio.create_task(knet.test(topic, progress_callback))
    session_manager.register_task(sid, task)

    try:
        await task

        with open("output.log.json", "r") as f:
            data = json.load(f)
        await sio.emit("research_complete", data, room=sid)
    except asyncio.CancelledError:
        logger.info(f"Test task for '{topic}' was cancelled")
        await sio.emit("research_aborted", room=sid)
    except Exception as e:
        logger.error(f"Test error: {str(e)}")
        await sio.emit("error", {"message": str(e)}, room=sid)


if __name__ == "__main__":
    logger.info("Starting KnowledgeNet server...")
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5000)
