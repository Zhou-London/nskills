// Client-safe config constants (no fs/path imports — usable from "use client"
// components). lib/data.ts re-exports these for server code.

// "with_skill" is the legacy single-tier config (iteration-1); the cc1/cc2
// configs are the comment-complexity tiers introduced in iteration-2.
export const CONFIGS = [
  "with_skill",
  "with_skill_cc1",
  "with_skill_cc2",
  "without_skill",
] as const;
export type ConfigName = (typeof CONFIGS)[number];

export const CONFIG_LABELS: Record<ConfigName, string> = {
  with_skill: "With skill",
  with_skill_cc1: "Skill · CC1 (concise)",
  with_skill_cc2: "Skill · CC2 (full detail)",
  without_skill: "Baseline (no skill)",
};

/** Compact labels for chips and column headers, where width is scarce. */
export const CONFIG_SHORT: Record<ConfigName, string> = {
  with_skill: "Skill",
  with_skill_cc1: "CC1",
  with_skill_cc2: "CC2",
  without_skill: "Baseline",
};

export const CONFIG_COLORS: Record<ConfigName, string> = {
  with_skill: "var(--series-1)",
  with_skill_cc1: "var(--series-3)",
  with_skill_cc2: "var(--series-4)",
  without_skill: "var(--series-2)",
};

export function pct(passed: number, total: number): number {
  return total === 0 ? 0 : Math.round((passed / total) * 1000) / 10;
}
