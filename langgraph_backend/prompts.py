from textwrap import dedent

# --- Prompt templates ---
RESEARCH_PLAN_PROMPT = dedent("""You are an expert Deep Research agent, part of a Multiagent system.

<User query>
{topic}
</User query>

---
Generate few very high level steps on which other agents can do info collection runs. Provide only data collection steps, no data identification, summarization, manipulation, selection, etc.
Do not presume any knowledge about the topic.
Return a string array of steps.""")

SITE_SUMMARY_PROMPT = dedent("""Extract specific verbatim key information from the following content that is related to the topic "{query}". No small talk.
<Findings>
{findings}
</Findings>
""")

CONTINUE_BRANCH_PROMPT = dedent("""Given the current state of research, decide whether to continue exploring the current branch or not.
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

SEARCH_QUERY_PROMPT = dedent("""Based on the following findings on topic {vertical}, create google search queries
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

REPORT_OUTLINE_PROMPT = dedent("""Generate a outline for a report based on the findings:
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

REPORT_FILLIN_PROMPT = dedent("""Fill in the content for the current outline heading based on the findings:
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
