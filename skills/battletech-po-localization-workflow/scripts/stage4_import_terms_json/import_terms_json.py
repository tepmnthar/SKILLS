"""Stage 4: import an external terms.json into terminology.

JSON shape: list of objects each containing "term" and "translation" keys.
- Insert if term is missing.
- Update translation only if the incoming value is non-empty (never blank an existing one).
"""
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
    ap.add_argument("--json", required=True)
    args = ap.parse_args()

    if not os.path.isfile(args.json):
        print(f"[stage4] ERROR: missing input json {args.json}", file=sys.stderr)
        sys.exit(1)
    with open(args.json, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        print("[stage4] ERROR: expected top-level JSON array", file=sys.stderr)
        sys.exit(1)

    conn = open_db(args.workspace)
    ensure_schema(conn)
    cur = conn.cursor()
    cur.execute("BEGIN")
    inserted = 0
    updated = 0
    skipped = 0
    for i, item in enumerate(data, 1):
        if not isinstance(item, dict):
            continue
        term = (item.get("term") or "").strip()
        translation = item.get("translation")
        if not term:
            continue
        cur.execute("SELECT translation FROM terminology WHERE term = ?", (term,))
        row = cur.fetchone()
        if row is None:
            cur.execute(
                "INSERT INTO terminology (term, translation) VALUES (?, ?)",
                (term, translation if (translation or "").strip() else None),
            )
            inserted += 1
        else:
            if translation and translation.strip():
                cur.execute(
                    "UPDATE terminology SET translation = ? WHERE term = ?",
                    (translation, term),
                )
                updated += 1
            else:
                skipped += 1
        if i % 500 == 0:
            print(f"[stage4] processed {i}/{len(data)}")
    conn.commit()

    cur.execute(
        "SELECT COUNT(*) FROM terminology WHERE translation IS NULL OR translation = ''"
    )
    null_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM terminology")
    total = cur.fetchone()[0]
    conn.close()

    print(f"[stage4] DONE — inserted={inserted} updated={updated} skipped(empty translation)={skipped}")
    print(f"[stage4] terminology now has {total} rows; {null_count} still have NULL/empty translation")
    print("[stage4] STOP — manually review the terminology table before running stage 5.")


if __name__ == "__main__":
    main()
