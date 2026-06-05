"""List pack status across the workspace + DB.

Scans pack files and queries the DB to show which packs are created,
preprocessed, translated, exported to CSV, and applied.
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
PACK_RE = re.compile(r"^pack_(\d{4})\.json$")


def collect_pack_indices(workspace: str):
    """Return sorted list of pack indices found in packs/ directory."""
    pack_dir = os.path.join(workspace, PACK_DIR)
    if not os.path.isdir(pack_dir):
        return []
    indices = set()
    for name in os.listdir(pack_dir):
        m = PACK_RE.match(name)
        if m:
            indices.add(int(m.group(1)))
    return sorted(indices)


def read_keys_from_file(path: str):
    """Read keys from JSON or CSV pack file."""
    if not os.path.isfile(path):
        return []
    if path.endswith(".csv"):
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            return [(row.get("Key") or "").strip() for row in reader if (row.get("Key") or "").strip()]
    else:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = data.get("entries", [])
        if isinstance(data, list):
            return [str(item.get("Key", "")).strip() for item in data if item.get("Key")]
    return []


def get_pack_keys(workspace: str, index: int):
    """Return list of keys for a pack, preferring the most processed file available."""
    pack_dir = os.path.join(workspace, PACK_DIR)
    for suffix in (".review.csv", ".preprocessed.json", ".json"):
        path = os.path.join(pack_dir, f"pack_{index:04d}{suffix}")
        keys = read_keys_from_file(path)
        if keys:
            return keys
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--detail", action="store_true", help="Show per-pack key details")
    args = ap.parse_args()

    config = load_config(args.workspace)

    indices = collect_pack_indices(args.workspace)
    if not indices:
        print("[list_packs] No packs found in workspace.")
        return

    conn = open_db(args.workspace, config["db_name"])
    ensure_schema(conn)
    cur = conn.cursor()

    max_index = max(indices)
    total_created = 0
    total_applied = 0
    total_partial = 0
    next_uncreated = None

    pack_dir = os.path.join(args.workspace, PACK_DIR)
    print("-" * 80)
    for idx in range(max_index + 1):
        has_created = os.path.isfile(os.path.join(pack_dir, f"pack_{idx:04d}.json"))
        has_preprocessed = os.path.isfile(os.path.join(pack_dir, f"pack_{idx:04d}.preprocessed.json"))
        has_translated = os.path.isfile(os.path.join(pack_dir, f"pack_{idx:04d}.translated.json"))
        has_csv = os.path.isfile(os.path.join(pack_dir, f"pack_{idx:04d}.review.csv"))

        if not has_created:
            if next_uncreated is None:
                next_uncreated = idx
            print(f"[pack {idx:04d}] not created")
            continue

        total_created += 1
        keys = get_pack_keys(args.workspace, idx)
        key_count = len(keys)

        translated_count = 0
        if keys:
            placeholders = ",".join("?" * len(keys))
            cur.execute(
                f"SELECT COUNT(*) FROM translations WHERE Key IN ({placeholders}) AND isTranslated = 1",
                tuple(keys),
            )
            translated_count = cur.fetchone()[0]

        if translated_count == key_count and key_count > 0:
            applied_mark = "applied {}/{} ✓".format(translated_count, key_count)
            total_applied += 1
        elif translated_count > 0:
            applied_mark = "applied {}/{} partial".format(translated_count, key_count)
            total_partial += 1
        else:
            applied_mark = "applied 0/{}".format(key_count)

        status_parts = [
            "created ✓" if has_created else "created -",
            "preprocessed ✓" if has_preprocessed else "preprocessed -",
            "translated ✓" if has_translated else "translated -",
            "exported ✓" if has_csv else "exported -",
            applied_mark,
        ]
        print(f"[pack {idx:04d}] {' | '.join(status_parts)}")

        if args.detail and keys:
            # Show which individual keys are pending
            placeholders = ",".join("?" * len(keys))
            cur.execute(
                f"SELECT Key FROM translations WHERE Key IN ({placeholders}) AND isTranslated = 0",
                tuple(keys),
            )
            pending_keys = [r[0] for r in cur.fetchall()]
            if pending_keys:
                print(f"         pending keys ({len(pending_keys)}): {', '.join(pending_keys[:10])}{'...' if len(pending_keys) > 10 else ''}")

    print("-" * 80)

    # DB-wide summary
    cur.execute("SELECT COUNT(*) FROM translations WHERE isTranslated = 0 AND hasPlaceholder = 0")
    remaining_valid = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM translations WHERE isTranslated = 1")
    total_translated = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM translations")
    total_rows = cur.fetchone()[0]
    conn.close()

    print("Summary:")
    print(f"  Total packs created:        {total_created}")
    print(f"  Packs fully applied:        {total_applied}")
    print(f"  Packs partially applied:    {total_partial}")
    print(f"  Packs pending:              {total_created - total_applied - total_partial}")
    print(f"  DB translated rows:         {total_translated} / {total_rows}")
    print(f"  DB remaining valid rows:    {remaining_valid}")
    if next_uncreated is not None:
        print(f"  Next pack index to create:  {next_uncreated}")
    else:
        print(f"  Next pack index to create:  {max_index + 1} (all indices up to {max_index} are created)")


if __name__ == "__main__":
    main()
