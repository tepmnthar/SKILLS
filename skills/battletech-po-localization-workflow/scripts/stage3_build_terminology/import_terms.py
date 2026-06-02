"""Stage 3c: import filtered_terms.json into terminology table (translation NULL)."""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.db import open_db, ensure_schema  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    args = ap.parse_args()

    src = os.path.join(args.workspace, "filtered_terms.json")
    if not os.path.isfile(src):
        print(f"[stage3c] ERROR: missing {src} (LLM filter step not done)", file=sys.stderr)
        sys.exit(1)
    with open(src, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = open_db(args.workspace)
    ensure_schema(conn)
    cur = conn.cursor()
    inserted = 0
    skipped = 0
    cur.execute("BEGIN")
    for i, item in enumerate(data, 1):
        term = item.get("term", "").strip()
        if not term:
            continue
        cur.execute("SELECT 1 FROM terminology WHERE term = ?", (term,))
        if cur.fetchone():
            skipped += 1
        else:
            cur.execute("INSERT INTO terminology (term, translation) VALUES (?, NULL)", (term,))
            inserted += 1
        if i % 200 == 0:
            print(f"[stage3c] processed {i}/{len(data)}")
    conn.commit()
    print(f"[stage3c] DONE — inserted={inserted} skipped(existing)={skipped} total_input={len(data)}")
    conn.close()


if __name__ == "__main__":
    main()
