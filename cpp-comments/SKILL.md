---
name: cpp-comments
description: Google C++ Style Guide rules for writing and reviewing comments — file/class/function/variable comments, declaration-vs-definition split, `/*param=*/` argument comments, TODO format, the professional register comments are written in (no filler, hedging, chattiness, or cutesy phrasing), and what NOT to comment. Optimizes for information density: short comments over long ones, every sentence earning its place with a fact, and no usage-example blocks. Use this skill whenever you write, generate, or modify C++ code (.h/.hpp/.cc/.cpp/.cxx/.cu), whenever you are asked to add, improve, shorten, translate, audit, review, or make more professional the comments or documentation in C++ code, and whenever a C++ review touches comment quality — even if the user never says "Google style" or "comment convention" and even for a small edit to a single function.
---

# C++ comments

Rules from the Google C++ Style Guide, plus a density budget. Everything needed is stated here; no prior knowledge of the guide is assumed.

## What a comment is for

A comment carries what the code cannot: **contract, constraint, intent, rationale**. The reader knows C++ and can read a loop. They cannot know what a caller may pass, whether the callee keeps a pointer, what a sentinel means, or what breaks under concurrency.

Test each comment: *delete it — what does the reader lose?* Nothing → delete it.

Two failures: restating code adds noise and trains readers to skip comments; a stale comment is worse than none, because the reader trusts it. Changing behavior includes updating the comments that describe it.

## Brevity

Density is facts per word — facts the code does not already state, divided by words spent. Maximize it. **Between two comments carrying the same facts, the shorter one is better.** A verbose comment is a defect even when everything in it is true: it buries the contract and trains readers to skip comments.

There is no sentence limit. Length is earned by facts, and by nothing else:

- **Write the shortest form that carries the contract.** One sentence is the normal case for a declaration. Two is common. Past three, check for padding or an interface doing too much.
- **Every added sentence must carry a fact no earlier sentence carries.** Otherwise delete it.
- **Importance does not buy length.** Complex code justifies more facts; facts justify more words. Never the reverse.
- **No usage-example blocks.** Many lines for one fact the reader gets from a call site or test.
- Cut words, not facts. Never drop a contract to make a comment shorter.
- What to document is unchanged: ownership, nullability, thread-safety, sentinels, units, rationale.

**Shortening.** Join related short facts with a semicolon rather than spending a sentence on each — bare assertions like "Not thread-safe" or "Not copyable" are the cheapest to join. Drop lead-ins, name symbols instead of describing them, and never restate the signature.

```cpp
// Tracks tasks awaiting retry. All `_s` values are seconds on a caller-supplied
// clock. Payloads are borrowed and must outlive their entry. Not thread-safe.
```

Same four facts, two sentences and 8 words shorter:

```cpp
// Tracks tasks awaiting retry; all `_s` values are seconds on a caller-supplied
// clock. Payloads are borrowed and must outlive their entry; not thread-safe.
```

## Say each fact once

The same guarantee stated in three places costs three times the words, earns nothing, and the copies drift apart until one is wrong.

Each fact has one home:

| Place | Answers |
|---|---|
| File comment (`.h`) | What is this file about as a whole? |
| Class comment (`.h`) | What is this type for, and what holds across it? |
| Function declaration (`.h`) | What does *this* function do, take, and return? |
| Member declaration (`.h`) | What do the name and type leave unsaid? |
| Function definition (`.cc`) | How does it work, and why this way? |
| Inside the body | Why is this line correct? |

Rules:

- **Type-wide properties go in the class comment only** — thread-safety, ordering guarantees, clock or unit conventions, lifetime rules. Method comments state only what is specific to that method.
- **Never copy a declaration comment into the `.cc`.** The `.cc` explains mechanism, never the contract the mechanism implements.
- **Member comments are the exception to upward hoisting.** Units, ranges, invariants, and sentinels belong at the member declaration even when the class comment states a convention. Conventions are ambiguous: `_s` says seconds but not whether the value is a duration or an absolute timestamp. Drop a member comment only when it adds nothing beyond the name.

