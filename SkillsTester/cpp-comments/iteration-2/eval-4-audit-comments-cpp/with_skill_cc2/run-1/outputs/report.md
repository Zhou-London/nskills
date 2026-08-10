# Comment audit: `session_store.h` / `session_store.cc`

Scope: comment quality only, per the Google C++ Style Guide comment rules. Findings are
ordered by severity — comments that are false first (they send readers confidently in the
wrong direction), then missing contract information, then misplaced comments, then noise
and mechanics. No code has been changed.

Files audited:

- `/Users/zhou/.claude/skills/SkillsTester/cpp-comments/evals/files/session_store.h`
- `/Users/zhou/.claude/skills/SkillsTester/cpp-comments/evals/files/session_store.cc`

---

## Severity 1 — Wrong: comments that contradict the code

### 1.1 `Get` declaration comment documents the wrong error behavior (h:15–18)

```cpp
// Returns the session data for `session_id`, or an empty string if the
// session does not exist or has expired. ...
std::string Get(const std::string& session_id, double now_s);
```

The comment says a missing or expired session yields an **empty string**. The
implementation (`session_store.cc:9–17`) does neither:

- A missing session id makes `sessions_.at(session_id)` throw `std::out_of_range`
  (cc:11).
- An expired session is evicted and then **explicitly throws** `std::out_of_range`
  (cc:12–15).

