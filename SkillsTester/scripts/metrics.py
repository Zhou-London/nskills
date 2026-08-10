#!/usr/bin/env python3
"""Semantic-density and register metrics for the comment-skill evals.

Two subcommands:

  score <path>...   Recompute the mechanical half of every metrics.json under
                    <path> (comment words, per-file density, register lint) and
                    leave the judged half — semantic_units, unit_list/unit_notes,
                    tone.score, tone.violations, tone.notes — exactly as written.

  check <path>...   Print the per-eval comparison (SD, units, words, tone) and
                    verdicts against the thresholds in eval_metadata.json.
                    Exits non-zero when a threshold is missed.

The word counter mirrors web/lib/comments.ts so the UI and the recorded metrics
can never disagree. See rubrics/semantic-density.md for what a semantic unit is
and how the thresholds are meant to be read.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

C_EXT = {
    "c", "h", "hh", "hpp", "cc", "cpp", "cxx", "cu", "java", "js", "jsx", "ts",
    "tsx", "go", "rs", "swift", "kt", "cs", "scala", "proto",
}
PY_EXT = {"py", "pyi", "pyx"}

CONFIGS = ["with_skill", "without_skill"]

# Fallback for an eval whose metadata carries no `metrics.thresholds` block.
# See rubrics/semantic-density.md for where the numbers come from.
DEFAULT_THRESHOLDS = {
    "with_skill": {"min_density": 7.5, "min_tone": 4},
}


# --------------------------------------------------------------------------
# Lexing: which characters of a file are comment, and how many words they hold
# --------------------------------------------------------------------------

def lang_of(name: str) -> str:
    """Comment syntax family for a file name, or "text" when it has none."""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext in C_EXT:
        return "c"
    if ext in PY_EXT:
        return "py"
    return "text"


def comment_mask(src: str, lang: str) -> bytearray:
    """Marks every character of `src` that belongs to a comment.

    String literals are tracked so that a `//` or `#` inside one is not mistaken
    for a comment. Python triple-quoted strings count as comments, which is what
    makes docstrings measurable as documentation.
    """
    mask = bytearray(len(src))
    if lang == "text":
        return mask
    i, n = 0, len(src)
    while i < n:
        ch = src[i]
        two = src[i:i + 2]
        three = src[i:i + 3]
        if lang == "c" and two == "//":
            while i < n and src[i] != "\n":
                mask[i] = 1
                i += 1
            continue
        if lang == "c" and two == "/*":
            end = src.find("*/", i + 2)
            stop = n if end == -1 else end + 2
            while i < stop:
                mask[i] = 1
                i += 1
            continue
        if lang == "py" and ch == "#":
            while i < n and src[i] != "\n":
                mask[i] = 1
                i += 1
            continue
        if lang == "py" and three in ('"""', "'''"):
            end = src.find(three, i + 3)
            stop = n if end == -1 else end + 3
            while i < stop:
                mask[i] = 1
                i += 1
            continue
        if ch in ('"', "'"):
            # Skip the literal without marking it, honouring backslash escapes.
            i += 1
            while i < n and src[i] != ch and src[i] != "\n":
                i += 2 if src[i] == "\\" else 1
            i += 1
            continue
        i += 1
    return mask


MARKERS = re.compile(r"^[\s/*#\"']+|[\s/*\"']+$")
CJK = re.compile(r"[㐀-䶿一-鿿豈-﫿぀-ヿ]")


LICENSE = re.compile(
    r"(copyright|licensed under|license at|WITHOUT WARRANTIES|SPDX-|"
    r"apache\.org/licenses|all rights reserved)", re.I)


def count_words(text: str) -> int:
    """Words of prose, counting each CJK character as one word.

    Whitespace splitting alone would score a 40-character Chinese sentence as a
    single word, so densities would not be comparable across languages. They
    still only compare meaningfully *within* one language.
    """
    cjk = len(CJK.findall(text))
    latin = [t for t in CJK.sub(" ", text).split() if t]
    return cjk + len(latin)


