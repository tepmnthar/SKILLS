"""Stage 1: parse a .po file into entries.jsonl.

Each output line: {Key, SourceLocation, msgid, msgstr, isTranslated, hasPlaceholder}.
Stdlib regex parser — handles multi-line msgid/msgstr with C-style escapes.
"""
import argparse
import json
import os
import re
import sys

CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")
ESCAPE_RE = re.compile(r"\\(.)")
ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"'}


def unescape(s: str) -> str:
    return ESCAPE_RE.sub(lambda m: ESCAPES.get(m.group(1), m.group(1)), s)


def collect_string(lines, idx):
    """Parse a quoted-string sequence starting at lines[idx]. Returns (joined_unescaped, next_idx)."""
    parts = []
    line = lines[idx].rstrip("\n")
    # Strip leading keyword (msgid / msgstr / msgctxt) before first quote.
    first_q = line.find('"')
    if first_q < 0:
        return "", idx + 1
    parts.append(line[first_q + 1:line.rfind('"')])
    idx += 1
    while idx < len(lines):
        nxt = lines[idx].rstrip("\n")
        if not nxt.startswith('"'):
            break
        parts.append(nxt[1:nxt.rfind('"')])
        idx += 1
    return unescape("".join(parts)), idx


def parse_po(path: str):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    i = 0
    entries = []
    cur = {"Key": None, "SourceLocation": None, "msgid": None, "msgstr": None}
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("#. Key:"):
            cur["Key"] = stripped.split(":", 1)[1].strip()
            i += 1
        elif stripped.startswith("#. SourceLocation:"):
            cur["SourceLocation"] = stripped.split(":", 1)[1].strip()
            i += 1
        elif stripped.startswith("msgid "):
            cur["msgid"], i = collect_string(lines, i)
        elif stripped.startswith("msgstr "):
            cur["msgstr"], i = collect_string(lines, i)
            # End of entry — flush.
            if cur["Key"] and cur["msgid"] != "":
                entries.append(cur)
            cur = {"Key": None, "SourceLocation": None, "msgid": None, "msgstr": None}
        else:
            i += 1
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--po", required=True)
    ap.add_argument("--workspace", required=True)
    args = ap.parse_args()

    if not os.path.isfile(args.po):
        print(f"[extract] ERROR: po not found: {args.po}", file=sys.stderr)
        sys.exit(1)
    os.makedirs(args.workspace, exist_ok=True)

    print(f"[extract] parsing {args.po}")
    entries = parse_po(args.po)
    out_path = os.path.join(args.workspace, "entries.jsonl")
    n = 0
    translated = 0
    placeholder = 0
    with open(out_path, "w", encoding="utf-8") as out:
        for e in entries:
            msgid = e["msgid"] or ""
            msgstr = e["msgstr"] or ""
            is_tr = bool(CHINESE_RE.search(msgstr))
            has_ph = "{" in msgid and "}" in msgid
            row = {
                "Key": e["Key"],
                "SourceLocation": e["SourceLocation"] or "",
                "msgid": msgid,
                "msgstr": msgstr,
                "isTranslated": is_tr,
                "hasPlaceholder": has_ph,
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
            translated += int(is_tr)
            placeholder += int(has_ph)
            if n % 500 == 0:
                print(f"[extract] processed {n} entries")
    print(f"[extract] DONE — wrote {n} entries to {out_path}")
    print(f"[extract] stats: translated={translated} placeholder={placeholder} valid={n - translated - placeholder}")


if __name__ == "__main__":
    main()
