"""Stage 8: apply pack_<I>.translated.json back to translations table."""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.db import open_db, ensure_schema  # noqa: E402
from common.config import load_config  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--index", type=int, required=True)
    args = ap.parse_args()

    config = load_config(args.workspace)

    src = os.path.join(args.workspace, f"pack_{args.index}.translated.json")
    if not os.path.isfile(src):
        print(f"[stage8] ERROR: missing {src} (LLM stage 7 not done)", file=sys.stderr)
        sys.exit(1)
    with open(src, "r", encoding="utf-8") as f:
        rows = json.load(f)
    if not isinstance(rows, list):
        print("[stage8] ERROR: expected JSON array", file=sys.stderr)
        sys.exit(1)

    conn = open_db(args.workspace, config["db_name"])
    ensure_schema(conn)
    cur = conn.cursor()
    cur.execute("BEGIN")
    updated = 0
    missing = 0
    blank = 0
    for i, r in enumerate(rows, 1):
        key = r.get("Key")
        msgstr = r.get("msgstr")
        if not key:
            continue
        if msgstr is None or msgstr == "":
            blank += 1
            continue
        cur.execute(
            "UPDATE translations SET msgstr = ?, isTranslated = 1 WHERE Key = ?",
            (msgstr, key),
        )
        if cur.rowcount == 0:
            missing += 1
            print(f"[stage8] WARN: no row for Key={key}")
        else:
            updated += 1
        if i % 50 == 0:
            print(f"[stage8] processed {i}/{len(rows)}")
    conn.commit()
    conn.close()
    print(f"[stage8] DONE — updated={updated} missing={missing} blank_skipped={blank} input={len(rows)}")


if __name__ == "__main__":
    main()
