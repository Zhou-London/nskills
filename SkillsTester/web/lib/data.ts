import fs from "fs";
import path from "path";

// The workspace root is the parent of web/ (override with SKILLSTESTER_WS).
export const WORKSPACE =
  process.env.SKILLSTESTER_WS || path.resolve(process.cwd(), "..");

import { CONFIGS, type ConfigName } from "./configs";

export {
  CONFIGS,
  CONFIG_LABELS,
  CONFIG_COLORS,
  pct,
  type ConfigName,
} from "./configs";

/** The configs actually present in this skill's latest iteration. */
export function skillConfigs(skill: SkillData): ConfigName[] {
  const present = new Set<ConfigName>();
  for (const e of skill.evals) {
    for (const c of CONFIGS) if (e.configs[c]) present.add(c);
  }
  return CONFIGS.filter((c) => present.has(c));
}

export interface Assertion {
  text: string;
  passed: boolean;
  evidence: string;
}

export interface RunData {
  assertions: Assertion[];
  passed: number;
  total: number;
  tokens: number | null;
  seconds: number | null;
  outputs: { name: string; content: string }[];
}

export interface EvalData {
  id: number;
  evalName: string;
  dirName: string;
  prompt: string;
  expectedOutput: string;
  files: string[];
  plantedDefects: string[];
  configs: Partial<Record<ConfigName, RunData>>;
}

export interface SkillData {
  name: string;
  description: string;
  iteration: number;
  evals: EvalData[];
  notes: string[];
}

function readJson(p: string): any | null {
  try {
    return JSON.parse(fs.readFileSync(p, "utf-8"));
  } catch {
    return null;
  }
}

function readText(p: string): string | null {
  try {
    return fs.readFileSync(p, "utf-8");
  } catch {
    return null;
  }
}

/** Directories under the workspace that hold an evals/evals.json. */
export function listSkillNames(): string[] {
  let entries: fs.Dirent[] = [];
  try {
    entries = fs.readdirSync(WORKSPACE, { withFileTypes: true });
  } catch {
    return [];
  }
  return entries
    .filter(
      (e) =>
        e.isDirectory() &&
        fs.existsSync(path.join(WORKSPACE, e.name, "evals", "evals.json"))
    )
    .map((e) => e.name)
    .sort();
}

export function isSkill(name: string): boolean {
  return /^[a-z0-9-]+$/.test(name) && listSkillNames().includes(name);
}

function latestIteration(skillDir: string): number {
  let best = 0;
  for (const e of fs.readdirSync(skillDir)) {
    const m = e.match(/^iteration-(\d+)$/);
    if (m) best = Math.max(best, parseInt(m[1], 10));
  }
  return best;
}

/** One-line description pulled from the skill's SKILL.md frontmatter. */
function skillDescription(evalsJson: any): string {
  const p = evalsJson?.skill_path;
  if (typeof p !== "string") return "";
  const text = readText(p);
  if (!text) return "";
  const m = text.match(/^description:\s*(.+)$/m);
  if (!m) return "";
  const firstSentence = m[1].split(/(?<=\.)\s/)[0];
  return firstSentence.length > 180
    ? firstSentence.slice(0, 177) + "..."
    : firstSentence;
}

function loadRun(evalDir: string, config: ConfigName): RunData | null {
  const runDir = path.join(evalDir, config, "run-1");
  const grading = readJson(path.join(runDir, "grading.json"));
  if (!grading) return null;
  const assertions: Assertion[] = (grading.expectations || []).map((e: any) => ({
    text: String(e.text ?? ""),
    passed: Boolean(e.passed),
    evidence: String(e.evidence ?? ""),
  }));
  const timing = readJson(path.join(runDir, "timing.json"));
  const outputs: { name: string; content: string }[] = [];
  const outDir = path.join(runDir, "outputs");
  if (fs.existsSync(outDir)) {
    for (const f of fs.readdirSync(outDir).sort()) {
      const fp = path.join(outDir, f);
      if (fs.statSync(fp).isFile()) {
        outputs.push({ name: f, content: readText(fp) ?? "" });
      }
    }
  }
  return {
    assertions,
    passed:
      grading.summary?.passed ?? assertions.filter((a) => a.passed).length,
    total: grading.summary?.total ?? assertions.length,
    tokens: timing?.total_tokens ?? null,
    seconds: timing?.total_duration_seconds ?? null,
    outputs,
  };
}

export function getSkillData(name: string): SkillData | null {
  if (!isSkill(name)) return null;
  const skillDir = path.join(WORKSPACE, name);
  const evalsJson = readJson(path.join(skillDir, "evals", "evals.json"));
  const iteration = latestIteration(skillDir);
  const iterDir = path.join(skillDir, `iteration-${iteration}`);
  const evals: EvalData[] = [];
  if (iteration > 0) {
    const dirs = fs
      .readdirSync(iterDir)
      .filter((d) => d.startsWith("eval-"))
      .sort();
    for (const d of dirs) {
      const evalDir = path.join(iterDir, d);
      const meta = readJson(path.join(evalDir, "eval_metadata.json")) || {};
      const fromEvalsJson = (evalsJson?.evals || []).find(
        (e: any) => e.id === meta.eval_id
      );
      const configs: Partial<Record<ConfigName, RunData>> = {};
      for (const c of CONFIGS) {
        const run = loadRun(evalDir, c);
        if (run) configs[c] = run;
      }
      evals.push({
        id: meta.eval_id ?? -1,
        evalName: meta.eval_name ?? d,
        dirName: d,
        prompt: meta.prompt ?? fromEvalsJson?.prompt ?? "",
        expectedOutput: fromEvalsJson?.expected_output ?? "",
        files: fromEvalsJson?.files ?? [],
        plantedDefects: meta.planted_defects ?? [],
        configs,
      });
    }
  }
  const benchmark = readJson(path.join(iterDir, "benchmark.json"));
  return {
    name,
    description: skillDescription(evalsJson),
    iteration,
    evals,
    notes: Array.isArray(benchmark?.notes) ? benchmark.notes : [],
  };
}

export interface ConfigTotals {
  passed: number;
  total: number;
  tokens: number;
  seconds: number;
}

export function configTotals(
  skill: SkillData,
  config: ConfigName
): ConfigTotals {
  const t: ConfigTotals = { passed: 0, total: 0, tokens: 0, seconds: 0 };
  for (const e of skill.evals) {
    const run = e.configs[config];
    if (!run) continue;
    t.passed += run.passed;
    t.total += run.total;
    t.tokens += run.tokens ?? 0;
    t.seconds += run.seconds ?? 0;
  }
  return t;
}
