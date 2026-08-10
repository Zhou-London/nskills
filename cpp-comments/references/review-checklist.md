# Reviewing comments in existing C++ code

Auditing comments is not the same job as writing them. When you write, you know the intent. When you review, you have to work out what the code actually does, compare it against what the comments claim, and rank the gaps by how much damage they do.

Sort findings by harm, and report them in that order. A wrong comment sends a reader confidently in the wrong direction; a missing one only slows them down; a redundant one just costs a line. Fixing the redundant ones first is busywork that leaves the real hazards in place.

## Pass 1 — Comments that are false or stale (highest harm)

These are the reason the audit is worth doing. Look for:

- A comment describing behavior the code no longer has — parameters that were renamed or dropped, a return value that changed, error handling that moved.
- Documented invariants or preconditions the implementation stopped enforcing (or never did).
- Thread-safety or lifetime claims contradicted by the body — "thread-safe" on a class with unguarded mutable state, "does not retain" above a function that stores the pointer.
- Copy-pasted comments carried onto a different function, or an `override` comment copied from a base class whose contract has since diverged.
- References to functions, files, flags, bugs, or design docs that no longer exist.
- `TODO`s whose stated condition has already passed ("remove after the 2019 migration").

To flag these you have to actually read the implementation. A comment that merely *sounds* plausible is not verified — check it against the code.

## Pass 2 — Missing contract information (high value)

Ask what a caller could get wrong that the code does not tell them. Most real bugs found in comment reviews are here:

- Ownership: does the callee retain a pointer or reference argument past the call? Who deletes what?
- Nullability: which pointer parameters accept null, and what happens then?
- Thread-safety on any class with state that could plausibly be shared.
- Lifetime constraints — an object that must not outlive its parent, an iterator invalidated by an operation.
- Sentinel or magic values in data members (`-1` meaning "unknown", empty string meaning "unset").
- Units and ranges on numeric members and parameters (milliseconds vs seconds, 0–1 vs 0–100).
- Why a non-obvious algorithm or a surprising-looking line is the way it is — especially anything that looks like it could be "simplified" into a bug.
- Global variables with no stated purpose.

## Pass 3 — Comments in the wrong place

- Header comments duplicated into the `.cc` (or the reverse). Keep the contract at the declaration, the reasoning at the definition, and delete the copy.
- Implementation detail leaking into an interface comment, describing *how* where the caller only needs *what*.
- A file comment that restates the class comments below it.

## Pass 4 — Noise and mechanics (lowest harm; fix, don't dwell)

- Comments that restate the code (`// Increment i` / `++i;`) or the signature (`// Returns the name.` / `const std::string& name() const;`).
- Boilerplate `Constructs the object` / `Destroys the object`.
- `Author:` lines.
- Commented-out code — delete it; version control has it.
- Imperative mood where declarative belongs ("Open the file" → "Opens the file").
- Mixed `//` and `/* */` within one file; end-of-line comments not separated by two spaces.
- Malformed `TODO`s (no context reference, no colon) or open-ended ones with no date or triggering event.
- Argument comments not in the exact `/*param_name=*/value` form, or with a name that no longer matches the declaration.

## Reporting

Group findings by file and give each one a line reference, the problem, and the fix. Distinguish clearly between:

- **Wrong** — the comment contradicts the code. Say what the code actually does.
- **Missing** — name the specific contract that is undocumented, not just "needs a comment".
- **Noise** — batch these together rather than listing each one; a single "17 comments restate their code, e.g. lines 44, 61, 88" is more useful than 17 entries.

If asked to fix rather than report, apply the same order, and when you cannot determine the true behavior with confidence, say so instead of writing a comment that guesses — a confident wrong comment is exactly what pass 1 exists to clean up.
