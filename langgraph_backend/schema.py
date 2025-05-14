from typing import List, TypedDict


class ResearchPlan(TypedDict):
    steps: List[str]


class ContinueBranch(TypedDict):
    decision: bool


class SearchQuery(TypedDict):
    branches: List[str]


class ReportOutline(TypedDict):
    title: str
    headings: List[str]


class ReportFillin(TypedDict):
    content: str
