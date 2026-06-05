# Stage 7 — Pack translation

You are translating a batch of game UI / dialogue strings from a **BattleTech-universe video game** into **Simplified Chinese (zh-Hans)**.

## Input

`<workspace>/packs/pack_0000.preprocessed.json` — a JSON array of:

```
{
  "Key": "<id>",
  "msgid": "<original English>",
  "matched_terms": [
    {"term": "<English term found in msgid>", "translation": "<Chinese translation from terminology DB>"}
  ]
}
```

## Task

Translate `msgid` to Simplified Chinese. The `matched_terms` array lists terminology entries that **appear** in the original text. You must use your own judgment to decide whether each matched term is semantically appropriate in the specific sentence context.

- If a matched term **fits the context**, use its provided Chinese translation (or a natural grammatical variant of it).
- If a matched term **does not fit the context** (e.g. the word looks the same but carries a different meaning), translate the passage yourself and **ignore** the suggested term.

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

## Output

Write `<workspace>/packs/pack_0000.translated.json` shaped:

```
[ { "Key": "<same as input>", "msgstr": "<Chinese translation or unchanged original>" }, ... ]
```

- Preserve `Key` byte-for-byte (it is the DB primary key).
- One entry per input entry, same order.
- If an entry is output **exactly unchanged** from `msgid`, the pipeline will **not** treat it as translated; it will be left for later human review or skipped. Therefore, only include a translated string when you have actually performed translation.
- Output ONLY the JSON array — no prose.
