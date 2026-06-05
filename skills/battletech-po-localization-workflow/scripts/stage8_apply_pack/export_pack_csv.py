"""Stage 8a: export pack_<I>.translated.json to pack_<I>.review.csv for human review.

Merges translated.json with preprocessed.json (for msgid),
producing a CSV the user can open in a spreadsheet editor to review or
 correct LLM translations.
"""
import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.config import load_config  # noqa: E402

PACK_DIR = "packs"
CSV_COLUMNS = ["Key", "msgid", "msgstr"]
PACK_RE = re.compile(r"^pack_(\d{4})\.translated\.json$")


def collect_pack_indices(pack_dir):
    indices = []
    for name in os.listdir(pack_dir):
        m = PACK_RE.match(name)
        if m:
            indices.append(int(m.group(1)))
    return sorted(indices)


def process_single_pack(workspace, index):
    pack_dir = os.path.join(workspace, PACK_DIR)
    translated_path = os.path.join(pack_dir, f"pack_{index:04d}.translated.json")
    preprocessed_path = os.path.join(pack_dir, f"pack_{index:04d}.preprocessed.json")

    if not os.path.isfile(translated_path):
        print(f"[stage8a] ERROR: missing {translated_path} (LLM stage 7 not done)", file=sys.stderr)
        sys.exit(1)

    with open(translated_path, "r", encoding="utf-8") as f:
        translated = json.load(f)
    if not isinstance(translated, list):
        print("[stage8a] ERROR: expected JSON array", file=sys.stderr)
        sys.exit(1)

    preproc_lookup = {}
    if os.path.isfile(preprocessed_path):
        with open(preprocessed_path, "r", encoding="utf-8") as f:
            preprocessed = json.load(f)
        entries = preprocessed.get("entries", []) if isinstance(preprocessed, dict) else preprocessed
        for item in entries:
            key = item.get("Key")
            if key:
                preproc_lookup[key] = item

    out_path = os.path.join(pack_dir, f"pack_{index:04d}.review.csv")
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for item in translated:
            key = item.get("Key", "").strip()
            if not key:
                continue
            pp = preproc_lookup.get(key, {})
            writer.writerow({
                "Key": key,
                "msgid": pp.get("msgid", ""),
                "msgstr": item.get("msgstr", ""),
            })

    print(f"[stage8a] DONE — wrote {len(translated)} rows to {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="export every pack that has a translated.json")
    group.add_argument("--index", type=int, help="export a single pack by index")
    args = ap.parse_args()

    load_config(args.workspace)

    pack_dir = os.path.join(args.workspace, PACK_DIR)

    if args.all:
        indices = collect_pack_indices(pack_dir)
        if not indices:
            print("[stage8a] ERROR: no translated packs found", file=sys.stderr)
            sys.exit(1)
        for idx in indices:
            process_single_pack(args.workspace, idx)
        print("[stage8a] NEXT: open the review CSVs in a spreadsheet editor, review/correct translations, then run apply_pack_csv.py")
    else:
        process_single_pack(args.workspace, args.index)
        print("[stage8a] NEXT: open the CSV in a spreadsheet editor, review/correct translations, then run apply_pack_csv.py")


if __name__ == "__main__":
    main()