## Register

Professional and concise, like a colleague stating a contract in review. State the fact; stop.

- **One fact per sentence, stated directly.** "Note that callers should be aware this may block." → "Blocks until the response arrives."
- **Third person, present tense, active voice.** "Returns nullptr on timeout" — not "Return nullptr", "You'll get nullptr", or "We return nullptr".
- **Precise, not emphatic.** Not "a bit slow" but "takes the table lock for the whole scan".
- **Name symbols exactly as the code spells them,** in backticks.

Delete on sight:

| Kind | Examples |
|---|---|
| Filler openers | "Basically", "Essentially", "Actually", "Of course", "Note that", "It should be noted that", "As you can see", "Simply", "Just" |
| Hedges | "should probably", "kind of", "sort of", "I think", "for some reason" — real uncertainty goes in a `TODO:` |
| Reader address, chattiness | "you", "your", "we'll", "let's", "don't worry", "feel free" |
| Cutesy or hyped words | "magic", "secret sauce", "sprinkle in", "awesome", "nifty", "voilà" |
| Intensifiers, vague scale, self-praise | "very", "extremely", "super", "a lot", "huge", "elegant", "clever trick" |
| Anthropomorphism | "the queue is happy to accept", "the parser wants a token" |
| Emotive punctuation, decoration | `!`, `?!`, emoji, `====` banners, ALL-CAPS emphasis, `*bold*` — only `TODO:`, `NOTE:`, `WARNING:` are conventional |
| Quality meta-commentary | "this is ugly but it works", "sorry about this", "hacky" |
| Construct restatement | "This function ...", "This class is a class that ...", "This method is used to ..." — start with the verb |

Same facts, before and after:

```cpp
  // Ugh, the old API is kind of a mess here, so we do this dance :(
  buffer.resize(n + 1);

  // The legacy decoder writes a trailing NUL past `n`; the extra byte keeps it
  // out of the caller's storage.
  buffer.resize(n + 1);
```

**Mechanics.** Complete sentences, capitalized and punctuated. End-of-line comments may be terser; stay consistent within a file.

**Language.** Match the surrounding code — scan the file, then the directory. New file with nothing to match: English. All rules here apply in any language, including the ban on filler, hedging, and sentence-ending particles.

## Comment syntax

Use `//` everywhere. `/* */` is legal but reserve it for the argument comment `/*param_name=*/value`, which must sit inside a call. Never mix the two styles in one file.

## File comments

Begin each file with the project's license boilerplate, copied from a neighboring file.

A `.h` file comment describes the theme when the header declares several related abstractions, and points at the important ones. It does not restate the class comments below it. If the header declares one thing that its own comment explains, omit the file comment.

A `.cc` gets a file comment only for something true of the whole implementation — an overall strategy, a shared invariant.

No `Author:` lines. Version control records authorship.

## Class comments

Every non-obvious class or struct gets a comment: what it is for, plus the constraints a caller cannot see.

```cpp
// Iterates over the contents of a GargantuanTable. Invalidated by any write to
// the table. Not thread-safe; one iterator per thread.
class GargantuanTableIterator { ... };
```

Two constraints callers get wrong without you:

- **Synchronization.** Thread-safe, thread-compatible (concurrent reads safe, writes need external locking), or single-thread only. State it. Silence reads as "probably fine".
- **Lifetime.** If an instance must not outlive something, or holds a reference the caller owns, say so.

This comment says how to use the type, and holds every type-wide guarantee. Implementation belongs at the implementation.

## Function comments

### Declaration — the contract

Comment nearly every declaration. Omit only where the reader cannot form a wrong expectation: `int size() const;` is the clear case.

Cover what the signature does not say, minus what the class comment says:

- What the inputs mean; what the return value is, including how errors are reported.
- Whether the callee retains a pointer or reference argument after returning, and who owns what. This is the most valuable line in most C++ comments.
- Which pointer arguments may be null, and what happens then.
- Which output parameters are filled in, and whether they are touched on failure.
- Costs the caller should know: takes a lock, does I/O, O(n) where O(1) is assumed.

