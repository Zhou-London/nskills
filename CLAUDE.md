# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

This repository is `~/.claude/skills` — the user's personal Agent Skills
directory. Editing a `SKILL.md` here changes Claude Code's behavior in every
session on this machine, so treat changes as behavioral, not cosmetic. See
[README.md](README.md) for the skill list.

## Layout

```
<skill-name>/SKILL.md        the skill; YAML frontmatter (name, description) + body
<skill-name>/references/     material the skill loads on demand, not up front
SkillsTester/                acceptance-testing framework for the skills
```

Only a directory containing `SKILL.md` is discovered as a skill. A packaged
`.skill` bundle (as in `panorama/`) is not loaded until it is unpacked — do not
unpack one without asking, since that silently activates a skill.

## Conventions

- **The `description` is the trigger.** It decides whether the skill fires at
  all, so it must name the concrete artifacts and phrasings that should trigger
  it, including the cases where the user never uses the skill's own vocabulary.
  Changing the body without revisiting the description is a common mistake.
- **Write the body as rules, not prose.** Short imperative statements, tables
  and checklists over paragraphs; the skills here practice the density they
  preach.
- Keep the body self-contained — state everything needed, assume no prior
  knowledge of the source style guide. Push bulk material into `references/`.
- Keep [README.md](README.md) in step: adding, renaming, or removing a skill
  means updating the skill table and the badge count.

## Testing a change

Skill edits are validated by a SkillsTester round, not by inspection. The
workflow is two-phase with a manual gate between them — produce outputs, look at
them, then score. `SkillsTester/README.md` is the authority; the short version:

```bash
cd SkillsTester
python3 scripts/round.py reset <skill>      # clear results/, keep metadata
python3 scripts/round.py prompts <skill>    # one brief per run
python3 scripts/round.py status <skill>     # which phase each run is in
python3 scripts/metrics.py check <skill>    # score table + threshold verdicts
```

`results/` is gitignored and unversioned — a new round overwrites it, so keep a
copy yourself if you want a before and after.

## Commits

One skill change per commit, imperative subject. Never commit `results/`,
`node_modules/`, or `.env*` — `.gitignore` already covers them.
