# Semantic density and register — the second axis of the comment evals

Assertion pass rates answer *is the required fact documented?* They say nothing
about what the reader pays for it. Two runs can both document the `-1.0`
sentinel and score identically while one spends nine words on it and the other
spends forty, opening with "Basically, you should note that...".

This rubric adds that second axis, in two numbers per run:

- **SD — semantic density.** Facts carried per 100 words of comment prose.
- **T — register score.** How close the prose sits to professional, concise,
  crisp, on a 0–5 scale.

Both are recorded in each run's `metrics.json` and shown in the web UI beside
the pass rates.

## SD — semantic density

```
SD = semantic_units / comment_words × 100
```

### The denominator: `comment_words`

Whitespace-separated words of comment and docstring prose, comment markers
stripped. Computed mechanically by `scripts/metrics.py`, which mirrors
`web/lib/comments.ts` exactly, so the UI and the score never disagree.

- Code files (`.py`, `.h`, `.cc`, ...): comment and docstring text only. Python
  docstrings count as comments. Code inside a docstring usage example counts as
  words — an example that earns no new fact is exactly the padding SD is meant
  to catch.
- A leading license header is excluded. Both skills tell the agent to copy the
  project's boilerplate from a neighbouring file, so those ~120 words are not
  the run's prose; counting them would let a header dilute a file's density by
  a third.

Section keywords (`Args:`, `Returns:`, `Raises:`) count as words. They are cheap
and they are the same for every config, so they do not distort the comparison.

### The numerator: `semantic_units`

A **semantic unit is one atomic claim a competent reader could not have
recovered from the code itself** — not from the identifier, the signature, the
annotations, or the types.

Counts as a unit:

| Category | Example |
|---|---|
| Parameter semantics | "`keys` are UTF-8 encoded before lookup" |
| Return semantics | "returns the number of tokens actually granted" |
| Sentinel meaning | "`-1.0` means the task is unknown or not pending" |
| Exception + trigger | "raises `KeyError` when `task_id` is unknown" |
| Ownership / lifetime | "does not retain `request`"; "must not outlive its parent" |
| Nullability | "`observer` may be null; progress updates are then dropped" |
| Thread-safety | "thread-compatible: concurrent reads are safe, writes need a lock" |
| Units / ranges | "`base_delay_s_` is in seconds"; "`rate` must be > 0" |
| Side effect | "drained tasks are removed from the queue"; "reads expire on access" |
| Cost / complexity | "takes the table lock for the whole scan" |
| Invariant / precondition | "`_pending` never holds more than `max_size` ids" |
| Rationale — the *why* | "monotonic clock, so a wall-clock jump cannot stall waiters" |
| Usage constraint | "call `close()` before the last reference drops" |
| TODO with a real condition | "remove once all clients handle XML" |

Does **not** count:

