---
name: sarna-browse
description: Browse and search www.sarna.net (BattleTech wiki). Supports three modes — news, search with cascade, and random page. Primary invocation uses explicit commands (news/search/random); keyword-based fallback is used only when no command is given. Use when the user wants BattleTech wiki content, recent news, or a random article.
---

# Sarna Browse

Browse www.sarna.net — a BattleTech/MechWarrior wiki.

## Output Rules

1. **All results go to the conversation**. The user interacts entirely through chat. Present every summary, link, and result in the conversation thread. Never present a local file path as the final answer.
2. **Local files are internal only**. `sarna-cache/` and `sarna-data/` exist for caching and downstream processing. If a user asks for previously fetched data, read the local file and echo its contents into the conversation.
3. **Full-text requests**: If a user asks for the full original article, provide the sarna.net URL link in the conversation, not the cached summary.

## Session Behavior

This skill remains active across multiple turns within the same conversation.

- If the user input starts with an explicit command (`news`, `search`, `random`) or clearly triggers keyword fallback for a **new request**, proceed with the appropriate mode and fetch data as needed.
- If the user input is a **follow-up** (does not start with a command and does not constitute a new search request), **never fetch new network content**. Only read the most recent local data (`sarna-data/` or `sarna-cache/`) and re-extract or transform it (e.g., translate, reformat, answer a specific question).
- If no relevant local data exists for a follow-up, inform the user and suggest running the appropriate command first.

## Mode Detection

Identify the mode using a two-tier approach.

### Tier 1 — Explicit command (preferred)

The first word after `/sarna-browse` is the command:

- `news [prompt]` → News mode
- `search <query> [prompt]` → Search mode
- `random [prompt]` → Random mode

Examples:
- `/sarna-browse news last 5 days` → News mode, 5 days
- `/sarna-browse search Timber Wolf` → Search mode, query "Timber Wolf"
- `/sarna-browse random` → Random mode

If the first word is a recognized command, use that mode regardless of what follows.

### Tier 2 — Keyword fallback (only when no explicit command is given)

If the first word is not `news`, `search`, or `random`, infer mode from keywords in the entire input:

| Keywords | Mode |
|---|---|
| `news`, `rss` | News |
| `search`, `find`, `lookup` + query | Search |
| `random` | Random |

If the intent remains unclear after keyword matching, ask the user to clarify by providing one of the explicit commands: `news`, `search`, or `random`.

## News Mode

Fetch recent news from `https://www.sarna.net/news/`.

### Parameters

- `days`: Time window in days (default: 3). User may override via prompt text (e.g., "last 5 days").
- `count`: Max number of news items (default: 5). User may override via prompt text (e.g., "10 articles").

### Cache

News articles are immutable once published. Cache processed summaries to avoid re-fetching.

- Cache directory: `sarna-cache/news/` in the project root.
- Cache key: article slug from the URL (e.g., `bad-mechs-cyclops` → `sarna-cache/news/bad-mechs-cyclops.md`).
- Cache content: **processed summary only**, never the raw full article.

### Steps

1. Use WebFetch on `https://www.sarna.net/news/` with prompt: "Extract all news articles on this page. For each article, provide: title, date, and URL. Return them in chronological order from newest to oldest."
2. Filter results: keep only items within the `days` threshold and up to `count` items.
3. For each filtered article:
   a. Compute the cache slug from its URL.
   b. Check if `sarna-cache/news/{slug}.md` exists (use Read or Glob).
   c. If cached: read the file and use its summary directly.
   d. If not cached: fetch the article via WebFetch, summarize preserving paragraph count, write the summary to `sarna-cache/news/{slug}.md`, then use it.
4. Present the compiled results in the conversation.

### Output Format (conversation)

```markdown
# Sarna News — {date}

## {Article Title}
*Published: {article date}* | *URL: {article_url}*

{Summarized content preserving paragraph structure}

---
[Repeat for each article]
```

## Search Mode

Search sarna.net wiki and cascade through linked pages with strict constraints.

### Parameters

- `query`: The search keyword (required, from user input). Extract from the command: for `search <query>`, the query is the first word after "search"; for keyword fallback, the query follows the keyword.
- `breadth`: Max links to follow per page (default: 5, max: 5)
- `depth`: Max cascade levels from first result (default: 3, max: 3)
- `total`: Max total pages fetched across all levels (default: 10, max: 10)

### Steps

