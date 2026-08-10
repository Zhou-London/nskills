# SkillsTester

A repeatable acceptance-testing framework for Claude skills (currently
`cpp-comments` and `python-comments`), with a Next.js web UI for reviewing runs
and reading reports. Each skill has its own test page and its own report; the
home page is the skill selector.

## Layout

```
web/                        # Next.js UI (port 3117)
  app/                      #   / (skill selector), /skills/<name> (eval review),
                            #   /skills/<name>/report, /api/feedback/<name>
  lib/data.ts               #   reads everything below straight from disk
python-comments/            # tests for the python-comments skill
  evals/evals.json          # 3 fixed evals (ids 0-2)
  evals/files/              # retry_queue.py (undocumented), session_store.py (11 planted defects)
  iteration-N/              # per-round results + benchmark.json/md
cpp-comments/               # tests for the cpp-comments skill
  evals/evals.json          # 3 fixed evals (ids 3-5)
  evals/files/              # retry_queue.{h,cc} (uncommented), session_store.{h,cc} (12 planted defects)
  compile_flags.txt         # for clangd (-xc++ -std=c++17), silences false diagnostics
  iteration-N/              # per-round results + benchmark.json/md
```

Inside every `iteration-N/eval-<id>-<name>/`:

```
eval_metadata.json     # assertions (acceptance criteria); audit evals also list planted_defects
with_skill/run-1/      # run forced to read SKILL.md first: outputs/ + grading.json + timing.json
without_skill/run-1/   # baseline run forbidden from using the skill
```

## Web UI

```
cd web
npm install        # first time only (requires Node; installed via Homebrew)
npm run build
npm run start      # serves http://127.0.0.1:3117
```

- **Home** — one card per skill (pass-rate meters for both configurations,
  links to review and report). Skills are auto-discovered: any workspace
  subdirectory with `evals/evals.json`.
- **/skills/&lt;name&gt;** — the test page: every eval with its prompt, side-by-side
  With-skill / Baseline columns (assertion-level pass/fail with evidence,
  full output files), the planted-defect list for audit evals, and a feedback
  box per eval. "Submit all feedback" writes
  `<skill>/iteration-N/feedback.json`.
- **/skills/&lt;name&gt;/report** — the report page: KPI tiles (pass rates, skill
  lift, token overhead), per-eval pass-rate bars, cost table, analyst notes
  (read from `benchmark.json`).

The UI always shows the latest `iteration-N`. `npm run dev` gives live reload
during development.

## Running a round

Ask Claude to "rerun the SkillsTester evals" (or name a single skill).
The procedure, per skill:

1. For each eval spawn two subagents: with_skill (reads the skill's SKILL.md
   first, then executes the prompt) and without_skill (explicitly forbidden from
   reading any SKILL.md). Outputs go to a fresh `iteration-N/.../run-1/outputs/`.
2. Grade every assertion from `eval_metadata.json`, writing `run-1/grading.json`
   (fields: text / passed / evidence, plus a summary block) and `run-1/timing.json`
   (total_tokens, duration_ms, total_duration_seconds).
3. Optionally aggregate with skill-creator's benchmark script (the UI reads
   grading/timing files directly and only uses `benchmark.json` for the notes):
   `python3 -m scripts.aggregate_benchmark <ws>/<skill>/iteration-N --skill-name <skill>`
4. Review in the web UI, submit feedback, and let Claude improve the skill from
   `<skill>/iteration-N/feedback.json` before the next round.

skill-creator path:
`/Users/zhou/.claude/plugins/cache/claude-plugins-official/skill-creator/unknown/skills/skill-creator`

## Extending

- New eval: append to the owning skill's `evals.json`, put input files in that
  skill's `evals/files/`, and write an `eval_metadata.json` with assertions in
  the new round's eval directory. Eval ids are globally unique (python holds
  0-2, cpp holds 3-5; new evals continue the sequence).
- New language/skill: create a sibling `<skill-name>/` subtree following the
  same pattern (three eval kinds: add documentation / audit planted defects /
  generate from scratch). The UI picks it up automatically.
- Historical note: iteration-1 outputs (agent-written files and review reports)
  were produced with Chinese prompts and are kept verbatim as run artifacts;
  all prompts are English from iteration-2 onward.