- Restating the name, signature, or annotation ("Returns the size", "This class
  is a rate limiter" on `class RateLimiter`).
- Repetition. A fact stated in both the `.h` and the `.cc`, or in both the
  summary line and the expanded description, counts **once for the file set** —
  the second copy costs words and earns nothing, which is the correct penalty.
- Filler, hedging, register breaks, and pep talk (see T below).
- Structural scaffolding: section headers, an `Args:` entry that only echoes the
  parameter name, `"""See base class."""`.
- Facts about the documentation itself ("documented below", "see above").

### Counting procedure

Walk the file top to bottom, and for every comment write down the units it
carries as short strings ("`-1.0` = unknown/not pending"). Drop any string that
duplicates one already on the list. The list length is `semantic_units`.

Record the evidence alongside it, so a later reader can audit the count rather
than trust it: `unit_list` (every string) when the file is small, otherwise
`unit_notes` — a sentence naming what was counted and, importantly, what was
dropped as duplicate. Two graders working from this rubric should land within
~10% of each other; that is the accuracy the thresholds below assume, and it is
why the thresholds are set as bands rather than to one decimal place.

## T — register score

Judged against the "Register: how a comment should sound" section that both
skills carry. `scripts/metrics.py` runs a lint first (filler openers,
hedges, chattiness, cutesy or hyped vocabulary, anthropomorphism, exclamation
marks and emoji, meta-commentary, intensifiers, "This function/class ..."
restatements — in English and Chinese) and records the hits; the score is then
assigned by the grader, using the lint as evidence rather than as the verdict,
because a lint cannot see a sentence that is bland, wordy, and clean.

T scores the *register*, not the length — wordiness is SD's job, and penalising
it twice would let one flaw sink both numbers.

| T | Anchor |
|---|---|
| 5 | Every sentence declarative, specific, and free of filler; a reviewer would not mark a single phrase. |
| 4 | Professional throughout; one or two soft spots — a stray "just"/"simply", a restating opener, a rhetorical flourish. |
| 3 | Mostly professional, but a recurring tic: several filler openers, hedged contracts, or a paragraph of throat-clearing. |
| 2 | Register slips visibly — chatty asides, intensifiers doing the work of facts, marketing adjectives, meta-commentary about the code's quality. |
| 1 | Pervasive informality: reader address, jokes, hype, self-deprecation. |
| 0 | Emoji, exclamation marks, or anthropomorphism in shipped comments. |

T is scored per run, over all of its output files.

## What the skill is expected to do

The design intent, in one line: **more facts, fewer words than the baseline.**

Thresholds live per eval, in each `eval_metadata.json` under
`metrics.thresholds`, so a case whose output sits on a different scale can carry
its own numbers.

| | With skill | Baseline |
|---|---|---|
| `SD` | **≥ 7.5**, and above the baseline | reported, no threshold |
| `semantic_units` | covers every contract the assertions require | reported |
| `T` | **≥ 4** | reported |

Read together:

- The skill **fails** if it hits its word budget by dropping facts (units below
  what the assertions require) rather than by dropping padding, or if terseness
  costs it register points — telegraphic fragments score no better than waffle.
- A baseline that out-densifies the skill on some eval is the signal worth
  chasing: it means the skill's own prose is the padding.

## Where the thresholds come from

The current round is scored in full, and the thresholds are set from it.
`SD · facts · T`:

| Eval | With skill | Baseline |
|---|---|---|
| add-docstrings | **7.7** · 25 · 5 | 6.1 · 26 · 5 |
| generate-module | **6.2** · 26 · 5 | 4.4 · 38 · 5 |
| add-comments-cpp | **7.5** · 24 · 5 | 5.6 · 17 · 5 |
| generate-module-cpp | **6.2** · 21 · 5 | 4.4 · 36 · 5 |

What it shows:

- The skill is denser than the baseline on all four evals, by 1.3–1.4×.
- It misses the 7.5 floor on both new-code evals (6.2 and 6.2), where its word
  counts are the highest of any skill run — the gap is padding, not missing
  facts.
- Register is uniform: T=5 on every run, no hard lint hits. The register rules
  are holding; density is where the work is.
- These numbers come from runs made before the CC tiers were removed (the CC1
  arm, which is what the single mode now specifies). Rerun to measure the
  simplified skill.

## `metrics.json`

One per run directory (`<skill>/results/<eval>/<config>/`), beside
`grading.json` and `timing.json`:

```json
{
  "schema": 1,
  "rubric": "rubrics/semantic-density.md",
  "tone": {
    "score": 4,
    "max": 5,
    "lint_hits": 2,
    "lint_hard_hits": 1,
    "lint": [
      { "file": "retry_queue.py", "line": 31, "kind": "filler",
        "severity": "hard", "match": "Note that",
        "quote": "Note that this simply returns the ready time." }
    ],
    "notes": "One filler opener; register otherwise clean."
  },
  "files": [
    {
      "name": "retry_queue.py",
      "kind": "code",
      "comment_words": 210,
      "semantic_units": 26,
      "density": 12.4,
      "lint": { "hits": 1, "hard": 1, "by_kind": { "filler": 1 } },
      "unit_notes": "Sentinel, KeyError, drain removal, ... Excluded: the class
                     docstring's restatement of the module summary."
    }
  ],
  "totals": { "comment_words": 210, "semantic_units": 26, "density": 12.4 }
}
```

`comment_words`, `density`, `totals`, and every `lint` field are written by
`scripts/metrics.py`. `semantic_units`, `unit_list`/`unit_notes`, `tone.score`,
`tone.violations`, and `tone.notes` are the grader's, and the script preserves
them on rerun.

Two caveats when reading the lint. It fires on the *text*, so an audit report
quoting a bad comment ("`obviously`") counts as a hit the grader should discount;
and `soft` hits ("just", "you", "actually") have honest uses. Only `hard` hits
are worth reacting to without looking, which is why `check` prints
`lint_hard_hits`.

## Using it

```bash
cd SkillsTester
python3 scripts/metrics.py score python-comments/results   # words + lint for every run
python3 scripts/metrics.py check python-comments           # tier table + threshold verdicts
```

`score` is idempotent and safe to rerun after a grader edits the judged fields.
`check` prints, per eval, the three configs side by side with SD, units, words
and T, and flags every threshold miss.
