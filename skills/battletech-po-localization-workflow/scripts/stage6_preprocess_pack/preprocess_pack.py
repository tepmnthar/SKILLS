"""Stage 6: dedup pack entries against existing DB translations and extract matched terminology.

Outputs packs/pack_<I>.preprocessed.json shaped:
    [{"Key": "...", "msgid": "<original>", "matched_terms": [{"term": "...", "translation": "..."}]}]
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.db import open_db, ensure_schema  # noqa: E402
from common.nlp import tokenize  # noqa: E402
from common.config import load_config  # noqa: E402

PACK_DIR = "packs"


def load_terminology(cur):
    """Return list of (term, translation) sorted by term length DESC for greedy match."""
    cur.execute(
        "SELECT term, translation FROM terminology "
        "WHERE translation IS NOT NULL AND translation != ''"
    )
    rows = cur.fetchall()
    rows.sort(key=lambda r: -len(r[0]))
    return rows


def find_matched_terms(msgid: str, terms, n_max: int = 3):
    """Greedy non-overlapping case-insensitive term matching over token spans.
    Returns a list of {"term": <original>, "translation": <zh>} dicts found in msgid.
    """
    toks = tokenize(msgid)
    if not toks:
        return []

    # Build lookup: lower-case phrase -> (original_term, translation)
    term_lookup = {}
    for term, translation in terms:
        lc = term.lower()
        if lc not in term_lookup:
            term_lookup[lc] = (term, translation)

    matched = []
    seen_terms = set()
    seen_positions = set()
    i = 0
    while i < len(toks):
        found_n = 0
        found_info = None
        for n in range(n_max, 0, -1):
            if i + n > len(toks):
                continue
            phrase = " ".join(t[0] for t in toks[i:i + n]).lower()
            if phrase in term_lookup:
                pos_range = range(i, i + n)
                if not any(p in seen_positions for p in pos_range):
                    found_n = n
                    found_info = term_lookup[phrase]
                    break
        if found_n:
            term_key = found_info[0].lower()
            if term_key not in seen_terms:
                matched.append({"term": found_info[0], "translation": found_info[1]})
                seen_terms.add(term_key)
            for p in range(i, i + found_n):
                seen_positions.add(p)
            i += found_n
        else:
            i += 1
    return matched


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


def process_single_pack(cur, terms, ngram_max, workspace: str, index: int):
    pack_path = os.path.join(workspace, PACK_DIR, f"pack_{index:04d}.json")
    if not os.path.isfile(pack_path):
        print(f"[stage6] ERROR: missing {pack_path}", file=sys.stderr)
        return 0, 0, None
    with open(pack_path, "r", encoding="utf-8") as f:
        pack = json.load(f)

    deduped = 0
    entries = []
    pack_terms = {}
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
        matched = find_matched_terms(msgid, terms, ngram_max) if terms else []
        for m in matched:
            tk = m["term"].lower()
            if tk not in pack_terms:
                pack_terms[tk] = m
        entries.append({
            "Key": key,
            "msgid": msgid,
        })
        if i % 50 == 0:
            print(f"[stage6] processed {i}/{len(pack)}")

    out_data = {
        "matched_terms": list(pack_terms.values()),
        "entries": entries,
    }
    out_path = os.path.join(workspace, PACK_DIR, f"pack_{index:04d}.preprocessed.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out_data, f, ensure_ascii=False, indent=2)

    return len(pack), deduped, out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--index", type=int, default=None)
    g.add_argument("--all", action="store_true", help="Preprocess all packs at once")
    args = ap.parse_args()

    config = load_config(args.workspace)

    conn = open_db(args.workspace, config["db_name"])
    ensure_schema(conn)
    cur = conn.cursor()
    terms = load_terminology(cur)
    print(f"[stage6] loaded {len(terms)} terminology entries with translations")

    if args.all:
        indices = collect_pack_indices(args.workspace)
        if not indices:
            print("[stage6] No packs found to preprocess.")
            conn.close()
            return
        total_input = 0
        total_deduped = 0
        cur.execute("BEGIN")
        for idx in indices:
            pack_len, deduped, out_path = process_single_pack(cur, terms, config["ngram_max"], args.workspace, idx)
            total_input += pack_len
            total_deduped += deduped
            print(f"[stage6] pack_{idx:04d}: input={pack_len} deduped={deduped} -> {out_path}")
        conn.commit()
        conn.close()
        print(f"[stage6] DONE — total_input={total_input} total_deduped={total_deduped} packs={len(indices)}")
    else:
        cur.execute("BEGIN")
        pack_len, deduped, out_path = process_single_pack(cur, terms, config["ngram_max"], args.workspace, args.index)
        conn.commit()
        conn.close()
        if out_path:
            forwarded = pack_len - deduped
            print(f"[stage6] DONE — input={pack_len} deduped_into_db={deduped} forwarded_to_llm={forwarded}")
            print(f"[stage6] wrote {out_path}")


if __name__ == "__main__":
    main()
