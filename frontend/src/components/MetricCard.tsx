import type { ReactNode } from "react";

export function MetricCard({
  icon,
  label,
  trend,
  value,
}: {
  icon: ReactNode;
  label: string;
  trend: string;
  value: string;
}) {
  return (
    <article className="metric-card">
      <div className="metric-card__top">
        <span className="metric-card__icon" aria-hidden="true">
          {icon}
        </span>
        <span className="metric-card__trend">{trend}</span>
      </div>
      <strong>{value}</strong>
      <span>{label}</span>
    </article>
  );
}
