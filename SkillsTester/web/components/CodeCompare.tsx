"use client";

import { useMemo, useRef, useState } from "react";
import {
  CONFIGS,
  CONFIG_LABELS,
  CONFIG_SHORT,
  CONFIG_COLORS,
  type ConfigName,
} from "@/lib/configs";
import type { EvalData, FileData } from "@/lib/data";
import { analyze, statsOf, langOf, type CodeLine } from "@/lib/comments";
import { FileActions, DiffButton } from "./OpenLocal";

// Side-by-side viewer for one eval: the same file as written by each
// configuration, in wrapped columns with the comments tinted, so the tiers can
// be compared by eye. "Comments only" strips the code away entirely, which is
// the fastest way to see how CC1 and CC2 differ.

interface Column {
  key: string;
  label: string;
  short: string;
  color: string;
  /** File contents by base name. */
  files: Record<string, FileData>;
}

const ORIGINAL = "__original__";

function buildColumns(ev: EvalData): Column[] {
  const cols: Column[] = [];
  if (ev.inputs.length > 0) {
    cols.push({
      key: ORIGINAL,
      label: "Original (eval input)",
      short: "Original",
      color: "var(--baseline)",
      files: Object.fromEntries(ev.inputs.map((f) => [f.name, f])),
    });
  }
  for (const c of CONFIGS) {
    const run = ev.configs[c];
    if (!run) continue;
    cols.push({
      key: c,
      label: CONFIG_LABELS[c],
      short: CONFIG_SHORT[c],
      color: CONFIG_COLORS[c],
      files: Object.fromEntries(run.outputs.map((f) => [f.name, f])),
    });
  }
  return cols;
}

/** Output file names first (those are what the agent wrote), then inputs. */
function fileTabs(cols: Column[]): string[] {
  const produced = new Set<string>();
  const inputOnly = new Set<string>();
  for (const c of cols) {
    for (const name of Object.keys(c.files)) {
      if (c.key === ORIGINAL) inputOnly.add(name);
      else produced.add(name);
    }
  }
  const rest = [...inputOnly].filter((n) => !produced.has(n)).sort();
  return [...[...produced].sort(), ...rest];
}

/** Total words — the only useful volume measure for prose files (reports). */
function wordCount(content: string): number {
  const t = content.trim();
  return t === "" ? 0 : t.split(/\s+/).length;
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <span className="cc-stat">
      <b className="tnum">{value}</b> {label}
    </span>
  );
}

function CodeBody({
  lines,
  commentsOnly,
}: {
  lines: CodeLine[];
  commentsOnly: boolean;
}) {
  const rows: React.ReactNode[] = [];
  let skipped = 0;
  const flush = (key: string) => {
    if (skipped === 0) return;
    rows.push(
      <div key={`gap-${key}`} className="code-gap">
        ⋯ {skipped} line{skipped === 1 ? "" : "s"} of code
      </div>
    );
    skipped = 0;
  };
  for (const l of lines) {
    if (commentsOnly && !l.hasComment) {
      // Blank lines inside a hidden run should not inflate the count.
      if (l.segs.some((s) => s.t.trim() !== "")) skipped++;
      continue;
    }
    flush(String(l.n));
    rows.push(
      <div key={l.n} className={`code-line${l.hasComment ? " has-cmt" : ""}`}>
        <span className="ln tnum">{l.n}</span>
        <span className="lt">
          {l.segs.length === 0 ? (
            " "
          ) : (
            l.segs.map((s, i) => (
              <span key={i} className={s.c ? "seg-cmt" : undefined}>
                {s.t}
              </span>
            ))
          )}
        </span>
      </div>
    );
  }
  flush("end");
  return <>{rows}</>;
}

