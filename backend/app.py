import json
import logging
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
CORS_ALLOWED_ORIGINS = [
    "*",
    "https://knowledge-net.vercel.app",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sio = socketio.AsyncServer(cors_allowed_origins=CORS_ALLOWED_ORIGINS, ping_timeout=60, ping_interval=10, async_mode="asgi")
app.mount("/", socketio.ASGIApp(sio))


class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, tuple[KNet, CrawlForAIScraper]] = {}

    async def get_or_create_session(self, sid: str) -> tuple[KNet, CrawlForAIScraper]:
        if sid not in self.sessions:
            scraper = CrawlForAIScraper()
            await scraper.start()
            knet = KNet(scraper)
            self.sessions[sid] = (knet, scraper)
        return self.sessions[sid]

    async def cleanup_session(self, sid: str):
        if sid in self.sessions:
            _, scraper = self.sessions[sid]
            await scraper.close()
            del self.sessions[sid]


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
    knet, scraper = await session_manager.get_or_create_session(sid)

    try:
        data = json.loads(data) if type(data) != dict else data
        topic = data.get("topic")
        session_id = sid
        logger.info(f"Starting research for client {session_id} on topic: {topic}")

        async def progress_callback(status):
            try:
                logger.debug(f"Progress update: {status['progress']}% - {status['message']}")
                await sio.emit(
                    "status",
                    {"message": status["message"], "progress": status["progress"]},
                    room=session_id,
                )
            except Exception as e:
                logger.error(f"Error in progress callback: {str(e)}")
                raise e

        research_results = await knet.conduct_research(topic, progress_callback)
        logger.info(f"Research completed for topic: {topic}")
        await sio.emit("research_complete", research_results, room=session_id)

    except Exception as e:
        logger.error(f"Research error: {str(e)}")
        await sio.emit("error", {"message": str(e)}, room=session_id)


@sio.event
async def test(sid, data):
    knet, scraper = await session_manager.get_or_create_session(sid)
    print("Testing...")
    data = json.loads(data) if type(data) != dict else data
    res = await knet.scraper._scrape_page(data["url"])
    print(json.dumps(res, indent=2))
    await sio.emit("test", res, room=sid)


if __name__ == "__main__":
    logger.info("Starting KnowledgeNet server...")
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5000)
