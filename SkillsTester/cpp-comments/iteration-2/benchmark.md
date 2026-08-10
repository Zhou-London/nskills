# cpp-comments — iteration 2 benchmark

Three configurations: the skill at its two comment-complexity tiers (CC1 concise
= default, CC2 full detail) and a no-skill baseline. CC1 runs carry extra
brevity assertions, so its totals have a larger denominator.

| Config | Pass | Rate | Tokens | Seconds |
|---|---|---|---|---|
| Skill · CC1 (concise) | 32/33 | 97.0% | 79,184 | 184 |
| Skill · CC2 (full detail) | 29/29 | 100% | 85,811 | 265 |
| Baseline (no skill) | 28/29 | 96.6% | 64,148 | 235 |

| Eval | CC1 | CC2 | Baseline |
|---|---|---|---|
| add-comments-cpp | 10/11 | 9/9 | 9/9 |
| audit-comments-cpp | 12/12 | 12/12 | 11/12 |
| generate-module-cpp | 10/10 | 8/8 | 8/8 |

Key findings (details in benchmark.json notes): CC2 is the first perfect run in
this workspace; CC1's only failure was over-trimming (base_delay_s_ /
max_attempts_ left uncommented — dropped a required contract instead of
shortening it); CC1 met every brevity assertion and was the cheapest and
fastest with-skill config; both tiers fixed the baseline's severity-ordering
failure on the audit.