export default function CodeCompare({ ev }: { ev: EvalData }) {
  const columns = useMemo(() => buildColumns(ev), [ev]);
  const tabs = useMemo(() => fileTabs(columns), [columns]);
  const [file, setFile] = useState(tabs[0] ?? "");
  const [hidden, setHidden] = useState<Set<string>>(new Set([ORIGINAL]));
  const [commentsOnly, setCommentsOnly] = useState(false);
  const [wrap, setWrap] = useState(true);
  const [sync, setSync] = useState(true);
  const panes = useRef<(HTMLDivElement | null)[]>([]);
  const scrolling = useRef(false);

  if (tabs.length === 0) {
    return <p className="muted">No output files recorded for this eval.</p>;
  }

  const visible = columns.filter((c) => !hidden.has(c.key));
  const lang = langOf(file);
  const canFilter = lang !== "text";

  function selectFile(name: string) {
    setFile(name);
    // A tab that only the Original column has would otherwise show nothing.
    const shown = columns.filter((c) => !hidden.has(c.key));
    if (!shown.some((c) => c.files[name])) {
      const next = new Set(hidden);
      for (const c of columns) if (c.files[name]) next.delete(c.key);
      setHidden(next);
    }
  }

  function toggleColumn(key: string) {
    const next = new Set(hidden);
    if (next.has(key)) next.delete(key);
    else if (visible.length > 1) next.add(key);
    setHidden(next);
  }

  function onScroll(i: number) {
    if (!sync || scrolling.current) return;
    const src = panes.current[i];
    if (!src) return;
    const range = src.scrollHeight - src.clientHeight;
    const ratio = range > 0 ? src.scrollTop / range : 0;
    scrolling.current = true;
    panes.current.forEach((p, j) => {
      if (!p || j === i) return;
      p.scrollTop = ratio * (p.scrollHeight - p.clientHeight);
    });
    requestAnimationFrame(() => (scrolling.current = false));
  }

  // Local-diff shortcuts for every pair of visible columns holding this file.
  const withFile = visible.filter((c) => c.files[file]);
  const pairs: [Column, Column][] = [];
  for (let i = 0; i < withFile.length; i++) {
    for (let j = i + 1; j < withFile.length; j++) {
      pairs.push([withFile[i], withFile[j]]);
    }
  }

  return (
    <div className="cc">
      <div className="cc-bar">
        <div className="cc-tabs">
          {tabs.map((t) => (
            <button
              key={t}
              className={`cc-tab mono${t === file ? " active" : ""}`}
              onClick={() => selectFile(t)}
            >
              {t}
            </button>
          ))}
        </div>
        <div className="cc-toggles">
          <label
            className={canFilter ? "" : "disabled"}
            title="Hide every line that carries no comment"
          >
            <input
              type="checkbox"
              checked={commentsOnly && canFilter}
              disabled={!canFilter}
              onChange={(e) => setCommentsOnly(e.target.checked)}
            />
            Comments only
          </label>
          <label title="Wrap long lines instead of scrolling sideways">
            <input
              type="checkbox"
              checked={wrap}
              onChange={(e) => setWrap(e.target.checked)}
            />
            Wrap
          </label>
          <label title="Scroll every column together">
            <input
              type="checkbox"
              checked={sync}
              onChange={(e) => setSync(e.target.checked)}
            />
            Sync scroll
          </label>
        </div>
      </div>

      <div className="cc-bar cc-bar-2">
        <div className="cc-chips">
          {columns.map((c) => (
            <button
              key={c.key}
              className={`cc-chip${hidden.has(c.key) ? " off" : ""}`}
              onClick={() => toggleColumn(c.key)}
              title={
                hidden.has(c.key) ? `Show ${c.label}` : `Hide ${c.label}`
              }
            >
              <span className="config-dot" style={{ background: c.color }} />
              {c.short}
            </button>
          ))}
        </div>
        {pairs.length > 0 && (
          <div className="cc-diffs">
            <span className="muted">Open a local diff:</span>
            {pairs.map(([a, b]) => (
              <DiffButton
                key={`${a.key}-${b.key}`}
                a={a.files[file].path}
                b={b.files[file].path}
                label={`${a.short} ↔ ${b.short}`}
              />
            ))}
          </div>
        )}
      </div>

      <div
        className={`cc-grid${wrap ? "" : " nowrap"}`}
        style={{
          gridTemplateColumns: `repeat(${visible.length}, minmax(0, 1fr))`,
        }}
      >
        {visible.map((c, i) => {
          const f = c.files[file];
          const lines = f ? analyze(f.content, lang) : [];
          const s = statsOf(lines);
          return (
            <div key={c.key} className="cc-col">
              <div className="cc-head">
                <span
                  className="config-dot"
                  style={{ background: c.color }}
                />
                <span className="cc-title">{c.label}</span>
                {f && <FileActions path={f.path} label="Open" compact />}
              </div>
              {f ? (
                <>
                  <div className="cc-stats">
                    <Stat value={String(s.lines)} label="lines" />
                    {canFilter ? (
                      <>
                        <Stat
                          value={String(s.commentLines)}
                          label="comment lines"
                        />
                        <Stat value={`${s.density}%`} label="density" />
                        <Stat value={String(s.words)} label="comment words" />
                      </>
                    ) : (
                      <Stat value={String(wordCount(f.content))} label="words" />
                    )}
                  </div>
                  <div
                    className="code-pane"
                    ref={(el) => {
                      panes.current[i] = el;
                    }}
                    onScroll={() => onScroll(i)}
                  >
                    <CodeBody
                      lines={lines}
                      commentsOnly={commentsOnly && canFilter}
                    />
                  </div>
                  <div className="cc-foot">
                    <FileActions path={f.path} label="Open file" />
                  </div>
                </>
              ) : (
                <p className="muted cc-empty">
                  This run produced no <span className="mono">{file}</span>.
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
