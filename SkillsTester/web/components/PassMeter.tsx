import { pct } from "@/lib/data";

export function PassMeter({
  label,
  passed,
  total,
  color,
}: {
  label: string;
  passed: number;
  total: number;
  color: string;
}) {
  const value = pct(passed, total);
  return (
    <div
      className="meter-row"
      title={`${label}: ${passed}/${total} assertions passed (${value}%)`}
    >
      <span className="meter-label">{label}</span>
      <span className="meter-track">
        <span
          className="meter-fill"
          style={{ width: `${value}%`, background: color }}
        />
      </span>
      <span className="meter-value tnum">
        {passed}/{total} · {value}%
      </span>
    </div>
  );
}

export function ConfigLegend() {
  return (
    <div className="legend">
      <span>
        <span className="swatch" style={{ background: "var(--series-1)" }} />
        With skill
      </span>
      <span>
        <span className="swatch" style={{ background: "var(--series-2)" }} />
        Baseline (no skill)
      </span>
    </div>
  );
}
