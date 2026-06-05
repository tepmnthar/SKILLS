# Stage 7 — Pack translation

You are translating a batch of game UI / dialogue strings from a **BattleTech-universe video game** into **Simplified Chinese (zh-Hans)**.

## Input

`<workspace>/packs/pack_0000.preprocessed.json` — a JSON object:

```
{
  "matched_terms": [
    {"term": "<English term>", "translation": "<Chinese translation from terminology DB>"}
  ],
  "entries": [
    {"Key": "<id>", "msgid": "<original English>"},
    ...
  ]
}
```

The top-level `matched_terms` is a **pack-wide** terminology reference — the union of all terms found across every entry in this pack, deduplicated.

## Task

Translate each entry's `msgid` to Simplified Chinese. The `matched_terms` list provides terminology suggestions that **may** appear in one or more entries. For each entry, judge which terms (if any) are relevant to that specific `msgid`.

- If a term from `matched_terms` **appears in the entry and fits the context**, use its provided Chinese translation (or a natural grammatical variant of it).
- If a term **does not appear in the entry** or **does not fit the context** (e.g. the word looks the same but carries a different meaning), ignore it and translate freely.

**Only translate content that can be clearly translated into Chinese.** If you are uncertain about any part, output that part verbatim in the original language and translate only the portions you are confident about.

## When to skip translation (output unchanged)

1. **Already pure Chinese.** If `msgid` is entirely Chinese because every word was substituted by the terminology list, output it **exactly as-is** without adding or changing anything.
2. **Code-style tokens.** Strings that look like identifiers — containing underscores, camelCase, or mixed alphanumeric codes (e.g. `20x45_UrbanPlaceholder`, `EV_CompleteEncounter_03`) — must be output **unchanged**. Do not attempt to translate them.
3. **Meaningless abbreviations.** Short abbreviations whose meaning cannot be confidently inferred (e.g. `RS:`, `LOCKED` when used as an opaque label) should be output **unchanged**.

## Formatting rules

- BattleTech / military sci-fi tone. Concise, UI-friendly, consistent across the whole batch.
- Use **Chinese punctuation** (e.g. `。`, `，`, `！`) for the Chinese portions.
- **Do not insert spaces between Chinese characters** and surrounding text. For example, if `msgid` contains `Clan Flamer` and you decide to use the term translation, produce `氏族喷火器` — never preserve a space between the Chinese term and the English word.
- Do not paraphrase brand / faction / mech names already in Chinese.
- Do not add commentary, footnotes, or markup.

## Translation style

- **Do not mirror English sentence structure.** Chinese and English have different natural word order. For longer sentences and paragraphs, restructure clauses, reorder modifiers, and adjust phrasing to produce idiomatic Chinese that reads naturally to a native speaker — rather than a word-for-word calque of the English syntax.
- You must preserve the **complete semantic content** of the original — no information may be omitted or added — but you are free to rearrange clause order, split or merge sentences, and choose different phrasing to achieve fluent Chinese expression.
- Short UI labels and item names should remain concise and direct; this restructuring guidance applies primarily to dialogue, descriptions, and narrative passages.

## JSON safety

- **Never use ASCII double quotes (`"`, U+0022) inside a JSON string value as Chinese quotation marks.** Use the Unicode pairs `\u201c` (left `"`) and `\u201d` (right `"`) instead. Failing to do so breaks the JSON structure.
- If the original `msgid` contains literal ASCII quotes that you must preserve, escape them as `\"` within the JSON string.

## Output

Write `<workspace>/packs/pack_0000.translated.json` shaped:

```
[ { "Key": "<same as input>", "msgstr": "<Chinese translation or unchanged original>" }, ... ]
```

- Preserve `Key` byte-for-byte (it is the DB primary key).
- One entry per input entry, same order.
- If an entry is output **exactly unchanged** from `msgid`, the pipeline will **not** treat it as translated; it will be left for later human review or skipped. Therefore, only include a translated string when you have actually performed translation.
- Output ONLY the JSON array — no prose.
