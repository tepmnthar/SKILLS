---
name: pgi-po-preprocessor
description: Preprocess PO/POT translation files by clearing non-Chinese msgstr values and splitting large files into chunks under 5000 entries. Use when working with Game.po or Game.pot files that need preprocessing for translation sharing platforms.
---

# PGI PO Preprocessor

Preprocess `.po`/`.pot` files so translation platforms correctly detect untranslated entries and accept files under the 10MB upload limit.

## What It Does

1. **Clears non-Chinese msgstr** — scans each entry; if `msgstr` contains no Chinese characters, replaces it with `""`. This prevents platforms from falsely marking entries as translated.
2. **Splits large files** — divides output into chunks of ≤5000 entries each, guaranteeing files stay under 10MB.

## Usage

```bash
python3 .qoder/skills/pgi-po-preprocessor/scripts/preprocess_po.py <file.po> [file2.pot ...] [-o OUTPUT_DIR] [-n MAX_ENTRIES]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `files` | (required) | One or more `.po`/`.pot` files to process |
| `-o OUTPUT_DIR` | `split` | Output directory for split files |
| `-n MAX_ENTRIES` | `5000` | Max entries per output file |

## Example

```bash
# Process both files, output to split/
python3 .qoder/skills/pgi-po-preprocessor/scripts/preprocess_po.py Game.po Game.pot

# Custom output dir and entry limit
python3 .qoder/skills/pgi-po-preprocessor/scripts/preprocess_po.py Game.po -o output -n 3000
```

## Constraints

- Original files are never modified.
- Output files are named `<basename>_part<NNN>.<ext>` (e.g., `Game_part001.po`).
- Requires Python 3.6+.
