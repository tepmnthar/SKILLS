"""Stage 2: load entries.jsonl into localization.sqlite::translations."""
import argparse
import json
import os
import sys
from pathlib import Path

# Allow `python3 stage2_init_db/load_db.py` run directly: add scripts/ to path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.db import open_db, ensure_schema  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    args = ap.parse_args()

    src = os.path.join(args.workspace, "entries.jsonl")
    if not os.path.isfile(src):
        print(f"[db] ERROR: missing {src} (run stage 1 first)", file=sys.stderr)
        sys.exit(1)

    conn = open_db(args.workspace)
    ensure_schema(conn)

    rows = []
    with open(src, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            rows.append((
                r["Key"],
                r.get("SourceLocation", ""),
                r["msgid"],
                r.get("msgstr", ""),
                1 if r.get("isTranslated") else 0,
                1 if r.get("hasPlaceholder") else 0,
            ))

    total = len(rows)
    print(f"[db] loading {total} rows into translations")
    cur = conn.cursor()
    cur.execute("BEGIN")
    inserted = 0
    for row in rows:
        cur.execute(
            "INSERT OR REPLACE INTO translations "
            "(Key, SourceLocation, msgid, msgstr, isTranslated, hasPlaceholder) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            row,
        )
        inserted += 1
        if inserted % 500 == 0:
            print(f"[db] inserted {inserted}/{total}")
    conn.commit()
    print(f"[db] DONE — {inserted}/{total} rows committed")
    conn.close()


if __name__ == "__main__":
    main()
