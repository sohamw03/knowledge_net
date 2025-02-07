from typing import Dict, List, Optional, Any
import google.generativeai as genai
import logging
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
        self.max_depth = 5
        self.min_importance_score = 0.6

        self.search_prompt = """Generate 3-5 specific search queries to research the following topic: {topic}

        Requirements:
        1. Queries should cover different aspects of the topic
        2. Be specific and technical
        3. Include key terms and concepts
        4. Format each query on a new line
        5. Return only the queries, no explanations"""

    def __del__(self):
        # Cleanup scraper when KNet instance is destroyed
        if hasattr(self, "scraper"):
            self.scraper.cleanup()

    def conduct_research(self, topic: str, progress_callback=None) -> Dict[str, Any]:
        progress = ResearchProgress(progress_callback)
        self.logger.info(f"Starting research on topic: {topic}")
        try:
            # Setup aiohttp session at start of research
            self.scraper.setup()
            root_node = ResearchNode(topic)
            research_stack = deque([root_node])
            explored_queries = set()

            # Generate initial search queries
            self.logger.info("Generating search queries...")
            response = self.llm.generate_content(self.search_prompt.format(topic=topic))
            search_queries = response.text.strip().split("\n")
            self.logger.info(f"Generated queries: {search_queries}")

            progress.update(10, "Starting deep research exploration...")
            self.logger.info("Research exploration initiated")

            # Process each generated query
            for query in search_queries:
                if query.strip():
                    data = self.scraper.search_and_scrape(query.strip())
                    if data:
                        root_node.data.extend(data)

            while research_stack:
                current_node = research_stack.pop()

                if (
                    current_node.query in explored_queries
                    or current_node.depth > self.max_depth
                ):
                    continue

                self.logger.info(
                    f"Exploring branch: {current_node.query} (Depth: {current_node.depth})"
                )
                progress.update(
                    30 + (len(explored_queries) * 50 / (self.max_depth * 3)),
                    f"Exploring: {current_node.query}",
                )

                # Conduct research for current node
                current_node.data = self.scraper.search_and_scrape(current_node.query)
                explored_queries.add(current_node.query)

                # Generate and evaluate new branches
                if current_node.depth < self.max_depth:
                    new_branches = self._analyze_and_branch(current_node)
                    for branch in reversed(
                        new_branches
                    ):  # Reverse to maintain DFS order
                        research_stack.append(branch)

            self.logger.info("Generating final research report")
            progress.update(80, "Generating comprehensive report...")
            final_report = self._generate_final_report(root_node)

            self.logger.info("Research completed successfully")
            progress.update(100, "Research complete!")

            return final_report

        except Exception as e:
            self.logger.error(f"Research failed: {str(e)}")
            self.scraper.cleanup()
            raise e
        finally:
            self.scraper.cleanup()

    def _analyze_and_branch(self, node: ResearchNode) -> List[ResearchNode]:
        analysis_prompt = f"""Analyze the research data and suggest new branches for deeper exploration.
        Current topic: {node.query}
        Current depth: {node.depth}
        Path from root: {' -> '.join(node.get_path_to_root())}

        Suggest new research directions that:
        1. Are specific and focused
        2. Explore unexplored aspects
        3. Follow promising leads from the current data

        For each suggestion, rate its importance (0-1) and explain why.
        Format: Importance Score | Query | Reason"""

        response = self.research_manager.generate_content(analysis_prompt)
        result = response.text

        new_nodes = []
        for line in result.split("\n"):
            if "|" not in line:
                continue

            parts = line.split("|")
            if len(parts) < 2:
                continue

            try:
                importance = float(parts[0].strip())
                query = parts[1].strip()

                if importance >= self.min_importance_score:
                    child_node = node.add_child(query)
                    child_node.importance_score = importance
                    new_nodes.append(child_node)
            except ValueError:
                continue

        return new_nodes

    def _generate_final_report(self, root_node: ResearchNode) -> Dict[str, Any]:
        def collect_data(node: ResearchNode) -> List[Dict]:
            all_data = node.data.copy()
            for child in node.children:
                all_data.extend(collect_data(child))
            return all_data

        all_research_data = collect_data(root_node)

        # Generate structured report using LLM
        report_prompt = f"""Generate a comprehensive research report using the collected data.
        Main Topic: {root_node.query}

        Structure the report with:
        1. Executive Summary
        2. Key Findings
        3. Detailed Analysis
        4. Related Topics and Branches
        5. Sources and References

        Include relevant quotes and citations."""

        response = self.research_manager.generate_content(report_prompt)
        report_content = response.text

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
                "max_depth_reached": max(
                    data.depth for data in collect_data(root_node)
                ),
                "total_branches": len(list(collect_data(root_node))),
            },
        }
