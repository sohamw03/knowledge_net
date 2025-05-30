import asyncio
import json
import logging
import os
import time
from collections import deque
from datetime import datetime
from textwrap import dedent
from typing import Any, Dict, List

from dotenv import load_dotenv
from google import genai
from google.genai import types

from research_node import ResearchNode
from scraper import CrawlForAIScraper

load_dotenv()

# Today's Date
DATE = datetime.now().strftime("%d %b, %Y")


class Prompt:
    def __init__(self) -> None:
        self.research_plan = dedent("""You are an expert Deep Research agent, part of a Multiagent system.

        <User query>
        {topic}
        </User query>

        ---
        Generate few very high level steps on which other agents can do info collection runs. Provide only data collection steps, no data identification, summarization, manipulation, selection, etc.
        Do not presume any knowledge about the topic.
        Return a string array of steps.""")

        self.site_summary = dedent("""Extract specific verbatim key information from the following content that is related to the topic "{query}". No small talk.
        <Findings>
        {findings}
        </Findings>
        """)

        self.continue_branch = dedent("""Given the current state of research, decide whether to continue exploring the current branch or not.
        <Global Research Plan>
        {research_plan}
        </Global Research Plan>

        Current Topic: {query}

        <Past Searched Queries>
        {past_queries}
        </Past Searched Queries>

        <Findings under current topic>
        {ctx_manager}
        </Findings under current topic>

        Consider:
        - Information saturation
        - Information duplication
        - Coverage of current topic
        - Potential for new insights

        Return only decision: true/false""")

        self.search_query = dedent("""Based on the following findings on topic {vertical}, create google search queries
        <Original user query>
        {topic}
        </Original user query>

        <Global Research Plan>
        {research_plan}
        </Global Research Plan>

        <Past Searched Queries>
        {past_queries}
        </Past Searched Queries>

        <Findings under current topic>
        {ctx_manager}
        </Findings under current topic>

        Suggest {n} specific google search queries that:
        - Covers what has not been covered yet
        - Builds upon these findings
        - Explores different aspects
        - Goes deeper into important details

        - Do not do quote searches
        - Queries should be generic and short
        - Do not presume any knowledge about the topic
        Return as JSON array of objects with properties:
        - query (string)""")

        self.report_outline = dedent("""Generate a outline for a report based on the findings:
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

        self.report_fillin = dedent("""Fill in the content for the current outline heading based on the findings:
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

        for prompt in [self.research_plan, self.site_summary, self.continue_branch, self.search_query]:
            prompt += f"\n\nFYI Date {DATE}"


class Schema:
    def __init__(self) -> None:
        self.research_plan = genai.types.Schema(
            type=genai.types.Type.OBJECT,
            required=["steps"],
            properties={"steps": genai.types.Schema(type=genai.types.Type.ARRAY, items=genai.types.Schema(type=genai.types.Type.STRING))},
        )

        self.continue_branch = genai.types.Schema(
            type=genai.types.Type.OBJECT,
            required=["decision"],
            properties={"decision": genai.types.Schema(type=genai.types.Type.BOOLEAN)},
        )

        self.search_query = genai.types.Schema(
            type=genai.types.Type.OBJECT,
            required=["branches"],
            properties={"branches": genai.types.Schema(type=genai.types.Type.ARRAY, items=genai.types.Schema(type=genai.types.Type.STRING))},
        )

        self.report_outline = genai.types.Schema(
            type=genai.types.Type.OBJECT,
            required=["title", "headings"],
            properties={
                "title": genai.types.Schema(type=genai.types.Type.STRING),
                "headings": genai.types.Schema(type=genai.types.Type.ARRAY, items=genai.types.Schema(type=genai.types.Type.STRING)),
            },
        )

        self.report_fillin = genai.types.Schema(
            type=genai.types.Type.OBJECT,
            required=["content"],
            properties={"content": genai.types.Schema(type=genai.types.Type.STRING)},
        )


class ResearchProgress:
    def __init__(self, callback, master_node: ResearchNode):
        self.progress = 0
        self.callback = callback
        self.master_node = master_node

    async def update(self, progress: int, message: str):
        self.progress = int(min(100, self.progress + progress))  # max 100
        await self.callback({"progress": self.progress, "message": message, "research_tree": self.master_node.build_tree_structure()})

    async def setter(self, progress: int, message: str):
        self.progress = int(min(100, progress))  # max 100
        await self.callback({"progress": self.progress, "message": message, "research_tree": self.master_node.build_tree_structure()})


class KNet:
    def __init__(self, scraper_instance: CrawlForAIScraper, max_depth: int = 1, num_sites_per_query: int = 5):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        assert self.api_key, "Google API key is required"
        self.scraper = scraper_instance
        self.logger = logging.getLogger(__name__)
        self.prompt = Prompt()
        self.schema = Schema()
        self.progress = None

        # Init Google GenAI client
        self.genai_client = genai.Client(api_key=self.api_key)

        # Parameters
        self.max_depth = max_depth
        self.num_sites_per_query = num_sites_per_query

        # Global State
        self.master_node = ResearchNode()
        self.research_plan: list[str] = []
        self.idx_research_plan: int = 0
        self.ctx_researcher: list[str] = []
        self.ctx_manager: list[str] = []
        self.token_count: int = 0

    async def conduct_research(self, topic: str, progress_callback, max_depth: int, num_sites_per_query: int) -> dict | bool:
        # Local Runtime State
        self.progress = ResearchProgress(progress_callback, self.master_node)
        self.max_depth = max_depth
        self.num_sites_per_query = num_sites_per_query

        # Reset global state
        self.research_plan = []
        self.idx_research_plan = 0
        self.ctx_researcher = []
        self.ctx_manager = []
        self.token_count = 0

        try:
            # Generate research plan
            await self.progress.update(0, "Generating research plan...")
            self._check_cancelled()

            self.research_plan = self.generate_content(self.prompt.research_plan.format(topic=topic), schema=self.schema.research_plan, temp=1.5)[
                "steps"
            ]
            self.logger.info(f"Research plan:\n{json.dumps(self.research_plan, indent=2)}")

            await self.progress.update(0, "Starting research...")

            # Iterate on research plan
            for self.idx_research_plan, _ in enumerate(self.research_plan):
                self._check_cancelled()

                # Generate initial search query
                query = self.generate_content(
                    self.prompt.search_query.format(
                        vertical=self.research_plan[self.idx_research_plan], topic=topic, research_plan="None", past_queries="None", ctx_manager="None", n=1
                    ),
                    schema=self.schema.search_query,
                    temp=1.5,
                )["branches"][0]

                root_node = ResearchNode(query)
                self.master_node.add_child(root_node.query, node=root_node)
                to_explore = deque([(root_node, 1)])  # (node, depth) pairs
                explored_queries = set()  # {string, string, ...}

                await self.progress.update(100 / (len(self.research_plan) + 1), f"{self.research_plan[self.idx_research_plan]}")

                while to_explore:
                    self._check_cancelled()

                    current_node, current_depth = to_explore.popleft()
                    if current_depth > self.max_depth:
                        continue

                    self.logger.info(f"Exploring: {current_node.query} (depth: {current_depth})")
                    await self.progress.update(0, f"s_{current_node.query}")

                    # Search and scrape
                    current_node.data = await self.scraper.search_and_scrape(
                        current_node.query, self.num_sites_per_query
                    )  # node -> data = [{url:...}, {url:...}, ...]
                    self.ctx_researcher.append(json.dumps(current_node.data, indent=2))
                    explored_queries.add(current_node.query)

                    # Only branch if we have data and haven't reached max depth
                    if self._should_continue_branch(current_node, topic):
                        if current_node.data and current_depth < self.max_depth:
                            new_branches = self._gen_queries(current_node, topic)
                            for branch in new_branches:
                                to_explore.appendleft((branch, current_depth + 1))

            self._check_cancelled()

            # Generate final report
            await self.progress.update(100 / (len(self.research_plan) + 1), "Generating final report...")
            final_report = await self._generate_final_report(topic)

            self.logger.info(f"Research completed. Explored {len(explored_queries)} queries across {self.master_node.max_depth()} levels")
            await self.progress.update(100, "Research complete!")

            with open("output.log.json", "w", encoding="utf-8") as f:
                json.dump(final_report, f, indent=2)
            return final_report

        except asyncio.CancelledError:
            self.logger.info(f"Research task for topic '{topic}' was cancelled")
            return {"status": False}
        except Exception:
            self.logger.error("Research failed", exc_info=True)
            raise

    async def _generate_final_report(self, topic: str, retry_count: int = 1) -> Dict[str, Any]:
        try:
            self._check_cancelled()

            await self.progress.setter(0, "Generating report...")
            findings = "\n\n------\n\n".join(self.ctx_manager)
            with open("ctx_manager.log.txt", "w", encoding="utf-8") as f:
                f.write(findings)

            # Generate report outline
            self._check_cancelled()
            outline = self.generate_content(self.prompt.report_outline.format(topic=topic, ctx_manager=findings), schema=self.schema.report_outline)
            self.logger.info(f"Report outline:\n{json.dumps(outline, indent=2)}")
            report = []
            raster_report = f"# {outline['title']}\n\n"

            # Fill in report outline
            for i, heading in enumerate(outline["headings"]):
                self._check_cancelled()

                await self.progress.update(100 / (len(outline["headings"]) + 1), "Generating report...")
                content = self.generate_content(
                    self.prompt.report_fillin.format(
                        topic=topic,
                        ctx_manager=findings,
                        report_progress=raster_report,
                        report_outline=["[done] " + outline["title"]] + [f"[done] {h}" for _, h in enumerate(outline["headings"]) if i < _],
                        slot=heading,
                    ),
                    schema=self.schema.report_fillin,
                )["content"]
                # Remove heading if LLM put it there regardless
                idx_heading = content.find(heading)
                if idx_heading != -1:
                    content = content[idx_heading + len(heading) :].strip()
                report.append({"heading": heading, "content": content})
                raster_report += f"\n\n## {heading}\n\n{content}"

            # Collate multimedia content
            media_content = {"images": [], "videos": [], "links": []}
            all_sources_data = self.master_node.get_all_data()
            for data in all_sources_data:
                if data.get("images"):
                    media_content["images"].extend(data["images"])
                if data.get("videos"):
                    media_content["videos"].extend(data["videos"])
                if data.get("links"):
                    media_content["links"].extend([{"url": link["href"], "text": link["text"]} for link in data["links"]])
            # Dedupe
            media_content["images"] = list(set(media_content["images"]))
            media_content["videos"] = list(set(media_content["videos"]))
            media_content["links"] = list({json.dumps(d, sort_keys=True) for d in media_content["links"]})
            media_content["links"] = [json.loads(d) for d in media_content["links"]]

            return {
                "topic": topic,
                "timestamp": datetime.now().isoformat(),
                "content": raster_report,
                "media": media_content,
                "research_tree": self.master_node.build_tree_structure(),
                "metadata": {
                    "total_queries": self.master_node.total_children(),
                    "total_sources": len(all_sources_data),
                    "max_depth_reached": self.master_node.max_depth(),
                    "total_tokens": self.token_count,
                },
            }

        except asyncio.CancelledError:
            raise
        except Exception as e:
            if e in ["GEMINI_RECITATION", "NO_RESPONSE"]:
                self.logger.error("GEMINI_RECITATION or NO_RESPONSE")
            if retry_count < 3:
                self.logger.error(f"Retrying final report:C:{retry_count} / 3", exc_info=True)
                return await self._generate_final_report(topic, retry_count + 1)
            self.logger.error("Error generating final report", exc_info=True)
            raise

    def _gen_queries(self, node: ResearchNode, topic: str, retry_count: int = 1) -> List[ResearchNode]:
        try:
            if not node.data or node.depth > self.max_depth:
                return []

            prompt = self.prompt.search_query.format(
                vertical=self.research_plan[self.idx_research_plan],
                topic=topic,
                research_plan="\n".join([f"[done] {step}" for i, step in enumerate(self.research_plan) if i < self.idx_research_plan]),
                past_queries="\n".join([f"[done] {query}" for query in node.get_path_to_root()[1:]]),
                ctx_manager="\n\n---\n\n".join(self.ctx_manager),
                n=1,
            )
            response = self.generate_content(prompt, schema=self.schema.search_query, temp=1.5)
            self.logger.info(f"Spawn branches '{node.query}':\n{json.dumps(response['branches'], indent=2)}")

            # Add children to current node
            #       |-> child
            # node -|-> child
            #       |-> child
            new_nodes = []
            for branch in response.get("branches", [])[:1]:
                child_node = node.add_child(branch)
                new_nodes.append(child_node)

            self.logger.info(f"Spawned {len(new_nodes)} new branch(es)")
            return new_nodes

        except Exception as e:
            if e in ["GEMINI_RECITATION", "NO_RESPONSE"]:
                self.logger.error("GEMINI_RECITATION or NO_RESPONSE")
            if retry_count < 3:
                self.logger.error(f"Retrying _gen_queries | C:{retry_count} / 3", exc_info=True)
                return self._gen_queries(node, topic, retry_count + 1)
            self.logger.error("_gen_queries failed", exc_info=True)
            raise

    def _should_continue_branch(self, node: ResearchNode, topic: str, retry_count: int = 1) -> bool:
        try:
            if node.depth > self.max_depth:
                return False

            # Generate summary of key findings into the manager's context
            if node.data:
                for idx in range(0, len(node.data), 3):
                    data = node.data[idx : idx + 3]
                    findings = ("\n" + "-" * 10 + "Next data" + "-" * 10 + "\n").join([json.dumps(d, indent=2) for d in data])
                    response = self.generate_content(self.prompt.site_summary.format(query=node.query, findings=findings), temp=0.2)
                    self.ctx_manager.append(response) if isinstance(response, str) else None

            # Research manager takes decision to proceed or not
            prompt = self.prompt.continue_branch.format(
                research_plan="\n".join([f"[done] {step}" for i, step in enumerate(self.research_plan) if i < self.idx_research_plan]),
                query=node.query,
                past_queries="\n".join([f"[done] {query}" for query in node.get_path_to_root()[1:]]),
                ctx_manager="\n\n---\n\n".join(self.ctx_manager),
            )
            response = self.generate_content(prompt, schema=self.schema.continue_branch)
            self.logger.info(f"Branch decision '{node.query}': {response['decision']}")

            return response["decision"]

        except Exception as e:
            if e in ["GEMINI_RECITATION", "NO_RESPONSE"]:
                self.logger.error("GEMINI_RECITATION or NO_RESPONSE")
            if retry_count < 3:
                self.logger.error(f"Retrying branch decision:C:{retry_count} / 3", exc_info=True)
                return self._should_continue_branch(node, topic, retry_count + 1)
            self.logger.error("Branch decision failed:", exc_info=True)
            raise

    def generate_content(self, prompt: str, schema: Dict[str, Any] = {}, temp: float = 1) -> Dict[str, Any] | str:
        safe = [
            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY, threshold=types.HarmBlockThreshold.BLOCK_NONE),
        ]
        if schema:
            generate_content_config = types.GenerateContentConfig(
                temperature=temp, response_mime_type="application/json", safety_settings=safe, response_schema=schema
            )
        else:
            generate_content_config = types.GenerateContentConfig(temperature=temp, response_mime_type="text/plain", safety_settings=safe)

        try:
            response = self.genai_client.models.generate_content(model="gemini-2.0-flash", contents=prompt, config=generate_content_config)
            if not response:
                raise Exception("NO_RESPONSE")

            self.token_count += response.usage_metadata.total_token_count
            return json.loads(response.text) if schema else response.text

        except Exception:
            if response.candidates[0].finish_reason == types.FinishReason.RECITATION:
                raise Exception("GEMINI_RECITATION")
            raise

    def _check_cancelled(self):
        """Check if the current task has been cancelled and raise CancelledError if so"""
        if asyncio.current_task() and asyncio.current_task().cancelled():
            raise asyncio.CancelledError("Research task was cancelled")

    async def test(self, topic: str, progress_callback):
        self.progress = ResearchProgress(progress_callback, self.master_node)
        try:
            for i in range(5):
                self._check_cancelled()

                await self.progress.setter(i * 10, f"Researching {topic} {i * 10}%")
                time.sleep(1)
                for j in range(5):
                    self._check_cancelled()

                    await self.progress.setter(i * 10, f"s_ example google search {str(j)}")
                    time.sleep(1)

            for i in range(10):
                self._check_cancelled()

                await self.progress.setter(i * 10, "Generating report...")
                time.sleep(1)

        except asyncio.CancelledError:
            self.logger.info(f"Test task for '{topic}' was cancelled")
            raise
