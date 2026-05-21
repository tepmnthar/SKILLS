# News Mode Output Formatter

Use this template when presenting news results in the conversation.

## Rules

- Links must be plain text, never markdown. Use `URL: https://...` on its own line.
- Preserve paragraph structure within each article overview.
- Present articles in chronological order from newest to oldest.
- Do not translate unless the user explicitly requests it.

## Template

```
# Sarna News — {yyyy-MM-dd}

## {Article Title}
Published: {article_date}
URL: {full_article_url}

{Overview paragraph 1}

{Overview paragraph 2}
...

---

## {Next Article Title}
Published: {article_date}
URL: {full_article_url}

{Overview paragraph 1}

{Overview paragraph 2}
...

---
[Repeat for each article]
```

## Example

```
# Sarna News — 2026-05-21

## Bad 'Mechs – Cyclops
Published: 2026/05/15
URL: https://www.sarna.net/news/bad-mechs-cyclops/

General Werner Von Wehner received word that his special order had arrived in bay seven. He eagerly prepared to inspect his newly acquired Cyclops, a rare BattleMech equipped with the Tacticon B-2000 Battle Computer. He had called in significant political favors to secure it, confident this edge would guarantee victory in retaking Skondia.

The invasion went disastrously wrong. After the B-2000 initially generated an attack plan, it suddenly froze — displaying absurd holographic prompts. While Von Wehner hammered at buttons, the Dracs counterattacked. An aide's report was cut off by an explosion, and LRMs struck his Cyclops. The console turned red, and when he demanded commands, a voice replied: "I can't do that, Werner."

---

## Silent But Deadly: Talking Silent Reapers with BattleTech Author Daniel Isberner
Published: 2026/05/13
URL: https://www.sarna.net/news/silent-assets-interview-battletech-author-daniel-isberner/

Following a recent book release, the writer discusses a fresh storytelling approach that shifts focus away from traditional mechanical perspectives.
```
