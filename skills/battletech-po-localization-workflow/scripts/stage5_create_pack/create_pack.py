"""Stage 5: slice the next pack of valid (untranslated, no-placeholder) entries."""
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
    ap.add_argument("--size", type=int, default=50)
    ap.add_argument("--index", type=int, required=True)
    args = ap.parse_args()

    if args.size <= 0:
        print("[stage5] ERROR: --size must be > 0", file=sys.stderr)
        sys.exit(1)
    if args.index < 0:
        print("[stage5] ERROR: --index must be >= 0", file=sys.stderr)
        sys.exit(1)

    conn = open_db(args.workspace)
    ensure_schema(conn)
    cur = conn.cursor()
    offset = args.size * args.index
    cur.execute(
        "SELECT Key, SourceLocation, msgid, msgstr FROM translations "
        "WHERE isTranslated = 0 AND hasPlaceholder = 0 "
        "ORDER BY Key ASC LIMIT ? OFFSET ?",
        (args.size, offset),
    )
    rows = cur.fetchall()
    cur.execute(
        "SELECT COUNT(*) FROM translations WHERE isTranslated = 0 AND hasPlaceholder = 0"
    )
    total_valid = cur.fetchone()[0]

    pack = [
        {"Key": k, "SourceLocation": sl, "msgid": mi, "msgstr": ms or ""}
        for (k, sl, mi, ms) in rows
    ]
    out_path = os.path.join(args.workspace, f"pack_{args.index}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(pack, f, ensure_ascii=False, indent=2)

    remaining_after = max(0, total_valid - offset - len(pack))
    print(f"[stage5] DONE — wrote {len(pack)} entries to {out_path}")
    print(f"[stage5] valid rows total={total_valid} this_pack_offset={offset} remaining_after_this_pack={remaining_after}")
    if len(pack) == 0:
        print("[stage5] (empty pack — index past end; translation phase complete)")
    conn.close()


if __name__ == "__main__":
    main()
