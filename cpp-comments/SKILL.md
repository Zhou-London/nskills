---
name: cpp-comments
description: Google C++ Style Guide rules for writing and reviewing comments — file/class/function/variable comments, declaration-vs-definition split, `/*param=*/` argument comments, TODO format, and what NOT to comment. Use this skill whenever you write, generate, or modify C++ code (.h/.hpp/.cc/.cpp/.cxx/.cu), whenever you are asked to add, improve, translate, audit, or review comments or documentation in C++ code, and whenever a C++ review touches comment quality — even if the user never says "Google style" or "comment convention" and even for a small edit to a single function.
---

# Writing C++ comments (Google style)

## The test a comment has to pass

A comment earns its place only when it carries information the code cannot. Assume the reader knows C++ at least as well as you do — they can read a `for` loop. What they cannot recover from the code is **intent, rationale, contract, and constraint**: why this algorithm and not the obvious one, what a caller is allowed to pass, whether the object keeps the pointer after the call, what a sentinel value means, what breaks under concurrency.

Before writing a comment ask: *if I delete this, what does the reader lose?* "Nothing" means delete it. "They'd have to reverse-engineer it from the body, or guess and get it wrong" means keep it.

Two failure modes, and the second is the dangerous one:

- **Over-commenting** — restating code in prose. Adds noise, and trains readers to skip comments.
- **Stale comments** — worse than no comment, because the reader trusts them. Any time you change behavior, the comments describing that behavior are part of the change.

## Where each kind of information lives

| Place | Answers | For whom |
|---|---|---|
| File comment (`.h`) | What is this file about as a whole? | Someone browsing the directory |
| Class comment (`.h`) | What is this for, and how do I use it? | The caller |
| Function declaration (`.h`) | What does it do, what may I pass, what do I get back? | The caller |
| Function definition (`.cc`) | How does it work, and why this way? | The maintainer |
| Inside the body | Why is this tricky bit correct? | The maintainer |

Never duplicate a comment across two of these places. Duplicates drift apart under maintenance, and then one of them is lying with no way for the reader to tell which.

## Style and language

Both `//` and `/* */` are legal, but a file must be internally consistent. In practice use `//` nearly everywhere — the exception is the inline argument comment `/*param_name=*/value`, which is deliberately `/* */` so it sits inside the call.

**Comment language:** match the surrounding code. Scan comments in the same file, then nearby files in the directory — if they are English, write English; if the codebase comments in Chinese (or another language), write in that language so the file reads as one voice. For a brand-new file with nothing to match, default to English. Formatting rules (`TODO:`, `/*param=*/`, third person, sentence punctuation) apply regardless of language.

## File comments

Start each file with the project's license boilerplate (Apache 2.0, BSD, whatever the project uses — copy the header from a neighboring file rather than inventing one).

When a `.h` declares several related abstractions, a file comment describes the overall theme and can point at the important pieces. Do not restate the class comments inside it — the file comment is the map, not the territory. If the header declares exactly one thing that its own comment already explains, a file comment adds nothing; skip it.

Detailed documentation belongs in the header. A `.cc` needs a file-level comment only when there is something to say about the implementation as a whole (an overall strategy, a layout invariant shared by all the functions). Otherwise, no file comment.

Do not add `Author:` lines. Version control already records authorship, and the line goes stale the moment someone else maintains the file.

## Class comments

Every non-obvious class or struct declaration gets a comment saying what it is for and how to use it. A short usage example is often worth more than a paragraph of prose:

```cpp
// Iterates over the contents of a GargantuanTable.
// Example:
//    std::unique_ptr<GargantuanTableIterator> iter = table->NewIterator();
//    for (iter->Seek("foo"); !iter->done(); iter->Next()) {
//      process(iter->key(), iter->value());
//    }
class GargantuanTableIterator { ... };
```

Two things callers cannot see and will get wrong without you:

- **Synchronization assumptions.** Is it thread-safe? Thread-compatible (safe for concurrent reads, external locking for writes)? Must all calls come from one thread? Say so explicitly — silence here reads as "probably fine", which is how data races ship.
- **Lifetime constraints.** If an instance must not outlive some event or another object, or if it holds a reference to something the caller owns, write it down.

The class comment is *how to use it*. How it is implemented belongs next to the implementation.

## Function comments

### At the declaration — what it does, how to call it

Nearly every function declaration gets a comment. Omit it only when the function is genuinely obvious, in the sense that a reader cannot form a wrong expectation about it — a plain accessor like `int size() const;` is the clear case.

Write in the third-person declarative, describing the function: "Opens the file", not "Open the file". You are documenting a thing, not issuing an order.

Cover whatever the signature does not already say:

- What the inputs mean and what the return value is (including how errors are reported).
- Whether the object retains a reference or pointer argument after the call returns, and who owns what afterwards. This is the single most valuable line in most C++ comments.
- Whether pointer arguments may be null, and what happens if they are.
- What output parameters get filled in, and whether they are touched on failure.
- Performance consequences the caller should know about — that it takes a lock, does I/O, is O(n) where the caller might assume O(1).

