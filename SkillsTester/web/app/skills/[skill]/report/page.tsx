import Link from "next/link";
import { notFound } from "next/navigation";
import {
  getSkillData,
  configTotals,
  metricTotals,
  skillConfigs,
  pct,
  CONFIG_LABELS,
  CONFIG_COLORS,
  type ConfigName,
} from "@/lib/data";
import { PassMeter, ConfigLegend } from "@/components/PassMeter";

export const dynamic = "force-dynamic";

export default async function ReportPage({
  params,
}: {
  params: Promise<{ skill: string }>;
}) {
  const { skill } = await params;
  const data = getSkillData(skill);
  if (!data) notFound();

  const configs = skillConfigs(data);
  const skillConfigsOnly = configs.filter((c) => c !== "without_skill");
  const totals = Object.fromEntries(
    configs.map((c) => [c, configTotals(data, c)])
  ) as Record<ConfigName, ReturnType<typeof configTotals>>;
  const baseline = totals.without_skill;
  const baselinePct = baseline ? pct(baseline.passed, baseline.total) : null;
  const metrics = Object.fromEntries(
    configs.map((c) => [c, metricTotals(data, c)])
  ) as Record<ConfigName, ReturnType<typeof metricTotals>>;
  const anyMetrics = configs.some((c) => metrics[c].runs > 0);

  return (
    <div className="shell">
      <h1 className="page-title">{data.name} — report</h1>
      <p className="page-sub">
        {data.evals.length} evals ·{" "}
        {configs.map((c) => `${totals[c].total} assertions (${CONFIG_LABELS[c]})`).join(" · ")}.{" "}
        <Link href={`/skills/${data.name}`}>← Back to eval review</Link>
      </p>

      {data.scoredRuns === 0 && (
        <div className="card" style={{ marginBottom: 22 }}>
          <p style={{ margin: 0, fontSize: 13.5 }}>
            <strong>Nothing scored yet.</strong>{" "}
            <span className="muted">
              {data.runs} runs have been produced but not graded, so every
              number below is empty. Review the outputs on the eval page and
              confirm to start the grading pass.
            </span>
          </p>
        </div>
      )}

      <div className="kpi-row">
        {configs.map((c) => (
          <div key={c} className="kpi">
            <div className="label">{CONFIG_LABELS[c]}</div>
            <div className="value" style={{ color: CONFIG_COLORS[c] }}>
              {pct(totals[c].passed, totals[c].total)}%
            </div>
            <div className="sub tnum">
              {totals[c].passed}/{totals[c].total} assertions
            </div>
          </div>
        ))}
        {baselinePct !== null &&
          skillConfigsOnly.map((c) => {
            const delta =
              Math.round(
                (pct(totals[c].passed, totals[c].total) - baselinePct) * 10
              ) / 10;
            const extraTokens =
              data.evals.length > 0
                ? Math.round(
                    ((totals[c].tokens - baseline.tokens) / data.evals.length) /
                      100
                  ) / 10
                : 0;
            return (
              <div key={`lift-${c}`} className="kpi">
                <div className="label">Lift · {CONFIG_LABELS[c]}</div>
                <div className="value">
                  {delta >= 0 ? "+" : ""}
                  {delta} pp
                </div>
                <div className="sub tnum">
                  {extraTokens >= 0 ? "+" : ""}
                  {extraTokens}k tokens per eval vs baseline
                </div>
              </div>
            );
          })}
      </div>

      {anyMetrics && (
        <>
          <h2 className="section-title">Semantic density and register</h2>
          <p className="page-sub">
            SD is facts carried per 100 words of comment prose; T is the
            register score out of 5. The skill should beat the baseline on
            both — <strong>more facts, fewer words</strong> — see{" "}
            <span className="mono">rubrics/semantic-density.md</span>.
          </p>
          <div className="kpi-row">
            {configs.map((c) => (
              <div key={`m-${c}`} className="kpi">
                <div className="label">{CONFIG_LABELS[c]}</div>
                <div className="value" style={{ color: CONFIG_COLORS[c] }}>
                  {metrics[c].density?.toFixed(1) ?? "—"}
                  <span style={{ fontSize: 14, fontWeight: 500 }}> SD</span>
                </div>
                <div className="sub tnum">
                  {metrics[c].units ?? "—"} facts / {metrics[c].words} words ·
                  T {metrics[c].tone ?? "—"}/5
                </div>
              </div>
            ))}
          </div>
          <div className="card">
            <table className="data">
              <thead>
                <tr>
                  <th>Eval</th>
                  {configs.map((c) => (
                    <th key={`sd-${c}`} className="num">
                      {CONFIG_LABELS[c]} (SD · facts · T)
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.evals.map((e) => (
                  <tr key={e.dirName}>
                    <td>{e.evalName}</td>
                    {configs.map((c) => {
                      const m = e.configs[c]?.metrics;
                      return (
                        <td key={`sd-${c}`} className="num">
                          {m
                            ? `${m.density?.toFixed(1) ?? "—"} · ${
                                m.units ?? "—"
                              } · ${m.tone ?? "—"}/5`
                            : "—"}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      <h2 className="section-title">Pass rate by eval</h2>
      <div className="card">
        <ConfigLegend configs={configs} />
        <div style={{ display: "grid", gap: 18 }}>
          {data.evals.map((e) => (
            <div key={e.dirName}>
              <div style={{ fontSize: 13.5, marginBottom: 6 }}>
                <strong>{e.evalName}</strong>{" "}
                <span className="muted mono">eval {e.id}</span>
              </div>
              <div className="meter-block">
                {configs.map((c) => {
                  const run = e.configs[c];
                  if (!run) return null;
                  return (
                    <PassMeter
                      key={c}
                      label={CONFIG_LABELS[c]}
                      passed={run.passed}
                      total={run.total}
                      color={CONFIG_COLORS[c]}
                    />
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      <h2 className="section-title">Cost</h2>
      <div className="card">
        <table className="data">
          <thead>
            <tr>
              <th>Eval</th>
              {configs.map((c) => (
                <th key={`t-${c}`} className="num">
                  {CONFIG_LABELS[c]} (tokens)
                </th>
              ))}
              {configs.map((c) => (
                <th key={`s-${c}`} className="num">
                  {CONFIG_LABELS[c]} (s)
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.evals.map((e) => (
              <tr key={e.dirName}>
                <td>{e.evalName}</td>
                {configs.map((c) => (
                  <td key={`t-${c}`} className="num">
                    {e.configs[c]?.tokens?.toLocaleString() ?? "—"}
                  </td>
                ))}
                {configs.map((c) => (
                  <td key={`s-${c}`} className="num">
                    {e.configs[c]?.seconds ?? "—"}
                  </td>
                ))}
              </tr>
            ))}
            <tr>
              <td>
                <strong>Total</strong>
              </td>
              {configs.map((c) => (
                <td key={`t-${c}`} className="num">
                  <strong>{totals[c].tokens.toLocaleString()}</strong>
                </td>
              ))}
              {configs.map((c) => (
                <td key={`s-${c}`} className="num">
                  <strong>{Math.round(totals[c].seconds)}</strong>
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      {data.notes.length > 0 && (
        <>
          <h2 className="section-title">Analyst notes</h2>
          <div className="card">
            <ul className="notes">
              {data.notes.map((n, i) => (
                <li key={i}>{n}</li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  );
}
