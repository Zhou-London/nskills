---
name: python-comments
description: Google Python Style Guide rules for writing and reviewing comments and docstrings — module/class/function docstrings with Args/Returns/Raises sections, block and inline comments, TODO format, the professional register comments are written in (no filler, hedging, chattiness, or cutesy phrasing), and what NOT to comment. Optimizes for information density: comment and docstring prose is capped at 2–3 sentences, structured entries at one sentence each, with no usage-example blocks. Use this skill whenever you write, generate, or modify Python code (.py, .pyi, notebooks), whenever you are asked to add, improve, shorten, translate, audit, review, or make more professional the comments, docstrings, or documentation in Python code, and whenever a Python review touches comment or docstring quality — even if the user never says "Google style" or "docstring convention" and even for a small edit to a single function.
---

# Writing Python comments and docstrings (Google style)

## The test a comment has to pass

A comment or docstring earns its place only when it carries information the code cannot. Assume the reader knows Python at least as well as you do — they can read a list comprehension. What they cannot recover from the code is **intent, contract, and constraint**: what a caller may pass, what comes back, what exceptions escape, why this algorithm and not the obvious one, what a sentinel value means.

Before writing one, ask: *if I delete this, what does the reader lose?* "Nothing" means delete it. "They'd have to read the function body, or guess and get it wrong" means keep it.

Two failure modes, and the second is the dangerous one:

- **Over-commenting** — restating code in prose. Adds noise, and trains readers to skip comments.
- **Stale comments** — worse than no comment, because the reader trusts them. Any time you change behavior, the docstrings and comments describing that behavior are part of the change.

## The budget

Documentation is measured by **facts per word**: how much a reader could not have recovered from the code, divided by the words you spent saying it. Maximize that ratio. A codebase where every function carries a paragraph trains readers to skim past docstrings, which is the same failure as documenting nothing.

The budget, which applies to everything you write:

- Each block or inline comment, and the free prose of each docstring (summary line plus any expanded description), is capped at **2–3 sentences**. Prefer a one-line docstring whenever the summary sentence already covers the contract.
- Structured sections (`Args:`, `Returns:`, `Raises:`, `Attributes:`) survive when they carry contract information the signature doesn't, but each entry is one short sentence.
- **No usage-example blocks and no example return values.** They are the most expensive words in a docstring: many lines for one fact a reader can get from a call site or a test.
- *What* to document does not change — parameter meaning, sentinel returns, escaping exceptions, and side effects are still the content. The budget changes *how much*: keep only the facts a caller would guess wrong, and cut everything the code or annotations already say.
- If a contract genuinely cannot fit (rare, and usually a sign the function does too much), keep the extra sentence rather than drop a load-bearing fact. The cap is a budget, not a license to ship an incomplete contract.

The way to hit the budget is not to drop facts, it is to stop spending words on non-facts. Before you finish, reread what you wrote and ask of each sentence: *which fact is this carrying?* If the answer is "none" or "the same one as the sentence above", delete it.

## Register: how a comment should sound

Professional, concise, crisp — the register of a competent colleague explaining a contract in a design review. State the fact and stop. Every word either carries information or costs the reader time.

Four rules do most of the work:

1. **One fact per sentence, stated directly.** Lead with the fact, not with throat-clearing. "Note that callers should be aware this may block." → "Blocks until the queue drains."
2. **Declarative third person, present tense, active voice.** Document the code, not the reader's experience of it: "Returns None on timeout", not "You'll get back None" or "We then return None".
3. **Precise words instead of emphatic ones.** Intensifiers ("very", "extremely", "super"), vague scale words ("a lot", "huge"), and self-praise ("elegant", "clever trick") carry nothing. If something is expensive, say how: "O(n) in the number of sessions", not "quite slow".
4. **Name things exactly as the code names them,** in backticks. A synonym invented for a symbol forces the reader to map it back.

Delete these on sight:

| Kind | Examples | Why |
|---|---|---|
| Filler openers | "Basically", "Essentially", "Actually", "Of course", "Note that", "It should be noted that", "As you can see", "Simply", "Just" | Zero information; the sentence is stronger without them |
| Hedges | "should probably", "kind of", "sort of", "I think", "for some reason" | Either you know the contract or you must go find out. Genuine unresolved uncertainty belongs in a `TODO:`, not in a shrug |
| Reader address, chattiness | "you", "your", "we'll", "let's", "don't worry", "feel free", "as promised" | A docstring is documentation, not a conversation |
| Cutesy or hyped vocabulary | "magic", "secret sauce", "bad boy", "sprinkle in", "awesome", "nifty", "boom", "voilà" | Reads as unserious in review and ages badly |
| Anthropomorphism | "the queue is happy to accept", "the parser wants a token", "asks the server nicely" | Obscures the mechanism it is supposed to explain |
| Emotive punctuation, decoration | `!`, `?!`, emoji, `====` banners, ALL-CAPS for emphasis, `*bold*` | Noise. The only conventional shouty tokens are `TODO:`, `NOTE:`, `WARNING:` |
| Meta-commentary on the code's quality | "this is ugly but it works", "sorry about this", "hacky" | Either fix it or write a `TODO:` naming what would fix it |
| Restating the construct | "This function ...", "This class is a class that ...", "This method is used to ..." | The reader can see what it is; start with the verb |