Do not restate the signature. `// Returns the size.` above `size_t size() const;` is pure noise.

For a virtual function `override` that behaves as the base class documents, add nothing — the base comment stands, and a copy will drift. Comment only the difference in behavior.

Constructors and destructors: skip "Constructs the object" / "Destroys the object". Comment them when they do something non-obvious — a destructor that flushes buffers, closes descriptors, or blocks on a background thread deserves a line.

```cpp
// Sends `request` to the backend and blocks until a response arrives or
// `timeout` elapses. Returns nullptr on timeout; the connection stays usable.
// Does not retain `request`; the caller may destroy it once this returns.
// `observer` may be null, in which case progress updates are dropped.
std::unique_ptr<Response> SendBlocking(const Request& request,
                                       absl::Duration timeout,
                                       ProgressObserver* observer);
```

### At the definition — how it works, and why

If the implementation does anything tricky, non-obvious, or interesting, explain it where it lives: why this algorithm was chosen, what clever trick is in play, how the stages of the function relate. Do not copy the header comment down into the `.cc` — the declaration comment is the contract and belongs in exactly one place.

## Variable comments

The name is usually the documentation. `num_retries_` needs no comment. Reach for a comment when the type and name together still leave something unsaid — most often units, ranges, invariants, or a sentinel value. A sentinel that is not documented is a bug waiting for the next maintainer:

```cpp
private:
 // Used to bounds-check table accesses. -1 means
 // that we don't yet know how many entries the table has.
 int num_total_entries_;
```

Global variables get a comment saying what they are for and — when it is not obvious — why they need to be global at all.

## Implementation comments

Put a block comment above a tricky or complicated stretch of code:

```cpp
// Divide result by two, taking into account that x
// contains the carry from the add.
for (int i = 0; i < result->size(); ++i) {
```

For a single non-obvious line, an end-of-line comment works. Separate it from the code by **two spaces**:

```cpp
mmap_budget = max<int64_t>(0, mmap_budget - index_->length());
if (mmap_budget >= data_size_ && !MmapData(mmap_chunk_bytes, mlock))
  return;  // Error already logged.
```

Never write a comment that is just the code translated into prose. `// Increment i` above `++i;` insults the reader and costs a line forever. Explain the intent, the reason, or the context the code cannot express.

## Function argument comments

When an argument's meaning is not obvious at the call site — a bare `true`, a magic number — the first move is to fix the call, not to annotate it. In descending order of preference: use a named constant or enum, hoist the value into a named local, or bundle related options into a struct.

```cpp
ProductOptions options;
options.set_precision_decimals(7);
options.set_use_cache(ProductOptions::kDontUseCache);
const DecimalNumber product =
    CalculateProduct(values, options, /*completion_callback=*/nullptr);
```

If a literal still has to be passed inline, name it with an argument comment in exactly the form `/*param_name=*/value` — no spaces around the `=`, immediately abutting the value. clang-tidy verifies the name against the declaration, so the exact spelling matters. Compare `CalculateProduct(values, 7, false, nullptr)`, where the reader has no way to know what any of it means.

## Punctuation, spelling, grammar

Comments are read far more often than they are written, so mind the mechanics. Complete sentences — capitalized, punctuated — read more easily than fragments. Short end-of-line comments can be looser, but stay consistent within a file.

## TODO comments

Use `TODO` for code that is temporary, a short-term solution, or good-enough-but-not-perfect. Format: uppercase `TODO`, then something that lets a reader find more context — a bug ID, a design doc, a username — then a colon and an explanation.

```cpp
// TODO: bug 12345678 - Remove this after the 2047q4 compatibility window expires.
// TODO: example.com/my-design-doc - Manually fix up this code the next time it's touched.
// TODO(bug 12345678): Update this list after the Foo service is turned down.
// TODO(John): Use a "*" here for concatenation operator.
```

The person or bug you name is *where to find context*, not who has been assigned the fix — do not write a name as a way of volunteering someone.

A TODO that says "someday" never gets done. If it is scheduled, tie it to a specific date ("Fix by November 2026") or a specific event ("Remove this code when all clients can handle XML responses") so a future reader can tell whether it is still live.

## Two rules from elsewhere in the guide that decide comment quality

- **Do not comment out code.** Large commented-out blocks are dead weight that no one dares delete and that no tooling checks. Version control remembers it; delete it.
- **Interface comments describe the abstraction, not the implementation.** A caller reading your header should not learn things that would break them when you rewrite the body. And when the implementation does change, updating the comments is part of the change, not cleanup for later — an out-of-date comment does more damage than no comment at all.

## Reviewing or improving existing comments

When the task is auditing comments rather than writing new code — "check the comments in this file", "improve the docs on this class", "review this PR's comments" — read `references/review-checklist.md` for the pass order and the findings format. Work from most-harmful to least: comments that are now false, then contracts that are missing, then noise.
