---
name: battle-tech-po-localization-workflow
description: BattleTech .po localization tool-chain — 9 sequential, independently-runnable stages that extract entries, build a sqlite DB, mine candidate terms, import an existing terminology JSON, slice translation packs, do dedup + inline term substitution, hand packs to an LLM for translation, then write back to PO. Use when the user wants to translate or update a BattleTech-game .po file with LLM assistance while keeping deterministic processing in scripts. Trigger when user mentions BattleTech .po, gettext localization workflow, or invokes /battle-tech-po-localization-workflow.
---

# BattleTech PO Localization Workflow

## Overview

A 9-stage pipeline. Stages 1–2, 4, 5, 6, 8, 9 are pure Python scripts. Stages 3 and 7 are split into a script half plus an LLM half. Each stage runs independently and end-to-end; the user advances stage-by-stage and confirms results before moving on. **Never auto-advance, never run stages in parallel, never run LLM calls in parallel.**

## Workspace

Every script requires `--workspace <path>` (no default). All artifacts live there:

```
<workspace>/
├── localization.sqlite          # created by stage 2
├── entries.jsonl                # stage 1 output
├── term_candidates.json         # stage 3a output
├── filtered_terms.json          # stage 3b LLM output (you write this)
├── pack_<I>.json                # stage 5 output
├── pack_<I>.preprocessed.json   # stage 6 output
└── pack_<I>.translated.json     # stage 7 LLM output (you write this)
```

`SKILL_ROOT` below = `~/.qoder/skills/battle-tech-po-localization-workflow`.

## Stage 1 — Extract PO entries

Run:
```
python3 $SKILL_ROOT/scripts/stage1_extract_po/extract_po.py \
    --po <path/to/source.po> --workspace <workspace>
```
Outputs `entries.jsonl`. Each line: `{Key, SourceLocation, msgid, msgstr, isTranslated, hasPlaceholder}`. **STOP** for user confirmation.

## Stage 2 — Load DB

Run:
```
python3 $SKILL_ROOT/scripts/stage2_init_db/load_db.py --workspace <workspace>
```
Creates/refreshes `localization.sqlite` table `translations` (PK `Key`, index on `msgid`). **STOP**.

## Stage 3 — Build terminology candidates

Two sub-steps:

**3a. Mine candidates (script):**
```
python3 $SKILL_ROOT/scripts/stage3_build_terminology/extract_candidates.py --workspace <workspace>
```
Writes `term_candidates.json`.

**3b. LLM filter (manual):** Read `term_candidates.json` and the prompt at `$SKILL_ROOT/scripts/stage3_build_terminology/llm_filter_prompt.md`. Output JSON `[{"term": "..."}]` to `<workspace>/filtered_terms.json`. Keep ONLY BattleTech-specific proper nouns / faction names / mech models / lore terms. Drop generic English.

**3c. Import filtered terms (script):**
```
python3 $SKILL_ROOT/scripts/stage3_build_terminology/import_terms.py --workspace <workspace>
```
Inserts terms into `terminology` (translation NULL). **STOP**.

## Stage 4 — Import existing terms.json

Run:
```
python3 $SKILL_ROOT/scripts/stage4_import_terms_json/import_terms_json.py \
    --workspace <workspace> --json <path/to/terms.json>
```
Upserts; never blanks an existing translation.

**HARD STOP.** User must manually review the `terminology` table (e.g. `sqlite3 <workspace>/localization.sqlite "SELECT term, translation FROM terminology WHERE translation IS NULL OR translation = ''"`). Only proceed when satisfied. Empty translations are silently skipped in stage 6.

## Stage 5 — Create translation pack

Run:
```
python3 $SKILL_ROOT/scripts/stage5_create_pack/create_pack.py \
    --workspace <workspace> --size 50 --index 0
```
Pack size is configurable (default 50). Index is 0-based and counts only valid (untranslated, no placeholder) rows. Outputs `pack_<I>.json`. Prints remaining valid count. **STOP**.

## Stage 6 — Preprocess pack (dedup + term substitution)

Run:
```
python3 $SKILL_ROOT/scripts/stage6_preprocess_pack/preprocess_pack.py \
    --workspace <workspace> --index 0
```
- Drops entries whose `msgid` already has a translated twin in DB (and copies that translation into the current row).
- For surviving entries, substitutes any matching terminology phrases inline into `source_for_llm` to save LLM tokens. `msgid` stays untouched as DB key.

Outputs `pack_<I>.preprocessed.json`. **STOP**.

## Stage 7 — LLM translation (manual)

Read `pack_<I>.preprocessed.json` and the prompt at `$SKILL_ROOT/scripts/stage7_translate_pack/translate_prompt.md`. Translate each entry's `source_for_llm` to Simplified Chinese, write `<workspace>/pack_<I>.translated.json` shaped `[{"Key": "...", "msgstr": "..."}]`.

## Stage 8 — Apply pack to DB

Run:
```
python3 $SKILL_ROOT/scripts/stage8_apply_pack/apply_pack.py \
    --workspace <workspace> --index 0
```
Updates `translations.msgstr` and flips `isTranslated = 1`. **STOP**.

Loop stages 5 → 8 (incrementing `--index`) until no valid rows remain.

## Stage 9 — Export PO

Run:
```
python3 $SKILL_ROOT/scripts/stage9_export_po/export_po.py \
    --workspace <workspace> --po <path/to/source.po> --out <path/to/translated.po>
```
Streams the original PO and rewrites only `msgstr` for entries with `hasPlaceholder = 0`. Placeholder entries are emitted unchanged.

## Non-negotiables

- One stage at a time; user confirms before next.
- No parallel script execution. No parallel LLM requests.
- LLM is used **only** in stages 3b and 7. Every other operation is deterministic.
- All scripts use stdlib only (Python 3.9+).
