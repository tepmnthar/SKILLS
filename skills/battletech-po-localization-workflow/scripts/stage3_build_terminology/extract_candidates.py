"""Stage 3a: mine candidate terms from translations (no LLM).

Reads all hasPlaceholder=0 rows, builds 1-3 gram frequency over English msgids,
keeps top 500 (default), attaches up to 3 sample sentences. Writes term_candidates.json.
"""
import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.db import open_db, ensure_schema  # noqa: E402
from common.nlp import tokenize, ngrams, is_meaningful  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--top", type=int, default=500)
    ap.add_argument("--max-samples", type=int, default=3)
    args = ap.parse_args()

    conn = open_db(args.workspace)
    ensure_schema(conn)
    cur = conn.cursor()
    cur.execute("SELECT msgid FROM translations WHERE hasPlaceholder = 0")

    counter = Counter()
    samples = defaultdict(list)
    n = 0
    for (msgid,) in cur.fetchall():
        if not msgid:
            continue
        toks = tokenize(msgid)
        seen_in_row = set()
        for phrase, window in ngrams(toks, 1, 3):
            if not is_meaningful(window[0][0]) or not is_meaningful(window[-1][0]):
                continue
            if phrase in seen_in_row:
                continue
            seen_in_row.add(phrase)
            counter[phrase] += 1
            if len(samples[phrase]) < args.max_samples:
                samples[phrase].append(msgid)
        n += 1
        if n % 500 == 0:
            print(f"[stage3a] scanned {n} rows; phrases so far: {len(counter)}")

    top = counter.most_common(args.top)
    out = [
        {"term": phrase, "freq": freq, "samples": samples[phrase]}
        for phrase, freq in top
    ]
    out_path = os.path.join(args.workspace, "term_candidates.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[stage3a] DONE — wrote {len(out)} candidates (of {len(counter)} unique phrases) to {out_path}")
    print("[stage3a] NEXT: hand candidates + llm_filter_prompt.md to LLM, save filtered_terms.json")
    conn.close()


if __name__ == "__main__":
    main()
