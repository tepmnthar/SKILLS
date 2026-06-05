"""Stage 3c: export filtered_terms.json + term_candidates.json to terminology.csv.

The CSV includes freq and sample columns for context, plus an empty translation
column for the user to fill in using a spreadsheet editor.
"""
import argparse
import csv
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.config import load_config  # noqa: E402

CSV_COLUMNS = ["term", "freq", "sample1", "sample2", "sample3", "translation"]


def clean_sample(text: str, term: str, window: int = 60) -> str:
    """Normalize newlines and return a short snippet around the first occurrence of term."""
    if not text:
        return ""
    # Collapse all line breaks to a single space so CSV rows stay intact
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    text = " ".join(text.split())  # collapse multiple spaces
    if not term:
        return text[: window * 2]
    idx = text.lower().find(term.lower())
    if idx == -1:
        return text[: window * 2]
    start = max(0, idx - window)
    end = min(len(text), idx + len(term) + window)
    snippet = text[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    args = ap.parse_args()

    config = load_config(args.workspace)

    filtered_path = os.path.join(args.workspace, "filtered_terms.json")
    candidates_path = os.path.join(args.workspace, "term_candidates.json")
    for label, path in [("filtered_terms.json", filtered_path),
                        ("term_candidates.json", candidates_path)]:
        if not os.path.isfile(path):
            print(f"[stage3c-export] ERROR: missing {path} ({label} not found)", file=sys.stderr)
            sys.exit(1)

    with open(filtered_path, "r", encoding="utf-8") as f:
        filtered = json.load(f)

    candidates_lookup = {}
    with open(candidates_path, "r", encoding="utf-8") as f:
        for item in json.load(f):
            candidates_lookup[item["term"]] = item

    out_path = os.path.join(args.workspace, "terminology.csv")
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for item in filtered:
            term = item.get("term", "").strip()
            if not term:
                continue
            cand = candidates_lookup.get(term, {})
            raw_samples = cand.get("samples", [])
            samples = [clean_sample(s, term) for s in raw_samples]
            translation = item.get("translation", "")
            writer.writerow({
                "term": term,
                "freq": cand.get("freq", 0),
                "sample1": samples[0] if len(samples) > 0 else "",
                "sample2": samples[1] if len(samples) > 1 else "",
                "sample3": samples[2] if len(samples) > 2 else "",
                "translation": translation if translation else "",
            })

    print(f"[stage3c-export] DONE — wrote {len(filtered)} terms to {out_path}")
    print("[stage3c-export] NEXT: open terminology.csv in a spreadsheet editor, fill in the translation column, then run import_terms_csv.py")


if __name__ == "__main__":
    main()
