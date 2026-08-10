"use client";

import { useState } from "react";
import {
  CONFIGS,
  CONFIG_LABELS,
  CONFIG_COLORS,
  type ConfigName,
} from "@/lib/configs";
import type { EvalData } from "@/lib/data";
import CodeCompare from "./CodeCompare";
import { FileActions } from "./OpenLocal";

/** Compact per-config summary: pass count and cost, above the code columns. */
function ConfigTile({
  config,
  run,
}: {
  config: ConfigName;
  run: NonNullable<EvalData["configs"][ConfigName]>;
}) {
  const allPass = run.passed === run.total;
  return (
    <div className="config-tile">
      <span className="config-dot" style={{ background: CONFIG_COLORS[config] }} />
      <span className="config-name">{CONFIG_LABELS[config]}</span>
      <span className={`badge ${allPass ? "pass" : "fail"}`}>
        {allPass ? "✓" : "✕"} {run.passed}/{run.total}
      </span>
      {run.tokens !== null && (
        <span className="muted tnum config-cost">
          {Math.round(run.tokens / 1000)}k tok · {Math.round(run.seconds ?? 0)}s
        </span>
      )}
    </div>
  );
}

function AssertionColumn({
  config,
  run,
}: {
  config: ConfigName;
  run: NonNullable<EvalData["configs"][ConfigName]>;
}) {
  return (
    <div className="config-col">
      <h4>
        <span
          className="config-dot"
          style={{ background: CONFIG_COLORS[config] }}
        />
        {CONFIG_LABELS[config]}
        <span className="muted" style={{ marginLeft: "auto", fontSize: 12 }}>
          {run.passed}/{run.total}
        </span>
      </h4>
      {run.assertions.map((a, i) => (
        <div key={i} className="assertion">
          <span className={`mark ${a.passed ? "ok" : "bad"}`}>
            {a.passed ? "✓" : "✕"}
          </span>
          <div>
            <div>{a.text}</div>
            <div className="evidence">{a.evidence}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function SkillReview({
  skill,
  evals,
}: {
  skill: string;
  evals: EvalData[];
}) {
  const [feedback, setFeedback] = useState<Record<string, string>>({});
  const [status, setStatus] = useState<string>("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true);
    setStatus("");
    try {
      const reviews = evals.map((e) => ({
        run_id: e.dirName,
        feedback: feedback[e.dirName] ?? "",
      }));
      const res = await fetch(`/api/feedback/${skill}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reviews }),
      });
      if (!res.ok) throw new Error(await res.text());
      const n = reviews.filter((r) => r.feedback.trim() !== "").length;
      setStatus(
        `Saved. ${n} eval${n === 1 ? "" : "s"} with comments, ` +
          `${reviews.length - n} approved as-is.`
      );
    } catch (err) {
      setStatus(`Failed to save: ${String(err)}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {evals.map((e) => {
        const present = CONFIGS.filter((c) => e.configs[c]);
        return (
          <section key={e.dirName} className="card eval-card">
            <div className="eval-head">
              <h3>{e.evalName}</h3>
              <span className="eval-id mono">eval {e.id}</span>
              {e.plantedDefects.length > 0 && (
                <span className="badge neutral">
                  {e.plantedDefects.length} planted defects
                </span>
              )}
              {e.inputs.length > 0 && (
                <span className="input-links">
                  <span className="muted">inputs:</span>
                  {e.inputs.map((f) => (
                    <span key={f.path} className="input-link">
                      <span className="mono">{f.name}</span>
                      <FileActions path={f.path} label="open" compact />
                    </span>
                  ))}
                </span>
              )}
            </div>
            <div className="prompt-block">
              <strong style={{ color: "var(--ink)" }}>Prompt.</strong> {e.prompt}
            </div>
            <div className="config-strip">
              {present.map((c) => (
                <ConfigTile key={c} config={c} run={e.configs[c]!} />
              ))}
            </div>
            <CodeCompare ev={e} />
            <details>
              <summary>
                Assertions per configuration (
                {present
                  .map((c) => {
                    const r = e.configs[c]!;
                    return `${r.passed}/${r.total}`;
                  })
                  .join(" · ")}
                )
              </summary>
              <div className="config-grid">
                {present.map((c) => (
                  <AssertionColumn key={c} config={c} run={e.configs[c]!} />
                ))}
              </div>
            </details>
            {e.plantedDefects.length > 0 && (
              <details>
                <summary>Planted defects ({e.plantedDefects.length})</summary>
                <ol style={{ fontSize: 13.5, color: "var(--ink-2)" }}>
                  {e.plantedDefects.map((d, i) => (
                    <li key={i} style={{ marginBottom: 4 }}>
                      {d}
                    </li>
                  ))}
                </ol>
              </details>
            )}
            <div className="feedback" style={{ marginTop: 12 }}>
              <textarea
                placeholder="Feedback for this eval — leave empty if it looks good."
                value={feedback[e.dirName] ?? ""}
                onChange={(ev) =>
                  setFeedback({ ...feedback, [e.dirName]: ev.target.value })
                }
              />
            </div>
          </section>
        );
      })}
      <div className="submit-bar">
        <button onClick={submit} disabled={busy}>
          {busy ? "Saving..." : "Submit all feedback"}
        </button>
        <span className="submit-status">{status}</span>
      </div>
    </>
  );
}
