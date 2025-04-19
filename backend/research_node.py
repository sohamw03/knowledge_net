import copy
from typing import Any, Dict, List, Optional, Self


class ResearchNode:
    def __init__(self, query: str = "_", parent: Optional[Self] = None, depth: int = 0):
        self.query = query
        self.parent = parent
        self.depth = depth
        self.children: List[ResearchNode] = []
        self.data: List[Dict[str, Any]] = []

    def add_child(self, query: str, node: Optional[Self] = None) -> Self:
        if node:
            child = node
            child.parent = self
            child.depth = self.depth + 1
        else:
            child = ResearchNode(query, parent=self, depth=self.depth + 1)
        self.children.append(child)
        return child

    def get_path_to_root(self) -> List[str]:
        """
        Returns the path from this node to the root node.
        List[str]: [root.query, ..., self.query]
        """
        path = [self.query]
        current = self
        while current.parent:
            current = current.parent
            path.append(current.query)
        return list(reversed(path))

    def max_depth(self) -> int:
        if not self.children:
            return self.depth
        return max([child.max_depth() for child in self.children])

    def total_children(self) -> int:
        if not self.children:
            return 0
        return len(self.children) + sum([child.total_children() for child in self.children])

    def get_all_data(self) -> List[Dict[str, Any]]:
        data = copy.deepcopy(self.data)
        for child in self.children:
            data.extend(child.get_all_data())
        return data

    # Build research tree structure
    def build_tree_structure(self) -> Dict:
        if not self:
            return {}
        sources = {d["url"]: d["text"] for d in self.data if d.get("url") and d.get("text")}
        return {
            "query": self.query,
            "depth": self.depth,
            "sources": sources,
            "children": [child.build_tree_structure() for child in self.children],
        }
