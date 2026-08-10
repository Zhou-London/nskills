import Link from "next/link";
import { notFound } from "next/navigation";
import { getSkillData, configTotals } from "@/lib/data";
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

  const w = configTotals(data, "with_skill");
  const wo = configTotals(data, "without_skill");

  return (
    <>
      <h1 className="page-title">{data.name}</h1>
      <p className="page-sub">
        {data.description} — iteration {data.iteration}, {data.evals.length}{" "}
        evals. Compare both runs per eval, then leave feedback below each one
        and submit.{" "}
        <Link href={`/skills/${data.name}/report`}>View the report →</Link>
      </p>
      <div className="card" style={{ marginBottom: 22 }}>
        <ConfigLegend />
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
      </div>
      <SkillReview skill={data.name} evals={data.evals} />
    </>
  );
}
