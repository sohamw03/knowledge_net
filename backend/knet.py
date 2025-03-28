import json
import logging
import os
from collections import deque
from datetime import datetime
from textwrap import dedent
from typing import Any, Dict, List

import google.generativeai as genai
from dotenv import load_dotenv
from google.ai.generativelanguage_v1beta.types import content

from research_node import ResearchNode


# Load environment variables
load_dotenv()


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
    def __init__(self, scraper_instance, max_depth: int = 1, max_breadth: int = 1, num_sites_per_query: int = 5):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        assert self.api_key, "Google API key is required"

        # Initialize Google GenAI
        genai.configure(api_key=self.api_key)

        # Keep both models with original configurations
        generation_config = {"temperature": 0.9}
        safe = [
            {
                "category": "HARM_CATEGORY_DANGEROUS",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE",
            },
        ]
        self.llm = genai.GenerativeModel(
            "gemini-2.0-flash-lite-preview-02-05",
            generation_config=generation_config,
            safety_settings=safe,
        )
        self.ctx_researcher = []

        self.research_manager = genai.GenerativeModel(
            "gemini-2.0-flash-lite-preview-02-05",
            generation_config=generation_config,
            safety_settings=safe,
        )
        self.ctx_manager = []

        # Initialize scraper
        self.scraper = scraper_instance

        self.logger = logging.getLogger(__name__)
        self.max_depth = max_depth
        self.max_breadth = max_breadth
        self.num_sites_per_query = num_sites_per_query

        self.search_prompt = """Generate 3-5 specific search queries to research the following topic: {topic}

        Requirements:
        1. Queries should cover different aspects of the topic
        2. Be specific and technical
        3. Include key terms and concepts
        4. Format each query on a new line
        5. Return only the queries, no explanations"""

        self.token_count = 0
        self.branch_decision_prompt = """Given the current research context and findings, should we explore this branch deeper?

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

        Return only: decision: true/false"""

        # Simplified decision schema for branching
        self.branch_schema = {
            "response_schema": content.Schema(
                type=content.Type.OBJECT,
                required=["decision"],
                properties={
                    "decision": content.Schema(type=content.Type.BOOLEAN),
                },
            ),
            "response_mime_type": "application/json",
        }

        # Analysis schema
        self.analysis_schema = {
            "response_schema": content.Schema(
                type=content.Type.OBJECT,
                required=["branches"],
                properties={
                    "branches": content.Schema(
                        type=content.Type.ARRAY,
                        items=content.Schema(
                            type=content.Type.OBJECT,
                            required=["importance", "query"],
                            properties={
                                "importance": content.Schema(type=content.Type.NUMBER),
                                "query": content.Schema(type=content.Type.STRING),
                            },
                        ),
                    )
                },
            ),
            "response_mime_type": "application/json",
        }

    def _track_tokens(self, tokens: int) -> None:
        self.token_count += tokens

    def _should_branch_deeper(self, node: ResearchNode, topic: str, retry_count: int = 0) -> bool:
        try:
            if node.depth > self.max_depth:
                return False

            # Generate summary of key findings into research_manager's context
            if node.data:
                findings = ("\n" + "-" * 10 + "Next data" + "-" * 10 + "\n").join([json.dumps(d, indent=2) for d in node.data])
                response = self.llm.generate_content(
                    f"Extract key findings from the following data related to the topic '{topic}':\n{findings}"
                )
                self._track_tokens(response.usage_metadata.total_token_count)
                findings = response.text
                self.ctx_manager.append(findings)

            # Research manager takes decision to proceed or not
            prompt = self.branch_decision_prompt.format(
                query=node.query,
                depth=node.depth,
                path=" -> ".join(node.get_path_to_root()),
                findings="\n".join(self.ctx_manager),
            )
            response = self.research_manager.generate_content(prompt, generation_config={**self.branch_schema})
            self._track_tokens(response.usage_metadata.total_token_count)
            result = json.loads(response.text)
            self.logger.info(f"Branch decision for '{node.query}': {result['decision']}")

            return result["decision"]
        except Exception as e:
            if result["candidates"][0]["finishReason"] == "RECITATION":
                self.logger.error(f"Retrying branch decision: {str(e)}\nC:{retry_count/3}")
                self._should_branch_deeper(node, topic, retry_count + 1)
            self.logger.error(f"Branch decision failed: {str(e)}")
            raise e

    async def conduct_research(
        self, topic: str, progress_callback, max_depth: int, max_breadth: int, num_sites_per_query: int
    ) -> Dict[str, Any]:
        self.max_depth = max_depth
        self.max_breadth = max_breadth
        self.num_sites_per_query = num_sites_per_query

        self.ctx_researcher = []
        self.ctx_manager = []
        self.token_count = 0
        progress = ResearchProgress(progress_callback)
        self.logger.info(f"Starting research on topic: {topic}")

        try:
            root_node = ResearchNode(topic)
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
                if current_node.data and current_depth < self.max_depth:
                    if self._should_branch_deeper(current_node, topic):
                        new_branches = self._analyze_and_branch(current_node, topic)
                        for branch in new_branches:
                            to_explore.append((branch, current_depth + 1))
                        self.logger.info(f"Added {len(new_branches)} new branch(es) at depth {current_depth + 1}")

            # Generate final report
            await progress.update(30, "Generating comprehensive report...")
            final_report = self._generate_final_report(root_node)

            self.logger.info(f"Research completed. Explored {len(explored_queries)} queries across {root_node.max_depth()} levels")
            await progress.update(100, "Research complete!")

            with open("output.json", "a", encoding="utf-8") as f:
                json.dump(final_report, f, indent=2)
            return final_report

        except Exception as e:
            self.logger.error(f"Research failed: {str(e)}")
            raise e

    def _analyze_and_branch(self, node: ResearchNode, topic: str, retry_count: int = 0) -> List[ResearchNode]:
        try:
            if not node.data or node.depth > self.max_depth:
                return []

            analysis_prompt = dedent(
                f"""Based on the following findings about "{topic}", suggest new research directions.
            Findings:
            {json.dumps(self.ctx_manager, indent=2)}

            Suggest up to {self.max_breadth} specific google search queries that would help data which:
            - Builds upon these findings
            - Explores different aspects
            - Goes deeper into important details

            Return as JSON array of objects with properties:
            - query (string)"""
            )

            response = self.research_manager.generate_content(analysis_prompt, generation_config={**self.analysis_schema})
            self._track_tokens(response.usage_metadata.total_token_count)
            result = json.loads(response.text)
            self.logger.info(f"New branches for '{node.query}': {result['branches']}")

            # Add children to current node
            #        +> child1
            # node - +> child2
            #        +> child3
            new_nodes = []
            for branch in result.get("branches", []):
                child_node = node.add_child(branch["query"])
                new_nodes.append(child_node)
            return new_nodes

        except Exception as e:
            if result["candidates"][0]["finishReason"] == "RECITATION" and retry_count <= 3:
                self.logger.error(f"Retrying analysis: {str(e)}\nC:{retry_count/3}")
                self._analyze_and_branch(node, topic, retry_count + 1)
            self.logger.error(f"Branch analysis failed: {str(e)}")
            raise e

    def _generate_final_report(self, root_node: ResearchNode, retry_count: int = 0) -> Dict[str, Any]:
        try:
            findings = "\n".join(self.ctx_manager)
            with open("output.json", "w") as f:
                f.write(findings)
            prompt = f"""Generate a comprehensive report on the topic "{root_node.query}" based on the following research findings:
            {findings}
            """
            response = self.research_manager.generate_content(prompt)
            self._track_tokens(response.usage_metadata.total_token_count)

            # Collate multimedia content
            media_content = {"images": [], "videos": [], "links": [], "references": []}
            all_sources_data = root_node.get_all_data()
            for data in all_sources_data:
                if data.get("images"):
                    media_content["images"].extend(data["images"])
                if data.get("videos"):
                    media_content["videos"].extend(data["videos"])
                if data.get("links"):
                    media_content["links"].extend([{"url": l["href"], "text": l["text"]} for l in data["links"]])
            # Deduplicate
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
                "content": response.text,
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
            if response["candidates"][0]["finishReason"] == "RECITATION":
                self.logger.error(f"Retrying final report: {str(e)}\nC:{retry_count/3}")
                self._generate_final_report(root_node, retry_count + 1)
            self.logger.error(f"Error generating final report: {str(e)}")
            raise e
