"""Stage 6: dedup pack entries against existing DB translations and inline-substitute terminology.

Outputs pack_<I>.preprocessed.json shaped:
    [{"Key": "...", "msgid": "<original>", "source_for_llm": "<after substitution>"}]
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.db import open_db, ensure_schema  # noqa: E402
from common.nlp import tokenize  # noqa: E402


def load_terminology(cur):
    """Return list of (term, translation) sorted by term length DESC for greedy match."""
    cur.execute(
        "SELECT term, translation FROM terminology "
        "WHERE translation IS NOT NULL AND translation != ''"
    )
    rows = cur.fetchall()
    rows.sort(key=lambda r: -len(r[0]))
    return rows


def substitute_terms(msgid: str, terms):
    """Greedy non-overlapping case-insensitive substitution over token spans.
    Walks the token list, tries longest matching term (1..3 tokens) at each position.
    """
    toks = tokenize(msgid)
    if not toks:
        return msgid

    term_lookup = {}
    for term, translation in terms:
        term_lookup.setdefault(term.lower(), translation)

    out_pieces = []
    cursor = 0
    i = 0
    while i < len(toks):
        matched_n = 0
        matched_translation = None
        for n in (3, 2, 1):
            if i + n > len(toks):
                continue
            phrase = " ".join(t[0] for t in toks[i:i + n]).lower()
            if phrase in term_lookup:
                matched_n = n
                matched_translation = term_lookup[phrase]
                break
        if matched_n:
            start = toks[i][1]
            end = toks[i + matched_n - 1][2]
            out_pieces.append(msgid[cursor:start])
            out_pieces.append(matched_translation)
            cursor = end
            i += matched_n
        else:
            i += 1
    out_pieces.append(msgid[cursor:])
    return "".join(out_pieces)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--index", type=int, required=True)
    args = ap.parse_args()

    pack_path = os.path.join(args.workspace, f"pack_{args.index}.json")
    if not os.path.isfile(pack_path):
        print(f"[stage6] ERROR: missing {pack_path}", file=sys.stderr)
        sys.exit(1)
    with open(pack_path, "r", encoding="utf-8") as f:
        pack = json.load(f)

    conn = open_db(args.workspace)
    ensure_schema(conn)
    cur = conn.cursor()
    terms = load_terminology(cur)
    print(f"[stage6] loaded {len(terms)} terminology entries with translations")

    cur.execute("BEGIN")
    deduped = 0
    out = []
    for i, entry in enumerate(pack, 1):
        msgid = entry["msgid"]
        key = entry["Key"]
        cur.execute(
            "SELECT msgstr FROM translations "
            "WHERE msgid = ? AND isTranslated = 1 AND Key != ? LIMIT 1",
            (msgid, key),
        )
        twin = cur.fetchone()
        if twin and twin[0]:
            cur.execute(
                "UPDATE translations SET msgstr = ?, isTranslated = 1 WHERE Key = ?",
                (twin[0], key),
            )
            deduped += 1
            continue
        substituted = substitute_terms(msgid, terms) if terms else msgid
        out.append({
            "Key": key,
            "msgid": msgid,
            "source_for_llm": substituted,
        })
        if i % 50 == 0:
            print(f"[stage6] processed {i}/{len(pack)}")
    conn.commit()
    conn.close()

    out_path = os.path.join(args.workspace, f"pack_{args.index}.preprocessed.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"[stage6] DONE — input={len(pack)} deduped_into_db={deduped} forwarded_to_llm={len(out)}")
    print(f"[stage6] wrote {out_path}")


if __name__ == "__main__":
    main()
