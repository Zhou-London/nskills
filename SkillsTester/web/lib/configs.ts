// Client-safe config constants (no fs/path imports — usable from "use client"
// components). lib/data.ts re-exports these for server code.

// Every eval runs twice: once with the skill loaded, once with it forbidden.
export const CONFIGS = ["with_skill", "without_skill"] as const;
export type ConfigName = (typeof CONFIGS)[number];

export const CONFIG_LABELS: Record<ConfigName, string> = {
  with_skill: "With skill",
  without_skill: "Baseline (no skill)",
};

/** Compact labels for chips and column headers, where width is scarce. */
export const CONFIG_SHORT: Record<ConfigName, string> = {
  with_skill: "Skill",
  without_skill: "Baseline",
};

export const CONFIG_COLORS: Record<ConfigName, string> = {
  with_skill: "var(--series-1)",
  without_skill: "var(--series-2)",
};

export function pct(passed: number, total: number): number {
  return total === 0 ? 0 : Math.round((passed / total) * 1000) / 10;
}
