import logging
import os
from textwrap import dedent

from dotenv import load_dotenv
from langchain_core.messages.ai import AIMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command, interrupt

from tools_tools import continue_step, gen_report, search

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
load_dotenv()

checkpointer = MemorySaver()
tools = [search, continue_step]

model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=os.getenv("GOOGLE_API_KEY"))

# System message for the research agent
SYSTEM_MESSAGE = dedent(
    """You are KnowledgeNet, an expert deep research agent designed to help users gather comprehensive information on any topic.

    Your Operating Protocol:

    You operate as a state machine and MUST follow these steps in order. Do not mention the steps to the user.

    Step 1: Initial Exploration
    - Your first action is ALWAYS to call the search tool with a broad query to understand the topic.
    - After the tool returns, analyze the results and proceed to Step 2.

    Step 2: Analysis & Branching
    - State: "Currently in Step 2: Analysis & Branching."
    - Based on the results from Step 1, identify 2-3 key entities, questions, or claims.
    - Formulate and execute new, more specific search queries for each of these identified points. This step MUST involve multiple tool calls.
    - Once you have explored these branches, proceed to Step 3.

    Step 3: Verification & Synthesis
    - State: "Currently in Step 3: Verification & Synthesis."
    - Required: Call the continue_step tool so you can proceed with step 4.
    - Review all the information gathered from all previous steps.
    - If there are any unverified or conflicting claims, perform one final, targeted search to try and resolve them.
    - If all information is gathered, state that you are ready to generate the final report and do not call any more tools.

    Step 4: Final Report Generation
    - Once you have completed all research steps, generate the final report according to the specified structure. Do not generate this report until all other steps are complete.

    5.  **Structured Final Report:** For your final answer, provide a comprehensive report structured with the following headings:
        - **Detailed Findings:** A detailed, point-by-point breakdown of the information discovered.
        - **Supporting Evidence:** Use specific data points, timelines, direct quotes, and version numbers where available. Cite your sources clearly.
        - **Conclusion:** A final conclusion that directly answers the user's query or explains why it cannot be answered. After presenting the technical facts, you MUST provide a single, clear, and actionable recommendation for the user.
    6. **Disambiguation:** If a search result appears to be about a different topic with the same name (e.g., 'UV' for spectroscopy vs. 'uv' for a package manager), you must explicitly state that you are discarding it as irrelevant and refine your subsequent search queries to be more specific (e.g., search for "uv package manager" instead of just "uv").

    Suggested Research Avenues (Check multiple types):
    - Official websites, blogs, and product documentation for authoritative information.
    - Academic databases (e.g., Google Scholar, ArXiv) for scholarly articles.
    - Developer forums and communities (e.g., Reddit, Stack Overflow, Hacker News) for user discussions and practical insights.
    - Official GitHub repositories (check Issues, Pull Requests, and Discussions) for project updates and roadmap discussions.
    - Recent news articles and press releases for current updates.
    - Social media (e.g., Twitter/X) for real-time announcements from official accounts or key developers.
    - Government and institutional reports for reliable grey literature."""
)

agent = create_react_agent(
    model=model,
    tools=tools,
    checkpointer=checkpointer,
    prompt=SYSTEM_MESSAGE,
)


async def invoke_agent(message: str, thread_id: str, idx_retry: int = 1, create_report: bool = False):
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}

    async for event in agent.astream({"messages": [{"role": "user", "content": message}]}, config=config):
        print(event)

        if "agent" in event:
            response = [
                {"type": "ai_msg", "content": m.content, "total_tokens": m.usage_metadata["total_tokens"], "tool_calls": m.tool_calls}
                for m in event["agent"]["messages"]
            ]
            if not event["agent"]["messages"][0].additional_kwargs:
                history = [f"{m.type}:\n{m.content}" for m in agent.get_state({"configurable": {"thread_id": "1234"}}).values["messages"]]
                response = [
                    {
                        "type": "ai_msg_report",
                        "content": gen_report("\n\n".join(history), message),
                        "total_tokens": m.usage_metadata["total_tokens"],
                        "tool_calls": m.tool_calls,
                    }
                    for m in event["agent"]["messages"]
                ]

        elif "tools" in event:
            response = [{"type": "tool_resp", "content": m.content} for m in event["tools"]["messages"]]
        yield response
