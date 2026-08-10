# SkillsTester

A repeatable acceptance-testing framework for Claude skills (currently
`cpp-comments` and `python-comments`), with a Next.js web UI for reviewing runs
and reading reports. Each skill has its own test page and its own report; the
home page is the skill selector.

## The two cases

Every skill runs the same two cases, because they are the two situations a
comment skill is actually used in:

| Case | Eval | What it measures |
|---|---|---|
| **existing-code** | `add-docstrings` / `add-comments-cpp` | The agent is handed an undocumented file and must fit comments to code it did not write. |
| **new-code** | `generate-module` / `generate-module-cpp` | The agent writes a new module and documents it in the same pass. |

Each case runs under two configurations — the skill loaded, and a no-skill
baseline — so a round is 2 cases x 2 configurations = 4 runs per skill, 8 for
the suite.

A third case (auditing planted defects, producing a written report) was
retired: it was the slowest and most expensive eval in the suite and the
weakest signal — every configuration passed nearly every assertion, and report
prose scored 1.2-2.8 SD against 4.4-7.7 for code, so it could not share a
threshold with the other cases. `evals.json` records the retirement under
`retired_evals`.

## The two phases

A round is split so that a bad run is thrown away before any grading effort is
spent on it:

1. **Produce.** One agent per (eval, configuration) writes `outputs/` and
   `timing.json` — nothing else. No grading, no metrics, and no compiling or
   smoke-testing, since the eval measures comments.
2. **Review.** The outputs appear in the web UI immediately, marked
   `⏸ unscored`, with the side-by-side comparison fully working. This is the
   gate: the round is graded only after you have looked at it and said so.
3. **Score.** Grade every assertion into `grading.json`, then judge the
   semantic-density and register half of `metrics.json`.

`python3 scripts/round.py status <skill>` reports exactly which phase each run
is in.

## Layout

```
rubrics/semantic-density.md # the SD (facts per 100 words) + register rubric
scripts/metrics.py          # scores SD/register into each run's metrics.json
scripts/round.py            # scaffolds a round, prints phase-1 briefs, reports status
web/                        # Next.js UI (port 3117)
  app/                      #   / (skill selector), /skills/<name> (eval review),
                            #   /skills/<name>/report, /api/feedback/<name>,
                            #   /api/open (opens/diffs workspace files locally)
  lib/data.ts               #   reads everything below straight from disk
  lib/comments.ts           #   marks comment spans, counts comment words
                            #   (mirrored by scripts/metrics.py)
  components/CodeCompare.tsx#   the side-by-side output comparison
python-comments/            # tests for the python-comments skill
  evals/evals.json          # 2 live evals (ids 0, 2) + the retired one
  evals/files/              # retry_queue.py (undocumented); session_store.py (retired case)
  results/                  # the one set of run results + benchmark.json
cpp-comments/               # tests for the cpp-comments skill
  evals/evals.json          # 2 live evals (ids 3, 5) + the retired one
  evals/files/              # retry_queue.{h,cc} (uncommented); session_store.{h,cc} (retired case)
  compile_flags.txt         # for clangd (-xc++ -std=c++17), silences false diagnostics
  results/                  # the one set of run results + benchmark.json
```

There is exactly one set of results per skill. A new round overwrites
`results/`; nothing is versioned, so keep a copy yourself if you want a before
and after.

Inside every `results/eval-<id>-<name>/`:

```
eval_metadata.json     # assertions (acceptance criteria) + this eval's metric thresholds
with_skill/            # the skill is loaded and applied
without_skill/         # baseline run forbidden from using the skill
```

Each run directory holds outputs/ + grading.json + timing.json + metrics.json.
eval_metadata.json carries the `assertions` and a `metrics` block with this
eval's density thresholds.

## The second axis: semantic density and register

Pass rates answer *is the required fact documented?* They say nothing about what
the reader pays for it, so every run also carries two numbers in `metrics.json`:

- **SD** — semantic units (facts a reader could not recover from the code) per
  100 words of comment prose.
- **T** — register score out of 5: professional, concise, crisp, or not.

The intent is **more facts, fewer words**: the skill run must clear its SD
floor while still covering every contract the assertions require, and it should
beat the baseline on both counts. `rubrics/semantic-density.md` defines what
counts as a fact, the T anchors, the per-eval thresholds, and the measured
numbers behind them.

```bash
python3 scripts/metrics.py score <skill>/results   # words + register lint
python3 scripts/metrics.py check <skill>            # score table + verdicts
```

`score` recomputes only the mechanical half (comment words, per-file density,
lint hits) and preserves whatever the grader judged (`semantic_units`,
`unit_notes`, `tone.score`, `tone.notes`). Its word counter mirrors
`web/lib/comments.ts` line for line — the two agree on every current output —
so the UI and the recorded metrics can never diverge. Leading license
boilerplate is excluded from the count, since both skills tell the agent to copy
it from a neighbouring file.

