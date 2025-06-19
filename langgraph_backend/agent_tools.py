import logging
import os

from dotenv import load_dotenv
from langchain_core.messages.ai import AIMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command, interrupt

from tools_tools import calc

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
load_dotenv()

checkpointer = MemorySaver()
tools = [calc]

# --- LangChain LLM setup (Gemini, correct usage) ---
model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=os.getenv("GOOGLE_API_KEY"))
agent = create_react_agent(
    model=model,
    tools=tools,
    checkpointer=checkpointer,
)

# Usage example
config = {"configurable": {"thread_id": "research_session_1"}}


async def invoke_agent(message: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}

    async for event in agent.astream({"messages": [{"role": "user", "content": message}]}, config=config):
        print(event)
        if "agent" in event:
            response = [
                {"type": "ai_msg", "content": m.content, "total_tokens": m.usage_metadata["total_tokens"], "tool_calls": m.tool_calls}
                for m in event["agent"]["messages"]
            ]
        elif "tools" in event:
            response = [{"type": "tool_resp", "content": m.content} for m in event["tools"]["messages"]]
        yield response
