"use client";

import { useState } from "react";
import type { EvalData, ConfigName } from "@/lib/data";

const CONFIG_LABELS: Record<ConfigName, string> = {
  with_skill: "With skill",
  without_skill: "Baseline (no skill)",
};
const CONFIG_COLORS: Record<ConfigName, string> = {
  with_skill: "var(--series-1)",
  without_skill: "var(--series-2)",
};

function ConfigColumn({
  config,
  run,
}: {
  config: ConfigName;
  run: EvalData["configs"][ConfigName];
}) {
  if (!run) {
    return (
      <div className="config-col">
        <h4>
          <span
            className="config-dot"
            style={{ background: CONFIG_COLORS[config] }}
          />
          {CONFIG_LABELS[config]}
        </h4>
        <p className="muted">No run recorded.</p>
      </div>
    );
  }
  const allPass = run.passed === run.total;
  return (
    <div className="config-col">
      <h4>
        <span
          className="config-dot"
          style={{ background: CONFIG_COLORS[config] }}
        />
        {CONFIG_LABELS[config]}
        <span className={`badge ${allPass ? "pass" : "fail"}`}>
          {allPass ? "✓" : "✕"} {run.passed}/{run.total}
        </span>
        {run.tokens !== null && (
          <span className="muted tnum" style={{ fontSize: 12, marginLeft: "auto" }}>
            {Math.round(run.tokens / 1000)}k tok · {Math.round(run.seconds ?? 0)}s
          </span>
        )}
      </h4>
      <details>
        <summary>Assertions ({run.assertions.length})</summary>
        <div>
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
      </details>
      <details>
        <summary>
          Outputs ({run.outputs.map((o) => o.name).join(", ") || "none"})
        </summary>
        <div>
          {run.outputs.map((o) => (
            <div key={o.name}>
              <div className="file-name mono">{o.name}</div>
              <pre className="output">{o.content}</pre>
            </div>
          ))}
        </div>
      </details>
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
      {evals.map((e) => (
        <section key={e.dirName} className="card eval-card">
          <div className="eval-head">
            <h3>{e.evalName}</h3>
            <span className="eval-id mono">eval {e.id}</span>
            {e.plantedDefects.length > 0 && (
              <span className="badge neutral">
                {e.plantedDefects.length} planted defects
              </span>
            )}
          </div>
          <div className="prompt-block">
            <strong style={{ color: "var(--ink)" }}>Prompt.</strong> {e.prompt}
          </div>
          <div className="config-grid">
            <ConfigColumn config="with_skill" run={e.configs.with_skill} />
            <ConfigColumn config="without_skill" run={e.configs.without_skill} />
          </div>
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
      ))}
      <div className="submit-bar">
        <button onClick={submit} disabled={busy}>
          {busy ? "Saving..." : "Submit all feedback"}
        </button>
        <span className="submit-status">{status}</span>
      </div>
    </>
  );
}