def strip_license(lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Drops a leading license header.

    Both skills tell the agent to copy the project's boilerplate from a
    neighbouring file, so those ~120 words are not the run's prose: counting
    them would let a header dilute a file's density by a third.
    """
    if not lines or lines[0][0] > 6:
        return lines
    end = 0
    while end + 1 < len(lines) and lines[end + 1][0] <= lines[end][0] + 2:
        end += 1
    block = lines[: end + 1]
    return lines[end + 1:] if any(LICENSE.search(t) for _, t in block) else lines


def prose_lines(content: str, lang: str) -> list[tuple[int, str]]:
    """(line number, comment prose) for every line carrying a comment.

    For a prose file every non-empty line is returned, minus fenced code blocks,
    which are evidence rather than register.
    """
    out: list[tuple[int, str]] = []
    if lang == "text":
        fenced = False
        for n, raw in enumerate(content.splitlines(), 1):
            if raw.lstrip().startswith("```"):
                fenced = not fenced
                continue
            if not fenced and raw.strip():
                out.append((n, raw.strip()))
        return out
    mask = comment_mask(content, lang)
    pos = 0
    for n, raw in enumerate(content.split("\n"), 1):
        seg = "".join(
            raw[i] for i in range(len(raw)) if mask[pos + i] == 1
        )
        pos += len(raw) + 1
        seg = MARKERS.sub("", seg).strip()
        if seg:
            out.append((n, seg))
    return strip_license(out)


def word_total(content: str, lang: str) -> int:
    """Comment words of a code file; total words of a prose file."""
    if lang == "text":
        return count_words(content)
    return sum(count_words(p) for _, p in prose_lines(content, lang))


# --------------------------------------------------------------------------
# Register lint
# --------------------------------------------------------------------------

# (kind, severity, pattern). "hard" hits are near-certain register breaks;
# "soft" hits need a human look — "just" and "you" have honest uses. The lint is
# evidence for the tone score, never the score itself.
LINT_RULES: list[tuple[str, str, re.Pattern]] = [
    ("filler", "hard", re.compile(
        r"\b(basically|essentially|needless to say|as you can see|"
        r"it should be noted that|note that|of course)\b", re.I)),
    ("filler", "soft", re.compile(
        r"\b(simply|just|actually|in fact|obviously)\b", re.I)),
    ("hedge", "hard", re.compile(
        r"\b(should probably|i think|for some reason|hopefully|somehow|"
        r"kinda|sorta)\b"
        # "the kind of failure" is ordinary English; only the hedging use fires.
        r"|\b(is|are|was|were|it's|be|seems|feels)\s+(kind|sort)\s+of\b", re.I)),
    ("hedge", "soft", re.compile(r"\b(maybe|presumably|apparently)\b", re.I)),
    ("chatty", "hard", re.compile(
        r"(\blet's\b|\bwe'll\b|\bdon't worry\b|\bfeel free\b|\bas promised\b|"
        r"\bgo ahead and\b)", re.I)),
    ("chatty", "soft", re.compile(r"\b(you|your|you're|yours)\b", re.I)),
    ("cutesy", "hard", re.compile(
        r"\b(magic|magical|secret sauce|bad boy|sprinkle|awesome|nifty|voil|"
        r"boom|yay|neat trick|clever trick|fancy|beautiful)\b", re.I)),
    ("anthropomorphic", "soft", re.compile(
        r"\b(is happy to|are happy to|wants a|wants the|asks the|knows how to|"
        r"doesn't like|likes to)\b", re.I)),
    ("emotive", "hard", re.compile(
        # Sentence-final "!" only: `!Run(x)` and `!=` inside an example are code.
        r"(?<=[A-Za-z0-9,;:'\")])!(?=$|\s)"
        r"|:-?\)|:-?\(|;-?\)"
        r"|[\U0001F300-\U0001FAFF☀-➿❤️]"
        r"|[=*~]{4,}")),
    ("meta", "hard", re.compile(
        r"\b(hacky|hack around|ugly but|sorry|don't ask|shouldn't have to|"
        r"unfortunately we)\b", re.I)),
    ("intensifier", "soft", re.compile(
        r"\b(very|really|super|extremely|incredibly|a lot|huge|tons of|"
        r"blazing)\b", re.I)),
    ("restating", "soft", re.compile(
        r"(^this (function|method|class|module|file)\s+(is a|is an|is the|"
        r"does the|will)\b|\bis used to\b|\bthe purpose of this\b|"
        r"\bis a class that\b)", re.I)),
    # Chinese equivalents — the register rules survive translation.
    ("filler", "hard", re.compile(r"(基本上|其实|众所周知|显然|简单来说|需要注意的是)")),
    ("hedge", "hard", re.compile(r"(大概|好像|貌似|可能吧|应该是吧)")),
    ("chatty", "hard", re.compile(r"(咱们|别担心|放心|你可以|大家)")),
    ("cutesy", "hard", re.compile(r"(神奇|魔法|超级|酷炫|完美|厉害|棒极了)")),
    ("emotive", "hard", re.compile(r"[！？]{1,}|[~～]{2,}")),
    ("restating", "soft", re.compile(r"(这个函数是|这个方法是|本函数|该函数用来)")),
]


def lint(content: str, lang: str, name: str) -> tuple[dict, list[dict]]:
    """Register lint over a file's comment prose. Returns (summary, hits)."""
    hits: list[dict] = []
    for line_no, text in prose_lines(content, lang):
        for kind, severity, pattern in LINT_RULES:
            m = pattern.search(text)
            if not m:
                continue
            hits.append({
                "file": name,
                "line": line_no,
                "kind": kind,
                "severity": severity,
                "match": m.group(0).strip(),
                "quote": text[:120],
            })
    by_kind: dict[str, int] = {}
    hard = 0
    for h in hits:
        by_kind[h["kind"]] = by_kind.get(h["kind"], 0) + 1
        if h["severity"] == "hard":
            hard += 1
    return {"hits": len(hits), "hard": hard, "by_kind": by_kind}, hits


# --------------------------------------------------------------------------
# Scoring a run
# --------------------------------------------------------------------------

def density(units, words) -> float | None:
    if units is None or not words:
        return None
    return round(units / words * 100, 1)


def find_runs(root: Path) -> list[Path]:
    """Run directories (those holding an outputs/) under `root`, sorted."""
    if (root / "outputs").is_dir():
        return [root]
    return sorted(p.parent for p in root.rglob("outputs") if p.is_dir())


def score_run(run_dir: Path) -> dict:
    """Rewrites run_dir/metrics.json, preserving every judged field."""
    path = run_dir / "metrics.json"
    prev = {}
    if path.exists():
        prev = json.loads(path.read_text())
    prev_files = {f.get("name"): f for f in prev.get("files", [])}

    files: list[dict] = []
    all_hits: list[dict] = []
    out_dir = run_dir / "outputs"
    for f in sorted(out_dir.iterdir()) if out_dir.is_dir() else []:
        if not f.is_file() or f.name.startswith("."):
            continue
        content = f.read_text(errors="replace")
        lang = lang_of(f.name)
        words = word_total(content, lang)
        summary, hits = lint(content, lang, f.name)
        all_hits.extend(hits)
        old = prev_files.get(f.name, {})
        units = old.get("semantic_units")
        entry = {
            "name": f.name,
            "kind": "prose" if lang == "text" else "code",
            "comment_words": words,
            "semantic_units": units,
            "density": density(units, words),
            "lint": summary,
        }
        for judged_field in ("unit_list", "unit_notes"):
            if old.get(judged_field):
                entry[judged_field] = old[judged_field]
        files.append(entry)

    total_words = sum(f["comment_words"] for f in files)
    judged = [f for f in files if f["semantic_units"] is not None]
    total_units = sum(f["semantic_units"] for f in judged) if judged else None
    if judged and len(judged) != len(files):
        total_units = None  # A partly judged run has no meaningful total.

    tone = dict(prev.get("tone") or {})
    tone.setdefault("score", None)
    tone["max"] = 5
    tone["lint_hits"] = len(all_hits)
    tone["lint_hard_hits"] = sum(1 for h in all_hits if h["severity"] == "hard")
    tone["lint"] = all_hits

    doc = {
        "schema": 1,
        "rubric": "rubrics/semantic-density.md",
        "tone": tone,
        "files": files,
        "totals": {
            "comment_words": total_words,
            "semantic_units": total_units,
            "density": density(total_units, total_words),
        },
    }
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return doc


# --------------------------------------------------------------------------
# Checking a whole iteration against the thresholds
# --------------------------------------------------------------------------

def read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def thresholds_for(meta: dict) -> dict:
    t = dict(DEFAULT_THRESHOLDS)
    for cfg, vals in ((meta.get("metrics") or {}).get("thresholds") or {}).items():
        t[cfg] = {**t.get(cfg, {}), **vals}
    return t


def check_results(results: Path) -> int:
    """Prints the score table for one results tree; returns the number of misses."""
    misses = 0
    eval_dirs = sorted(d for d in results.iterdir()
                       if d.is_dir() and d.name.startswith("eval-"))
    for ev in eval_dirs:
        meta = read_json(ev / "eval_metadata.json") or {}
        limits = thresholds_for(meta)
        print(f"\n{ev.name}")
        print(f"  {'config':<16}{'SD':>7}{'units':>8}{'words':>8}{'tone':>7}"
              f"{'lint':>7}  verdict")
        rows = []
        for cfg in CONFIGS:
            m = read_json(ev / cfg / "metrics.json")
            if not m:
                continue
            rows.append((cfg, m.get("totals", {}), m.get("tone", {})))

        for cfg, tot, tone in rows:
            lim = limits.get(cfg, {})
            problems = []
            sd, units = tot.get("density"), tot.get("semantic_units")
            score = tone.get("score")
            if sd is None or units is None:
                problems.append("ungraded (semantic_units missing)")
            elif "min_density" in lim and sd < lim["min_density"]:
                problems.append(f"SD {sd} < {lim['min_density']}")
            if "min_tone" in lim:
                if score is None:
                    problems.append("tone unscored")
                elif score < lim["min_tone"]:
                    problems.append(f"tone {score} < {lim['min_tone']}")
            verdict = "ok" if not problems else "; ".join(problems)
            misses += len(problems)
            print(f"  {cfg:<16}{fmt(sd):>7}{fmt(units):>8}"
                  f"{fmt(tot.get('comment_words')):>8}{fmt(score):>7}"
                  f"{fmt(tone.get('lint_hard_hits')):>7}  {verdict}")

    return misses


def fmt(v) -> str:
    return "—" if v is None else (f"{v:g}" if isinstance(v, float) else str(v))


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score", help="recompute words + lint into metrics.json")
    s.add_argument("paths", nargs="+", type=Path)
    c = sub.add_parser("check", help="tier table and threshold verdicts")
    c.add_argument("paths", nargs="+", type=Path)
    args = ap.parse_args()

    if args.cmd == "score":
        n = 0
        for p in args.paths:
            for run in find_runs(p):
                doc = score_run(run)
                t = doc["totals"]
                print(f"{run}: {t['comment_words']} words, "
                      f"units {fmt(t['semantic_units'])}, SD {fmt(t['density'])}, "
                      f"lint {doc['tone']['lint_hard_hits']} hard / "
                      f"{doc['tone']['lint_hits']} total")
                n += 1
        print(f"\nscored {n} run(s)")
        return 0

    misses = 0
    for p in args.paths:
        # Accept either a skill directory or its results/ directory.
        results = p if any(d.name.startswith("eval-") for d in p.iterdir()) else p / "results"
        print(f"\n=== {results} ===")
        misses += check_results(results)
    print(f"\n{misses} threshold miss(es)")
    return 1 if misses else 0


if __name__ == "__main__":
    sys.exit(main())
