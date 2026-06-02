"""Stage 9: write the original PO back out, replacing msgstr from DB.

Skips re-writing entries with hasPlaceholder=1 — those stay as in the source PO.
"""
import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.db import open_db, ensure_schema  # noqa: E402


ESCAPE_RE = re.compile(r"\\(.)")
ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"'}


def unescape(s: str) -> str:
    return ESCAPE_RE.sub(lambda m: ESCAPES.get(m.group(1), m.group(1)), s)


def escape_for_po(s: str) -> str:
    out = s.replace("\\", "\\\\").replace('"', '\\"')
    out = out.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
    return out


def msgstr_lines(value: str):
    """Render a msgstr block. Multi-line (\\n bearing) values use the leading-empty form."""
    escaped = escape_for_po(value)
    if "\\n" in escaped and value:
        # Split on logical newlines from the original value.
        parts = value.split("\n")
        rendered = ['msgstr ""']
        for j, part in enumerate(parts):
            piece = escape_for_po(part)
            if j != len(parts) - 1:
                piece += "\\n"
            rendered.append(f'"{piece}"')
        return rendered
    return [f'msgstr "{escaped}"']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--po", required=True, help="original .po file (read-only source)")
    ap.add_argument("--out", required=True, help="output .po path")
    args = ap.parse_args()

    if not os.path.isfile(args.po):
        print(f"[stage9] ERROR: missing source {args.po}", file=sys.stderr)
        sys.exit(1)

    conn = open_db(args.workspace)
    ensure_schema(conn)
    cur = conn.cursor()

    with open(args.po, "r", encoding="utf-8") as f:
        lines = f.readlines()

    out_lines = []
    i = 0
    n = len(lines)
    cur_key = None
    blocks = 0
    written = 0
    skipped_placeholder = 0
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("#. Key:"):
            cur_key = stripped.split(":", 1)[1].strip()
            out_lines.append(line)
            i += 1
            continue
        if stripped.startswith("msgstr "):
            # Collect the original msgstr block extent.
            start = i
            i += 1
            while i < n and lines[i].lstrip().startswith('"'):
                i += 1
            blocks += 1
            db_row = None
            if cur_key:
                cur.execute(
                    "SELECT msgstr, hasPlaceholder, isTranslated FROM translations WHERE Key = ?",
                    (cur_key,),
                )
                db_row = cur.fetchone()
            if db_row is None:
                # Entry not in DB (e.g. header). Keep verbatim.
                out_lines.extend(lines[start:i])
            else:
                msgstr_val, has_ph, is_tr = db_row
                if has_ph:
                    out_lines.extend(lines[start:i])
                    skipped_placeholder += 1
                else:
                    new_lines = msgstr_lines(msgstr_val or "")
                    for nl in new_lines:
                        out_lines.append(nl + "\n")
                    written += 1
            cur_key = None
            if blocks % 500 == 0:
                print(f"[export] processed {blocks} blocks")
            continue
        out_lines.append(line)
        i += 1

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.writelines(out_lines)
    conn.close()
    print(f"[export] DONE — blocks={blocks} rewritten={written} kept_placeholder={skipped_placeholder}")
    print(f"[export] wrote {args.out}")


if __name__ == "__main__":
    main()
