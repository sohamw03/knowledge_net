# pip install asyncio eventlet
# pip install google-genai beautifulsoup4 selenium newspaper3k lxml_html_clean
from fastapi import FastAPI
import socketio
import json, logging
from knet import KNet
from scraper import CrawlForAIScraper, WebScraper
from dotenv import load_dotenv
load_dotenv()
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
# Increased pingTimeout and added logger
sio = socketio.AsyncServer(cors_allowed_origins="*", ping_timeout=60, ping_interval=10, async_mode="asgi")
app.mount('/', socketio.ASGIApp(sio))

# Initialize the scraper and KNet
scraper_instance = CrawlForAIScraper()
# scraper_instance = WebScraper()
knet = KNet(scraper_instance)


@sio.event
def connect(sid, environ, auth):
    logger.info(f"Client connected: {sid}")


@sio.event
def disconnect(sid, reason):
    logger.info(f"Client disconnected: {sid}")


@sio.event
async def health_check(sid, data):
    logger.debug("Health check received")
    await sio.emit("health_check", {"status": "ok"}, room=sid)


@sio.event
async def start_research(sid, data):
    try:
        data = json.loads(data)
        topic = data.get("topic")
        session_id = sid
        logger.info(f"Starting research for client {session_id} on topic: {topic}")

        async def progress_callback(status):
            try:
                logger.debug(f"Progress update: {status['progress']}% - {status['message']}")
                await sio.emit("status", {"message": status["message"], "progress": status["progress"]}, room=session_id)
            except Exception as e:
                logger.error(f"Error in progress callback: {str(e)}")
                raise e

        try:
            research_results = await knet.conduct_research(topic, progress_callback)
            logger.info(f"Research completed for topic: {topic}")
            await sio.emit("research_complete", research_results, room=session_id)
        except Exception as e:
            logger.error(f"Research error: {str(e)}")
            await sio.emit("error", {"message": str(e)}, room=session_id)
            raise e

    except Exception as e:
        logger.error(f"Error handling research request: {str(e)}")
        await sio.emit("error", {"message": str(e)}, room=sid)
        raise e


@sio.event
async def test(sid, data):
    print("Testing...")
    data = json.loads(data)
    res = await knet.scraper._scrape_page(data["url"])
    print(json.dumps(res, indent=2))
    await scraper_instance.close()
    await sio.emit("test", res, room=sid)

if __name__ == "__main__":
    logger.info("Starting KnowledgeNet server...")
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=5000)
