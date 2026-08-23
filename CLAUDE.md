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
  knowledge of any source style guide. Push bulk material into `references/`.
- **One skill per subject, not one per language.** `humandoc` covers every
  piece of developer-facing prose in every language. A rule that fits inside an
  existing skill belongs in that skill's body, not in a second skill that
  repeats its neighbors.
- Keep [README.md](README.md) in step: adding, renaming, or removing a skill
  means updating the skill table and the count badge.
- Prose in this repository follows `humandoc` itself, including these files.

## Testing a change

Skill edits are validated by use, not by a score. Load the edited skill in a
real task of the kind it governs, and check two things: the skill fired without
being named, and its rules changed the output. A skill that has to be invoked
by name has a `description` problem, which is a body edit away from useless.

Test the trigger in both directions. Give it a request that never uses the
skill's vocabulary ("add comments here") and confirm it fires; give it an
unrelated request and confirm it stays quiet.

## Commits

One skill change per commit, imperative subject. Never commit `node_modules/`
or `.env*` — `.gitignore` already covers them.
