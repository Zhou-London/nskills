# python-comments — iteration 2 benchmark

Three configurations: the skill at its two comment-complexity tiers (CC1 concise
= default, CC2 full detail) and a no-skill baseline. CC1 runs carry extra
brevity assertions, so its totals have a larger denominator.

| Config | Pass | Rate | Tokens | Seconds |
|---|---|---|---|---|
| Skill · CC1 (concise) | 30/34 | 88.2% | 79,617 | 192 |
| Skill · CC2 (full detail) | 28/29 | 96.6% | 84,447 | 236 |
| Baseline (no skill) | 26/28 | 92.9% | 61,027 | 199 |

| Eval | CC1 | CC2 | Baseline |
|---|---|---|---|
| add-docstrings | 10/12 | 8/9 | 8/9 |
| audit-comments | 11/11 | 11/11 | 10/11 |
| generate-module | 9/11 | 9/9 | 8/8 |

Key findings (details in benchmark.json notes): CC1 still emitted forbidden
"Typical usage example:" blocks in both writing evals and skipped the
Attributes: section on generate; the unannotated-code Args-type rule failed in
all three configs (skill-wide gap, not a tier effect); both tiers fixed the
baseline's severity-ordering failure on the audit.
