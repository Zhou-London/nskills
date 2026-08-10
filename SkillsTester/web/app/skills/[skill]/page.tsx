import Link from "next/link";
import { notFound } from "next/navigation";
import {
  getSkillData,
  configTotals,
  skillConfigs,
  CONFIG_LABELS,
  CONFIG_COLORS,
} from "@/lib/data";
import { PassMeter, ConfigLegend } from "@/components/PassMeter";
import SkillReview from "@/components/SkillReview";

export const dynamic = "force-dynamic";

export default async function SkillPage({
  params,
}: {
  params: Promise<{ skill: string }>;
}) {
  const { skill } = await params;
  const data = getSkillData(skill);
  if (!data) notFound();

  const configs = skillConfigs(data);

  return (
    <div className="shell wide">
      <h1 className="page-title">{data.name}</h1>
      <p className="page-sub">
        {data.description} — {data.evals.length}{" "}
        evals. Each eval shows the same file as written by each configuration,
        side by side with its comments tinted; switch on{" "}
        <em>Comments only</em> to compare the documentation alone, or open the
        files on this machine to diff them yourself.{" "}
        <Link href={`/skills/${data.name}/report`}>View the report →</Link>
      </p>
      <div className="card" style={{ marginBottom: 22 }}>
        {data.scoredRuns === 0 ? (
          <p style={{ margin: 0, fontSize: 13.5 }}>
            <strong>Phase 1 complete — {data.runs} runs produced, none scored.</strong>{" "}
            <span className="muted">
              Compare the outputs below. When they look right, confirm and the
              grading pass will fill in assertions, semantic density and
              register.
            </span>
          </p>
        ) : (
          <>
            <ConfigLegend configs={configs} />
            <div className="meter-block">
              {configs.map((c) => {
                const t = configTotals(data, c);
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
            {data.scoredRuns < data.runs && (
              <p className="muted" style={{ fontSize: 12.5, marginBottom: 0 }}>
                {data.runs - data.scoredRuns} of {data.runs} runs are still
                unscored; the meters cover the graded ones only.
              </p>
            )}
          </>
        )}
      </div>
      <SkillReview skill={data.name} evals={data.evals} />
    </div>
  );
}
