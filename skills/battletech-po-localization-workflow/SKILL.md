---
name: battle-tech-po-localization-workflow
description: BattleTech .po localization tool-chain — 9 sequential, independently-runnable stages that extract entries, build a sqlite DB, mine candidate terms, import an existing terminology JSON, slice translation packs, do dedup + matched-terms extraction, hand packs to an LLM for translation, then write back to PO. Use when the user wants to translate or update a BattleTech-game .po file with LLM assistance while keeping deterministic processing in scripts. Trigger when user mentions BattleTech .po, gettext localization workflow, or invokes /battle-tech-po-localization-workflow.
---

# BattleTech PO Localization Workflow

## Overview

A 9-stage pipeline. Stages 1–2, 4, 5, 6, 8, 9 are pure Python scripts. Stages 3 and 7 are split into a script half plus an LLM half. Each stage runs independently and end-to-end; the user advances stage-by-stage and confirms results before moving on. **Never auto-advance, never run stages in parallel, never run LLM calls in parallel.**

## Workspace

Every script requires `--workspace <path>` (no default). All artifacts live there:

```
<workspace>/
├── config.json                  # optional, pipeline-wide configuration
├── localization.sqlite          # created by stage 2
├── entries.jsonl                # stage 1 output
├── term_candidates.json         # stage 3a output
├── filtered_terms.json          # stage 3b LLM output (you write this)
├── terminology.csv              # stage 3c output (user edits this)
└── packs/                       # all numbered pack files live here
    ├── pack_0000.json           # stage 5 output (4-digit zero-padded)
    ├── pack_0000.preprocessed.json
    ├── pack_0000.translated.json # stage 7 LLM output (you write this)
    └── pack_0000.review.csv     # stage 8a output (user edits this)
```

`SKILL_ROOT` below = `~/.qoder/skills/battletech-po-localization-workflow`.

## Configuration

An optional `<workspace>/config.json` file controls parameters across all stages. If the file is absent, built-in defaults are used. CLI arguments (where applicable) override config values.

| Key              | Default                | Description                                      |
|------------------|------------------------|--------------------------------------------------|
| `db_name`        | `"localization.sqlite"`| Database filename                                |
| `ngram_min`      | `1`                    | Minimum n-gram length for term mining            |
| `ngram_max`      | `3`                    | Maximum n-gram length for term mining            |
| `min_token_length`| `3`                   | Minimum token length to be considered meaningful |
| `top_candidates` | `500`                  | Number of top candidate terms to extract (stage 3a) |
| `max_samples`    | `3`                    | Max example sentences per candidate (stage 3a)   |
| `pack_size`      | `50`                   | Entries per translation pack (stage 5)           |

### Small-scale testing

For quick end-to-end validation, create `config.json` with reduced values:

```json
{
    "top_candidates": 50,
    "max_samples": 2,
    "pack_size": 10
}
```

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

Four sub-steps:

**3a. Mine candidates (script):**
```
python3 $SKILL_ROOT/scripts/stage3_build_terminology/extract_candidates.py --workspace <workspace>
```
Writes `term_candidates.json`. The number of candidates is controlled by `--top` CLI arg or `top_candidates` in config (default 500).

**3b. LLM filter (manual):** Read `term_candidates.json` and the prompt at `$SKILL_ROOT/scripts/stage3_build_terminology/llm_filter_prompt.md`. Output JSON `[{"term": "..."}]` to `<workspace>/filtered_terms.json`. Keep ONLY BattleTech-specific proper nouns / faction names / mech models / lore terms. Drop generic English.

**3c. Export CSV (script):**
```
python3 $SKILL_ROOT/scripts/stage3_build_terminology/export_terms_csv.py --workspace <workspace>
```
Reads `filtered_terms.json` + `term_candidates.json`, outputs `terminology.csv` with columns: `term`, `freq`, `sample1`, `sample2`, `sample3`, `translation`.
- `sample1~3` are truncated to short snippets (term ± 60 chars) so users see concise context instead of full paragraphs.
- Newlines inside samples are collapsed to spaces so every CSV row stays on a single line and spreadsheet editors don't break.

**STOP.** Tell the user to open `terminology.csv` in a spreadsheet editor (Excel, LibreOffice, etc.), review the terms, and fill in the `translation` column with Simplified Chinese translations. The CSV uses UTF-8 BOM encoding for Excel compatibility.

**3d. Import CSV (script, user-triggered):**
```
python3 $SKILL_ROOT/scripts/stage3_build_terminology/import_terms_csv.py --workspace <workspace>
```
Reads the user-edited `terminology.csv` and upserts into the `terminology` table:
- Terms with a non-empty translation → INSERT new or UPDATE existing (overwrite).
- Terms with an empty translation → INSERT new (translation NULL), but **never** overwrite an existing non-empty translation.

Run only when the user says they are done editing the CSV. **STOP**.

## Stage 4 — Import existing terms.json

Run:
```
python3 $SKILL_ROOT/scripts/stage4_import_terms_json/import_terms_json.py \
    --workspace <workspace> --json <path/to/terms.json>
```
Upserts; never blanks an existing translation.

**HARD STOP.** User must manually review the `terminology` table (e.g. `sqlite3 <workspace>/localization.sqlite "SELECT term, translation FROM terminology WHERE translation IS NULL OR translation = ''"`). Only proceed when satisfied. Empty translations are silently skipped in stage 6.

## Stage 5 — Create translation packs

