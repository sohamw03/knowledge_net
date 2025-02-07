from typing import List, Dict, Any, Optional
from datetime import datetime

class ResearchNode:
    def __init__(self, query: str, parent: Optional['ResearchNode'] = None, depth: int = 0):
        self.query = query
        self.parent = parent
        self.depth = depth
        self.children: List[ResearchNode] = []
        self.data: List[Dict[str, Any]] = []
        self.explored = False
        self.importance_score = 0.0
        self.timestamp = datetime.now()

    def add_child(self, query: str) -> 'ResearchNode':
        child = ResearchNode(query, parent=self, depth=self.depth + 1)
        self.children.append(child)
        return child

    def get_path_to_root(self) -> List[str]:
        path = [self.query]
        current = self
        while current.parent:
            current = current.parent
            path.append(current.query)
        return list(reversed(path))
