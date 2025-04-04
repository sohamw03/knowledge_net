import json
import logging
import os
from collections import deque
from datetime import datetime
from textwrap import dedent
from typing import Any, Dict, List

from dotenv import load_dotenv
from google import genai
from google.genai import types

from research_node import ResearchNode
from scraper import CrawlForAIScraper

# Load environment variables
load_dotenv()


class Prompt:
    def __init__(self) -> None:
        self.continue_branch = dedent("""Given the current research context and findings, should we explore this branch deeper?

        Current Topic: {query}
        Current Depth: {depth}
        Path from Root: {path}
        Key Findings:
        {findings}

        Consider:
        1. Relevance to main topic
        2. Potential for new insights
        3. Depth vs breadth tradeoff
        4. Information saturation

        Return only: decision: true/false""")

        self.search_query = dedent("""Based on the following findings about "{topic}", suggest new research directions.
        Findings:
        {ctx_manager}

        Suggest up to {n} specific google search queries that would help data which:
        - Builds upon these findings
        - Explores different aspects
        - Goes deeper into important details

        Return as JSON array of objects with properties:
        - query (string)""")


class Schema:
    def __init__(self) -> None:
        self.continue_branch = genai.types.Schema(
            type=genai.types.Type.OBJECT,
            required=["decision"],
            properties={
                "decision": genai.types.Schema(type=genai.types.Type.BOOLEAN),
            },
        )

        self.search_query = genai.types.Schema(
            type=genai.types.Type.OBJECT,
            required=["branches"],
            properties={
                "branches": genai.types.Schema(
                    type=genai.types.Type.ARRAY,
                    items=genai.types.Schema(
                        type=genai.types.Type.OBJECT,
                        required=["query"],
                        properties={
                            "query": genai.types.Schema(type=genai.types.Type.STRING),
                        },
                    ),
                )
            },
        )


class ResearchProgress:
    def __init__(self, callback):
        self.progress = 0
        self.callback = callback

    async def update(self, progress: int, message: str):
        self.progress += progress
        if self.progress > 100:
            self.progress = 100
        if self.callback:
            await self.callback({"progress": self.progress, "message": message})