Run:
```
python3 $SKILL_ROOT/scripts/stage5_create_pack/create_pack.py \
    --workspace <workspace> --all
```
Pack size is controlled by `--size` CLI arg or `pack_size` in config (default 50). `--all` creates every pack at once, slicing all valid (untranslated, no placeholder) rows. Outputs go to `<workspace>/packs/pack_0000.json` (4-digit zero-padded index).

If you ever need to recreate a single pack, use `--index <I>` instead of `--all`.

Each `pack_<I>.json` contains only `Key`, `msgid`, and `msgstr` (no `SourceLocation`, to keep downstream LLM prompts lean). **STOP**.

You can check the status of all packs at any time with `list_packs.py` (see [Pack status query](#pack-status-query) below).

## Stage 6 — Preprocess packs (dedup + term matching)

Run:
```
python3 $SKILL_ROOT/scripts/stage6_preprocess_pack/preprocess_pack.py \
    --workspace <workspace> --all
```
- Drops entries whose `msgid` already has a translated twin in DB (and copies that translation into the current row).
- For surviving entries, finds matching terminology phrases and accumulates them into a **pack-level** `matched_terms` list (deduplicated across all entries) for the LLM to judge contextual appropriateness in Stage 7. `msgid` stays untouched as DB key.

Processes every pack in `<workspace>/packs/` at once. Outputs `pack_0000.preprocessed.json` for each, shaped `{"matched_terms": [{"term": "...", "translation": "..."}], "entries": [{"Key": "...", "msgid": "..."}]}`. The `matched_terms` array is a pack-wide terminology reference; the LLM decides in Stage 7 which terms apply to each entry.

If you need to reprocess a single pack, use `--index <I>` instead of `--all`. **STOP**.

## Stage 7 — LLM translation (manual)

Read every `<workspace>/packs/pack_*.preprocessed.json` and the prompt at `$SKILL_ROOT/scripts/stage7_translate_pack/translate_prompt.md`. The file contains a top-level `matched_terms` (pack-wide terminology reference) and an `entries` array. Translate each entry's `msgid` to Simplified Chinese using the terminology for reference, write corresponding `<workspace>/packs/pack_*.translated.json` shaped `[{"Key": "...", "msgstr": "..."}]`.

Process all packs before moving on; there is no looping back.

## Stage 8 — Apply pack to DB

Two sub-steps:

**8a. Export review CSVs (script):**
```
python3 $SKILL_ROOT/scripts/stage8_apply_pack/export_pack_csv.py \
    --workspace <workspace> --all
```
Reads every `<workspace>/packs/pack_*.translated.json` + `pack_*.preprocessed.json`, outputs corresponding `<workspace>/packs/pack_*.review.csv` with columns: `Key`, `msgid`, `msgstr`.

**STOP.** Tell the user to open the review CSVs in a spreadsheet editor to review or correct LLM translations. The CSV uses UTF-8 BOM encoding for Excel compatibility.

If you need to re-export a single pack, use `--index <I>` instead of `--all`.

**8b. Apply review CSVs (script, user-triggered):**
```
python3 $SKILL_ROOT/scripts/stage8_apply_pack/apply_pack_csv.py \
    --workspace <workspace> --all
```
Reads every user-reviewed `<workspace>/packs/pack_*.review.csv` and updates the DB.
- Blank `msgstr` values are skipped (not marked translated).
- Entries where `msgstr` is **identical to the original `msgid`** are also skipped (treated as "no translation performed"). **STOP**.

If you need to re-apply a single pack, use `--index <I>` instead of `--all`.

**One-pass execution.** Stages 5 through 8 are executed **once in order**; you never loop back to an earlier stage. `--all` handles every pack in a single run. `--index` is provided only for spot-testing or re-processing an individual pack.

## Stage 9 — Export PO

Run:
```
python3 $SKILL_ROOT/scripts/stage9_export_po/export_po.py \
    --workspace <workspace> --po <path/to/source.po> --out <path/to/translated.po>
```
Streams the original PO and rewrites only `msgstr` for entries with `hasPlaceholder = 0`. Placeholder entries are emitted unchanged.

## Pack status query

At any point during the pipeline, run this to see the state of every pack:

```
python3 $SKILL_ROOT/scripts/stage5_create_pack/list_packs.py --workspace <workspace>
```

Output example:
```
[pack 0000] created ✓ | preprocessed ✓ | translated ✓ | exported ✓ | applied 50/50 ✓
[pack 0001] created ✓ | preprocessed ✓ | translated ✓ | exported - | applied 0/50
[pack 0002] created ✓ | preprocessed - | translated - | exported - | applied 0/48
...
Summary:
  Total packs created:        3
  Packs fully applied:        1
  Packs pending:              2
  DB remaining valid rows:    98
  Next pack index to create:  3
```

This helps you:
- **Interrupt recovery**: after a crash or pause, instantly see which packs still need work.
- **Multi-thread preparation**: identify packs that are already preprocessed but not yet translated — these can be handed to different LLM sessions in parallel (only the LLM step, not scripts).
- **Result reproducibility**: even if the DB is lost or corrupted, every pack's `pack_0000.review.csv` file retains the full translation result and can be re-imported.

Add `--detail` to see individual pending keys per pack.

## Non-negotiables

- One stage at a time; user confirms before next.
- No parallel script execution. No parallel LLM requests.
- LLM is used **only** in stages 3b and 7. Every other operation is deterministic.
- All scripts use stdlib only (Python 3.9+).
