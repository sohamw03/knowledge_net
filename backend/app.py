# pip install flask[async] flask-socketio flask-cors
# pip install google-genai beautifulsoup4 selenium newspaper3k lxml_html_clean eventlet
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import os, json, logging
from knet import KNet
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
knet = KNet()

app = Flask(__name__)
CORS(app)

# Increased pingTimeout and added logger
socketio = SocketIO(app, cors_allowed_origins="*", ping_timeout=9999, ping_interval=25)


@socketio.on("connect")
def handle_connect():
    logger.info(f"Client connected: {request.sid}")


@socketio.on("disconnect")
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")


@socketio.on("health_check")
def handle_health_check(_):
    logger.debug("Health check received")
    emit("health_check", {"status": "ok"})


@socketio.on("start_research")
def handle_research(data):
    try:
        data = json.loads(data)
        topic = data.get("topic")
        session_id = request.sid
        logger.info(f"Starting research for client {session_id} on topic: {topic}")

        def progress_callback(status):
            try:
                logger.debug(
                    f"Progress update: {status['progress']}% - {status['message']}"
                )
                socketio.emit(
                    "status",
                    {"message": status["message"], "progress": status["progress"]},
                    room=session_id,
                )
            except Exception as e:
                logger.error(f"Error in progress callback: {str(e)}")

        try:
            research_results = knet.conduct_research(topic, progress_callback)
            logger.info(f"Research completed for topic: {topic}")
            socketio.emit("research_complete", research_results, room=session_id)
        except Exception as e:
            logger.error(f"Research error: {str(e)}")
            socketio.emit("error", {"message": str(e)}, room=session_id)

    except Exception as e:
        logger.error(f"Error handling research request: {str(e)}")
        socketio.emit("error", {"message": str(e)}, room=request.sid)


if __name__ == "__main__":
    logger.info("Starting KnowledgeNet server...")
    socketio.run(app, debug=True, port=5000)
