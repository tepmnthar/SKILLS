"""Stage 8b: apply pack_<I>.review.csv back to the translations table.

Reads the user-reviewed CSV and UPDATEs translations.msgstr / isTranslated.
Blank msgstr values are skipped (not marked translated).
"""
import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.db import open_db, ensure_schema  # noqa: E402
from common.config import load_config  # noqa: E402

PACK_DIR = "packs"
PACK_RE = re.compile(r"^pack_(\d{4})\.review\.csv$")


def collect_pack_indices(pack_dir):
    indices = []
    for name in os.listdir(pack_dir):
        m = PACK_RE.match(name)
        if m:
            indices.append(int(m.group(1)))
    return sorted(indices)


def process_single_pack(workspace, index, conn, cur):
    csv_path = os.path.join(workspace, PACK_DIR, f"pack_{index:04d}.review.csv")
    if not os.path.isfile(csv_path):
        print(f"[stage8b] ERROR: missing {csv_path} (run export_pack_csv.py first)", file=sys.stderr)
        sys.exit(1)

    preprocessed_path = os.path.join(workspace, PACK_DIR, f"pack_{index:04d}.preprocessed.json")
    msgid_lookup = {}
    if os.path.isfile(preprocessed_path):
        with open(preprocessed_path, "r", encoding="utf-8") as f:
            preprocessed = json.load(f)
        if isinstance(preprocessed, list):
            for item in preprocessed:
                k = item.get("Key")
                if k:
                    msgid_lookup[k] = item.get("msgid", "")

    updated = 0
    blank_skipped = 0
    unchanged_skipped = 0
    missing = 0
    total = 0

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        if "Key" not in fieldnames or "msgstr" not in fieldnames:
            print("[stage8b] ERROR: CSV missing required 'Key' or 'msgstr' column", file=sys.stderr)
            sys.exit(1)

        for row in reader:
            total += 1
            key = (row.get("Key") or "").strip()
            if not key:
                continue
            msgstr = (row.get("msgstr") or "").strip()
            if not msgstr:
                blank_skipped += 1
                continue
            if msgstr == msgid_lookup.get(key, ""):
                unchanged_skipped += 1
                continue
            cur.execute(
                "UPDATE translations SET msgstr = ?, isTranslated = 1 WHERE Key = ?",
                (msgstr, key),
            )
            if cur.rowcount == 0:
                missing += 1
                print(f"[stage8b] WARN: no row for Key={key}")
            else:
                updated += 1
            if total % 50 == 0:
                print(f"[stage8b] processed {total}")

    print(f"[stage8b] pack {index:04d} — updated={updated} blank_skipped={blank_skipped} unchanged_skipped={unchanged_skipped} missing={missing} total_rows={total}")
    return updated, blank_skipped, unchanged_skipped, missing, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="apply every pack that has a review.csv")
    group.add_argument("--index", type=int, help="apply a single pack by index")
    args = ap.parse_args()

    config = load_config(args.workspace)
    pack_dir = os.path.join(args.workspace, PACK_DIR)

    conn = open_db(args.workspace, config["db_name"])
    ensure_schema(conn)
    cur = conn.cursor()

    if args.all:
        indices = collect_pack_indices(pack_dir)
        if not indices:
            print("[stage8b] ERROR: no review CSVs found", file=sys.stderr)
            sys.exit(1)
        cur.execute("BEGIN")
        for idx in indices:
            process_single_pack(args.workspace, idx, conn, cur)
        conn.commit()
        print(f"[stage8b] DONE — applied {len(indices)} packs")
    else:
        cur.execute("BEGIN")
        process_single_pack(args.workspace, args.index, conn, cur)
        conn.commit()
        print("[stage8b] DONE")

    conn.close()


if __name__ == "__main__":
    main()
