from typing import Dict, List, Optional, Any
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
import logging
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from scraper import WebScraper
from research_node import ResearchNode
from collections import deque

# Load environment variables
load_dotenv()


class ResearchProgress:
    def __init__(self, callback=None):
        self.progress = 0
        self.callback = callback

    def update(self, progress: int, message: str):
        self.progress = progress
        if self.callback:
            self.callback({"progress": progress, "message": message})


class KNet:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key is required")

        # Initialize Google GenAI
        genai.configure(api_key=self.api_key)

        # Keep both models with original configurations
        self.llm = genai.GenerativeModel(
            "gemini-2.0-flash-lite-preview-02-05",
            generation_config={"temperature": 0.7},
        )

        self.research_manager = genai.GenerativeModel(
            "gemini-2.0-flash-lite-preview-02-05",
            generation_config={"temperature": 0.3},
        )

        # Initialize scraper
        self.scraper = WebScraper()
        self.logger = logging.getLogger(__name__)
        self.max_depth = 3
        self.min_importance_score = 0.6

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
        Key Findings: {findings}

        Consider:
        1. Relevance to main topic
        2. Potential for new insights
        3. Depth vs breadth tradeoff
        4. Information saturation

        Return only: {"decision": true/false}"""

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

        # Analysis schema without reason
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

    def __del__(self):
        # Cleanup scraper when KNet instance is destroyed
        if hasattr(self, "scraper"):
            self.scraper.cleanup()

    def _track_tokens(self, tokens: int) -> None:
        self.token_count += tokens

    def _should_branch_deeper(self, node: ResearchNode) -> bool:
        findings = ""
        if node.data:
            findings = "\n".join(
                [
                    f"- {d.get('title', 'Untitled')}: {d.get('summary', '')}"
                    for d in node.data[:3]
                    if d
                ]
            )

        prompt = self.branch_decision_prompt.format(
            query=node.query,
            depth=node.depth,
            path=" -> ".join(node.get_path_to_root()),
            findings=findings,
        )

        response = self.research_manager.generate_content(
            prompt, generation_config={**self.branch_schema}
        )
        self._track_tokens(response.usage_metadata.total_token_count)

        result = json.loads(response.text)
        self.logger.info(f"Branch decision for '{node.query}': {result['decision']}")

        return result["decision"]

    def conduct_research(self, topic: str, progress_callback=None) -> Dict[str, Any]:
        self.token_count = 0
        progress = ResearchProgress(progress_callback)
        self.logger.info(f"Starting research on topic: {topic}")

        try:
            self.scraper.setup()
            root_node = ResearchNode(topic)
            to_explore = deque([(root_node, 0)])  # (node, depth) pairs
            explored_queries = set()
            max_branches = self.max_depth * 3

            progress.update(10, "Starting research...")

            while to_explore and len(explored_queries) < max_branches:
                current_node, current_depth = to_explore.popleft()

                if current_node.query in explored_queries or current_depth >= self.max_depth:
                    continue

                self.logger.info(f"Exploring: {current_node.query} (Depth: {current_depth})")
                progress.update(
                    30 + (len(explored_queries) * 50 / max_branches),
                    f"Exploring: {current_node.query}",
                )

                # Search and scrape
                current_node.data = self.scraper.search_and_scrape(current_node.query)
                explored_queries.add(current_node.query)

                # Only branch if we have data and haven't reached max depth
                if current_node.data and current_depth < self.max_depth:
                    if self._should_branch_deeper(current_node):
                        new_branches = self._analyze_and_branch(current_node)
                        for branch in new_branches:
                            to_explore.append((branch, current_depth + 1))
                        self.logger.info(
                            f"Added {len(new_branches)} new branches at depth {current_depth + 1}"
                        )

            # Generate final report
            progress.update(80, "Generating comprehensive report...")
            final_report = self._generate_final_report(root_node)
            final_report["metadata"]["total_tokens"] = self.token_count

            self.logger.info(
                f"Research completed. Explored {len(explored_queries)} queries across {root_node.depth + 1} levels"
            )
            progress.update(100, "Research complete!")

            return final_report

        except Exception as e:
            self.logger.error(f"Research failed: {str(e)}")
            raise e
        finally:
            self.scraper.cleanup()

    def _analyze_and_branch(self, node: ResearchNode) -> List[ResearchNode]:
        if not node.data:
            return []

        findings = "\n".join([
            f"- {d.get('title', 'Untitled')}: {d.get('summary', d.get('text', '')[:200])}"
            for d in node.data[:3] if d
        ])

        analysis_prompt = f"""Based on the following findings about "{node.query}", suggest new research directions.

        Findings:
        {findings}

        Suggest up to 3 specific research queries that:
        1. Build upon these findings
        2. Explore different aspects
        3. Go deeper into important details

        Return as JSON array of objects with only:
        - importance (0.0-1.0)
        - query (string)"""

        try:
            response = self.research_manager.generate_content(
                analysis_prompt,
                generation_config={**self.analysis_schema},
            )
            self._track_tokens(response.usage_metadata.total_token_count)

            result = json.loads(response.text)
            self.logger.info(f"New branches for '{node.query}': {result['branches']}")

            new_nodes = []
            for branch in result.get("branches", []):
                if branch["importance"] >= self.min_importance_score:
                    child_node = node.add_child(branch["query"])
                    child_node.importance_score = branch["importance"]
                    new_nodes.append(child_node)

            return new_nodes

        except Exception as e:
            self.logger.error(f"Branch analysis failed: {str(e)}")
            return []

    def _generate_final_report(self, root_node: ResearchNode) -> Dict[str, Any]:
        def collect_data(node: ResearchNode) -> List[Dict]:
            all_data = []
            if node.data:
                all_data.extend(node.data)
            for child in node.children:
                all_data.extend(collect_data(child))
            return all_data

        all_research_data = collect_data(root_node)

        # Generate part 1 of the report
        part1_prompt = f"""Generate part 1 of a research report focusing on overview and key findings.
        Main Topic: {root_node.query}

        Structure for Part 1:
        1. Executive Summary (brief overview)
        2. Key Findings (main discoveries and insights)

        Keep it concise and focused. Part 2 will cover detailed analysis and references."""

        response1 = self.research_manager.generate_content(part1_prompt)
        self._track_tokens(response1.usage_metadata.total_token_count)
        part1_content = response1.text

        # Generate part 2 with awareness of part 1
        part2_prompt = f"""Generate part 2 of the research report. Here's part 1 for context:

        {part1_content}

        Now continue with:
        1. Detailed Analysis (expand on the key findings)
        2. Related Topics and Branches (explore connections)
        3. Sources and References (cite sources)

        Focus on details that complement part 1 without repeating the same information."""

        response2 = self.research_manager.generate_content(part2_prompt)
        self._track_tokens(response2.usage_metadata.total_token_count)

        # Combine reports with clear section separation
        report_content = f"""# Research Report: {root_node.query}

Part 1: Overview and Key Findings
--------------------------------
{part1_content}

Part 2: Detailed Analysis and References
--------------------------------------
{response2.text}"""

        # Organize multimedia content
        media_content = {"images": [], "videos": [], "links": [], "references": []}

        for data in all_research_data:
            if data.get("images"):
                media_content["images"].extend(data["images"])
            if data.get("videos"):
                media_content["videos"].extend(data["videos"])
            if data.get("links"):
                media_content["links"].append(
                    {
                        "url": data["url"],
                        "title": data.get("title", ""),
                        "summary": data.get("summary", ""),
                    }
                )

        # Build research tree structure
        def build_tree_structure(node: ResearchNode) -> Dict:
            return {
                "query": node.query,
                "importance": node.importance_score,
                "depth": node.depth,
                "children": [build_tree_structure(child) for child in node.children],
            }

        return {
            "topic": root_node.query,
            "timestamp": datetime.now().isoformat(),
            "content": report_content,
            "media": media_content,
            "research_tree": build_tree_structure(root_node),
            "metadata": {
                "total_sources": len(all_research_data),
                "max_depth_reached": root_node.depth,
                "total_branches": len(root_node.children),
                "total_tokens": self.token_count,
            },
        }