1. **Level 0 — Search**: Use WebFetch on the search URL `https://www.sarna.net/wiki/index.php?title=Special%3ASearch&search={query}&fulltext=Search` with prompt: "Extract all search result titles and their wiki page URLs. Return each result as: Title | URL. Only include results that link to sarna.net/wiki/ pages (exclude Special:, Help:, MediaWiki: pages)."
2. **Level 0 — Fetch results**: Fetch each search result page via WebFetch with prompt: "Provide the full article content of this page. Preserve the original paragraph structure. Also list all wiki article links found on this page that are under sarna.net/wiki/ (exclude Special:, Help:, Category: unless highly relevant to '{query}'). Return as: Title | URL."
3. **Cascade**: For each fetched page at the current level, select up to `breadth` (5) most relevant linked pages to follow next. Relevance priority:
   - Links directly related to the search query topic
   - Links to specific units, characters, or technology pages
   - Prefer content pages over meta/category pages
4. **Track constraints**: Maintain counters — never exceed `depth` (3) levels or `total` (10) pages. Stop cascade when either limit is reached.
5. **Summarize**: For each page, summarize content preserving original paragraph count. Keep original language (no translation).
6. **Aggregate**: Compile all fetched page summaries into the hierarchical aggregate format and save to `sarna-data/search-{query}-{yyyy-MM-dd-HH-mm-ss}.md`. This is the complete dataset for downstream processing and follow-up extraction.
7. **User-level output**: Read the aggregate file. Identify the content most relevant to the user's original query. Re-summarize into a focused, coherent narrative that directly answers the user's question. Preserve paragraph structure where possible. Present this curated summary in the conversation.

### Cascade Constraint Tracking

- `pages_fetched`: total count across all levels (<= 10)
- `current_depth`: current cascade level (<= 3, starting at 0)
- `breadth_per_page`: links followed from each single page (<= 5)

If `pages_fetched` reaches 10 or `current_depth` reaches 3, stop cascade immediately.

### Aggregate Format (saved locally)

```markdown
# Sarna Search — {query} — {date}

## Level 0: Search Results

### {Page Title}
*URL: {page_url}*

{Summarized content preserving paragraph structure}

---

## Level 1: Cascade

### {Page Title}
*From: {parent page title}* | *URL: {page_url}*

{Summarized content preserving paragraph structure}

---

[Continue for Level 2 if applicable]

## Summary
- Pages fetched: {count}/{max}
- Cascade depth: {depth}/{max}
```

### User-Level Output Format (conversation)

```markdown
# Sarna Search — {query}

{Focused narrative summarizing the most relevant findings from the aggregate data}

---

## Sources
- {Page Title}: {page_url}
- [Repeat for key sources]

## Details
### {Most Relevant Page Title}
{Selected paragraphs most relevant to the query}

---
### {Next Most Relevant Page Title}
{Selected paragraphs most relevant to the query}
```

## Random Mode

Fetch a random wiki page — no cascade.

### Steps

1. Use WebFetch on `https://www.sarna.net/wiki/Special:Random` with prompt: "Provide the full content of this wiki page. Preserve the original paragraph structure. Include the page title."
2. Summarize the page — preserve original paragraph count, keep original language (no translation).
3. **Present results in the conversation** and also save to `sarna-data/random-{yyyy-MM-dd-HH-mm-ss}.md`.

### Output Format (conversation)

```markdown
# Sarna Random — {date}

## {Page Title}
*URL: {page_url}*

{Summarized content preserving paragraph structure}
```

## Follow-up Handling

When the user provides input that is not a new explicit command, treat it as a follow-up on data already fetched.

1. **Identify the most recent local data**:
   - For news: check `sarna-cache/news/` (most recently accessed).
   - For search: check `sarna-data/search-{query}-*.md` (most recent by timestamp).
   - For random: check `sarna-data/random-*.md` (most recent by timestamp).
2. **Read the local file(s)**.
3. **Re-extract or transform** based on the follow-up request:
   - "Translate" → translate the saved content into the requested language.
   - "Tell me more about X" → extract sections mentioning X.
   - "Bullet points" → reformat the saved content.
   - "Shorter summary" → condense while preserving key facts.
   - Any other transformation.
4. **Never use WebFetch, WebSearch, or any network tool** during follow-up.
5. If no relevant local data exists, inform the user and suggest running the appropriate command first.

## Content Processing Rules

1. **Preserve paragraph count**: Do not collapse multiple paragraphs into one. Match the source's paragraph structure.
2. **No automatic translation**: Output in the same language as the source unless user explicitly requests translation.
3. **Save locally**: Write fetched data to `sarna-data/` directory for downstream processing. Write news summaries to `sarna-cache/news/` for caching.
4. **Timestamp format**: Use `yyyy-MM-dd-HH-mm-ss` for file names (year-month-day-hour-minute-second). Use `yyyy-MM-dd` for display headers.

## Resources

- `references/urls.md` — URL patterns, sitemap, and valid link criteria for cascade
