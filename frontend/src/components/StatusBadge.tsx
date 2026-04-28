import type { ReactNode } from "react";

type StatusTone = "ok" | "warning" | "neutral";

export function StatusBadge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: StatusTone;
}) {
  return <span className={`status-badge status-badge--${tone}`}>{children}</span>;
}