## Web UI

```
cd web
npm install        # first time only (requires Node; installed via Homebrew)
npm run build
npm run start      # serves http://127.0.0.1:3117
```

- **Home** — one card per skill (pass-rate meters per configuration, or an
  "awaiting scoring" line while a round sits at the gate, links to review and
  report). Skills are auto-discovered: any workspace subdirectory with
  `evals/evals.json`.
- **/skills/&lt;name&gt;** — the test page (full-width): every eval with its prompt,
  a compact pass/cost tile per configuration, then the **output comparison** —
  the same file as written by each configuration, in wrapped side-by-side columns with
  the comments tinted. Below that, assertion-level pass/fail with evidence (or
  a "not scored yet" note while the round is at the gate) and a feedback box
  per eval. "Submit all feedback" writes `<skill>/results/feedback.json`.

  The comparison controls:
  - **file tabs** — one per output file, plus the eval's input files
    (selecting an input-only file reveals the *Original* column automatically)
  - **Comments only** — hides every line that carries no comment, which is the
    fastest way to see how the skill changes the documentation
  - **Wrap** (on by default) and **Sync scroll**
  - **column chips** — hide a configuration to give the others more width
  - **per-column stats** — lines, comment lines, comment density, comment
    words. Once a run is scored, each column also shows that file's facts and SD.
  - **Open / Reveal / Path** and **Open a local diff** — hand the files to the
    machine serving the UI (`/api/open`, which refuses paths outside the
    workspace). Diffs prefer `code --diff`, then `cursor`, `bcompare`,
    `opendiff`, falling back to opening both files.
- **/skills/&lt;name&gt;/report** — the report page: KPI tiles (pass rates, skill
  lift, token overhead), a semantic-density section (SD/facts/T per config and
  per eval), per-eval pass-rate bars, cost table, analyst notes (read from
  `benchmark.json`).

The UI reads `results/` straight off disk on every request. `npm run dev` gives
live reload during development.

## Running a round

Ask Claude to "run a SkillsTester round" (or name a single skill). Claude stops
after phase 1 and waits; say "score it" to start phase 2.

### Phase 1 — produce

```bash
python3 scripts/round.py reset python-comments cpp-comments  # clear results/, keep metadata
python3 scripts/round.py prompts python-comments             # one brief per run
```

Spawn one agent per brief — 4 per skill, 8 for the full suite. Each agent:

- reads the skill's `SKILL.md` first (with-skill arms), or is explicitly
  forbidden from reading any `SKILL.md`, `rubrics/` or `scripts/` (baseline);
- copies the eval's input files into its own `run-1/outputs/` and works only on
  those copies, so the shared `evals/files/` originals are never touched;
- writes `outputs/` and `timing.json`, and nothing else — no grading, no
  metrics, and no compiling or smoke-testing, which is pure latency in a test
  that measures comments;
- never reads another run's outputs, which would contaminate the comparison.

Then `python3 scripts/round.py status <skill>` should show `files` and `timing`
for every run, and `-` under `graded`/`scored`.

### Review — the gate

The outputs are already in the web UI, marked `⏸ unscored`, with the
side-by-side comparison working. Look at them. If a run is wrong (an agent
misread the brief, an API error truncated a file), rerun that one agent before
anything is graded.

### Phase 2 — score

Only after the outputs are confirmed:

1. Grade every assertion from `eval_metadata.json` into each run's `grading.json`
   (fields: text / passed / evidence, plus a summary block).
2. `python3 scripts/metrics.py score <skill>/results` to fill in comment
   words and the register lint, then count semantic units per output file
   against `rubrics/semantic-density.md`, write them plus `unit_notes` and
   `tone.score` into each `metrics.json`, and rerun `score`.
3. `python3 scripts/metrics.py check <skill>` for the score table
   and threshold verdicts.
4. Write `results/benchmark.json` (configurations, per_eval, notes) — the
   UI reads grading and timing directly and uses `benchmark.json` only for the
   analyst notes.
5. Review in the web UI, submit feedback, and let Claude improve the skill from
   `<skill>/results/feedback.json` before the next round.

## Extending

- New eval: append to the owning skill's `evals.json` with a `case` field, put
  input files in that skill's `evals/files/`, and write an `eval_metadata.json`
  with assertions in the new round's eval directory. Eval ids are globally
  unique and stable — python holds 0-2, cpp holds 3-5, new evals continue the
  sequence — so retiring an eval means moving it to `retired_evals`, never
  renumbering the survivors.
- New language/skill: create a sibling `<skill-name>/` subtree following the
  same pattern (the two cases: document existing code / document a new module).
  The UI picks it up automatically.
