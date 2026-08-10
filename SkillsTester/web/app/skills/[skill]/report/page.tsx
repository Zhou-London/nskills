import Link from "next/link";
import { notFound } from "next/navigation";
import { getSkillData, configTotals, pct } from "@/lib/data";
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

  const w = configTotals(data, "with_skill");
  const wo = configTotals(data, "without_skill");
  const wPct = pct(w.passed, w.total);
  const woPct = pct(wo.passed, wo.total);
  const delta = Math.round((wPct - woPct) * 10) / 10;
  const extraTokens =
    data.evals.length > 0
      ? Math.round((w.tokens - wo.tokens) / data.evals.length / 100) / 10
      : 0;

  return (
    <>
      <h1 className="page-title">{data.name} — report</h1>
      <p className="page-sub">
        Iteration {data.iteration} · {data.evals.length} evals ·{" "}
        {w.total} assertions per configuration.{" "}
        <Link href={`/skills/${data.name}`}>← Back to eval review</Link>
      </p>

      <div className="kpi-row">
        <div className="kpi">
          <div className="label">With skill</div>
          <div className="value" style={{ color: "var(--series-1)" }}>
            {wPct}%
          </div>
          <div className="sub tnum">
            {w.passed}/{w.total} assertions
          </div>
        </div>
        <div className="kpi">
          <div className="label">Baseline (no skill)</div>
          <div className="value" style={{ color: "var(--series-2)" }}>
            {woPct}%
          </div>
          <div className="sub tnum">
            {wo.passed}/{wo.total} assertions
          </div>
        </div>
        <div className="kpi">
          <div className="label">Skill lift</div>
          <div className="value">
            {delta >= 0 ? "+" : ""}
            {delta} pp
          </div>
          <div className="sub">pass-rate delta</div>
        </div>
        <div className="kpi">
          <div className="label">Skill overhead</div>
          <div className="value tnum">{extraTokens}k</div>
          <div className="sub">extra tokens per eval (avg)</div>
        </div>
      </div>

      <h2 className="section-title">Pass rate by eval</h2>
      <div className="card">
        <ConfigLegend />
        <div style={{ display: "grid", gap: 18 }}>
          {data.evals.map((e) => {
            const rw = e.configs.with_skill;
            const rwo = e.configs.without_skill;
            return (
              <div key={e.dirName}>
                <div style={{ fontSize: 13.5, marginBottom: 6 }}>
                  <strong>{e.evalName}</strong>{" "}
                  <span className="muted mono">eval {e.id}</span>
                </div>
                <div className="meter-block">
                  {rw && (
                    <PassMeter
                      label="With skill"
                      passed={rw.passed}
                      total={rw.total}
                      color="var(--series-1)"
                    />
                  )}
                  {rwo && (
                    <PassMeter
                      label="Baseline"
                      passed={rwo.passed}
                      total={rwo.total}
                      color="var(--series-2)"
                    />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <h2 className="section-title">Cost</h2>
      <div className="card">
        <table className="data">
          <thead>
            <tr>
              <th>Eval</th>
              <th className="num">With skill (tokens)</th>
              <th className="num">Baseline (tokens)</th>
              <th className="num">With skill (s)</th>
              <th className="num">Baseline (s)</th>
            </tr>
          </thead>
          <tbody>
            {data.evals.map((e) => (
              <tr key={e.dirName}>
                <td>{e.evalName}</td>
                <td className="num">
                  {e.configs.with_skill?.tokens?.toLocaleString() ?? "—"}
                </td>
                <td className="num">
                  {e.configs.without_skill?.tokens?.toLocaleString() ?? "—"}
                </td>
                <td className="num">
                  {e.configs.with_skill?.seconds ?? "—"}
                </td>
                <td className="num">
                  {e.configs.without_skill?.seconds ?? "—"}
                </td>
              </tr>
            ))}
            <tr>
              <td>
                <strong>Total</strong>
              </td>
              <td className="num">
                <strong>{w.tokens.toLocaleString()}</strong>
              </td>
              <td className="num">
                <strong>{wo.tokens.toLocaleString()}</strong>
              </td>
              <td className="num">
                <strong>{Math.round(w.seconds)}</strong>
              </td>
              <td className="num">
                <strong>{Math.round(wo.seconds)}</strong>
              </td>
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
    </>
  );
}
