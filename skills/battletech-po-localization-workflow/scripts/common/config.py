"""Centralised configuration for the BattleTech PO workflow.

Reads <workspace>/config.json (if present) and merges over built-in defaults.
CLI args in individual scripts may still override these values.
"""
import json
import os
import sys

DEFAULTS = {
    "db_name": "localization.sqlite",
    "ngram_min": 1,
    "ngram_max": 3,
    "min_token_length": 3,
    "top_candidates": 500,
    "max_samples": 3,
    "pack_size": 50,
}

_INT_KEYS = {"ngram_min", "ngram_max", "min_token_length",
             "top_candidates", "max_samples", "pack_size"}
_STR_KEYS = {"db_name"}


def _validate(cfg: dict) -> dict:
    """Return a validated copy; invalid values fall back to defaults with a warning."""
    out = {}
    for key, default in DEFAULTS.items():
        val = cfg.get(key, default)
        if key in _INT_KEYS:
            try:
                val = int(val)
            except (TypeError, ValueError):
                print(f"[config] WARNING: invalid value for '{key}' (got {val!r}), using default {default}",
                      file=sys.stderr)
                val = default
            if val < 1:
                print(f"[config] WARNING: '{key}' must be >= 1 (got {val}), using default {default}",
                      file=sys.stderr)
                val = default
        elif key in _STR_KEYS:
            val = str(val) if val else default
        out[key] = val
    if out["ngram_max"] < out["ngram_min"]:
        print(f"[config] WARNING: ngram_max ({out['ngram_max']}) < ngram_min ({out['ngram_min']}), "
              f"resetting ngram_max to {out['ngram_min']}", file=sys.stderr)
        out["ngram_max"] = out["ngram_min"]
    return out


def load_config(workspace: str) -> dict:
    """Load <workspace>/config.json merged over DEFAULTS. Missing file = pure defaults."""
    cfg = dict(DEFAULTS)
    path = os.path.join(workspace, "config.json")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            user_cfg = json.load(f)
        if isinstance(user_cfg, dict):
            overrides = 0
            for key in DEFAULTS:
                if key in user_cfg:
                    cfg[key] = user_cfg[key]
                    overrides += 1
            cfg = _validate(cfg)
            print(f"[config] loaded {path} ({overrides} overrides)")
        else:
            print(f"[config] WARNING: {path} is not a JSON object, using defaults",
                  file=sys.stderr)
    return cfg
