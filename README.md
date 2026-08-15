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
| [`dont-look-back`](dont-look-back/SKILL.md) | Design principles for writing and refactoring: no backward compatibility, delete deprecated code outright, design from a global perspective, comments describe only the present, warn before large-scale refactors. |
| [`panorama`](panorama/) | Panoramic teaching methodology — map before location, gap before definition. Shipped here as a packaged `panorama.skill` bundle rather than an unpacked directory. |

Both comment skills optimize the same objective: **more facts, fewer words** —
every sentence must carry information a reader could not recover from the code
itself. That objective is what [`SkillsTester`](SkillsTester/README.md)
measures.

## SkillsTester

[`SkillsTester/`](SkillsTester/README.md) is a repeatable acceptance-testing
framework for these skills, with a Next.js web UI for reviewing runs and reading
reports. Each skill runs two cases (document existing code / document a new
module) under two configurations (skill loaded vs. no-skill baseline), scored on
assertion pass rate plus two quality numbers: semantic density (facts per 100
words of comment prose) and register.

```bash
cd SkillsTester/web
npm install        # first time only
npm run build
npm run start      # http://127.0.0.1:3117
```

See its [README](SkillsTester/README.md) for the round workflow, the scoring
rubric, and how to add an eval or a new skill.

## Contribution
Fork and make a PR if you would like to give some improvements.

## License
MIT