class KNet:
    def __init__(self, scraper_instance: CrawlForAIScraper, max_depth: int = 1, max_breadth: int = 1, num_sites_per_query: int = 5):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        assert self.api_key, "Google API key is required"
        self.scraper = scraper_instance
        self.logger = logging.getLogger(__name__)
        self.prompt = Prompt()
        self.schema = Schema()

        # Init Google GenAI client
        self.genai_client = genai.Client(api_key=self.api_key)

        # Parameters
        self.max_depth = max_depth
        self.max_breadth = max_breadth
        self.num_sites_per_query = num_sites_per_query

        # Global State
        self.ctx_researcher: list[str] = []
        self.ctx_manager: list[str] = []
        self.token_count: int = 0

    async def conduct_research(self, topic: str, progress_callback, max_depth: int, max_breadth: int, num_sites_per_query: int) -> dict:
        # Local Runtime State
        progress = ResearchProgress(progress_callback)
        self.max_depth = max_depth
        self.max_breadth = max_breadth
        self.num_sites_per_query = num_sites_per_query

        # Reset global state
        self.ctx_researcher = []
        self.ctx_manager = []
        self.token_count = 0

        try:
            # Generate initial search query
            query = self.generate_content(
                self.prompt.search_query.format(topic=topic, ctx_manager=json.dumps(self.ctx_manager, indent=2), n=1),
                schema=self.schema.search_query,
            )
            root_node = ResearchNode(query.get("branches")[0]["query"])
            to_explore = deque([(root_node, 0)])  # (node, depth) pairs
            explored_queries = set()  # {string, string, ...}

            await progress.update(5, "Starting research...")

            while to_explore:
                current_node, current_depth = to_explore.popleft()

                if current_node.query in explored_queries or current_depth > self.max_depth:
                    continue

                self.logger.info(f"Exploring: {current_node.query} (Depth: {current_depth})")
                await progress.update(5, f"Exploring: {current_node.query}")

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
                            to_explore.append((branch, current_depth + 1))

            # Generate final report
            await progress.update(30, "Generating comprehensive report...")
            final_report = self._generate_final_report(root_node)

            self.logger.info(f"Research completed. Explored {len(explored_queries)} queries across {root_node.max_depth()} levels")
            await progress.update(100, "Research complete!")

            with open("output.json", "a", encoding="utf-8") as f:
                json.dump(final_report, f, indent=2)
            return final_report

        except Exception:
            self.logger.error("Research failed", exc_info=True)
            raise

    def _generate_final_report(self, root_node: ResearchNode, retry_count: int = 1) -> Dict[str, Any]:
        try:
            findings = "\n".join(self.ctx_manager)
            with open("output.json", "w", encoding="utf-8") as f:
                f.write(findings)
            prompt = f"""Generate a comprehensive report on the topic "{root_node.query}" based on the following research findings:
            {findings}
            """
            response = self.generate_content(prompt)

            # Collate multimedia content
            media_content = {"images": [], "videos": [], "links": [], "references": []}
            all_sources_data = root_node.get_all_data()
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

            # Build research tree structure
            def build_tree_structure(node: ResearchNode) -> Dict:
                if not node:
                    return {}

                sources = [d["url"] for d in node.data if d.get("url")]
                return {
                    "query": node.query,
                    "depth": node.depth,
                    "sources": sources,
                    "children": [build_tree_structure(child) for child in node.children],
                }

            return {
                "topic": root_node.query,
                "timestamp": datetime.now().isoformat(),
                "content": response,
                "media": media_content,
                "research_tree": build_tree_structure(root_node),
                "metadata": {
                    "total_queries": root_node.total_children(),
                    "total_sources": len(all_sources_data),
                    "max_depth_reached": root_node.max_depth(),
                    "total_tokens": self.token_count,
                },
            }

        except Exception as e:
            if e in ["GEMINI_RECITATION", "NO_RESPONSE"] and retry_count < 3:
                self.logger.error(f"Retrying final report:C:{retry_count / 3}", exc_info=True)
                self._generate_final_report(root_node, retry_count + 1)
            self.logger.error("Error generating final report", exc_info=True)
            raise

    def _gen_queries(self, node: ResearchNode, topic: str, retry_count: int = 1) -> List[ResearchNode]:
        try:
            if not node.data or node.depth > self.max_depth:
                return []

            prompt = self.prompt.search_query.format(
                topic=topic,
                ctx_manager=json.dumps(self.ctx_manager, indent=2),
                n=self.max_breadth,
            )
            response = self.generate_content(prompt, schema=self.schema.search_query)
            self.logger.info(f"Spawn branches '{node.query}':\n{json.dumps(response['branches'], indent=2)}")

            # Add children to current node
            #       |-> child
            # node -|-> child
            #       |-> child
            new_nodes = []
            for branch in response.get("branches", []):
                child_node = node.add_child(branch["query"])
                new_nodes.append(child_node)

            self.logger.info(f"Spawned {len(new_nodes)} new branch(es)")
            return new_nodes

        except Exception as e:
            if e in ["GEMINI_RECITATION", "NO_RESPONSE"] and retry_count < 3:
                self.logger.error(f"Retrying _gen_queries | C:{retry_count / 3}", exc_info=True)
                self._gen_queries(node, topic, retry_count + 1)
            self.logger.error("_gen_queries failed", exc_info=True)
            raise

    def _should_continue_branch(self, node: ResearchNode, topic: str, retry_count: int = 1) -> bool:
        try:
            if node.depth > self.max_depth:
                return False

            # Generate summary of key findings into the manager's context
            if node.data:
                findings = ("\n" + "-" * 10 + "Next data" + "-" * 10 + "\n").join([json.dumps(d, indent=2) for d in node.data])
                response = self.generate_content(f"Extract key findings from the following data related to the topic '{topic}':\n{findings}")
                self.ctx_manager.append(response)

            # Research manager takes decision to proceed or not
            prompt = self.prompt.continue_branch.format(
                query=node.query,
                depth=node.depth,
                path=" -> ".join(node.get_path_to_root()),
                findings="\n".join(self.ctx_manager),
            )
            response = self.generate_content(prompt, schema=self.schema.continue_branch)
            self.logger.info(f"Branch decision '{node.query}': {response['decision']}")

            return response["decision"]

        except Exception as e:
            if e in ["GEMINI_RECITATION", "NO_RESPONSE"] and retry_count < 3:
                self.logger.error(f"Retrying branch decision:C:{retry_count / 3}", exc_info=True)
                self._should_continue_branch(node, topic, retry_count + 1)
            self.logger.error("Branch decision failed:", exc_info=True)
            raise

    def generate_content(self, prompt: str, schema: Dict[str, Any] = {}) -> Dict[str, Any] | str:
        safe = [
            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_CIVIC_INTEGRITY, threshold=types.HarmBlockThreshold.BLOCK_NONE),
        ]
        if schema:
            generate_content_config = types.GenerateContentConfig(
                temperature=0.9, response_mime_type="application/json", safety_settings=safe, response_schema=schema
            )
        else:
            generate_content_config = types.GenerateContentConfig(temperature=0.9, response_mime_type="text/plain", safety_settings=safe)

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
