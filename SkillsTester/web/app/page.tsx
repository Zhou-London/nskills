import Link from "next/link";
import {
  listSkillNames,
  getSkillData,
  configTotals,
  skillConfigs,
  CONFIG_LABELS,
  CONFIG_COLORS,
} from "@/lib/data";
import { PassMeter } from "@/components/PassMeter";

export const dynamic = "force-dynamic";

export default function Home() {
  const skills = listSkillNames()
    .map((n) => getSkillData(n))
    .filter((s) => s !== null);

  return (
    <div className="shell">
      <h1 className="page-title">SkillsTester</h1>
      <p className="page-sub">
        Repeatable acceptance testing for Claude skills. Every skill runs the
        same three-part gauntlet — add documentation, audit planted defects,
        generate from scratch — under each configuration: the skill at its CC1
        (concise) and CC2 (full detail) comment-complexity tiers, and a
        no-skill baseline. Pick a skill to review its runs or read its report.
      </p>
      <div className="skill-grid">
        {skills.map((s) => {
          const configs = skillConfigs(s);
          const first = configs.length > 0 ? configTotals(s, configs[0]) : null;
          return (
            <div key={s.name} className="card skill-card">
              <h2>{s.name}</h2>
              <p className="desc">
                {s.description || "No description found in SKILL.md."}
              </p>
              <div className="muted" style={{ fontSize: 12.5 }}>
                iteration {s.iteration} · {s.evals.length} evals ·{" "}
                {first?.total ?? 0} assertions
              </div>
              <div className="meter-block">
                {configs.map((c) => {
                  const t = configTotals(s, c);
                  return (
                    <PassMeter
                      key={c}
                      label={CONFIG_LABELS[c]}
                      passed={t.passed}
                      total={t.total}
                      color={CONFIG_COLORS[c]}
                    />
                  );
                })}
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
    </div>
  );
}
