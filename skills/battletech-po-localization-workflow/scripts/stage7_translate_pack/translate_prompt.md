# Stage 7 — Pack translation

You are translating a batch of game UI / dialogue strings from a **BattleTech-universe video game** into **Simplified Chinese (zh-Hans)**.

## Input

`<workspace>/pack_<I>.preprocessed.json` — a JSON array of:

```
{ "Key": "<id>", "msgid": "<original English>", "source_for_llm": "<English with some Chinese terminology already substituted>" }
```

## Task

For each entry, translate `source_for_llm` (NOT `msgid`) to Simplified Chinese. Some Chinese fragments are already embedded — keep them **exactly as-is** and translate only the surrounding English.

## Style rules

- BattleTech / military sci-fi tone. Concise, UI-friendly, consistent across the whole batch.
- Do not paraphrase brand / faction / mech names already in Chinese.
- Do not add commentary, footnotes, or markup.

## Output

Write `<workspace>/pack_<I>.translated.json` shaped:

```
[ { "Key": "<same as input>", "msgstr": "<Chinese translation>" }, ... ]
```

- Preserve `Key` byte-for-byte (it is the DB primary key).
- One entry per input entry, same order.
- Output ONLY the JSON array — no prose.
