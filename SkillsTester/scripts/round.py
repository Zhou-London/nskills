#!/usr/bin/env python3
"""Scaffolding and status for a two-phase test round.

A round is deliberately split, so that a bad run is thrown away before any
grading effort is spent on it:

  phase 1 — produce   one agent per (eval, configuration) writes outputs/ and
                      timing.json, and nothing else.
  ---- the operator reviews the outputs in the web UI and confirms ----
  phase 2 — score     grading.json per run, then the judged half of
                      metrics.json (see rubrics/semantic-density.md).

Each skill keeps exactly one set of results, in `<skill>/results/`. A new round
overwrites it; the previous round is not kept.

Subcommands:

  reset <skill>...    Clear `<skill>/results/` and lay out the directories for
                      the live evals, keeping each eval_metadata.json. Refuses
                      to discard existing outputs unless given --force.

  prompts <skill>...  Print the phase-1 brief for every run: which files to
                      copy in, which prompt to run, where the outputs go. One
                      brief per agent (2 evals x 2 configurations per skill).

  status <skill>...   Show where each run stands — outputs, timing, grading,
                      and whether the metrics have been judged. This is the
                      check that says whether a phase is actually finished.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
CONFIGS = ["with_skill", "without_skill"]


def read_json(p: Path):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def results_dir(skill: str) -> Path:
    return WS / skill / "results"


def eval_dir_name(ev: dict) -> str:
    return f"eval-{ev['id']}-{ev['eval_name']}"


def live_evals(skill_dir: Path) -> list[dict]:
    js = read_json(skill_dir / "evals" / "evals.json") or {}
    return js.get("evals", [])


def cmd_reset(skills: list[str], force: bool) -> int:
    for skill in skills:
        skill_dir = WS / skill
        target = results_dir(skill)
        produced = [p for p in target.rglob("outputs/*") if p.is_file()]
        if produced and not force:
            print(f"{skill}: results/ already holds {len(produced)} output files. "
                  f"Rerun with --force to discard them.")
            continue
        # eval_metadata.json carries the assertions and thresholds; it survives.
        keep = {}
        for ev in live_evals(skill_dir):
            meta = target / eval_dir_name(ev) / "eval_metadata.json"
            if meta.exists():
                keep[eval_dir_name(ev)] = meta.read_text()
        if target.exists():
            shutil.rmtree(target)
        for ev in live_evals(skill_dir):
            name = eval_dir_name(ev)
            for cfg in CONFIGS:
                (target / name / cfg / "outputs").mkdir(parents=True, exist_ok=True)
            if name in keep:
                (target / name / "eval_metadata.json").write_text(keep[name])
            else:
                print(f"  ! {name}: no eval_metadata.json carried over; write one by hand")
        print(f"{skill}: results/ reset for {len(live_evals(skill_dir))} evals "
              f"x {len(CONFIGS)} configs")
    return 0


def cmd_prompts(skills: list[str]) -> int:
    for skill in skills:
        skill_dir = WS / skill
        if not results_dir(skill).exists():
            print(f"{skill}: no results/; run `round.py reset {skill}` first")
            continue
        skill_md = (read_json(skill_dir / "evals" / "evals.json") or {}).get("skill_path", "")
        for ev in live_evals(skill_dir):
            name = eval_dir_name(ev)
            for cfg in CONFIGS:
                run = results_dir(skill) / name / cfg
                print(f"\n=== {skill} / {name} / {cfg} ===")
                print(f"run dir : {run}")
                if cfg == "without_skill":
                    print("skill   : FORBIDDEN — must not read any SKILL.md, rubrics/ or scripts/")
                else:
                    print(f"skill   : read {skill_md} first")
                for rel in ev.get("files", []):
                    src = skill_dir / rel
                    print(f"copy    : {src} -> {run}/outputs/{Path(rel).name}")
                if not ev.get("files"):
                    print("copy    : (none — this case generates a new module)")
                print(f'prompt  : "{ev["prompt"]}"')
                print("write   : outputs/ + timing.json only. No grading, no metrics, "
                      "no compiling or smoke-testing — the eval measures comments.")
    return 0


def cmd_status(skills: list[str]) -> int:
    incomplete = 0
    for skill in skills:
        it = results_dir(skill)
        if it.exists():
            print(f"\n=== {skill}/results ===")
            print(f"  {'eval / config':<46}{'files':>6}{'timing':>8}"
                  f"{'graded':>8}{'scored':>8}")
            for ev in sorted(d for d in it.iterdir()
                             if d.is_dir() and d.name.startswith("eval-")):
                for cfg in CONFIGS:
                    run = ev / cfg
                    if not run.exists():
                        continue
                    out = run / "outputs"
                    files = len([f for f in out.iterdir()
                                 if f.is_file() and not f.name.startswith(".")]) if out.is_dir() else 0
                    timing = "yes" if (run / "timing.json").exists() else "-"
                    graded = "yes" if (run / "grading.json").exists() else "-"
                    m = read_json(run / "metrics.json") or {}
                    judged = m.get("totals", {}).get("semantic_units") is not None
                    tone = (m.get("tone") or {}).get("score") is not None
                    scored = "yes" if (judged and tone) else ("part" if m else "-")
                    if files == 0 or timing == "-" or graded == "-" or scored != "yes":
                        incomplete += 1
                    print(f"  {ev.name + ' / ' + cfg:<46}{files:>6}{timing:>8}"
                          f"{graded:>8}{scored:>8}")
    print(f"\n{incomplete} run(s) not fully scored")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("reset")
    s.add_argument("skills", nargs="+")
    s.add_argument("--force", action="store_true",
                   help="discard the outputs already in results/")
    for name in ("prompts", "status"):
        s = sub.add_parser(name)
        s.add_argument("skills", nargs="+")
    a = ap.parse_args()
    if a.cmd == "reset":
        return cmd_reset(a.skills, a.force)
    if a.cmd == "prompts":
        return cmd_prompts(a.skills)
    return cmd_status(a.skills)


if __name__ == "__main__":
    sys.exit(main())
