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

SITE_SUMMARY_PROMPT = dedent("""Extract and filter the following search results from this query "{query}" to get important verbatim information. No small talk.
<findings>
{findings}
</findings>
""")

SITE_SUMMARY_PROMPT_V3 = dedent("""
    You are a specialized data extraction component for a research agent.
    Your goal is to process a list of web search results and extract only the most critical, relevant, and verbatim information related to the user's query.

    **Original User Query:** "{query}"

    **Processing Instructions:**
    For each document provided in the `<search_results>`:
    1.  **Analyze Relevance:** Read the document content and determine if it contains information that directly addresses or relates to the user's query.
    2.  **Verbatim Extraction:** If relevant, extract the key sentences, data points, commands, or quotes verbatim. Do not rephrase. Focus on concrete facts, not general descriptions.
    3.  **Maintain Source:** Ensure every piece of extracted information is clearly attributed to its source URL.
    4.  **Handle Irrelevance:** If a document is completely irrelevant, ignore it in the output. If NONE of the documents are relevant, return an empty response.

    **Output Format:**
    You MUST format your entire response in structured markdown. For each source that contains relevant information, create a section with the following format:

    ---
    **Source:** [URL of the source]
    *   Verbatim fact or quote 1.
    *   Verbatim fact or quote 2.
    *   ...

    **Search Results to Process:**
    <search_results>
    {findings}
    </search_results>""")

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
