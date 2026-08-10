# Reviewing comments and docstrings in existing Python code

Auditing documentation is not the same job as writing it. When you write, you know the intent. When you review, you have to work out what the code actually does, compare it against what the docstrings and comments claim, and rank the gaps by how much damage they do.

Sort findings by harm, and report them in that order. A wrong docstring sends a caller confidently in the wrong direction; a missing one only slows them down; a formatting slip just costs a glance. Fixing the formatting first is busywork that leaves the real hazards in place.

## Pass 1 — Docstrings and comments that are false or stale (highest harm)

These are the reason the audit is worth doing. Look for:

- A docstring describing behavior the code no longer has — parameters renamed, added, or dropped without the `Args:` section following; a changed return shape; error handling that moved.
- An `Args:` section that no longer matches the signature: missing parameters, extra parameters, or descriptions that contradict a default value or an annotation.
- A `Raises:` section listing exceptions the function can no longer raise, or silent about exceptions it now raises as part of its contract.
- Types stated in the docstring that contradict the annotations — when they disagree, one of them is lying; find out which.
- `"""See base class."""` on an override whose behavior has since diverged from the base contract.
- Copy-pasted docstrings carried onto a different function.
- References to functions, modules, flags, bugs, or docs that no longer exist.
- `TODO`s whose stated condition has already passed ("remove after the 2019 migration").

To flag these you have to actually read the implementation. A docstring that merely *sounds* plausible is not verified — check it against the code.

## Pass 2 — Missing contract information (high value)

Ask what a caller could get wrong that the docstring does not tell them. Most real bugs found in documentation reviews are here:

- A public, non-trivial, or non-obvious function with no docstring at all.
- Parameters whose meaning, valid range, or expected type (in unannotated code) is undocumented.
- A return value whose semantics are unstated — especially `None`-on-failure, sentinel values, or a tuple whose parts are not named.
- Exceptions that escape to the caller as part of normal use but appear nowhere in `Raises:`.
- Side effects the caller must know about — mutation of arguments, I/O, global state, caching.
- A class with public attributes and no `Attributes:` section.
- A module with no docstring, or one that gives no idea what the module is for.
- Why a non-obvious algorithm or a surprising-looking line is the way it is — especially anything that looks like it could be "simplified" into a bug.

## Pass 3 — Content in the wrong place or wrong register

- Implementation detail in a docstring, describing *how* where the caller only needs *what* — unless the detail (a side effect, a performance cliff) genuinely affects usage.
- Interface information buried in body comments that belongs in the docstring, where tools and callers can find it.
- Imperative summary lines ("Fetch rows...") where descriptive belongs ("Fetches rows...").
- A full docstring copy-pasted from the base class onto an override with identical behavior — replace with `"""See base class."""`.
- Types repeated in the docstring of a fully annotated function — the annotation is the source of truth; the docstring should carry semantics only.

## Pass 4 — Structure, formatting, and noise (lowest harm; fix, don't dwell)

- Single or triple-single quotes on docstrings instead of `"""`.
- Summary line missing terminal punctuation, over 80 characters, or not followed by a blank line before further content.
- Missing or misnamed sections (`Arguments:` instead of `Args:`, `Return:` instead of `Returns:`); generator documented with `Returns:` instead of `Yields:`.
- Inconsistent continuation indentation inside `Args:` (mixing 2- and 4-space hanging indents in one file).
- Inline comments not separated from code by at least two spaces, or missing the space after `#`.
- Comments that restate the code (`# increment i` above `i += 1`) or docstrings that restate the name (`"""Class Foo."""`).
- "Tests for X" module docstrings that add nothing — delete rather than pad.
- Malformed `TODO`s (no context reference, no colon) or open-ended ones with no date or triggering event.
- Commented-out code — delete it; version control has it.
- Docstring lines exceeding 80 characters (unwrappable URLs and paths excepted).

## Reporting

Group findings by file and give each one a line reference, the problem, and the fix. Distinguish clearly between:

- **Wrong** — the docstring or comment contradicts the code. Say what the code actually does.
- **Missing** — name the specific contract that is undocumented (the exception, the side effect, the sentinel), not just "needs a docstring".
- **Noise / mechanics** — batch these together rather than listing each one; a single "12 docstrings use single quotes, e.g. lines 40, 77, 102" is more useful than 12 entries.

If asked to fix rather than report, apply the same order, and when you cannot determine the true behavior with confidence, say so instead of writing a docstring that guesses — a confident wrong docstring is exactly what pass 1 exists to clean up.