Before and after — same facts, professional register:

```python
    """This is a helper that basically just goes and grabs the rows for you!

    It's super fast, so don't worry about hitting it in a loop :)
    """
```

```python
    """Fetches rows for `keys`, serving hits from the process-local cache.

    Uncached keys cost one RPC each; batch them rather than looping.
    """
```

```python
    # Okay so this is a bit of a hack, but we basically just need to make
    # sure the poor task doesn't get retried forever!
    if task.attempts >= self._max_attempts:
```

```python
    # Dropping here rather than at the next dequeue keeps `_pending`
    # bounded when a caller never drains the queue.
    if task.attempts >= self._max_attempts:
```

**Mechanics.** Comments are read far more often than written. Complete sentences — capitalized, properly punctuated — read better than fragments. Short end-of-line comments may be terser, but stay consistent within a file. When the file's comments are in another language, the register rules above still apply: the same ban on filler, hedging, cuteness, and sentence-ending particles or emoticons.

**The sound check.** Read the comment as if saying it aloud in a code review. Anything you would not say there — a joke, an apology, an exclamation, a pep talk — does not belong in the file either.

## Where each kind of information lives

Python institutionalizes interface documentation as **docstrings** — the first statement inside a module, class, or function, accessible at runtime via `__doc__` and extracted by pydoc, Sphinx, and IDEs. That machine-readability is the reason for the rigid format rules below: tools and readers both depend on the structure.

| Place | Answers | For whom |
|---|---|---|
| Module docstring | What is this module about, and how is it typically used? | Someone browsing the package |
| Class docstring | What is this for, and what public attributes does it have? | The caller |
| Function docstring | What does it do, what may I pass, what do I get back, what can it raise? | The caller |
| Block comment in the body | Why is this tricky bit correct? | The maintainer |
| Inline comment | What does this non-obvious line mean? | The maintainer |

The docstring documents the *interface* — calling syntax and semantics, enough that a caller can use the function **without reading its source**. Implementation details stay out of it unless they matter to the caller (side effects, performance characteristics). How the body works is explained by comments *in* the body.

## Docstring mechanics

- Always triple double quotes: `"""` (PEP 257). Even if the project uses single quotes for ordinary strings, docstrings stay `"""`.
- The first line is a one-sentence summary ending in a period, question mark, or exclamation point, at most 80 characters. Write it in the **descriptive** register — "Fetches rows from a Bigtable.", not the imperative "Fetch rows...". You are documenting a thing, not issuing an order.
- If there is more to say, leave one blank line after the summary, then the details, indented to the same level as the opening quotes.
- Lines inside docstrings obey the 80-character limit too; URLs and long paths that cannot wrap are the exception.
- Section names (`Args:`, `Returns:`, `Raises:`, `Yields:`, `Attributes:`) end with a colon; their content is indented beneath them.
- Type annotations carry the type information. When a signature is annotated, do not repeat types in the docstring — describe *meaning*, not type. Only when code lacks annotations does the docstring need to state expected types.

**Docstring and comment language:** match the surrounding code. Scan the same file, then nearby files — if they document in English, write English; if the codebase comments in Chinese (or another language), write in that language so the file reads as one voice. For a brand-new file with nothing to match, default to English. The structural rules (section names, `"""`, `TODO:` format) apply regardless of language — `Args:`/`Returns:`/`Raises:` stay in English because tools key on them.

## Module docstrings

Start each file with the project's license boilerplate — copy the header from a neighboring file rather than inventing one.

Every module gets a docstring: a one-line summary, plus — only when the summary leaves something a reader must know before using the module — one or two sentences carrying that constraint. What earns the space is the fact a caller would otherwise discover the hard way: that state is process-local, that nothing is thread-safe, that expiry is lazy. Not a tour of the exports, and not a usage example.

```python
"""In-memory session store with lazy TTL expiry.

Entries expire `ttl` seconds after `put()` and are evicted on read or by
`purge()`. Not thread-safe.
"""
```

Test files are the exception: a module docstring is required only when it adds real information — an unusual way the tests must be run, an environment they depend on. "Tests for foo.bar" carries nothing the filename doesn't; omit it.

## Function and method docstrings

A docstring is **required** for any function that is part of a public API, is non-trivial in size, or has logic that isn't obvious at a glance. The only functions that may skip it are short, private, *and* obvious — all three.

Organize the content into the standard sections:

