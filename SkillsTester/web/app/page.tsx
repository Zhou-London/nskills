import Link from "next/link";
import { listSkillNames, getSkillData, configTotals } from "@/lib/data";
import { PassMeter, ConfigLegend } from "@/components/PassMeter";

export const dynamic = "force-dynamic";

export default function Home() {
  const skills = listSkillNames()
    .map((n) => getSkillData(n))
    .filter((s) => s !== null);

  return (
    <>
      <h1 className="page-title">SkillsTester</h1>
      <p className="page-sub">
        Repeatable acceptance testing for Claude skills. Every skill runs the
        same three-part gauntlet — add documentation, audit planted defects,
        generate from scratch — once with the skill loaded and once without.
        Pick a skill to review its runs or read its report.
      </p>
      <div className="skill-grid">
        {skills.map((s) => {
          const w = configTotals(s, "with_skill");
          const wo = configTotals(s, "without_skill");
          return (
            <div key={s.name} className="card skill-card">
              <h2>{s.name}</h2>
              <p className="desc">
                {s.description || "No description found in SKILL.md."}
              </p>
              <div className="muted" style={{ fontSize: 12.5 }}>
                iteration {s.iteration} · {s.evals.length} evals ·{" "}
                {w.total} assertions
              </div>
              <div className="meter-block">
                <PassMeter
                  label="With skill"
                  passed={w.passed}
                  total={w.total}
                  color="var(--series-1)"
                />
                <PassMeter
                  label="Baseline"
                  passed={wo.passed}
                  total={wo.total}
                  color="var(--series-2)"
                />
              </div>
              <div className="card-actions">
                <Link href={`/skills/${s.name}`} className="btn primary">
                  Review evals
                </Link>
                <Link href={`/skills/${s.name}/report`} className="btn">
                  Report
                </Link>
              </div>
            </div>
          );
        })}
      </div>
      {skills.length === 0 && (
        <p className="muted">
          No skills found. A skill is any workspace subdirectory containing
          evals/evals.json.
        </p>
      )}
    </>
  );
}
