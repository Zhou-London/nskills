<img src="https://capsule-render.vercel.app/api?type=waving&height=400&text=N-Skills&fontAlign=80&fontAlignY=40&color=gradient" />

<p align="center">
  <img alt="Agent Skills" src="https://img.shields.io/badge/Claude-Agent%20Skills-D97757?logo=anthropic&logoColor=white" />
  <img alt="Skills: 3" src="https://img.shields.io/badge/skills-3-4c1" />
  <img alt="Scope: developer prose" src="https://img.shields.io/badge/scope-developer%20prose-blue" />
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-yellow" />
</p>

Project of NowQuant.

Agent Skills for common use in quant engineering. This repository *is*
`~/.claude/skills`, so every subdirectory holding a `SKILL.md` is a skill Claude
Code discovers automatically.

## Skills

| Skill | What it does |
|---|---|
| [`humandoc`](humandoc/SKILL.md) | Plain-language rules for every piece of developer-facing prose — comments, docstrings, API docs, READMEs, changelogs, error messages, commit messages, PR descriptions. Three laws, one checklist, worked before/after tables. |
| [`algo-video`](algo-video/SKILL.md) | Makes or revises one episode of a Chinese algorithm-explainer video series from voice recordings. It drives a shared Three.js engine for the animation, adds Tone.js sound, and exports with ffmpeg. |
| [`panorama`](panorama/) | Panoramic teaching methodology — map before location, gap before definition. Shipped as a packaged `panorama.skill` bundle rather than an unpacked directory. |

## humandoc

One idea runs through the whole skill: **a comment is a precomputed answer.
Finish the computation; store only the result.**

Prose fails when the writer's private context leaks out raw — history notes,
double negatives, because-chains, insider words, sentences ordered by the
writer's thought instead of the reader's need. Each leak is unfinished work
that every later reader has to finish again.

The target audience is the **floor reader**: a competent engineer, tired,
reading English as a second language, holding half the system in their head.
Prose that reader parses in one pass, every reader parses faster.

| Law | Rule | Example |
|---|---|---|
| 1 | Write the state, not the delta | `// This used to return None, but now falls back to [].` → `// Returns [] when no rows match.` |
| 2 | Put the payload first | `// This function is responsible for parsing the header.` → `// Parses the header.` |
| 3 | Speak only the shared language | `Only after the flush does the reader see the write.` → `The reader sees the write only after the flush.` |

The skill fires on any request that produces developer prose, including ones
that never name a style — "add comments", "document this", "update the README".
It also fires when a refactor leaves existing comments stale.

## Adding a skill

Create `<skill-name>/SKILL.md` with YAML frontmatter (`name`, `description`) and
a body of short imperative rules. The `description` is the trigger: it decides
whether the skill fires at all, so it must name the artifacts and phrasings that
should reach it. Push bulk material into `<skill-name>/references/`, which the
skill loads on demand. Then update the table above and the skill-count badge.

## Releases

### 2026-10-28

- **`algo-video` added.** It turns improvised voice recordings into one
  episode of the algorithm-explainer video series. The animation follows the
  voice, and only the audio from the recording goes into the final cut.


### 2026-08-22

Three overlapping style skills became one, and the tester that scored them was
retired with them.

- **`humandoc` replaces `cpp-comments`, `python-comments`, and
  `dont-look-back`.** The three said the same thing three times, split by
  language and by topic, so a Python file got Python rules and a README got
  none. `humandoc` governs every piece of developer-facing prose in any
  language: comments, docstrings, API docs, READMEs, changelogs, error
  messages, commit messages, PR descriptions.
- **Three laws instead of two style guides.** Write the state, not the delta
  (`dont-look-back`'s rule, generalized past comments). Put the payload first
  (the front-loaded verb the comment skills asked for, now applied at every
  scale from a docstring's first line to a README section). Speak only the
  shared language (plain words, one clause, subject–verb–object, near 15
  words).
- **The floor reader replaces the density score.** Semantic density measured
  facts per 100 words, which rewards compression but says nothing about
  whether a reader parses the result. The calibration target is now a named
  reader — tired, second-language, half the system in their head — and the
  seven-item checklist is what a sentence is scanned against.
- **`SkillsTester` is gone.** It scored exactly the two skills that no longer
  exist, and its Next.js review UI, evals, and rubrics went with them.

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