There is no code path that returns an empty string for a missing/expired session (an
empty string is returned only when the stored data itself is empty — which the comment's
claim makes ambiguous, since a caller following the comment cannot distinguish "empty
data" from "no session"). This is the most damaging finding in the audit: a caller who
trusts the header will write `if (store.Get(id, now).empty())` and get an unhandled
exception in production instead. **Fix:** rewrite the comment to state the real contract
— throws `std::out_of_range` if the session does not exist or has expired (and, per
finding 2.1, that expired sessions are evicted as a side effect) — or, if the empty-string
contract is the intended one, the *code* is what needs fixing; the audit cannot decide
which, but the two must be reconciled.

### 1.2 `Get` declaration comment describes a parameter that does not exist (h:16–17)

```cpp
// ... The `timeout_s` argument
// overrides the store-wide TTL for this lookup only.
```

The function signature is `Get(const std::string& session_id, double now_s)`. There is no
`timeout_s` parameter, and nothing in the implementation performs a per-lookup TTL
override — `now_s` is compared against the store-wide `ttl_s_` only (cc:12). This is a
stale remnant of an earlier signature. A reader may waste time hunting for the override
mechanism or, worse, assume `now_s` plays that role and pass a timeout value as the
current time. **Fix:** delete the sentence and instead document what `now_s` actually is
(the caller-supplied current time, in seconds, used for expiry checks — see finding 2.4).

---

## Severity 2 — Missing: contract information a caller will get wrong

### 2.1 `Get` has undocumented side effects (h:18, cc:9–17)

`Get` is not a pure lookup:

- It increments `lookup_count_` on every call, including failed ones (cc:10) — which is
  why it cannot be `const`, something a reader will otherwise flag as a mistake.
- It **evicts** an expired session before throwing (cc:13), so a failed `Get` mutates the
  store: a subsequent `Purge` will not count that session, and `Delete` on it will return
  `false`.

Neither effect is visible from the declaration and both belong in the declaration
comment, since callers can observe them.

### 2.2 The negative-TTL sentinel is undocumented (h:12–13, h:41)

Both `Get` (cc:12) and `Purge` (cc:36) guard expiry with `ttl_s_ >= 0`, meaning a
**negative TTL disables expiry entirely** — sessions live forever. Neither the
constructor comment ("expire ttl_s seconds after creation") nor the `ttl_s_` member
documents this sentinel. An undocumented sentinel is exactly the kind of thing the next
maintainer "fixes" into a bug. **Fix:** state it at the constructor declaration (the
caller-facing contract), e.g. "A negative `ttl_s` means sessions never expire."

### 2.3 No thread-safety statement on the class (h:10)

`SessionStore` has mutable state (`sessions_`, `lookup_count_`) and no synchronization,
yet the class comment is silent on threading. Silence reads as "probably fine", which is
how data races ship. **Fix:** add one line to the class comment, e.g. "Not thread-safe;
callers must serialize access externally."

### 2.4 `now_s` is undocumented in every signature that takes it (h:18, h:21–22, h:28)

`Get`, `Put`, and `Purge` all take `double now_s`, and no comment says what it means: the
caller-supplied current time in seconds (a monotonic-vs-wall-clock choice the caller must
get consistent across calls, since expiry is computed as `now_s - created_s`). The `Put`
comment also omits that `now_s` becomes the session's creation time — i.e. that
re-`Put`ting an existing id **resets its TTL**, an observable behavior worth one clause.

### 2.5 `Evict`'s `notify` parameter is undocumented and inert (h:38, cc:46–51)

The private helper `Evict(const std::string&, bool notify)` has no comment, and `notify`
currently does nothing (the body is an empty block with a placeholder comment, cc:48–50).
A `bool` parameter whose effect cannot be discovered from the code needs a line saying
what it is *supposed* to do — or, better, the parameter should be removed until the hook
exists. At minimum, document the intent above the declaration.

### 2.6 Boundary semantics of expiry are unstated (h:12, cc:12, cc:36)

Expiry uses strict `>` (`now_s - created_s > ttl_s_`), so a session is still alive at
exactly `ttl_s` seconds. Minor, but "expire ttl_s seconds after creation" (h:12) is
off-by-one ambiguous; one word ("strictly more than `ttl_s` seconds") settles it.

---

## Severity 3 — Wrong place: duplicated / misplaced comments

### 3.1 Header contract comment duplicated onto the `.cc` definition (cc:7–8)

```cpp
// Returns the session data for `session_id`, or an empty string if the
// session does not exist or has expired.
std::string SessionStore::Get(...)
```

This is a copy of the declaration comment from `session_store.h:15–18` — and it has
already drifted (the `timeout_s` sentence was dropped in one copy), demonstrating exactly
why the guide forbids the duplication: the two copies now disagree and a reader cannot
tell which one is authoritative (in fact both are false, per finding 1.1). The contract
belongs at the declaration only. **Fix:** delete the `.cc` copy; if the definition needs
a comment at all, it should explain *how/why* (e.g. why expired entries are evicted
lazily on read), not restate the contract.

---

## Severity 4 — Noise and mechanics (batch fixes)

### 4.1 Commented-out code (cc:21–24)

```cpp
// old implementation kept for reference
// if (sessions_.count(session_id) > 0) {
//   throw std::invalid_argument("duplicate session");
// }
```

Delete it. Version control remembers it; "kept for reference" blocks are dead weight no
tooling checks, and this one also silently documents a contract change (duplicate `Put`
used to throw, now overwrites) that is better captured by the `Put` declaration comment —
which already says "Overwrites any existing session with the same id."

### 4.2 Malformed TODO (cc:32)

`// TODO fix this later` breaks every rule of the TODO format: no colon, no context
reference (bug ID, doc link, or username), no statement of *what* is wrong with `Purge`,
and no date or triggering event — a "someday" TODO that will never get done. Either give
it the standard shape (`// TODO: bug NNNN - <specific problem, and when to fix it>`) or
delete it.

### 4.3 Malformed argument comment (cc:13)

`Evict(session_id, /* notify */ false)` — the required form is `/*notify=*/false`: no
spaces inside the delimiters, `=` abutting the value. clang-tidy verifies the exact
spelling against the declaration, so the current form gets no tooling protection.

### 4.4 `Author:` line (h:1)

`// Author: bob@example.com` — remove. Version control records authorship, and the line
goes stale the moment someone else maintains the file. (Separately, if the project uses
license boilerplate, the file should open with it — copy the header from a neighboring
file.)

### 4.5 Comment restates the code (cc:10)

`++lookup_count_;  // increment the lookup counter` — pure prose translation of the code;
delete it. (The *useful* fact — that failed lookups are counted too — belongs in the
declaration comment, per finding 2.1.) Also lowercase/unpunctuated, but deletion moots
that.

### 4.6 Imperative mood and missing punctuation (h:24)

`// Delete the session and return whether it existed` — should be third-person
declarative with a period: "Deletes the session and returns whether it existed." Its
neighbors (h:15, h:20, h:27) already use the declarative form, so this one is also
internally inconsistent.

---

## Summary

| Severity | Count | Findings |
|---|---|---|
| 1 — Wrong | 2 | Get's empty-string claim vs. thrown `std::out_of_range`; phantom `timeout_s` parameter |
| 2 — Missing | 6 | Get's side effects; negative-TTL sentinel; thread-safety; `now_s` semantics / TTL reset on Put; `Evict(notify)`; expiry boundary |
| 3 — Misplaced | 1 | Header contract duplicated (and drifted) onto the `.cc` definition |
| 4 — Noise | 6 | Commented-out code; malformed TODO; malformed `/*param=*/`; Author line; code-restating comment; imperative mood |

The two Severity-1 findings should be resolved first, and they require a decision the
audit cannot make alone: whether the intended contract of `Get` is "throws" (fix the
comments) or "returns empty string" (fix the code).
