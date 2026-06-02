"""Lightweight tokenizer / phrase enumerator. Stdlib only."""
import re

# Compact stopword list — generic English fillers we don't want as terms.
STOPWORDS = frozenset("""
a an the and or but if then else of to in on at by for with from as is are was were be been being
have has had do does did will would shall should can could may might must not no nor so than that
this these those there here it its his her their our your my you he she we they them us him me i
into onto upon over under above below between within without about against during before after while
when where why how which who whom whose what each every any all some many much few both either neither
just only also too very more most less least same other another such own same one two three four five six seven
eight nine ten new old up down out off back end start go come get got make made take took give gave keep kept
also yet still even ever never always often sometimes maybe perhaps thus hence therefore however moreover
""".split())

# Token = run of ASCII letters / digits / apostrophes / hyphens / inner dots.
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9'\-]*")


def tokenize(text: str):
    """Return list of (token, start, end) preserving original casing for span replay."""
    return [(m.group(0), m.start(), m.end()) for m in TOKEN_RE.finditer(text)]


def is_meaningful(tok: str) -> bool:
    low = tok.lower()
    if len(low) < 3:
        return False
    if low in STOPWORDS:
        return False
    if low.isdigit():
        return False
    return True


def ngrams(tokens, n_min=1, n_max=3):
    """Yield (phrase_lower, [tokens_with_spans]) for n in [n_min, n_max]."""
    spans = list(tokens)
    L = len(spans)
    for n in range(n_min, n_max + 1):
        for i in range(L - n + 1):
            window = spans[i:i + n]
            phrase = " ".join(t[0] for t in window).lower()
            yield phrase, window


def enumerate_candidate_phrases(text: str, n_min=1, n_max=3):
    """High-level: enumerate filtered candidate phrases for terminology mining.
    Drops any n-gram whose first or last token is a stopword/short token.
    Returns list of phrase strings (lowercased)."""
    toks = tokenize(text)
    out = []
    for phrase, window in ngrams(toks, n_min, n_max):
        if not is_meaningful(window[0][0]) or not is_meaningful(window[-1][0]):
            continue
        out.append(phrase)
    return out
