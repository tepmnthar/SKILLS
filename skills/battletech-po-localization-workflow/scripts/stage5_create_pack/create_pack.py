"""Stage 5: slice valid (untranslated, no-placeholder) entries into packs.

Packs are written to <workspace>/packs/ so the root directory stays tidy.
Supports single-index mode (--index) or batch mode (--all).
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.db import open_db, ensure_schema  # noqa: E402
from common.config import load_config  # noqa: E402

PACK_DIR = "packs"


def write_pack(workspace: str, index: int, rows):
    pack = [
        {"Key": k, "msgid": mi, "msgstr": ms or ""}
        for (k, mi, ms) in rows
    ]
    pack_dir = os.path.join(workspace, PACK_DIR)
    os.makedirs(pack_dir, exist_ok=True)
    out_path = os.path.join(pack_dir, f"pack_{index:04d}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(pack, f, ensure_ascii=False, indent=2)
    return out_path, len(pack)


def create_single_pack(cur, workspace: str, index: int, size: int):
    offset = size * index
    cur.execute(
        "SELECT Key, msgid, msgstr FROM translations "
        "WHERE isTranslated = 0 AND hasPlaceholder = 0 "
        "ORDER BY Key ASC LIMIT ? OFFSET ?",
        (size, offset),
    )
    rows = cur.fetchall()
    out_path, count = write_pack(workspace, index, rows)
    return count, out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--size", type=int, default=None)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--index", type=int, default=None)
    g.add_argument("--all", action="store_true", help="Create all packs at once")
    args = ap.parse_args()

    config = load_config(args.workspace)
    size = args.size if args.size is not None else config["pack_size"]

    if size <= 0:
        print("[stage5] ERROR: --size must be > 0", file=sys.stderr)
        sys.exit(1)
    if args.index is not None and args.index < 0:
        print("[stage5] ERROR: --index must be >= 0", file=sys.stderr)
        sys.exit(1)

    conn = open_db(args.workspace, config["db_name"])
    ensure_schema(conn)
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM translations WHERE isTranslated = 0 AND hasPlaceholder = 0"
    )
    total_valid = cur.fetchone()[0]

    if args.all:
        index = 0
        total_written = 0
        while True:
            offset = size * index
            if offset >= total_valid:
                break
            count, out_path = create_single_pack(cur, args.workspace, index, size)
            remaining = max(0, total_valid - offset - count)
            print(f"[stage5] pack_{index:04d}: wrote {count} entries -> {out_path}")
            total_written += count
            index += 1
        print(f"[stage5] DONE — created {index} pack(s), total {total_written} entries")
    else:
        count, out_path = create_single_pack(cur, args.workspace, args.index, size)
        offset = size * args.index
        remaining_after = max(0, total_valid - offset - count)
        print(f"[stage5] DONE — wrote {count} entries to {out_path}")
        print(f"[stage5] valid rows total={total_valid} this_pack_offset={offset} remaining_after_this_pack={remaining_after}")
        if count == 0:
            print("[stage5] (empty pack — index past end; translation phase complete)")

    conn.close()


if __name__ == "__main__":
    main()
