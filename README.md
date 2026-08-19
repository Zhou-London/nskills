<img src="https://capsule-render.vercel.app/api?type=waving&height=400&text=N-Skills&fontAlign=80&fontAlignY=40&color=gradient" />

<p align="center">
  <img alt="Agent Skills" src="https://img.shields.io/badge/Claude-Agent%20Skills-D97757?logo=anthropic&logoColor=white" />
  <img alt="Skills: 4" src="https://img.shields.io/badge/skills-4-4c1" />
  <img alt="Tested with SkillsTester" src="https://img.shields.io/badge/tested-SkillsTester-blue" />
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-yellow" />
</p>

Project of NowQuant.

Agent Skills for common use in quant engineering. This repository *is*
`~/.claude/skills`, so every subdirectory holding a `SKILL.md` is a skill Claude
Code discovers automatically.

## Skills

| Skill | What it does |
|---|---|
| [`cpp-comments`](cpp-comments/SKILL.md) | Google C++ Style Guide rules for comments, plus a density budget — file/class/function/variable comments, the declaration-vs-definition split, `/*param=*/` argument comments, TODO format, professional register, and what *not* to comment. Ships a [review checklist](cpp-comments/references/review-checklist.md). |
| [`python-comments`](python-comments/SKILL.md) | The same for Python: module/class/function docstrings with Args/Returns/Raises, block and inline comments, prose capped at 2–3 sentences. Ships a [review checklist](python-comments/references/review-checklist.md). |
| [`dont-look-back`](dont-look-back/SKILL.md) | Design principles for writing and refactoring: no backward compatibility, delete deprecated code outright, design from a global perspective, comments describe only the present and never correct the past, warn before large-scale refactors. |
| [`panorama`](panorama/) | Panoramic teaching methodology — map before location, gap before definition. Shipped here as a packaged `panorama.skill` bundle rather than an unpacked directory. |

Both comment skills optimize the same objective: **more facts, fewer words** —
every sentence must carry information a reader could not recover from the code
itself. That objective is what [`SkillsTester`](SkillsTester/README.md)
measures.

## SkillsTester

[`SkillsTester/`](SkillsTester/README.md) is a repeatable acceptance-testing
framework, with a Next.js web UI for reviewing runs and reading reports. It
covers the two comment skills — the ones whose output is comment prose a run
can be scored on; `dont-look-back` and `panorama` carry no evals. Each covered
skill runs two cases (document existing code / document a new module) under two
configurations (skill loaded vs. no-skill baseline), scored on assertion pass
rate plus two quality numbers: semantic density (facts per 100 words of comment
prose) and register.

```bash
cd SkillsTester/web
npm install        # first time only
npm run build
npm run start      # http://127.0.0.1:3117
```

See its [README](SkillsTester/README.md) for the round workflow, the scoring
rubric, and how to add an eval or a new skill.

## Releases

### 2026-08-16

- **`dont-look-back`: never correct the past.** A comment may not deny a state
  the codebase no longer has. A negation whose only referent is history ("not
  wire data", "no longer cached") is noise to a reader who never saw the old
  code; state the property positively instead. Negations that forestall a
  misreading of the *current* code ("not thread-safe", "not owned; caller
  frees") are still correct and still expected.

### 2026-08-15

- **Four skills documented** — `cpp-comments`, `python-comments`,
  `dont-look-back`, and the packaged `panorama` bundle, each with its trigger
  description tuned so the skill fires on the artifacts it governs rather than
  on its own vocabulary.
- **`panorama` added** as a `.skill` bundle. It stays packed: unpacking a
  bundle activates a skill in every session on the machine, which is not
  something to do silently.
- **SkillsTester** scores a change instead of leaving it to inspection — two
  cases per skill under skill-loaded and baseline configurations, reported as
  assertion pass rate plus semantic density and register.

## Contribution
Fork and make a PR if you would like to give some improvements.

## License
MIT
