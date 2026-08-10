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

/** A file on disk shown in the UI; `path` is absolute so it can be opened. */
export interface FileData {
  name: string;
  content: string;
  path: string;
}

/** Semantic density and register for one output file (from metrics.json). */
export interface FileMetric {
  name: string;
  commentWords: number;
  /** Facts a reader could not recover from the code; null until graded. */
  semanticUnits: number | null;
  /** semanticUnits / commentWords x 100. */
  density: number | null;
  lintHits: number;
}

/** Run-level roll-up of rubrics/semantic-density.md. */
export interface RunMetrics {
  words: number;
  units: number | null;
  density: number | null;
  /** Register score, 0-5; null until graded. */
  tone: number | null;
  lintHits: number;
  lintHard: number;
  files: Record<string, FileMetric>;
}

export interface RunData {
  /**
   * False between the two phases of a round: the run has produced its outputs
   * but has not been graded yet, so its assertions and metrics are empty and
   * every pass-rate roll-up must exclude it.
   */
  scored: boolean;
  assertions: Assertion[];
  passed: number;
  total: number;
  tokens: number | null;
  seconds: number | null;
  /** Absolute path of the run's outputs/ directory. */
  outputsDir: string;
  outputs: FileData[];
  metrics: RunMetrics | null;
}

export interface EvalData {
  id: number;
  evalName: string;
  dirName: string;
  prompt: string;
  expectedOutput: string;
  files: string[];
  /** The eval's input files (evals/files/...), for comparison against runs. */
  inputs: FileData[];
  plantedDefects: string[];
  configs: Partial<Record<ConfigName, RunData>>;
}

