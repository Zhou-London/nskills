---
name: dont-look-back
description: Design principles for writing, modifying, or refactoring code - no backward compatibility, delete deprecated code entirely, pursue the best design from a global perspective. Use whenever writing or changing code.
---

# Don't Look Back

Follow these principles whenever you write, modify, or refactor code in this environment. Core idea: write code only for the ideal end state — leave no traces of the past. These principles override any default instinct toward conservative, compatibility-preserving edits.

## 1. No backward compatibility

- Do not keep compatibility layers for old interfaces, old call sites, or old data formats.
- Do not write deprecated markers, compatibility shims, re-export stubs, version branches, or transitional code. Adopt the new design directly and update all call sites.
- API signatures, config formats, and data structures may be freely changed to their best form.
- Assume no backward compatibility is needed — including for published APIs and persisted data formats — unless the user explicitly says otherwise. Do not make this decision for the user.

## 2. Delete deprecated things entirely

- Code, files, configs, and dependencies that become obsolete must be deleted outright — keep nothing.
- Do not comment out old code "just in case". Do not create backups like `.bak`, `_old`, or `legacy/` copies. Do not leave dead code paths behind feature flags.
- Do not worry about restoration — git owns the history. The working tree keeps only what is currently in use. Content covered by git history (committed) is deleted directly; no backup step first.
- Exception: if the content is not covered by git history (untracked files, uncommitted modifications, or a directory that is not a git repository) and it is genuinely important, do not delete it directly — move it into a `trash/` directory at the project root and add `trash/` to `.gitignore`.
- After deleting, verify: the build and tests still pass, and no references to the deleted code remain.

## 3. Pursue the best design from a global perspective

- When designing, first derive the best approach independently from a global view of the problem — do not start by checking whether it fits the existing framework.
- Do not bend to the existing architecture. If the best approach requires changing existing designs (directory structure, abstraction layers, module boundaries, interfaces), change them.
- "Global" means the problem domain of the current task, not the entire codebase. If the ideal design requires expanding beyond the task's scope, that triggers principle 5.
- Architectural conventions in the codebase are references, not constraints. Naming and code style, however, stay consistent with the existing codebase. Aim for the ideal end state instead of patching over old structures.
- Leave vendored, generated, and third-party code alone — it is outside the scope of these principles.

## 4. Comments describe only the present

- Comments and docstrings describe only what the code currently does and its design intent.
- Never mention the previous implementation, never explain why the old code was bad, and avoid phrasing like "changed to", "no longer", "replaces X", "previously", or "refactored from".
- Never correct the past. A comment must not deny or contrast with a state the codebase no longer has — a negation whose only referent is history ("not wire data", "no longer cached", "this is not a singleton") reads as noise to anyone without that history and pollutes the codebase. State the fact positively as a property of the current design ("written by the owning book"). A negation is legitimate only when it forestalls a misreading a fresh reader could form from the current code alone ("not thread-safe", "not owned; caller frees").
- The code should read as if it was designed this way from the start. Commit messages, and documents whose purpose is describing change (CHANGELOG, release notes, migration guides), may describe the change; source comments may not.

## 5. Warn the user before large-scale refactors

- The only exception to acting directly: if the codebase is large and the task requires a wide-ranging refactor (many files, core architecture changes, hard-to-estimate blast radius), inform the user before starting.
- Briefly state: what will change, the affected scope, and the rough scale. Wait for confirmation before proceeding.
- In non-interactive contexts where confirmation is impossible, fall back to the conservative scope: complete the task without the large-scale refactor, and note what you would have restructured.
- Small and medium changes need no confirmation — apply the principles above directly.
