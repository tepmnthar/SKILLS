# Stage 3b — Term candidate filtering

You are filtering English n-gram candidates mined from a BattleTech-universe video game `.po` file. The file `term_candidates.json` contains entries shaped:

```
{ "term": "...", "freq": <int>, "samples": ["...", "..."] }
```

## Goal

Output ONLY a JSON array to `<workspace>/filtered_terms.json`:

```
[ { "term": "<verbatim term from input>" }, ... ]
```

## What happens next

The filtered terms will be exported to a CSV spreadsheet where a human reviewer will add Simplified Chinese translations. Prioritise terms that (a) are BattleTech-specific and (b) are non-obvious to translate — proper nouns and lore terms that require a consistent, agreed-upon Chinese rendering across the entire game.

## Keep

- BattleTech-specific proper nouns (mech model names, weapon system names, faction names, planet names, character names).
- Lore terms whose translation must be consistent across the game (e.g. "BattleMech", "Inner Sphere", "Federated Suns", "Clan Wolf", "AC/20").
- Multi-word phrases that form a single domain concept (e.g. "extreme weather", "drop ship") — only if BattleTech-specific.

## Drop

- Generic English words ("damage", "armor", "weapon" — unless qualified into a BattleTech-specific phrase).
- Filler n-grams ("the player", "you can").
- Numbers, dates, anything that isn't a term.

## Rules

- Preserve the term string EXACTLY as it appears in the input (same casing, same spacing).
- No commentary, no markdown, no surrounding text — output ONLY valid JSON.
- When in doubt, drop. A smaller high-quality list is better than a noisy one.
