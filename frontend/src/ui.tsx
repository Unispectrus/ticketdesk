import type { ReactNode } from "react";

export const fmt = (iso: string) => new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });

export function Badge({ kind, children }: { kind: string; children: ReactNode }) {
  return <span className={`badge b-${kind}`}>{children}</span>;
}
