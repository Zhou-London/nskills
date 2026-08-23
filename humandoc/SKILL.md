---
name: humandoc
description: Plain-language rules for every piece of developer-facing prose — code comments, docstrings, API docs, README files, changelogs, error messages, commit messages, and PR descriptions. Use this skill whenever you write or edit any of those, even when the request is only "add comments", "document this", "update the README", or "fix these comments", and says nothing about style. Also use it when a refactor or bug fix leaves existing comments or docs stale.
---

# HumanDoc

## The philosophy

Code prose is written once and read many times, by readers the writer never
meets. Every cost the writer skips lands on every reader, multiplied.

The writer holds context the reader lacks: the old code, the diff, the chain
of reasoning, the vocabulary of the moment. Prose fails when this private
context leaks out raw — as history notes, double negatives, because-chains,
insider words, sentences ordered by the writer's thought instead of the
reader's need. Each leak is unfinished work: a computation the writer started
and every reader must now finish.

**A comment is a precomputed answer. Finish the computation; store only the
result.**

Finishing the computation means five moves:

1. Collapse history into present state.
2. Resolve every negation into the positive fact.
3. Complete the reasoning; write its conclusion.
4. Translate private vocabulary into shared words.
5. Order each sentence by information — the most informative word first.

Calibrate against the **floor reader**: a competent engineer, tired, reading
English as a second language, holding half the system in their head. This is
not a lowered bar — it is the honest model of any real audience at 3 a.m.
mid-incident. Prose the floor reader parses in one pass, every reader parses
faster.

Three laws follow, one per kind of unfinished computation.

## Law 1 — Write the state, not the delta

The reader sees only the present code. The past exists for them only if a
comment resurrects it — and then they must parse a ghost just to discard it.

- Describe what the code **is**. Never what it was, changed from, or no
  longer does: no `used to`, `no longer`, `previously`, `now`, `the old way`.
- Delete a comment whose only content is history. Git already stores it.
- Resolve negations before writing. `not uncommon` stores the formula;
  `common` stores the value. The reader must never compute ¬(¬x).
- Keep a negation only when it blocks a live misreading of the current code:
  `not thread-safe`, `not owned; caller frees`.
- Fix wrong prose by rewriting the sentence from the fact. Never patch the
  words: a patched sentence keeps the dead sentence's skeleton, and the
  skeleton keeps its ghost.

| Transcript of the writer | Fact for the reader |
|---|---|
| `// No longer uses the global lock; per-instance locking is not insufficient.` | `// Locks per instance.` |
| `// This used to return None, but now falls back to [].` | `// Returns [] when no rows match.` |
| `not uncommon` | `common` |
| `does not fail unless the queue is empty` | `fails only when the queue is empty` |
| `// Removed the retry here because it caused duplicates.` | (delete — git holds it) |

Deltas do have homes: `git blame`, the commit message, the changelog. Write
them there — and there, Laws 2 and 3 still govern the wording.

## Law 2 — Put the payload first

Attention is spent front-loaded: the first words of a sentence receive the
most, and it decays from there. Spend the best position on the most
information.

- Open with a third-person verb + object: `Returns the cached entry.` Never
  `This function`, `It`, `We`, `Note that`, `Basically`, `In order to`.
- Make the opening verb carry fact: `caches`, `dedupes`, `validates`. The
  verbs `is`, `does`, `handles`, `processes`, `manages` spend the best
  position on nothing.
- One fact per sentence, always. One sentence per comment, whenever one
  sentence carries the fact.
- Action before reason. Cut `because … so/therefore` chains: state what the
  code does; when the reason earns its place, give it its own short sentence
  after the action.
- Apply the law at every scale. Docstring: first line answers the question,
  detail follows. Error message: what happened, then what to do. README
  section: the point, then the support.
- Prose about a named thing opens with the name, verb immediately after:
  `TokenBucket limits request rate.`

| Payload buried | Payload first |
|---|---|
| `// This function is responsible for parsing the header.` | `// Parses the header.` |
| `// Because the API sometimes returns stale entries, we therefore retry after invalidating the cache.` | `// Retries after invalidating the cache. The API sometimes returns stale entries.` |
| `// It handles the case where the user is not logged in.` | `// Redirects anonymous users to /login.` |
| `// Note that this manages cleanup of temp files.` | `// Deletes temp files older than one hour.` |

## Law 3 — Speak only the shared language

The floor reader shares two things with you: the technical vocabulary of the
domain, and plain textbook English. Nothing else — not your idioms, not your
culture, not your appetite for grammar puzzles.

- Choose the common word: `use` not `utilize` or `leverage`, `start` not
  `initiate`, `end` not `terminate`, `enough` not `sufficient`.
- Technical terms are shared vocabulary: `mutex`, `idempotent`, `backoff` are
  welcome. Insider idiom is not: `happy path`, `footgun`, `nuke the cache`,
  `boil the ocean`.
- Build every sentence as one clause in subject–verb–object order. No nested
  relative clauses, no inversion: not `Only after the flush does the reader
  see the write` but `The reader sees the write only after the flush.`
- Keep sentences near 15 words. A sentence that needs a comma to breathe
  becomes two sentences.
- Give each thing one name and keep it. Alternating `entry` / `record` /
  `item` for one thing invents three things.
- Replace ambiguous `it` and `this` with the noun. Pronouns tax the floor
  reader hardest.

| Insider | Shared |
|---|---|
| `Leverages the sidecar to hydrate the config.` | `Reads the config from the helper process.` |
| `Only after the flush does the reader see the write.` | `The reader sees the write only after the flush.` |
| `utilize`, `initiate`, `terminate`, `sufficient` | `use`, `start`, `end`, `enough` |
| `happy path`, `footgun` | `normal case`, `easy to misuse` |

## Checklist — scan every sentence you wrote

- [ ] Opens with an information-carrying verb, or a name plus that verb.
- [ ] Describes the present code; contains no history word.
- [ ] States the fact affirmatively; any negation blocks a live misreading.
- [ ] Puts action first; any reason stands as its own short sentence.
- [ ] Runs one clause, subject–verb–object, near 15 words.
- [ ] Uses common words and technical terms; no idiom, no slang.
- [ ] Leaves no `it` or `this` without an obvious noun.

One failed check means rewriting that sentence from the fact it should state.
Editing the words patches the delta; rewriting finishes the computation.