Never restate the signature: `// Returns the size.` above `size_t size() const;` is noise.

An `override` matching the base contract gets no comment; the base comment stands and a copy drifts. Comment only a difference.

Skip "Constructs the object" and "Destroys the object". Comment a destructor that flushes, closes, or blocks.

Six facts, two sentences — what it does, when it unblocks, the timeout return, the connection surviving, `request` not retained, `observer` nullable:

```cpp
// Sends `request` to the backend, blocking until a response arrives or `timeout`
// elapses; returns nullptr on timeout and the connection stays usable. Does not
// retain `request`; `observer` may be null.
std::unique_ptr<Response> SendBlocking(const Request& request,
                                       absl::Duration timeout,
                                       ProgressObserver* observer);
```

### Definition — the mechanism

Explain anything tricky where it lives: why this algorithm, what the non-obvious line does, how the stages relate. Never restate the header contract.

## Variable comments

The name is usually the documentation; `num_retries_` needs none. Comment when the name and type leave something unsaid — in practice **units, ranges, invariants, sentinels**. An undocumented sentinel is a bug waiting for the next maintainer.

```cpp
private:
 // Bounds-checks table accesses. -1 means the entry count is not yet known.
 int num_total_entries_;
```

Global variables: what they are for, and why they are global if that is not obvious.

## Implementation comments

Block comment above a tricky stretch. For one line, an end-of-line comment, separated by **two spaces**:

```cpp
if (mmap_budget >= data_size_ && !MmapData(mmap_chunk_bytes, mlock))
  return;  // Error already logged.
```

Never translate code into prose: `// Increment i` above `++i;` costs a line forever and tells the reader nothing. Explain intent, reason, or context.

Never comment out code. Version control has it; delete it.

## Argument comments

When a literal's meaning is unclear at the call site, fix the call first: a named constant or enum, a named local, or an options struct.

```cpp
ProductOptions options;
options.set_precision_decimals(7);
options.set_use_cache(ProductOptions::kDontUseCache);
const DecimalNumber product =
    CalculateProduct(values, options, /*completion_callback=*/nullptr);
```

If a literal must stay inline, write `/*param_name=*/value` — no spaces around `=`, abutting the value. clang-tidy checks the name against the declaration, so spelling matters. Compare `CalculateProduct(values, 7, false, nullptr)`, which tells the reader nothing.

## TODO comments

For temporary, short-term, or good-enough-for-now code. Format: uppercase `TODO`, a context reference (bug ID, design doc, or username), a colon, an explanation.

```cpp
// TODO: bug 12345678 - Remove after the 2047q4 compatibility window expires.
// TODO(John): Use a "*" here for the concatenation operator.
```

The name or bug is where to find context, not an assignment — do not volunteer someone. Tie the TODO to a date ("Fix by November 2026") or an event ("Remove when all clients handle XML"), so a reader can tell whether it is still live.

## Interface vs implementation

A header comment describes the abstraction. A caller must not learn anything that would break them when the body is rewritten.

## Before finishing

One pass over the comments, in file order. Delete only; do not revisit the design or edit working code.

1. Which fact does this sentence carry? None → delete.
2. Stated already? → keep the copy at the scope that owns it, delete the rest.
3. Can these facts fit in fewer words or fewer sentences? → shorten.
4. Usage example or `Author:` line → delete.

## Auditing existing comments

Only for review tasks — "check the comments", "improve the docs", "review this PR's comments". Read `references/review-checklist.md` for pass order and findings format. Writing code never needs that file.

Order by harm: false comments, then missing contracts, then comments in the wrong place, then noise. Register and verbosity are findings too — filler, hedging, chattiness, a usage example, a fact another comment already carries, or a correct comment that spends four sentences on what fits in two. Quote the wordy version and give the shorter rewrite; "too long" alone is not actionable.