export interface SkillData {
  name: string;
  description: string;
  evals: EvalData[];
  notes: string[];
  /** Runs present in this iteration, and how many have been graded. */
  runs: number;
  scoredRuns: number;
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

/** Where a skill's single set of run results lives. */
export const RESULTS_DIR = "results";

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

function loadMetrics(runDir: string): RunMetrics | null {
  const m = readJson(path.join(runDir, "metrics.json"));
  if (!m) return null;
  const files: Record<string, FileMetric> = {};
  for (const f of m.files || []) {
    files[String(f.name)] = {
      name: String(f.name),
      commentWords: Number(f.comment_words ?? 0),
      semanticUnits: f.semantic_units ?? null,
      density: f.density ?? null,
      lintHits: Number(f.lint?.hits ?? 0),
    };
  }
  return {
    words: Number(m.totals?.comment_words ?? 0),
    units: m.totals?.semantic_units ?? null,
    density: m.totals?.density ?? null,
    tone: m.tone?.score ?? null,
    lintHits: Number(m.tone?.lint_hits ?? 0),
    lintHard: Number(m.tone?.lint_hard_hits ?? 0),
    files,
  };
}

function loadRun(evalDir: string, config: ConfigName): RunData | null {
  const runDir = path.join(evalDir, config);
  const outDir = path.join(runDir, "outputs");
  const grading = readJson(path.join(runDir, "grading.json"));
  const assertions: Assertion[] = (grading?.expectations || []).map((e: any) => ({
    text: String(e.text ?? ""),
    passed: Boolean(e.passed),
    evidence: String(e.evidence ?? ""),
  }));
  const timing = readJson(path.join(runDir, "timing.json"));
  const outputs: FileData[] = [];
  if (fs.existsSync(outDir)) {
    for (const f of fs.readdirSync(outDir).sort()) {
      const fp = path.join(outDir, f);
      if (fs.statSync(fp).isFile()) {
        outputs.push({ name: f, content: readText(fp) ?? "", path: fp });
      }
    }
  }
  // A run with outputs but no grading.json is phase-1 work awaiting review; an
  // empty outputs/ is just the scaffolding for a round that has not run yet.
  if (!grading && outputs.length === 0) return null;
  return {
    scored: Boolean(grading),
    assertions,
    passed:
      grading?.summary?.passed ?? assertions.filter((a) => a.passed).length,
    total: grading?.summary?.total ?? assertions.length,
    tokens: timing?.total_tokens ?? null,
    seconds: timing?.total_duration_seconds ?? null,
    outputsDir: outDir,
    outputs,
    metrics: loadMetrics(runDir),
  };
}

/** Loads an eval's input files; their paths are relative to the skill dir. */
function loadInputs(skillDir: string, files: string[]): FileData[] {
  const out: FileData[] = [];
  for (const rel of files) {
    const fp = path.join(skillDir, rel);
    const content = readText(fp);
    if (content !== null) out.push({ name: path.basename(rel), content, path: fp });
  }
  return out;
}

export function getSkillData(name: string): SkillData | null {
  if (!isSkill(name)) return null;
  const skillDir = path.join(WORKSPACE, name);
  const evalsJson = readJson(path.join(skillDir, "evals", "evals.json"));
  const resultsDir = path.join(skillDir, RESULTS_DIR);
  const evals: EvalData[] = [];
  if (fs.existsSync(resultsDir)) {
    const dirs = fs
      .readdirSync(resultsDir)
      .filter((d) => d.startsWith("eval-"))
      .sort();
    for (const d of dirs) {
      const evalDir = path.join(resultsDir, d);
      const meta = readJson(path.join(evalDir, "eval_metadata.json")) || {};
      const fromEvalsJson = (evalsJson?.evals || []).find(
        (e: any) => e.id === meta.eval_id
      );
      const configs: Partial<Record<ConfigName, RunData>> = {};
      for (const c of CONFIGS) {
        const run = loadRun(evalDir, c);
        if (run) configs[c] = run;
      }
      const files: string[] = fromEvalsJson?.files ?? [];
      evals.push({
        id: meta.eval_id ?? -1,
        evalName: meta.eval_name ?? d,
        dirName: d,
        prompt: meta.prompt ?? fromEvalsJson?.prompt ?? "",
        expectedOutput: fromEvalsJson?.expected_output ?? "",
        files,
        inputs: loadInputs(skillDir, files),
        plantedDefects: meta.planted_defects ?? [],
        configs,
      });
    }
  }
  const benchmark = readJson(path.join(resultsDir, "benchmark.json"));
  let runs = 0;
  let scoredRuns = 0;
  for (const e of evals) {
    for (const c of CONFIGS) {
      const r = e.configs[c];
      if (!r) continue;
      runs++;
      if (r.scored) scoredRuns++;
    }
  }
  return {
    name,
    description: skillDescription(evalsJson),
    evals,
    notes: Array.isArray(benchmark?.notes) ? benchmark.notes : [],
    runs,
    scoredRuns,
  };
}

export interface ConfigTotals {
  passed: number;
  total: number;
  tokens: number;
  seconds: number;
}

export interface MetricTotals {
  words: number;
  units: number | null;
  /** Pooled density: total units over total words, not a mean of means. */
  density: number | null;
  /** Mean register score over the graded runs. */
  tone: number | null;
  lintHard: number;
  /** Runs that have a judged unit count, out of the runs present. */
  graded: number;
  runs: number;
}

export function metricTotals(
  skill: SkillData,
  config: ConfigName
): MetricTotals {
  let words = 0;
  let units = 0;
  let graded = 0;
  let runs = 0;
  let lintHard = 0;
  let toneSum = 0;
  let toneN = 0;
  for (const e of skill.evals) {
    const m = e.configs[config]?.metrics;
    if (!m) continue;
    runs++;
    lintHard += m.lintHard;
    if (m.tone !== null) {
      toneSum += m.tone;
      toneN++;
    }
    if (m.units === null) continue;
    graded++;
    words += m.words;
    units += m.units;
  }
  return {
    words,
    units: graded > 0 ? units : null,
    density: graded > 0 && words > 0 ? Math.round((units / words) * 1000) / 10 : null,
    tone: toneN > 0 ? Math.round((toneSum / toneN) * 10) / 10 : null,
    lintHard,
    graded,
    runs,
  };
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
