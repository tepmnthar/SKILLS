"""Stage 3d: import terminology.csv into the terminology table.

Merge logic:
- CSV term has non-empty translation -> INSERT new or UPDATE existing (overwrite).
- CSV term has empty translation -> INSERT new (NULL translation), but NEVER
  overwrite an existing non-empty translation in the DB.
"""
import argparse
import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.db import open_db, ensure_schema  # noqa: E402
from common.config import load_config  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--csv", default=None,
                    help="Path to CSV file (default: <workspace>/terminology.csv)")
    args = ap.parse_args()

    config = load_config(args.workspace)

    csv_path = args.csv if args.csv else os.path.join(args.workspace, "terminology.csv")
    if not os.path.isfile(csv_path):
        print(f"[stage3d] ERROR: missing {csv_path}", file=sys.stderr)
        sys.exit(1)

    conn = open_db(args.workspace, config["db_name"])
    ensure_schema(conn)
    cur = conn.cursor()

    inserted = 0
    updated = 0
    skipped_empty = 0
    total = 0

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if "term" not in (reader.fieldnames or []):
            print("[stage3d] ERROR: CSV missing required 'term' column", file=sys.stderr)
            sys.exit(1)

        cur.execute("BEGIN")
        for row in reader:
            total += 1
            term = (row.get("term") or "").strip()
            if not term:
                continue
            translation = (row.get("translation") or "").strip()

            cur.execute("SELECT translation FROM terminology WHERE term = ?", (term,))
            existing = cur.fetchone()

            if translation:
                if existing is None:
                    cur.execute(
                        "INSERT INTO terminology (term, translation) VALUES (?, ?)",
                        (term, translation),
                    )
                    inserted += 1
                else:
                    cur.execute(
                        "UPDATE terminology SET translation = ? WHERE term = ?",
                        (translation, term),
                    )
                    updated += 1
            else:
                if existing is None:
                    cur.execute(
                        "INSERT INTO terminology (term, translation) VALUES (?, NULL)",
                        (term,),
                    )
                    inserted += 1
                else:
                    skipped_empty += 1

            if total % 200 == 0:
                print(f"[stage3d] processed {total} rows")

    conn.commit()

    cur.execute(
        "SELECT COUNT(*) FROM terminology WHERE translation IS NULL OR translation = ''"
    )
    null_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM terminology")
    db_total = cur.fetchone()[0]
    conn.close()

    print(f"[stage3d] DONE — inserted={inserted} updated={updated} skipped_empty={skipped_empty} total_csv_rows={total}")
    print(f"[stage3d] terminology now has {db_total} rows; {null_count} still have NULL/empty translation")


if __name__ == "__main__":
    main()
