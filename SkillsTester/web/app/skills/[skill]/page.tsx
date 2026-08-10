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
    <>
      <h1 className="page-title">{data.name}</h1>
      <p className="page-sub">
        {data.description} — iteration {data.iteration}, {data.evals.length}{" "}
        evals. Compare the runs per eval, then leave feedback below each one
        and submit.{" "}
        <Link href={`/skills/${data.name}/report`}>View the report →</Link>
      </p>
      <div className="card" style={{ marginBottom: 22 }}>
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
      </div>
      <SkillReview skill={data.name} evals={data.evals} />
    </>
  );
}