```python
def fetch_smalltable_rows(
    table_handle: smalltable.Table,
    keys: Sequence[bytes | str],
    require_all_keys: bool = False,
) -> Mapping[bytes, tuple[str, ...]]:
    """Fetches rows for `keys` from a Smalltable, as a dict of key to row tuple.

    Args:
        table_handle: An open smalltable.Table instance.
        keys: Keys of the rows to fetch; string keys are UTF-8 encoded.
        require_all_keys: If True, only rows with values set for all keys are returned.

    Returns:
        A dict mapping each found key (always bytes) to its row, a tuple of
        strings; missing rows are absent from the dict.

    Raises:
        IOError: An error occurred accessing the smalltable.
    """
```

Every fact a caller needs is there — the UTF-8 encoding, the `require_all_keys` filter, the bytes keys, the missing-row behavior, the escaping exception — in nine lines. An expanded description that restated the summary, and a worked example of the return value, would have tripled the length and added nothing.

### `Args:`

List each parameter as `name: description`. If a description wraps, indent continuation lines by 2 or 4 extra spaces — pick one and use it consistently across the file. Include `*args` and `**kwargs` if the function accepts them. Without type annotations, the description must state the expected type; with annotations, describe only the semantics.

### `Returns:` (or `Yields:` for generators)

Describe the semantics of the return value — and its type, when the signature isn't annotated. Skip this section entirely when the function returns `None`, or when the summary line already covers it ("Returns True if the row exists."). A returned tuple deserves description as named parts, not "a tuple".

### `Raises:`

List every exception that is *part of the interface*, with the condition that triggers it. Do not list exceptions that only occur when the caller violates a documented precondition — that failure is the caller's, not part of your contract.

### Overrides

A method that overrides a base-class method and keeps its behavior can carry just `"""See base class."""` — a copy of the base docstring would only drift. But if the override's behavior differs materially, or there are extra details a caller needs, it gets a full docstring of its own. Never lean on "See base class" to hide a real behavioral difference.

## Class docstrings

The class gets a docstring summarizing what it represents, with public attributes documented in an `Attributes:` section formatted like `Args:`:

```python
class SampleClass:
    """Summary of class here.

    Longer class information...

    Attributes:
        likes_spam: A boolean indicating if we like SPAM or not.
        eggs: An integer count of the eggs we have laid.
    """
```

What not to write:

- `class Foo:` followed by `"""Class Foo."""` — pure noise; say what it's *for* or say nothing (and for a class, "nothing" is not an option — find the real summary).
- "This class is a..." / "...is a class that..." — the reader can see it's a class.
- For an exception subclass, describe the error condition it represents, not the mechanics of it being an exception.

## Block and inline comments

Comment placement follows the same logic as everywhere else: a block comment before a tricky stretch of code; an inline comment on a single non-obvious line. Inline comments sit **at least two spaces** after the code, with one space after the `#`:

```python
# We use a weighted dictionary search to find out where i is in
# the array.  We extrapolate position based on the largest num
# in the array and the array size and then do binary search to
# get the exact number.

if i & (i-1) == 0:  # True if i is 0 or a power of 2.
```

Never describe what the code literally does — assume the reader knows Python better than you do. Explain intent and reasoning, not syntax. This is the canonical *bad* example:

```python
# BAD COMMENT: Now go through the b array and make sure whenever i occurs
# the next element is i+1
```

## TODO comments

Use `TODO` for code that is temporary, a short-term solution, or good-enough-but-not-perfect. Format: uppercase `TODO`, a reference where the reader can find context — a bug link, a username — then a colon and an explanation:

```python
# TODO: crbug.com/192795 - Investigate cpplint usage.
# TODO(yourname): File an issue and use a '*' for repetition.
```

The name or bug you cite is *where to find context*, not who has been assigned the fix. A TODO with a real completion condition should say so concretely — a specific date ("Fix by November 2026") or a specific event ("Remove when all clients handle XML responses") — so a future reader can tell whether it is still live.

## Peripheral rules that affect comments

- **pylint** flags missing docstrings. Suppress with `# pylint: disable=...` only locally and only with good reason — a suppression is a claim that the warning is wrong here, not a way to skip the work.
- **Do not comment out code.** Version control remembers it; delete it.
- **When the implementation changes, its documentation changes in the same edit** — an out-of-date docstring does more damage than a missing one.

## Reviewing or improving existing comments

When the task is auditing rather than writing — "check the docstrings in this file", "improve the docs on this module", "review this PR's comments" — read `references/review-checklist.md` for the pass order and the findings format. Work from most-harmful to least: docstrings that are now false, then missing contracts, then structure violations, then noise.

Register is part of the audit: filler, hedging, chattiness, cuteness, exclamation marks, and meta-commentary are findings wherever they appear, and the fix is a rewrite that keeps the facts and drops the words around them.

So is the budget. A docstring or comment that is correct but runs past its 2–3 sentence budget is itself a finding — trim it to its load-bearing sentences — and so is a usage-example block, an example return value, or any sentence that carries no fact the sentence before it did not.
